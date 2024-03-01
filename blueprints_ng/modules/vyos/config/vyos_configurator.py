from __future__ import annotations

from typing import List

from pydantic import Field

from blueprints_ng.ansible_builder import AnsiblePlaybookBuilder, AnsibleTask
from blueprints_ng.resources import VmResourceAnsibleConfiguration
from blueprints_ng.utils import rel_path

class AnsibleVyOSConfigTask(AnsibleTask):
    lines: List[str] = Field(default=[])
    save: str = Field(default='yes')


class VmVyOSConfigurator(VmResourceAnsibleConfiguration):
    """
    This class is an example for an Ansible configurator for a VM

    The fields in this class will be saved to the DB and can be used to customize the configuration at runtime
    """

    def dump_playbook(self) -> str:
        """
        This method need to be implemented, it should return the Ansible playbook as a string
        """

        # While not mandatory it is recommended to use AnsiblePlaybookBuilder to create the playbook
        ansible_builder = AnsiblePlaybookBuilder("Playbook ExampleVmUbuntuConfigurator")

        # Set the playbook variables (can be done anywhere in this method, but it needs to be before the build)
        ansible_builder.set_var("ansible_python_interpreter", "/usr/bin/python3")
        ansible_builder.set_var("ansible_network_os", "vyos")
        ansible_builder.set_var("ansible_connection", "network_cli")

        config_task = AnsibleVyOSConfigTask(lines=["set interface ethernet eth0 description 'Management Network'"])
        ansible_builder.add_task('Description of eth0', 'vyos.vyos.vyos_config', config_task)

        data_config_task = self.setup_data_int_task()
        ansible_builder.add_task('Setup Data interfaces', 'vyos.vyos.vyos_config', data_config_task)

        loopback_ipaddr = "10.200." + str(self.vm_resource.area%256) + ".1/32"
        config_loopback_task = AnsibleVyOSConfigTask(lines=[f"set interfaces loopback lo address {loopback_ipaddr}"])
        ansible_builder.add_task('Loopbback int setup', 'vyos.vyos.vyos_config', config_loopback_task)

        # Build the playbook and return it
        return ansible_builder.build()

    def setup_data_int_task(self) -> AnsibleTask:
        data_int_task: AnsibleVyOSConfigTask
        lines = []

        interface_index = 1  # STARTING From 1 because management interface is always present and called eth0
        # This code works because vyos create sequential interfaces starting from eth0, eth1, eth2, ..., ethN


        for network_name, interface in self.vm_resource.network_interfaces.items():
            if self.vm_resource.management_network == network_name:
                continue
            # Getting prefix length
            prefix_length = interface.fixed.get_prefix()
            interface_address = interface.fixed.ip

            # NOTE: the ip address is got by get IP address, but OSM is not reporting netmask! setting /24 as default
            if interface_address is None:
                lines.append("set interfaces ethernet eth{} address dhcp".format(interface_index))
            else:
                lines.append("set interfaces ethernet eth{} address {}/{}".format(interface_index, interface_address,
                                                                                  prefix_length))
            lines.append("set interfaces ethernet eth{} description \'{}\'".format(interface_index, self.vm_resource.id))
            lines.append("set interfaces ethernet eth{} duplex auto".format(interface_index))
            lines.append("set interfaces ethernet eth{} speed auto".format(interface_index))
            # MAX supported MTU is 1450 by OPENSTACK
            lines.append("set interfaces ethernet eth{} mtu 1450".format(interface_index))
            interface_index = interface_index + 1

        return AnsibleVyOSConfigTask(lines=lines)
