from enum import Enum
from ipaddress import IPv4Network
from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field, conlist
from models.virtual_link_desc import VirtLinkDescr


class Cni(Enum):
    flannel = 'flannel'
    calico = 'calico'


class LbType(Enum):
    layer2 = 'layer2'
    layer3 = 'layer3'


class LBPool(BaseModel):
    mode: LbType = Field(
        'layer2', description='Operating mode of Metal-LB. Default Layer-2.'
    )
    net_name: str = Field(
        ..., description='name of the network in the topology'
    )
    ip_start: Optional[str]
    ip_end: Optional[str]
    range_length: Optional[int] = Field(
        None,
        description='Number of IPv4 addresses to reserved if no ip start and end are passed. Default 10 addresses.',
    )

    class Config:
        use_enum_values = True


class K8sNetworkEndpoints(BaseModel):
    mgt: str = Field(
        ..., description='name of the topology network to be used for management'
    )
    data_nets: List[LBPool] = Field(description='topology networks to be used by the load balancer', min_items=1)


class VMFlavors(BaseModel):
    memory_mb: str = Field(8192, alias='memory-mb')
    storage_gb: str = Field(12, alias='storage-gb')
    vcpu_count: str = Field(4, alias='vcpu-count')


class K8sNsdInterfaceDesc(BaseModel):
    nsd_id: str
    nsd_name: str
    vld: List[VirtLinkDescr]


class K8sAreaInfo(BaseModel):
    id: int
    core: Optional[bool] = False
    workers_replica: int
    worker_flavor_override: Optional[VMFlavors]
    # TODO: We need to support multiple IPs when we have multiple replica for each area
    worker_mgt_int: Dict[str, K8sNsdInterfaceDesc] = Field(default={})
    worker_data_int: Dict[str, K8sNsdInterfaceDesc] = Field(default={})


class K8sConfig(BaseModel):
    version: Optional[str] = "1.24"
    cni: Optional[Cni] = "flannel"
    linkerd: Optional[dict]
    pod_network_cidr: Optional[IPv4Network] \
        = Field('10.254.0.0/16', description='K8s Pod network IPv4 cidr to init the cluster')
    network_endpoints: K8sNetworkEndpoints
    worker_flavors: VMFlavors = VMFlavors()
    master_flavors: VMFlavors = VMFlavors()
    nfvo_onboarded: bool = False
    core_area: K8sAreaInfo = Field(default=None, description="The core are of the cluster")
    controller_ip: str = Field(default="", description="The IP of the k8s controller or master")
    master_key_add_worker: str = Field(default="", description="The master key to be used by a worker to join the k8s cluster")
    master_credentials: str = Field(default="", description="The certificate of the admin, to allow k8s administration")

    class Config:
        use_enum_values = True


class K8sBlueprintCreate(BaseModel):
    type: Literal['K8s', 'K8sBeta']
    callbackURL: Optional[str] = Field(
        None,
        description='url that will be used to notify when the blueprint processing finishes',
    )
    config: K8sConfig
    areas: conlist(K8sAreaInfo, min_items=1) = Field(
        ...,
        description='list of areas to instantiate the Blueprint',
    )

    class Config:
        use_enum_values = True


class K8sBlueprintModel(K8sBlueprintCreate):
    """
    Model used to represent the K8s Blueprint instance. It EXTENDS the model for k8s blueprint creation
    K8sBlueprintCreate
    """
    blueprint_instance_id: str = Field(description="The blueprint ID generated when it has been instantiated")


class K8sBlueprintScale(BaseModel):
    callbackURL: Optional[str] = Field(
        None,
        description='URL that will be used to notify when the blueprint processing finishes',
    )
    operation: Literal['scale']
    add_areas: List[K8sAreaInfo]
    modify_areas: List[K8sAreaInfo]
    del_areas: List[K8sAreaInfo]

