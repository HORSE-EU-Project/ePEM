from __future__ import annotations

from typing import List, Optional

from blueprints.blue_5g_base.blueprint_5g_base_beta import SstConvertion
from pydantic import Field

from blueprints.blue_5g_base.models import Create5gModel
from blueprints.blue_5g_base.models.blue_5g_model import SubDataNets, SubSliceProfiles, SubArea
from models.base_model import NFVCLBaseModel
from utils.log import create_logger

logger = create_logger('BlueSDCoreValuesConverter')


# Models are incomplete, generated from the example values.yaml

class Images(NFVCLBaseModel):
    repository: str


class Kafka(NFVCLBaseModel):
    deploy: bool


class ReadinessProbe(NFVCLBaseModel):
    timeout_seconds: int = Field(..., alias='timeoutSeconds')


class LivenessProbe(NFVCLBaseModel):
    timeout_seconds: int = Field(..., alias='timeoutSeconds')


class Persistence(NFVCLBaseModel):
    enabled: bool


class Mongodb(NFVCLBaseModel):
    readiness_probe: ReadinessProbe = Field(..., alias='readinessProbe')
    liveness_probe: LivenessProbe = Field(..., alias='livenessProbe')
    use_password: bool = Field(..., alias='usePassword')
    persistence: Persistence
    architecture: str
    replica_count: int = Field(..., alias='replicaCount')


class Resources(NFVCLBaseModel):
    enabled: bool


class Mongodb1(NFVCLBaseModel):
    name: str
    url: str


class ManagedByConfigPod(NFVCLBaseModel):
    enabled: bool


class Sctplb(NFVCLBaseModel):
    deploy: bool


class Upfadapter(NFVCLBaseModel):
    deploy: bool


class Metricfunc(NFVCLBaseModel):
    deploy: bool
    service_type: str = Field(..., alias='serviceType')


class Webui(NFVCLBaseModel):
    service_type: str = Field(..., alias='serviceType')


class Configuration(NFVCLBaseModel):
    enable_db_store: bool = Field(..., alias='enableDBStore')


class AmfcfgConf(NFVCLBaseModel):
    configuration: Configuration


class CfgFiles(NFVCLBaseModel):
    amfcfg_conf: AmfcfgConf = Field(..., alias='amfcfg.conf')


class Amf(NFVCLBaseModel):
    service_type: str = Field(..., alias='serviceType')
    cfg_files: CfgFiles = Field(..., alias='cfgFiles')


class Configuration1(NFVCLBaseModel):
    enable_db_store: bool = Field(..., alias='enableDBStore')


class SmfcfgConf(NFVCLBaseModel):
    configuration: Configuration1


class SMFCfgFiles(NFVCLBaseModel):
    smfcfg_conf: SmfcfgConf = Field(..., alias='smfcfg.conf')


class Smf(NFVCLBaseModel):
    service_type: str = Field(..., alias='serviceType')
    cfg_files: SMFCfgFiles = Field(..., alias='cfgFiles')


class Configuration2(NFVCLBaseModel):
    mongo_db_stream_enable: bool = Field(..., alias='mongoDBStreamEnable')
    nf_profile_expiry_enable: bool = Field(..., alias='nfProfileExpiryEnable')
    nf_keep_alive_time: int = Field(..., alias='nfKeepAliveTime')


class NrfcfgConf(NFVCLBaseModel):
    configuration: Configuration2


class CfgFiles2(NFVCLBaseModel):
    nrfcfg_conf: NrfcfgConf = Field(..., alias='nrfcfg.conf')


class Nrf(NFVCLBaseModel):
    service_type: str = Field(..., alias='serviceType')
    cfg_files: CfgFiles2 = Field(..., alias='cfgFiles')


class Config(NFVCLBaseModel):
    mongodb: Mongodb1
    managed_by_config_pod: ManagedByConfigPod = Field(..., alias='managedByConfigPod')
    sctplb: Sctplb
    upfadapter: Upfadapter
    metricfunc: Metricfunc
    webui: Webui
    amf: Amf
    smf: Smf
    nrf: Nrf


class Field5gControlPlane(NFVCLBaseModel):
    enable5_g: bool = Field(..., alias='enable5G')
    images: Images
    kafka: Kafka
    mongodb: Mongodb
    resources: Resources
    config: Config


class Images1(NFVCLBaseModel):
    repository: str
    pull_policy: Optional[str] = Field(default=None, alias='pullPolicy')


class Info(NFVCLBaseModel):
    version: str


class SubProvisionEndpt(NFVCLBaseModel):
    addr: str


class Subscriber(NFVCLBaseModel):
    ue_id_start: str = Field(..., alias='ueId-start')
    ue_id_end: str = Field(..., alias='ueId-end')
    plmn_id: str = Field(..., alias='plmnId')
    opc: str
    op: str
    key: str
    sequence_number: str = Field(..., alias='sequenceNumber')


