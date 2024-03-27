import time
from pathlib import Path
from typing import List, Dict

import paramiko
from openstack.compute.v2.flavor import Flavor
from openstack.compute.v2.server import Server
from openstack.connection import Connection
from openstack.network.v2.network import Network
from openstack.network.v2.port import Port
from openstack.network.v2.subnet import Subnet

from blueprints_ng.ansible_builder import AnsiblePlaybookBuilder
from blueprints_ng.cloudinit_builder import CloudInit
from blueprints_ng.providers.configurators.ansible_utils import run_ansible_playbook
from blueprints_ng.providers.virtualization.virtualization_provider_interface import VirtualizationProviderException, \
    VirtualizationProviderInterface, VirtualizationProviderData
from blueprints_ng.resources import VmResourceAnsibleConfiguration, VmResourceNetworkInterface, \
    VmResourceNetworkInterfaceAddress, VmResource, VmResourceConfiguration, NetResource
from models.vim import VimModel
from utils.openstack.openstack_client import OpenStackClient


class VirtualizationProviderDataOpenstack(VirtualizationProviderData):
    os_dict: Dict[str, str] = {}
    flavors: List[str] = []
    networks: List[str] = []
    subnets: List[str] = []


class VirtualizationProviderOpenstackException(VirtualizationProviderException):
    pass


class VmInfoGathererConfigurator(VmResourceAnsibleConfiguration):
    """
    This configurator is used to gather information about the VM
    """

    def dump_playbook(self) -> str:
        ansible_playbook_builder = AnsiblePlaybookBuilder("Info gathering")

        # Get interface name -> mac address correlation
        # https://unix.stackexchange.com/a/445913
        ansible_playbook_builder.add_run_command_and_gather_output_tasks(
            R"""find /sys/class/net -mindepth 1 -maxdepth 1 ! -name lo -printf "%P: " -execdir cat {}/address \;""",
            "interfaces_mac"
        )

        return ansible_playbook_builder.build()


os_clients_dict: Dict[int, OpenStackClient] = {}


def get_os_client_from_vim(vim: VimModel, area: int):
    global os_clients_dict

    if area not in os_clients_dict:
        os_clients_dict[area] = OpenStackClient(vim)

    return os_clients_dict[area].client


