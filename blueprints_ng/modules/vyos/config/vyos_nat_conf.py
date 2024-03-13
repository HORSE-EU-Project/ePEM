from __future__ import annotations
from blueprints.blue_vyos import VyOSDestNATRule, VyOSSourceNATRule, VyOS1to1NATRule
from models.blueprint_ng.vyos.vyos_models import AnsibleVyOSConfigTask, VyOSNATRuleAlreadyPresent, VyOSNATRuleNotFound
from blueprints_ng.ansible_builder import AnsiblePlaybookBuilder, AnsibleTask
from blueprints_ng.resources import VmResourceAnsibleConfiguration


class VmVyOSNatConfigurator(VmResourceAnsibleConfiguration):
    """
    This class is an example for an Ansible configurator for a VM

    The fields in this class will be saved to the DB and can be used to customize the configuration at runtime
    """

    def dump_playbook(self) -> str:
        """
        This method need to be implemented, it should return the Ansible playbook as a string
        """

        # While not mandatory, it is recommended to use AnsiblePlaybookBuilder to create the playbook
        ansible_builder = AnsiblePlaybookBuilder("Playbook VyOS NAT configuration")

        # Set the playbook variables (can be done anywhere in this method, but it needs to be before the build)
        ansible_builder.set_var("ansible_python_interpreter", "/usr/bin/python3")
        ansible_builder.set_var("ansible_network_os", "vyos")
        ansible_builder.set_var("ansible_connection", "network_cli")

        for name, task in self._task_list.items():
            ansible_builder.add_task(name, 'vyos.vyos.vyos_config', task)
        self.vm_resource.task_list = {}

        # Build the playbook and return it
        return ansible_builder.build()

    def add_dnat_rule(self, rule: VyOSDestNATRule):
        if rule.rule_number in self._nat_rules:
            raise VyOSNATRuleAlreadyPresent(f"Rule {rule.rule_number} is already present")
        else:
            self._setup_dnat_rule(rule)

    def _setup_dnat_rule(self, rule: VyOSDestNATRule):
        """
        Create instructions for ansible to set up a DNAT rule.
        Args:
            rule: DNAT rule to be set up in the VYOS instance
        """
        lines = []

        lines.append(f"set nat destination rule {rule.rule_number} inbound-interface {rule.inbound_interface}")
        lines.append(f"set nat destination rule {rule.rule_number} destination address {rule.virtual_ip}")
        lines.append(f"set nat destination rule {rule.rule_number} translation address {rule.real_destination_ip}")
        lines.append(f"set nat destination rule {rule.rule_number} description '{rule.description}'")

        self.vm_resource.nat_rules.append(rule.rule_number)
        self.vm_resource.applied_dnat_rules.append(rule)
        self.vm_resource.task_list.append(("DNAT rule {} creation", AnsibleVyOSConfigTask(lines=lines)))

    def add_snat_rule(self, rule: VyOSSourceNATRule):
        if rule.rule_number in self._nat_rules:
            raise VyOSNATRuleAlreadyPresent(f"Rule {rule.rule_number} is already present")
        else:
            self._setup_snat_rule(rule)

    def _setup_snat_rule(self, rule: VyOSSourceNATRule):
        """
        Create a task which will add the instructions to configure an SNAT rule on the router.
        Args:
            rule: SNAT rule to be set up in the VYOS instance
        """
        lines = []

        lines.append(f"set nat source rule {rule.rule_number} outbound-interface { rule.outbound_interface}")
        lines.append(f"set nat source rule {rule.rule_number} source address {rule.source_address}")
        lines.append(f"set nat source rule {rule.rule_number} translation address {rule.virtual_ip}")

        self.vm_resource.applied_snat_rules.append(rule)
        self.vm_resource.task_list.append((f"SNAT rule {rule.rule_number} creation", AnsibleVyOSConfigTask(lines=lines)))

    def add_1to1_rule(self, rule: VyOS1to1NATRule):
        if rule.rule_number in self._nat_rules:
            raise VyOSNATRuleAlreadyPresent(f"Rule {rule.rule_number} is already present")
        else:
            snat_rule = VyOSSourceNATRule.model_validate(rule)
            dnat_rule = VyOSDestNATRule.model_validate(rule)

            self._setup_snat_rule(snat_rule)
            self._setup_dnat_rule(dnat_rule)

    def delete_nat_rule(self, rule_number: int) -> None:
        """
        """
        if rule_number in self._nat_rules:
            raise VyOSNATRuleNotFound(f"Rule {rule_number} has not been found")

        for snat_rule in self._snat_rules:
            if snat_rule.rule_number == rule_number:
                self._delete_snat_rule(snat_rule)
                self.vm_resource.applied_snat_rules.remove(snat_rule)
        for dnat_rule in self._dnat_rules:
            if dnat_rule.rule_number == rule_number:
                self._delete_dnat_rule(dnat_rule)
                self.vm_resource.applied_dnat_rules.remove(dnat_rule)

    def _delete_snat_rule(self, rule: VyOSSourceNATRule):
        lines = []

        lines.append(f"del nat source rule {rule.rule_number}")
        self.vm_resource.applied_snat_rules.append(rule)
        self.vm_resource.task_list.append((f"SNAT rule {rule.rule_number} deletion", AnsibleVyOSConfigTask(lines=lines)))

    def _delete_dnat_rule(self, rule: VyOSSourceNATRule):
        lines = []

        lines.append(f"del nat destination rule {rule.rule_number}")
        self.vm_resource.applied_snat_rules.append(rule)
        self.vm_resource.ask_list.append((f"DNAT rule {rule.rule_number} deletion", AnsibleVyOSConfigTask(lines=lines)))