class TrafficClass(NFVCLBaseModel):
    name: str
    qci: int
    arp: int
    pdb: int
    pelr: int


class UeDnnQos(NFVCLBaseModel):
    dnn_mbr_downlink: int = Field(..., alias='dnn-mbr-downlink')
    dnn_mbr_uplink: int = Field(..., alias='dnn-mbr-uplink')
    bitrate_unit: str = Field(..., alias='bitrate-unit')
    traffic_class: TrafficClass = Field(..., alias='traffic-class')


class IpDomainExpanded(NFVCLBaseModel):
    dnn: str
    dns_primary: str = Field(..., alias='dns-primary')
    mtu: int
    ue_ip_pool: str = Field(..., alias='ue-ip-pool')
    ue_dnn_qos: UeDnnQos = Field(..., alias='ue-dnn-qos')


class DeviceGroup(NFVCLBaseModel):
    name: str
    imsis: List[str]
    ip_domain_name: str = Field(..., alias='ip-domain-name')
    ip_domain_expanded: IpDomainExpanded = Field(..., alias='ip-domain-expanded')
    site_info: str = Field(..., alias='site-info')


class SliceId(NFVCLBaseModel):
    sd: str
    sst: int


class ApplicationFilteringRule(NFVCLBaseModel):
    rule_name: str = Field(..., alias='rule-name')
    priority: int
    action: str
    endpoint: str


class GNodeB(NFVCLBaseModel):
    name: str
    tac: int


class Plmn(NFVCLBaseModel):
    mcc: str
    mnc: str


class Upf(NFVCLBaseModel):
    upf_name: str = Field(..., alias='upf-name')
    upf_port: int = Field(..., alias='upf-port')


class SiteInfo(NFVCLBaseModel):
    g_node_bs: List[GNodeB] = Field(..., alias='gNodeBs')
    plmn: Plmn
    site_name: str = Field(..., alias='site-name')
    upf: Upf


class NetworkSlice(NFVCLBaseModel):
    name: str
    slice_id: SliceId = Field(..., alias='slice-id')
    site_device_group: List[str] = Field(..., alias='site-device-group')
    application_filtering_rules: List[ApplicationFilteringRule] = Field(
        ..., alias='application-filtering-rules'
    )
    site_info: SiteInfo = Field(..., alias='site-info')


