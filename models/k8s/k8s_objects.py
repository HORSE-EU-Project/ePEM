from enum import Enum
from typing import List, Optional

from pydantic import Field, field_validator

from models.base_model import NFVCLBaseModel


class K8sServiceType(Enum):
    """
    https://kubernetes.io/docs/concepts/services-networking/service/#publishing-services-service-types
    """
    ClusterIP = "ClusterIP"
    NodePort = "NodePort"
    LoadBalancer = "LoadBalancer"
    ExternalName = "ExternalName"


class K8sServicePortProtocol(Enum):
    """
    https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.28/#serviceport-v1-core
    """
    TCP = "TCP"
    UDP = "UDP"
    SCTP = "SCTP"


class K8sServicePort(NFVCLBaseModel):
    """
    https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.28/#serviceport-v1-core
    """
    name: str = Field()
    port: int = Field()
    protocol: K8sServicePortProtocol = Field()
    targetPort: int | str = Field()


class K8sService(NFVCLBaseModel):
    """
    https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.28/#service-v1-core
    """
    type: K8sServiceType = Field()
    name: str = Field()
    cluster_ip: Optional[str] = Field(default=None)
    external_ip: Optional[List[str]] = Field(default=None)
    ports: List[K8sServicePort] = Field(default=[])

    @field_validator('cluster_ip', 'external_ip')
    def none_str_to_none(cls, v):
        if v == 'None':
            return None
        return v
