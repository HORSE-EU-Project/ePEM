# NFVCL K8S APIs examples

## Plugin installation
/k8s/{cluster_id}/plugins

Some plugins are installed by default on K8S cluster generated by the NFVCL: Flannel, Openebs and MetalLb. In case
the cluster is onboarded from external there could be not installed plugins, or if in the creation request, 
the 'install_plugins' flag was set to zero there are no plugins installed.
There are some additional data (template_fill_data) that is needed by some plugins:
- Flannel needs the 'pod_network_cidr': the cidr of the cluster to be set in the CNI installation process
- MetalLB needs:
    - lb_ipaddresses: a list of the IP addresses to be added at the load balancer in auto-assign mode False.
    - lb_ipaddresses_auto: a list of the IP addresses to be added at the load balancer in auto-assign mode True.
    - lb_pools: a list of IP pools to be added at the load balancer in auto-assign mode True.
```
{
  "plugin_list": [
    "flannel"
  ],
  "template_fill_data": {
    "pod_network_cidr": "",
    "lb_ipaddresses": [],
    "lb_ipaddresses_auto": [],
    "lb_pools": []
  },
  "skip_plug_checks": false
}
```