class SimAppYamlConfiguration(NFVCLBaseModel):
    provision_network_slice: bool = Field(..., alias='provision-network-slice')
    sub_provision_endpt: SubProvisionEndpt = Field(..., alias='sub-provision-endpt')
    subscribers: List[Subscriber]
    device_groups: List[DeviceGroup] = Field(..., alias='device-groups')
    network_slices: List[NetworkSlice] = Field(..., alias='network-slices')

    def __get_areas_with_slice(self, generic_model: Create5gModel, slice_profile: SubSliceProfiles) -> List[SubArea]:
        area_list: List[SubArea] = []
        for area in generic_model.areas:
            for slice in area.slices:
                if slice.sliceId == slice_profile.sliceId:
                    area_list.append(area)
        return area_list

    def from_generic_5g_model(self, generic_model: Create5gModel):
        self.device_groups = []
        self.network_slices = []
        self.subscribers = []

        for generic_slice in generic_model.config.sliceProfiles:

            # Prechecks TODO need to be moved
            if len(generic_slice.dnnList) != 1:
                raise ValueError("config.sliceProfiles[].dnnList need to be of size 1")

            slice_name = f"slice_{generic_slice.sliceId}"
            device_group_name = f"device-group-{slice_name}"
            site_name = f"site-{slice_name}"

            # TODO check size, should be 1
            data_net_for_this_slice: SubDataNets = list(filter(lambda x: x.dnn == generic_slice.dnnList[0], generic_model.config.network_endpoints.data_nets))[0]

            if data_net_for_this_slice.downlinkAmbr.split(" ")[1].lower() != data_net_for_this_slice.uplinkAmbr.split(" ")[1].lower():
                raise ValueError("SD-Core does not support different units for downlinkAmbr and uplinkAmbr")
            if data_net_for_this_slice.downlinkAmbr.split(" ")[1].lower() not in ["mbps", "gbps", "kbps"]:
                raise ValueError("Unsupported unit for downlinkAmbr/uplinkAmbr, use one of [mbps, gbps, kbps]")

            logger.warning("config.network_endpoints.data_nets[].default5qi IGNORED")
            # logger.warning("config.sliceProfiles[].sliceType IGNORED")
            logger.warning("config.sliceProfiles[].profileParams IGNORED")
            logger.warning("config.sliceProfiles[].locationConstraints IGNORED")
            logger.warning("config.sliceProfiles[].enabledUEList IGNORED, if a subscriber have a slice in snssai it will be added to the UE list for that slice")
            logger.warning("config.subscribers[].authenticationMethod IGNORED")
            logger.warning("config.subscribers[].authenticationManagementField IGNORED")
            logger.warning("config.subscribers[].snssai[].sliceType IGNORED")
            logger.warning("config.subscribers[].snssai[].pduSessionIds IGNORED")
            logger.warning("config.subscribers[].snssai[].default_slice IGNORED")

            new_network_slice = NetworkSlice(
                name=slice_name,
                slice_id=SliceId(
                    sd=generic_slice.sliceId,
                    sst=SstConvertion.sstType[generic_slice.sliceType]
                ),
                site_device_group=[device_group_name],
                application_filtering_rules=[ApplicationFilteringRule(  # TODO read this from config
                    rule_name="ALLOW-ALL",
                    priority=250,
                    action="permit",
                    endpoint="0.0.0.0/0"
                )],
                site_info=SiteInfo(
                    g_node_bs=list(map(lambda x: GNodeB(name=f"gnb{x.id}", tac=x.id), self.__get_areas_with_slice(generic_model, generic_slice))),
                    plmn=Plmn(
                        mcc=generic_model.config.plmn[:3],
                        mnc=generic_model.config.plmn[3:]
                    ),
                    site_name=site_name,
                    upf=Upf(
                        upf_name=f"{site_name}-upf",  # Is replaced in blueprint
                        upf_port=8805
                    )
                )
            )
            new_device_group = DeviceGroup(
                name=device_group_name,
                imsis=[],
                ip_domain_name="pool1",  # TODO what is this used for?
                ip_domain_expanded=IpDomainExpanded(
                    dnn=data_net_for_this_slice.dnn,
                    dns_primary=data_net_for_this_slice.dns,
                    mtu=1410,
                    ue_ip_pool=data_net_for_this_slice.pools[0].cidr,  # TODO multiple pools? what else other than cidr?
                    ue_dnn_qos=UeDnnQos(
                        dnn_mbr_downlink=int(data_net_for_this_slice.downlinkAmbr.split(" ")[0]),
                        dnn_mbr_uplink=int(data_net_for_this_slice.uplinkAmbr.split(" ")[0]),
                        bitrate_unit=data_net_for_this_slice.downlinkAmbr.split(" ")[1].lower(),  # Can be gbps, mbps, kbps
                        traffic_class=TrafficClass(  # TODO read this from config
                            name="platinum",
                            qci=9,
                            arp=6,
                            pdb=300,
                            pelr=6
                        )
                    )
                ),
                site_info=site_name
            )
            self.device_groups.append(new_device_group)
            self.network_slices.append(new_network_slice)

        for generic_subscriber in generic_model.config.subscribers:
            self.subscribers.append(Subscriber(
                ue_id_start=generic_subscriber.imsi,
                ue_id_end=generic_subscriber.imsi,
                plmn_id=generic_model.config.plmn,
                opc=generic_subscriber.opc,
                op="",
                key=generic_subscriber.k,
                sequence_number="16f3b3f70fc2"  # TODO where should we get this from
            ))
            for generic_subscriber_snssai in generic_subscriber.snssai:
                # TODO check size, should be 1
                matching_slice: NetworkSlice = list(filter(lambda x: x.slice_id.sd == generic_subscriber_snssai.sliceId, self.network_slices))[0]
                # TODO check size, should be 1
                # TODO need to be changed if we implement DeviceGroup configuration support (matching_slice.site_device_group)
                matching_device_groups: DeviceGroup = list(filter(lambda x: x.name == matching_slice.site_device_group[0], self.device_groups))[0]
                matching_device_groups.imsis.append(generic_subscriber.imsi)


class SimAppYaml(NFVCLBaseModel):
    info: Optional[Info] = Field(default=None)
    configuration: Optional[SimAppYamlConfiguration] = Field(default=None)


class SimAppCfgFiles(NFVCLBaseModel):
    simapp_yaml: SimAppYaml = Field(..., alias='simapp.yaml')


class SimApp(NFVCLBaseModel):
    cfg_files: SimAppCfgFiles = Field(..., alias='cfgFiles')


class OmecSubProvisionConfig(NFVCLBaseModel):
    simapp: SimApp


class OmecSubProvision(NFVCLBaseModel):
    enable: bool
    images: Images1
    config: OmecSubProvisionConfig


class OmecControlPlane(NFVCLBaseModel):
    enable4g: bool = Field(..., alias='enable4G')


class OmecUserPlane(NFVCLBaseModel):
    enable: bool


class Field5gRanSim(NFVCLBaseModel):
    enable: bool


class SDCoreValuesModel(NFVCLBaseModel):
    field_5g_control_plane: Field5gControlPlane = Field(..., alias='5g-control-plane')
    omec_sub_provision: OmecSubProvision = Field(..., alias='omec-sub-provision')
    omec_control_plane: OmecControlPlane = Field(..., alias='omec-control-plane')
    omec_user_plane: OmecUserPlane = Field(..., alias='omec-user-plane')
    field_5g_ran_sim: Field5gRanSim = Field(..., alias='5g-ran-sim')