class VirtualizationProviderOpenstack(VirtualizationProviderInterface):
    def init(self):
        self.data: VirtualizationProviderDataOpenstack = VirtualizationProviderDataOpenstack()
        vim = self.topology.get_vim_from_area_id_model(self.area)
        self.conn = get_os_client_from_vim(vim, self.area)
        self.vim_need_floating_ip = vim.config.use_floating_ip

    def __create_image_from_url(self, vm_resource: VmResource):
        image_attrs = {
            'name': vm_resource.image.name,
            'disk_format': 'qcow2',
            'container_format': 'bare',
            'visibility': 'public',
        }
        image = self.conn.image.create_image(**image_attrs)
        self.conn.image.import_image(image, method="web-download", uri=vm_resource.image.url)
        self.conn.wait_for_image(image)
        return image

    def create_vm(self, vm_resource: VmResource):
        self.logger.info(f"Creating VM {vm_resource.name}")
        image = self.conn.get_image(vm_resource.image.name)
        if image is None:
            if vm_resource.image.url:
                self.logger.info(f"Image {vm_resource.image.name} not found on VIM, downloading from {vm_resource.image.url}")
                image = self.__create_image_from_url(vm_resource)
                self.logger.info(f"Image {vm_resource.image.name} download completed")
            else:
                raise VirtualizationProviderOpenstackException(f"Image >{vm_resource.image.name}< not found")

        flavor_name = f"Flavor_{vm_resource.name}"
        if flavor_name in self.data.flavors:
            flavor = self.conn.get_flavor(flavor_name)
            if flavor is None:
                raise VirtualizationProviderOpenstackException(f"Flavor '{flavor_name}' should be present but is None")
        else:
            flavor: Flavor = self.conn.create_flavor(
                flavor_name,
                vm_resource.flavor.memory_mb,
                vm_resource.flavor.vcpu_count,
                vm_resource.flavor.storage_gb,
                is_public=False
            )
            self.data.flavors.append(flavor_name)

        cloudin = CloudInit(password=vm_resource.password).build_cloud_config()
        self.logger.debug(f"Cloud config:\n{cloudin}")

        # Create a list with all the network interfaces that need to be added to the new VM
        networks = [vm_resource.management_network]
        networks.extend(vm_resource.additional_networks)

        # The floating IP should be requested if the VIM require it or if explicitly requested in the blueprint
        auto_ip = self.vim_need_floating_ip or vm_resource.require_floating_ip

        # Get the floating ip network name
        floating_ip_net = None
        if auto_ip:
            float_ip_nets: List[Network] = self.conn.get_external_ipv4_floating_networks()
            if len(float_ip_nets) == 1:
                floating_ip_net = float_ip_nets[0].name
            else:
                # TODO instead of raising an exception we should add a way to set the floating ip net in the vim
                raise VirtualizationProviderOpenstackException("Multiple floating ip networks found")

        # Create the VM and wait for completion
        server_obj: Server = self.conn.create_server(
            vm_resource.name,
            image=image,
            flavor=flavor,
            wait=True,
            auto_ip=auto_ip,
            nat_destination=vm_resource.management_network,
            ip_pool=floating_ip_net,
            network=networks,
            userdata=cloudin
        )

        # Don't put code that may crash here, we first need to register the vm_resource server_obj id correlation in the DB
        # This allows to delete a blueprint that crash during the create_vm execution

        # Register the VM in the provider data, this is needed to be able to delete it using only the vm_resource
        self.data.os_dict[vm_resource.id] = server_obj.id
        self.blueprint.to_db()

        # Getting detailed info about the networks attached to the machine
        subnet_detailed = self.__get_network_details(self.conn, networks)
        # Parse the OS output and create a structured network_interfaces dictionary
        self.__parse_os_addresses(vm_resource, server_obj.addresses, subnet_detailed)

        # Find the IP to use for configuring the VM, floating if present or the fixed one from the management interface if not
        if server_obj.access_ipv4 and len(server_obj.access_ipv4) > 0:
            vm_resource.access_ip = server_obj.access_ipv4
        else:
            vm_resource.access_ip = vm_resource.network_interfaces[vm_resource.management_network].fixed.ip

        # Disable port security on every port
        server_ports: List[Port] = self.conn.list_ports(filters={"device_id": server_obj.id})
        if len(server_ports) != len(networks):
            raise VirtualizationProviderOpenstackException(f"Mismatch in number of request network interface and ports, query: device_id={server_obj.id}")
        for port in server_ports:
            self.__disable_port_security(self.conn, port.id)

        # Run an Ansible playbook to gather information about the newly created VM
        self.__gather_info_from_vm(vm_resource)

        # The VM is now created
        vm_resource.created = True

        self.logger.success(f"Creating VM {vm_resource.name} finished")
        self.blueprint.to_db()

    def create_net(self, net_resource: NetResource):
        self.logger.info(f"Creating NET {net_resource.name}")

        if self.conn.get_network(net_resource.name):
            raise VirtualizationProviderOpenstackException(f"Network {net_resource.name} already exist")
        if self.conn.list_subnets(filters={"cidr": net_resource.cidr}):
            raise VirtualizationProviderOpenstackException(f"Subnet with cidr {net_resource.cidr} already exist")

        network: Network = self.conn.create_network(net_resource.name, port_security_enabled=False)
        subnet: Subnet = self.conn.create_subnet(
            network.id,
            cidr=net_resource.cidr,
            enable_dhcp=True,
            disable_gateway_ip=True
        )

        self.data.subnets.append(subnet.id)
        self.data.networks.append(network.id)

        self.logger.success(f"Creating NET {net_resource.name} finished")

    def __gather_info_from_vm(self, vm_resource: VmResource):
        self.logger.info(f"Starting VM info gathering")

        facts = self.__configure_vm_ansible(VmInfoGathererConfigurator(vm_resource=vm_resource))

        mac_name_dict = {}

        interfaces_mac: str = facts["interfaces_mac"]
        for interface_line in interfaces_mac.strip().splitlines():
            interface_line_splitted = interface_line.split(": ")
            # Skip if the interface doesn't have a mac address
            if len(interface_line_splitted) != 2:
                continue
            name = interface_line_splitted[0].strip()
            mac = interface_line_splitted[1].strip()
            mac_name_dict[mac] = name

        for value in vm_resource.network_interfaces.values():
            value.fixed.interface_name = mac_name_dict[value.fixed.mac]
            if value.floating:
                value.floating.interface_name = mac_name_dict[value.floating.mac]

        self.logger.info(f"Ended VM info gathering")

    def configure_vm(self, vm_resource_configuration: VmResourceConfiguration) -> dict:
        # The parent method checks if the resource is created and throw an exception if not
        super().configure_vm(vm_resource_configuration)
        self.logger.info(f"Configuring VM {vm_resource_configuration.vm_resource.name}")

        configurator_facts = None

        # Different handlers for different configuration types
        if isinstance(vm_resource_configuration, VmResourceAnsibleConfiguration):  # VmResourceNativeConfiguration
            configurator_facts = self.__configure_vm_ansible(vm_resource_configuration)

        self.logger.success(f"Configuring VM {vm_resource_configuration.vm_resource.name} finished")
        self.blueprint.to_db()

        return configurator_facts

    def __wait_for_ssh_to_be_ready(self, host: str, port: int, user: str, passwd: str, timeout: int, retry_interval: float) -> bool:
        self.logger.debug(f"Starting SSH connection to {host}:{port} as user <{user}> and passwd <{passwd}>. Timeout is {timeout}, retry interval is {retry_interval}")
        client = paramiko.client.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        timeout_start = time.time()
        while time.time() < timeout_start + timeout:
            try:
                client.connect(host, port, username=user, password=passwd, allow_agent=False, look_for_keys=False)
                self.logger.debug('SSH transport is available!')
                client.close()
                return True
            except paramiko.ssh_exception.SSHException as e:
                # socket is open, but not SSH service responded
                self.logger.debug(f"Socket is open, but not SSH service responded: {e}")
                time.sleep(retry_interval)
                continue

            except paramiko.ssh_exception.NoValidConnectionsError as e:
                self.logger.debug('SSH transport is not ready...')
                time.sleep(retry_interval)
                continue
        return False

    def __configure_vm_ansible(self, vm_resource_configuration: VmResourceAnsibleConfiguration) -> dict:
        nfvcl_tmp_dir = Path("/tmp/nfvcl/playbook")
        nfvcl_tmp_dir.mkdir(exist_ok=True, parents=True)

        playbook_str = vm_resource_configuration.dump_playbook()

        with open(Path(nfvcl_tmp_dir, f"{self.blueprint.id}_{vm_resource_configuration.vm_resource.name}.yml"), "w+") as f:
            f.write(playbook_str)

        # Wait for SSH to be ready, this is needed because sometimes cloudinit is still not finished and the server doesn't allow password connections
        self.__wait_for_ssh_to_be_ready(
            vm_resource_configuration.vm_resource.access_ip,
            22,
            vm_resource_configuration.vm_resource.username,
            vm_resource_configuration.vm_resource.password,
            300,
            5
        )

        ansible_runner_result, fact_cache = run_ansible_playbook(
            vm_resource_configuration.vm_resource.access_ip,
            vm_resource_configuration.vm_resource.username,
            vm_resource_configuration.vm_resource.password,
            playbook_str,
            self.logger
        )

        if ansible_runner_result.status == "failed":
            raise VirtualizationProviderOpenstackException("Error running ansible configurator")

        return fact_cache

    def destroy_vm(self, vm_resource: VmResource):
        self.logger.info(f"Destroying VM {vm_resource.name}")
        if vm_resource.id in self.data.os_dict:
            self.conn.delete_server(self.data.os_dict[vm_resource.id], wait=True)
        else:
            self.logger.warning(f"Unable to find VM id for resource '{vm_resource.id}' with name '{vm_resource.name}', manually check on VIM")
        self.logger.success(f"Destroying VM {vm_resource.name} finished")
        self.blueprint.to_db()

    def final_cleanup(self):
        # Delete flavors
        for flavor_name in self.data.flavors:
            self.conn.delete_flavor(flavor_name)
        # Delete subnets
        for subnet_id in self.data.subnets:
            self.conn.delete_subnet(subnet_id)
        # Delete networks
        for network_id in self.data.networks:
            self.conn.delete_network(network_id)

    def __parse_os_addresses(self, vm_resource: VmResource, addresses, subnet_details: Dict[str, Subnet]):
        for network_name, network_info in addresses.items():
            fixed = None
            floating = None
            for address in network_info:
                if address["OS-EXT-IPS:type"] == "fixed":
                    fixed = VmResourceNetworkInterfaceAddress(ip=address["addr"], mac=address["OS-EXT-IPS-MAC:mac_addr"], cidr=subnet_details[network_name].cidr)
                if address["OS-EXT-IPS:type"] == "floating":
                    floating = VmResourceNetworkInterfaceAddress(ip=address["addr"], mac=address["OS-EXT-IPS-MAC:mac_addr"], cidr=subnet_details[network_name].cidr)
            vm_resource.network_interfaces[network_name] = VmResourceNetworkInterface(fixed=fixed, floating=floating)

    def __disable_port_security(self, conn: Connection, port_id):
        try:
            return conn.update_port(port_id, port_security_enabled=False, security_groups=[])
        except Exception as e:
            raise e

    def __get_network_details(self, connection: Connection, network_names: List[str]) -> Dict[str, Subnet]:
        """
        Given the network names, it retrieves the details of the first subnet of every network
        Args:
            connection: The connection to openstack
            network_names: The network names

        Returns:
            A list containing the details of every FIRST subnet of the netowrk
        """
        subnet_detail_list = {}
        for network_name in network_names:
            network_detail: Network = connection.get_network(network_name)
            subnet_detail_list[network_name] = connection.get_subnet(network_detail.subnet_ids[0])
        return subnet_detail_list