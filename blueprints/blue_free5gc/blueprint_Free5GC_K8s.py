from blueprints.blueprint import BlueprintBase
from blueprints.blue_5g_base import Blue5GBase
from blueprints.blue_free5gc import free5GC_default_config
from nfvo import sol006_VNFbuilder, sol006_NSD_builder, get_kdu_services, get_ns_vld_ip
from blueprints.blue_free5gc.configurators import Configurator_Free5GC, Configurator_Free5GC_User, \
    Configurator_Free5GC_Core
import copy
from main import *

db = persistency.DB()
nbiUtil = NbiUtil(username=osm_user, password=osm_passwd, project=osm_proj, osm_ip=osm_ip, osm_port=osm_port)

# create logger
logger = create_logger('Free5GC_K8s')

# if mcc == None: mcc = self.conf['plmn'][:3]
# if mnc == None: mnc = self.conf['plmn'][3:]

class Free5GC_K8s(Blue5GBase):
    """
    Free5GC modules exported as external VMs
    """
    edge_vnfd_type = ['upf']

    def __init__(self, conf: dict, id_: str, recover: bool) -> None:
        BlueprintBase.__init__(self, conf, id_, db=db, nbiutil=nbiUtil)
        logger.info("Creating \"Free5GC_K8s\" Blueprint")
        self.supported_operations = {
            'init': [{
                'day0': [{'method': 'bootstrap_day0'}],
                'day2': [{'method': 'init_day2_conf'}],
                'dayN': []
            }],
            'add_tac': [{
                'day0': [{'method': 'add_tac_nsd'}],
                'day2': [{'method': 'add_tac_conf'}],
                'dayN': []
            }],
            'del_tac': [{
                'day0': [],
                'day2': [{'method': 'del_tac_conf'}],
                'dayN': [{'method': 'del_tac_nsd'}]
            }],
            'add_ues': [{
                'day0': [],
                'day2': [{'method': 'add_ues'}],
                'dayN': []
            }],
            'del_ues': [{
                'day0': [],
                'day2': [{'method': 'del_ues'}],
                'dayN': []
            }],
            'add_slice': [{
                'day0': [],
                'day2': [ {'method': 'add_slice'}],
                'dayN': []
            }],
            'del_slice': [{
                'day0': [],
                'day2': [{'method': 'del_slice'}],
                'dayN': []
            }],
            'update_core': [{
                'day0': [],
                'day2': [{'method': 'core_upXade'}],
                'dayN': []
            }],
            'add_ext': [{
                'day0': [{'method': 'add_ext_nsd'}],
                'day2': [{'method': 'add_ext_conf'}],
                'dayN': []
            }],
            'del_ext': [{
                'day0': [],
                'day2': [],
                'dayN': [{'method': 'del_ext_conf'}]
            }],
            'monitor': [{
                'day0': [],
                'day2': [{'method': 'enable_prometheus'}],
                'dayN': []
            }],
            'log': [{
                'day0': [],
                'day2': [{'method': 'enable_elk'}],
                'dayN': []
            }],
        }
        self.primitives = []
        self.vnfd = {'core': [], 'area': []}
        self.vim_core = next((item for item in self.get_vims() if item['core']), None)
        self.chart = "nfvcl_helm_repo/free5gc:3.2.0"
        self.image = "free5gc_v3.0.7"
        # default slices
        self.defaultSliceList = []
        self.userManager = Configurator_Free5GC_User()
        self.coreManager = Configurator_Free5GC_Core(copy.deepcopy(free5GC_default_config.default_config))
        if self.vim_core is None:
            raise ValueError('Vim CORE not found in the input')

    def set_baseCoreVnfd(self, vls=None) -> None:
        vnfd = sol006_VNFbuilder(self.nbiutil, self.db, {
            'id': '{}_5gc'.format(self.get_id()),
            'name': '{}_5gc'.format(self.get_id()),
            'kdu': [{
                'name': '5gc',
                'helm-chart': self.chart,
                'interface': vls
            }]})
        self.vnfd['core'].append({'id': 'core', 'name': vnfd.get_id(), 'vl': vls})

    def set_upfVnfd(self, area: str, vls=None, area_id: int = 0) -> None:
        interfaces = None
        list_ = None
        if area == "core":
            interfaces = vls
        elif area == "area":
            vim = self.get_vim(area_id)
            if vim == None:
                raise ValueError("area = {} has not a valid vim".format(area_id))
            interfaces = [
                {"vim_net": vim['mgt'], "vld": "mgt", "name": "ens3", "mgt": True}
            ]
            areaObj = next((item for item in self.vnfd['area'] if item['area'] == area_id), None)
            if areaObj == None:
                areaObj = {'area': area_id, 'vnfd': []}
                self.vnfd['area'].append(areaObj)

            list_ = areaObj['vnfd']
        else:
            raise ValueError("area = {} is UNKNOWN".format(area))

        if list_ :
            # area
            vnfd = sol006_VNFbuilder(self.nbiutil, self.db, {
                'username': 'root',
                'password': 'root',
                'id': self.get_id() + '_free5gc_upf_' + str(area_id),
                'name': self.get_id() + '_free5gc_upf_' + str(area_id),
                'vdu': [{
                    'count': 1,
                    'id': 'VM',
                    'image': self.image,
                    'vm-flavor': {'memory-mb': '4096', 'storage-gb': '8', 'vcpu-count': '2'},
                    'interface': interfaces,
                    'vim-monitoring': True
                }]}, charm_name='helmflexvnfm')

            list_.append({'id': 'upf', 'name': vnfd.get_id(), 'vl': interfaces, 'type': 'upf'})
        else :
            # core
            vnfd = sol006_VNFbuilder(self.nbiutil, self.db, {
                'username': 'root',
                'password': 'root',
                'id': self.get_id() + '_free5gc_upf_core',
                'name': self.get_id() + '_free5gc_upf_core',
                'vdu': [{
                    'count': 1,
                    'id': 'VM',
                    'image': self.image,
                    'vm-flavor': {'memory-mb': '4096', 'storage-gb': '8', 'vcpu-count': '2'},
                    'interface': interfaces,
                    'vim-monitoring': True
                }]}, charm_name='helmflexvnfm')

            self.vnfd[area].append({'id': 'upf', 'name': vnfd.get_id(), 'vl': interfaces, 'type': 'upf'})
        logger.debug(self.vnfd)

    def set_coreVnfd(self, vls=None) -> None:
        self.set_baseCoreVnfd(vls)

        logger.debug(self.vnfd)

    def set_edgeVnfd(self, area: str, area_id: int = 0) -> None:
        self.set_upfVnfd(area=area, area_id=area_id)

    def getVnfd(self, area: str, area_id: int = 0, type: str = None) -> list:
        id_list = []
        if area == "core":
            id_list = self.vnfd['core']
        elif area == "area":
            area_obj = next((item for item in self.vnfd['area'] if item['area'] == area_id), None)
            if area_obj is None:
                raise ValueError("area {} not found in getting Vnfd".format(area_id))
            if type:
                # create list with vnfd elements where "id" field is equal to "id" param
                id_list = [item for item in area_obj['vnfd'] if 'type' in item and item['type'] == type]
            else :
                id_list = [item for item in area_obj['vnfd'] if 'type' not in item]
        else:
            raise ValueError("area = {} is UNKNOWN".format(area))
        return id_list

    def add_ues_from_configfile(self) -> None:
        """
        Add UEs subscribers
        """
        if 'config' in self.conf and 'subscribers' in self.conf['config']:
            if 'subscribers' not in self.running_free5gc_conf:
                self.running_free5gc_conf['subscribers'] = []
            for s in self.conf['config']['subscribers']:
                if s not in self.running_free5gc_conf['subscribers']:
                    self.running_free5gc_conf['subscribers'].append(s)
    def core_nsd(self) -> str:
        logger.info("Creating Core NSD(s)")
        core_v = next((item for item in self.get_vims() if item['core']), None)
        if core_v == None:
            raise ValueError("Core VIM in msg doesn't exist")
        vim_net_mapping = [
            {'vld': 'data', 'vim_net': core_v['wan']['id'], 'name': 'ens4', "mgt": True, 'k8s-cluster-net': 'data_net'}
        ]
        nsd_names = []

        self.setVnfd('core', vls=vim_net_mapping)

        # set networking parameters for 5GC core running configuration files
        self.set_core_networking_parameters( interfaceName = "ens3", subnetIP = "192.168.0.0",
                                             gatewayIP = "192.168.0.254" )

        # reset configuration
        self.amf_reset_configuration()
        self.ausf_reset_configuration()
        self.n3iwf_reset_configuration()
        self.nrf_reset_configuration()
        self.nssf_reset_configuration()
        self.pcf_reset_configuration()
        self.smf_reset_configuration()
        self.udm_reset_configuration()
        self.udr_reset_configuration()

        # set configuration
        tacList = []
        sliceList = []
        dnnList = []

        smfName = "SMF-{0:06X}".format(random.randrange(0x000000, 0xFFFFFF))
        n3iwfId = random.randint(1, 9999)
        nssfName = "{0:06x}".format(random.randrange(0x000000, 0xFFFFFF))


        # add tac, slice and dnn ids to all tacs of all vims
        if "areas" in self.conf:
            # add tac id to tacList (area_id = tac)
            for area in self.conf["areas"]:
                tacList.append(area["id"])
                if len(self.defaultSliceList) != 0:
                    for s in self.defaultSliceList:
                        self.smf_set_configuration(smfName=smfName, dnnList=s["dnnList"],
                                               sliceList=[s])
                    self.n3iwf_set_configuration(n3iwfId=n3iwfId, tac=area["id"],
                                                 sliceSupportList=self.defaultSliceList)
                    self.nssf_set_configuration(nssfName=nssfName, sliceList=self.defaultSliceList,
                                                tac=area["id"])

                if "slices" in area:
                    # add slice to sliceList
                    tacSliceList = []
                    for slice in area["slices"]:
                        s = {"sd": slice["sd"], "sst": slice["sst"]}
                        if s not in tacSliceList:
                            tacSliceList.append(s)
                        if s not in sliceList:
                            sliceList.append(s)
                        if "dnnList" in slice:
                            # add dnn to dnnList
                            dnnSliceList = []
                            for dnn in slice["dnnList"]:
                                if dnn not in dnnSliceList:
                                    dnnSliceList.append(dnn)
                                if dnn not in dnnList:
                                    dnnList.append(dnn)

                            self.smf_set_configuration(smfName=smfName, dnnList=dnnSliceList, sliceList=[s])

                    self.n3iwf_set_configuration(n3iwfId=n3iwfId, tac=area["id"], sliceSupportList=tacSliceList)
                    self.nssf_set_configuration(nssfName=nssfName, sliceList=tacSliceList, tac=area["id"])

            # if there are not "tac" or "slices" associated with tac (excluding default values),
            # it executes a default configuration
            if len(tacList) == 0 or len(sliceList) == 0:
                self.smf_set_configuration(smfName=smfName, dnnList=dnnList, sliceList=sliceList)
                self.n3iwf_set_configuration(n3iwfId=n3iwfId)
                self.nssf_set_configuration(nssfName=nssfName)

        if len(self.defaultSliceList) != 0:
            sliceList.extend(self.defaultSliceList)
            for s in self.defaultSliceList:
                dnnList.extend(s["dnnList"])
        self.amf_set_configuration(supportedTacList = tacList, snssaiList = sliceList, dnnList = dnnList)

        self.ausf_set_configuration()
        self.nrf_set_configuration()
        self.pcf_set_configuration()
        # SMF: "nodes" and "links" will be configured during "day2", because ip addresses are not known in this phase
        self.udm_set_configuration()
        self.udr_set_configuration()

        self.save_conf()

        vnfd_ = self.getVnfd('core')
        # Kubernetes
        vnfd_k8s = []
        # OpenStack
        vnfd_os = []
        for item in vnfd_ :
            if "type" in item and item["type"] in self.edge_vnfd_type:
                vnfd_os.append(item)
            else:
                vnfd_k8s.append(item)

        if vnfd_k8s:
            kdu_configs = [{
                'vnf_id': '{}_5gc'.format(self.get_id()),
                'kdu_confs': [{'kdu_name': '5gc',
                               "k8s-namespace": str(self.get_id()).lower(),
                               "additionalParams": self.running_free5gc_conf}]
            }]
            param = {
                'name': '5GC_' + str(self.conf['plmn']) + "_" + str(self.get_id()),
                'id': '5GC_' + str(self.conf['plmn']) + "_" + str(self.get_id()),
                'type': 'core'
            }
            n_obj = sol006_NSD_builder(
                vnfd_k8s, core_v, param, vim_net_mapping, knf_configs=kdu_configs
            )
            nsd_item = n_obj.get_nsd()
            nsd_item['vld'] = vim_net_mapping
            self.nsd_.append(nsd_item)
            nsd_names.append(param["name"])

        if vnfd_os:
            for item in vnfd_os:
                param = {
                    'name': str(item["id"]) + '_' + str(self.conf['plmn']) + "_" + str(self.get_id()),
                    'id': str(item["id"]) + '_' + str(self.conf['plmn']) + "_" + str(self.get_id()),
                    'type': 'core'
                }
                n_obj = sol006_NSD_builder([item], core_v, param, vim_net_mapping)
                nsd_item = n_obj.get_nsd()
                nsd_item['vld'] = vim_net_mapping
                self.nsd_.append(nsd_item)
                nsd_names.append(param["name"])

        return nsd_names

    def edge_nsd(self, area_id: int = 0) -> str:
        vim = self.get_vim(area_id)
        if vim == None:
            raise ValueError("Area {} has not a valid VIM".format(area_id))
        logger.info("Creating EDGE NSD(s) for tac {} on vim {}".format(area_id, vim["id"]))
        param_name_list = []

        self.set_edgeVnfd('area', area_id)

        if vim['mgt'] != vim['wan']['id']:
            vim_net_mapping = [
                {'vld': 'mgt', 'vim_net': vim['mgt'], 'name': 'ens3', 'mgt': True},
                {'vld': 'datanet', 'vim_net': vim['wan']['id'], 'name': 'ens4', 'mgt': False}
            ]
        else:
            vim_net_mapping = [
                {'vld': 'mgt', 'vim_net': vim['wan']['id'], 'name': 'ens3', 'mgt': True}
            ]

        for type in self.edge_vnfd_type :
            param = {
                'name': '{}_{}_{}_{}'.format(type.upper(), str(area_id), str(self.conf['plmn']), str(self.get_id())),
                'id': '{}_{}_{}_{}'.format(type.upper(), str(area_id), str(self.conf['plmn']), str(self.get_id())),
                'type': '{}'.format(type)
            }
            edge_vnfd = self.getVnfd('area', area_id, type)
            if not edge_vnfd:
                continue
            n_obj = sol006_NSD_builder(edge_vnfd, vim, param, vim_net_mapping)
            nsd_item = n_obj.get_nsd()
            nsd_item['area'] = area_id
            nsd_item['vld'] = vim_net_mapping
            self.nsd_.append(nsd_item)
            param_name_list.append(param['name'])
        return param_name_list

    def add_ext_nsd(self, msg: dict) -> list:
        """
        Add external UPF(s) (not core) to the system
        For every TAC in the configuration message (in VIMs -> tacs) add an UPF (execution of "edge_nsd" function)
        :param msg: configuration message
        :return: list of nsd to create
        """
        nsd_names = []
        if 'areas' in msg:
            for area in msg['areas']:
                nsd_n = self.edge_nsd(area["id"])
                try:
                    nsd_names.extend(nsd_n)
                except TypeError:
                    nsd_names.append(nsd_n)
        return nsd_names

    def core_day2_conf(self, arg: dict, nsd_item: dict) -> list:
        """
        Used only to configure 5GC modules OpenStack VM (at the moment of this comment, it is only "UPF")
        :param arg:
        :param nsd_item:
        :return:
        """
        logger.info("Initializing Core Day2 configurations")
        res = []

        conf_data = {
            'plmn': str(self.conf['plmn']),
            'upf_nodes': self.conf['config']['upf_nodes']
        }

        config = Configurator_Free5GC(
            nsd_item['descr']['nsd']['nsd'][0]['id'],
            1,
            self.get_id(),
            conf_data
        )

        res += config.dump()
        logger.info("CONF_DATA: {}".format(conf_data))
        logger.info("Module configuration built for core ")

        return res

    def edge_day2_conf(self, arg: dict, nsd_item: dict) -> list:
        logger.info("Initializing Edge Day2 configurations")
        res = []

        conf_data = {
            'plmn': str(self.conf['plmn']),
            'upf_nodes': self.conf['config']['upf_nodes'],
            'tac': nsd_item['area'] # tac of the node is the area ID
        }

        config = Configurator_Free5GC(
            nsd_item['descr']['nsd']['nsd'][0]['id'],
            1,
            self.get_id(),
            conf_data
        )

        res += config.dump()
        logger.info("Configuration built for tac " + str(nsd_item['tac']))

        return res

    def smf_del_upf(self, smfName: str, tac: int, slice: dict = None, dnnInfoList: list = None):
        """
        Del UPF(s) data to the configuration of SMF and restart SMF module in Free5GC deployment

        :return: day2 object to add to "res" list for execution
        """
        logger.info("upf_nodes: {}".format(self.conf["config"]["upf_nodes"]))

        self.smf_unset_configuration(dnnList=dnnInfoList, sliceList=[slice], tacList=[{"id": tac}])
        self.config_5g_core_for_reboot()

        msg2up = {'config': self.running_free5gc_conf}
        return self.core_upXade(msg2up)

    def smf_add_upf(self, smfName: str, tac: int, links: list = None, slice: dict = None, dnnInfoList: list = None):
        """
        Add UPF(s) data to the configuration of SMF and restart SMF module in Free5GC deployment

        :return: day2 object to add to "res" list for execution
        """
        logger.info("upf_nodes: {}".format(self.conf["config"]["upf_nodes"]))
        upNodes = {}
        # fill "upNodes" with UPFs
        # TODO complete with UPFs of core
        if "config" in self.conf:
            if "upf_nodes" in self.conf["config"]:
                upfList = self.conf["config"]["upf_nodes"]
                for upf in upfList:
                    logger.info(" * upf[\"tac\"] = {} , tac = {}".format(upf["tac"], tac))
                    if upf["tac"] == tac:
                        dnnUpfInfoList = []
                        for dnnInfo in dnnInfoList:
                            dnnUpfInfoList.append({"dnn": dnnInfo["dnn"], "pools": dnnInfo["pools"]})
                        UPF = {"nodeID": upf["ip"], "type": "UPF",
                                 "interfaces": [{"endpoints": [upf["ip"]], "interfaceType": "N3",
                                                 "networkInstance": dnnInfoList[0]["dnn"]}],
                                 "sNssaiUpfInfos": [{"dnnUpfInfoList": dnnUpfInfoList, "sNssai": slice}]}
                        upNodes["UPF-{}".format(tac)] = UPF

        if "areas" in self.conf:
            for area in self.conf["areas"]:
                vim = self.get_vim(area["id"])
                if vim == None:
                    logger.error("area {} has not a valid VIM".format(area["id"]))
                    continue
                if area["id"] == tac and "nb_wan_ip" in area:
                    upNodes["gNB-{}".format(tac)] = {"type": "AN", "an_ip": "{}".format(area["nb_wan_ip"])}
                    break

        upNodesList = list(upNodes)
        if links == None:
            if len(upNodesList) != 2:
                logger.error("len of link is {}, links = {}".format(len(upNodesList), upNodesList))
                raise ValueError("len of link is {}, links = {}".format(len(upNodesList), upNodesList))
            links = [{"A": upNodesList[0], "B": upNodesList[1]}]

        self.smf_set_configuration(smfName = smfName, links = links, upNodes = upNodes)
        self.config_5g_core_for_reboot()

        msg2up = {'config': self.running_free5gc_conf}
        return self.core_upXade(msg2up)

    def init_day2_conf(self, msg: dict) -> list:
        logger.info("Initializing Day2 configurations")
        res = []
        tail_res = []
        self.save_conf()

        smfName = self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["configurationBase"]["smfName"]

        if "areas" in msg:
            for area in msg["areas"]:
                dnnList = []
                if len(self.defaultSliceList) != 0:
                    for s in self.defaultSliceList:
                        tail_res += self.smf_add_upf(smfName=smfName, tac=area["id"], slice=s,
                                                dnnInfoList=s["dnnList"])
                        for dnn in s["dnnList"]:
                            if dnn not in dnnList:
                                dnnList.append(dnn)
                if "slices" in area:
                    for slice in area["slices"]:
                        s = {"sd": slice["sd"], "sst": slice["sst"] }
                        if "dnnList" in slice:
                            tail_res += self.smf_add_upf(smfName=smfName, tac=area["id"], slice=s,
                                                    dnnInfoList=slice["dnnList"])
                            for dnn in slice["dnnList"]:
                                if dnn not in dnnList:
                                    dnnList.append(dnn)

                if len(dnnList) != 0:
                    #  add default and slices Dnn list to UPF conf
                    for upf in self.conf["config"]["upf_nodes"]:
                        if upf["tac"] == area["id"]:
                            if "dnnList" in upf:
                                upf["dnnList"].extend(dnnList)
                            else:
                                upf["dnnList"] = copy.deepcopy(dnnList)
                            break

        for n in self.nsd_:
            if n['type'] == 'core':
                # split return a list. nsd_name is something like "amf_00101_DEGFE". We need the first characters
                nsd_type = (n["descr"]["nsd"]["nsd"][0]["name"]).split("_")
                if nsd_type and nsd_type[0] in self.edge_vnfd_type:
                    res += self.core_day2_conf(msg, n)
            elif n['type'] == 'ran':
                tail_res += self.ran_day2_conf(msg, n)
            elif n['type'] in self.edge_vnfd_type:
                res += self.edge_day2_conf(msg, n)

        self.save_conf()
        res = res + tail_res

        return res

    def add_ext_conf(self, msg: dict) -> list:
        """
        Day-2 for added external UPF
        :param msg:
        :return:
        """
        res = []
        if 'areas' in msg:
            for area in msg['areas']:
                nsd_list = []
                for nsd_item in self.nsd_:
                    if nsd_item['area'] == area['id'] and nsd_item['type'] in self.edge_vnfd_type:
                        nsd_list.append(nsd_item)
                if not nsd_list: # list is empty
                    raise ValueError('nsd for tac {} not found'.format(area['id']))
                for nsd in nsd_list:
                    vim = self.get_vim(area["id"])
                    if vim == None:
                        logger.error("area {} has not a valid VIM".format(area["id"]))
                        continue
                    res += self.edge_day2_conf({'vim': vim['name'], 'tac': area['id']}, nsd)
        return res

    def del_tac_nsd(self, msg: dict) -> list:
        nsi_to_delete = super().del_tac(msg)
        if "areas" in msg:
            for area in msg['areas']:
                for type in self.edge_vnfd_type:
                    nsd_i = next((index for index, item in enumerate(self.nsd_) if item['area'] == area['id'] and item['type'] == type), None)
                    if nsd_i is None:
                        raise ValueError('nsd not found')
                    nsi_to_delete.append(self.nsd_[nsd_i]['nsi_id'])
                    self.nsd_.pop(nsd_i)
        return nsi_to_delete

    def add_tac_conf(self, msg: dict) -> list:
        res = []
        smfName = self.running_free5gc_conf["free5gc-smf"]["smf"] \
            ["configuration"]["configurationBase"]["smfName"]
        sliceList = []
        if 'areas' in msg:
            for area in msg['areas']:
                if len(self.defaultSliceList) != 0:
                    for slice in self.defaultSliceList:
                        res += self.smf_add_upf(smfName=smfName, tac=area["id"], slice=slice,
                                     dnnInfoList=slice["dnnList"])
                        slice["tacList"] = [{"id": area["id"]}]
                        sliceList.append(slice)
                # add specific slices
                if "slices" in area:
                    for slice in area["slices"]:
                        res += self.smf_add_upf(smfName=smfName, tac=area["id"],
                                    slice={"sst": slice["sst"], "sd": slice["sd"]},dnnInfoList=slice["dnnList"])
                        sdSstDnnlist = [{s["sd"], s["sst"], s["dnnList"]} for s in sliceList]
                        if slice in sdSstDnnlist:
                            elem = sdSstDnnlist[sdSstDnnlist.index(slice)]
                            if {"id": area["id"]} not in elem["tacList"]:
                                elem["tacList"].append({"id": area["id"]})
                        else:
                            slice["tacList"] = [{"id": area["id"]}]
                            sliceList.append(slice)

        if sliceList != []:
            message = {"config": {"slices": sliceList}}
            self.add_slice(message)

        return res

    def del_tac_conf(self, msg: dict) -> list:
        res = []
        smfName = self.running_free5gc_conf["free5gc-smf"]["smf"] \
            ["configuration"]["configurationBase"]["smfName"]
        sliceList = []
        if 'areas' in msg:
            for area in msg['areas']:
                res += self.smf_del_upf(smfName=smfName, tac=area["id"])
                if "slices" in area:
                    if "slices" in area:
                        for slice in area["slices"]:
                            slice["tacList"] = [{"id": area["id"]}]
                            sliceList.append(slice)
        if sliceList != []:
            message = {"config": {"slices": sliceList}}
            self.del_slice(message)

        return res

    def add_slice(self, msg: dict) -> list:
        res = []
        tail_res = []

        tacList = []
        sliceList = []
        dnnList = []

        # add callback IP in self.conf
        if "callback" in msg:
            self.conf["callback"] = msg["callback"]

        amfId = self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configurationBase"] \
            ["servedGuamiList"][0]["amfId"]
        smfName= self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["configurationBase"]["smfName"]
        n3iwfId = self.running_free5gc_conf["free5gc-n3iwf"]["n3iwf"]["configuration"]["configurationBase"] \
            ["N3IWFInformation"]["GlobalN3IWFID"]["N3IWFID"]
        nssfName = self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"]["nssfName"]

        if "areas" in msg:
            for area in msg["areas"]:
                if "slices" in area:
                    for extSlice in area["slices"]:
                        dnnSliceList = []
                        slice = {"sd": extSlice["sd"], "sst": extSlice["sst"]}
                        sliceList.append(slice)
                        if "dnnList" in extSlice:
                            for dnn in extSlice["dnnList"]:
                                dnnSliceList.append(dnn)
                                dnnList.append(dnn)

                        self.smf_set_configuration(smfName=smfName, dnnList=dnnSliceList, sliceList=[slice])

                        # add DNNs to upf configuration
                        if len(dnnSliceList) != 0:
                            for upf in self.conf["config"]["upf_nodes"]:
                                if upf["tac"] == area["id"]:
                                    if "dnnList" in upf:
                                        upf["dnnList"].extend(dnnSliceList)
                                    else:
                                        upf["dnnList"] = copy.deepcopy(dnnSliceList)
                                    break

                        tacList.append(area["id"])
                        self.n3iwf_set_configuration(n3iwfId=n3iwfId, tac=area["id"], sliceSupportList=[slice])
                        self.nssf_set_configuration(nssfName=nssfName, sliceList=[slice], tac=area["id"])
                        tail_res += self.smf_add_upf(smfName=smfName, tac=area["id"], slice=slice, dnnInfoList=extSlice["dnnList"])
                    self.amf_set_configuration(amfId=amfId, supportedTacList = tacList, snssaiList = sliceList, dnnList = dnnList)

                    # Add DNN to UPF
                    for tacItem in tacList:
                        for nsd_item in self.nsd_:
                            if "area" in nsd_item and nsd_item['area'] == tacItem:
                                if nsd_item['type'] in self.edge_vnfd_type:
                                    conf_data = {
                                        'plmn': str(self.conf['plmn']),
                                        'upf_nodes': self.conf['config']['upf_nodes'],
                                        'tac': tacItem # tac of the node
                                    }

                                    config = Configurator_Free5GC(
                                        nsd_item['descr']['nsd']['nsd'][0]['id'],
                                        1,
                                        self.get_id(),
                                        conf_data
                                    )

                                    res += config.dump()
                                elif nsd_item['type'] == 'ran':
                                    tail_res += self.ran_day2_conf(msg, nsd_item)

                    self.config_5g_core_for_reboot()
                    msg2up = {'config': self.running_free5gc_conf}
                    res += tail_res + self.core_upXade(msg2up)

        return res

    def add_ues(self, msg: dict) -> list:
        res = []

        mongoDbPath = None
        if "config" in self.conf:
            if "mongodb" in self.conf["config"]:
                mongoDbPath = "mongodb://{}:27017/".format(self.conf["config"]["mongodb"])

        if "config" in msg and "plmn" in msg["config"]:
            if "subscribers" in msg["config"]:
                for subscriber in msg["config"]["subscribers"]:
                    plmn = msg["config"]["plmn"]
                    imsi = subscriber["imsi"]
                    if "k" in subscriber and "opc" in subscriber:
                        key = subscriber["k"]
                        opc = subscriber["opc"]

                        self.userManager.add_ue_to_db(plmn=plmn, imsi=imsi, key=key, ocv=opc, mongodbServiceHost=mongoDbPath)

                    if "snssai" in subscriber:
                        for snssaiElem in subscriber["snssai"]:
                            sst = snssaiElem["sst"] # TODO "sliceId" in the json
                            sd = snssaiElem["sd"] # TODO "sliceType" in the json
                            default = snssaiElem["default"]

                            self.userManager.add_snssai_to_db(plmn=plmn, imsi=imsi, sst=sst, sd=sd, default=default,
                                                  mongodbServiceHost=mongoDbPath)

                            if "dnnList" in snssaiElem:
                                for dnnElem in snssaiElem["dnnList"]:
                                    dnn = dnnElem["dnn"]
                                    uplinkAmbr = dnnElem["uplinkAmbr"]
                                    downlinkAmbr = dnnElem["downlinkAmbr"]
                                    default5qi = dnnElem["default5qi"]

                                    self.userManager.add_dnn_to_db(imsi=imsi, sst=sst, sd=sd, dnn=dnn, d5qi=default5qi,
                                                       upambr=uplinkAmbr, downambr=downlinkAmbr,
                                                       mongodbServiceHost=mongoDbPath)

                                    # TODO complete with flowRules

        return res

    def del_ues(self, msg: dict) -> list:
        res = []

        mongoDbPath = None
        if "config" in self.conf:
            if "mongodb" in self.conf["config"]:
                mongoDbPath = "mongodb://{}:27017/".format(self.conf["config"]["mongodb"])

        if "config" in msg and "plmn" in msg["config"]:
            if "subscribers" in msg["config"]:
                for subscriber in msg["config"]["subscribers"]:
                    plmn = msg["config"]["plmn"]
                    imsi = subscriber["imsi"]
                    self.userManager.del_ue_from_db(plmn=plmn, imsi=imsi, mongodbServiceHost=mongoDbPath)
        return res

    def del_slice(self, msg: dict) -> list:
        res = []
        tail_res = []

        # add callback IP in self.conf
        if "callback" in msg:
            self.conf["callback"] = msg["callback"]

        if "areas" in msg:
            for area in msg["areas"]:
                if "slices" in area:
                    for extSlice in area["slices"]:
                        dnnSliceList = []
                        sliceList = [{"sd": extSlice["sd"], "sst": extSlice["sst"]}]
                        if "dnnList" in extSlice:
                            for dnn in extSlice["dnnList"]:
                                dnnSliceList.append(dnn)
                        self.amf_unset_configuration(sliceList,dnnSliceList)
                        self.smf_unset_configuration(dnnSliceList, sliceList)
                        self.n3iwf_unset_configuration(sliceList)
                        self.nssf_unset_configuration(sliceList)

                        # remove DNNs to upf configuration
                        removingDnnList = []
                        if len(dnnSliceList) != 0:
                            for upf in self.conf["config"]["upf_nodes"]:
                                if upf["tac"] == area["id"]:
                                    if "dnnList" in upf:
                                        for dnnIndex, dnnElem in enumerate(upf["dnnList"]):
                                            if dnnElem in dnnSliceList:
                                                removingDnnList.append(dnnElem)
                                                upf["dnnList"].pop(dnnIndex)

                        if len(removingDnnList) != 0:
                            for nsd_item in self.nsd_:
                                if "area" in nsd_item and nsd_item['area'] == area["id"]:
                                    if nsd_item['type'] in self.edge_vnfd_type:
                                        conf_data = {
                                            'plmn': str(self.conf['plmn']),
                                            'upf_nodes': self.conf['config']['upf_nodes'],
                                            'tac': area["id"],  # tac of the node
                                            'removingDnnList': removingDnnList
                                        }

                                        config = Configurator_Free5GC(
                                            nsd_item['descr']['nsd']['nsd'][0]['id'],
                                            1,
                                            self.get_id(),
                                            conf_data
                                        )

                                        res += config.dump()

                                    elif nsd_item['type'] == 'ran':
                                        tail_res += self.ran_day2_conf(msg,nsd_item)

                    self.config_5g_core_for_reboot()

                    msg2up = {'config': self.running_free5gc_conf}
                    res += self.core_upXade(msg2up) + tail_res

        return res

    def config_5g_core_for_reboot(self) -> None:
        """
        This method modifies the running configuration of all 5G core modules.
        So k8s, after loading it, restarts each module
        :return:
        """
        self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configurationBase"]\
            ["reboot"] = random.randrange(0, 9999)
        self.running_free5gc_conf["free5gc-ausf"]["ausf"]["configuration"]["configurationBase"]\
            ["reboot"] = random.randrange(0, 9999)
        self.running_free5gc_conf["free5gc-n3iwf"]["n3iwf"]["configuration"]["configurationBase"]\
            ["reboot"] = random.randrange(0, 9999)
        # Don't reboot NRF
        #self.running_free5gc_conf["free5gc-nrf"]["nrf"]["configuration"]["configurationBase"]\
        #    ["reboot"] = random.randrange(0, 9999)
        self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"]\
            ["reboot"] = random.randrange(0, 9999)
        self.running_free5gc_conf["free5gc-pcf"]["pcf"]["configuration"]["configurationBase"]\
            ["reboot"] = random.randrange(0, 9999)
        self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["configurationBase"]\
            ["reboot"] = random.randrange(0, 9999)
        self.running_free5gc_conf["free5gc-udm"]["udm"]["configuration"]["configurationBase"]\
            ["reboot"] = random.randrange(0, 9999)
        self.running_free5gc_conf["free5gc-udr"]["udr"]["configuration"]["configurationBase"]\
            ["reboot"] = random.randrange(0, 9999)
        self.running_free5gc_conf["free5gc-webui"]["webui"]["configuration"]["configurationBase"]\
            ["reboot"] = random.randrange(0, 9999)

        amfConfigurationBase = self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configuration"] = \
            yaml.dump(amfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)
        ausfConfigurationBase = self.running_free5gc_conf["free5gc-ausf"]["ausf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-ausf"]["ausf"]["configuration"]["configuration"] = \
            yaml.dump(ausfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)
        n3iwfConfigurationBase = self.running_free5gc_conf["free5gc-n3iwf"]["n3iwf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-n3iwf"]["n3iwf"]["configuration"]["configuration"] = \
            yaml.dump(n3iwfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)
        # Don't reboot NRF
        # nrfConfigurationBase = self.running_free5gc_conf["free5gc-nrf"]["nrf"]["configuration"]["configurationBase"]
        # self.running_free5gc_conf["free5gc-nrf"]["nrf"]["configuration"]["configuration"] = \
        #     yaml.dump(nrfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)
        nssfConfigurationBase = self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configuration"] = \
            yaml.dump(nssfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)
        pcfConfigurationBase = self.running_free5gc_conf["free5gc-pcf"]["pcf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-pcf"]["pcf"]["configuration"]["configuration"] = \
            yaml.dump(pcfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)
        smfConfigurationBase = self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["configuration"] = \
            yaml.dump(smfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)
        udmConfigurationBase = self.running_free5gc_conf["free5gc-udm"]["udm"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-udm"]["udm"]["configuration"]["configuration"] = \
            yaml.dump(udmConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)
        udrConfigurationBase = self.running_free5gc_conf["free5gc-udr"]["udr"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-udr"]["udr"]["configuration"]["configuration"] = \
            yaml.dump(udrConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)
        webuiConfigurationBase = self.running_free5gc_conf["free5gc-webui"]["webui"]["configuration"][
            "configurationBase"]
        self.running_free5gc_conf["free5gc-webui"]["webui"]["configuration"]["configuration"] = \
            yaml.dump(webuiConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)

    def core_upXade(self, msg: dict) -> list:
        ns_core = next((item for item in self.nsd_ if item['type'] == 'core'), None)
        if ns_core is None:
            raise ValueError('core NSD not found')
        return self.kdu_upgrade(ns_core['descr']['nsd']['nsd'][0]['name'], msg['config'], nsi_id=ns_core['nsi_id'])

    def kdu_upgrade(self, nsd_name: str, conf_params: dict, vnf_id="1", kdu_name="5gc", nsi_id=None):
        if 'kdu_model' not in conf_params:
            conf_params['kdu_model'] = self.chart

        res = [
            {
                'ns-name': nsd_name,
                'primitive_data': {
                    'member_vnf_index': vnf_id,
                    'kdu_name': kdu_name,
                    'primitive': 'upgrade',
                    'primitive_params': self.running_free5gc_conf
                }
            }
        ]
        if nsi_id is not None:
            res[0]['nsi_id'] = nsi_id

        # TODO check if the the following commands are needed
        if hasattr(self, "nsi_id"):
            if self.nsi_id is not None:
                for r in res:
                    r['nsi_id'] = self.nsi_id

        return res

    def get_ip(self) -> None:
        logger.info('Getting IP addresses of VNFIs (ext version)')
        for n in self.nsd_:
            if n['type'] in self.edge_vnfd_type:
                try:
                    vim = next((item for item in self.get_vims() if item['name'] == n['vim']), None)
                    if vim is None:
                        raise ValueError("get_ip vim is None")
                    area = next((item for item in vim['areas'] if item['id'] == n['area']), None)
                    if area is None:
                        raise ValueError("get_ip tac is None")

                    logger.info('(EXT)Setting IP addresses for {} nsi for Area {} on VIM {}'
                                .format(n['type'].upper(), area["id"], vim['name']))

                    # retrieving vlds from the vnf
                    vnfd = self.getVnfd('area', area["id"], n['type'])[0]
                    vld_names = [i['vld'] for i in vnfd['vl']]
                    vlds = get_ns_vld_ip(n['nsi_id'], vld_names)

                    if len(vld_names) == 1:
                        area['{}_ip'.format(n['type'])] = vlds["mgt"][0]['ip']
                        logger.info('{}(1) ip: {}'.format(n['type'].upper(), area['{}_ip'.format(n['type'])]))
                    elif 'datanet' in vld_names:
                        area['{}_ip'.format(n['type'])] = vlds["datanet"][0]['ip']
                        logger.info('{}(2) ip: {}'.format(n['type'].upper(), area['{}_ip'.format(n['type'])]))
                    else:
                        raise ValueError('({})mismatch in the enb interfaces'.format(n['type']))

                    if '{}_nodes'.format(n['type']) not in self.conf['config']: self.conf['config']['{}_nodes'.format(n['type'])] = []
                    self.conf['config']['{}_nodes'.format(n['type'])].append({
                        'ip': area['{}_ip'.format(n['type'])],
                        'nsi_id': n['nsi_id'],
                        'ns_id': n['descr']['nsd']['nsd'][0]['id'],
                        'type': n['type'],
                        'area': n['area'] if 'area' in n else None
                    })
                    logger.info("node ip: {}".format(area['{}_ip'.format(n['type'])]))
                    logger.info("nodes: {}".format(self.conf['config']['{}_nodes'.format(n['type'])]))
                except Exception as e:
                    logger.error("({})Exception in getting IP addresses from EDGE nsi: {}"
                                 .format(n['type'].upper(), str(e)))
                    raise ValueError(str(e))

        super().get_ip()


    def get_ip_core(self, n) -> None:
        logger.debug('get_ip_core')
        vlds = get_ns_vld_ip(n['nsi_id'], ["data"])
        key = None
        if "data" in vlds and len(vlds["data"]) and "ip" in vlds["data"][0]:
            if vlds["data"][0]["vnfd_name"][-3:].lower() == "amf":
                key = "amf_nodes"
                # save IP for ueransim nb
                if "config" not in self.conf:
                    self.conf['config'] = {}
                self.conf['config']['amf_ip'] = vlds["data"][0]["ip"]
            if vlds["data"][0]["vnfd_name"][-3:].lower() == "upf":
                key = "upf_nodes"
            if vlds["data"][0]["vnfd_name"][-5:].lower() == "n3iwf":
                key = "n3iwf_nodes"
            if vlds["data"][0]["vnfd_name"][-3:].lower() == "smf":
                key = "smf_nodes"

            if key:
                if key not in self.conf['config']: self.conf['config'][key] = []
                self.conf['config'][key].append({
                    'ip': vlds["data"][0]["ip"],
                    'nsi_id': n['nsi_id'],
                    'ns_id': n['descr']['nsd']['nsd'][0]['id'],
                    'type': n['type'],
                    'tac': n['area'] if 'area' in n else None
                })

        try:
           kdu_services = get_kdu_services(n['nsi_id'], '5gc')
           for service in kdu_services:
               if service['type'] == 'LoadBalancer':
                   if service['name'][:3] == "nrf":
                       self.conf['config']['nrf_ip'] = service['external_ip'][0]
                   if service['name'][:4] == "ausf":
                       self.conf['config']['ausf_ip'] = service['external_ip'][0]
                   if service['name'][:4] == "nssf":
                       self.conf['config']['nssf_ip'] = service['external_ip'][0]
                   if service['name'][:3] == "udm":
                       self.conf['config']['udm_ip'] = service['external_ip'][0]
                   if service['name'][:3] == "udr":
                       self.conf['config']['udr_ip'] = service['external_ip'][0]
                   if service['name'][:3] == "pcf":
                       self.conf['config']['pcf_ip'] = service['external_ip'][0]
                   if service['name'][:3] == "amf":
                       self.conf['config']['amf_ip'] = service['external_ip'][0]
                   if service['name'][:3] == "smf":
                       self.conf['config']['smf_ip'] = service['external_ip'][0]
                   if service['name'][:3] == "n3iwf":
                       self.conf['config']['n3iwf_ip'] = service['external_ip'][0]
                   if service['name'] == "mongodb":
                       self.conf['config']['mongodb'] = service['external_ip'][0]

        except Exception as e:
            logger.info("kdu not found, managed exception: {}".format(str(e)))
