from blueprints.blueprint import BlueprintBase
from blueprints.blue_5g_base import Blue5GBase
from typing import List
import copy
from main import *


db = persistency.DB()
nbiUtil = NbiUtil(username=osm_user, password=osm_passwd, project=osm_proj, osm_ip=osm_ip, osm_port=osm_port)

# create logger
logger = create_logger('Configurator_Free5GC_User')

class NoAliasDumper(yaml.SafeDumper):
    """
    Used to remove "anchors" and "aliases" from yaml file
    """
    def ignore_aliases(self, data):
        return True

class Configurator_Free5GC_Core(Blue5GBase):
    def __init__(self, conf: dict, id_: str, running_free5gc_conf: string = None) -> None:
        BlueprintBase.__init__(self, conf, id_, db=db, nbiutil=nbiUtil)
        if running_free5gc_conf == None:
            raise ValueError("The Free5GC configuration file is empty")
        self.running_free5gc_conf = running_free5gc_conf
        # used for NSSF configuration
        self.nsiIdCounter = 0
        self.smfName = "SMF-{0:06X}".format(random.randrange(0x000000, 0xFFFFFF))
        self.n3iwfId = random.randint(1, 9999)
        self.nssfName = "{0:06x}".format(random.randrange(0x000000, 0xFFFFFF))

    def amf_reset_configuration(self) -> None:
        """
        AMF reset configuration
        """
        self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configurationBase"]["servedGuamiList"] = []
        self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configurationBase"]["supportTaiList"] = []
        self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configurationBase"]["plmnSupportList"] = []
        self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configurationBase"]["supportDnnList"] = []
        amfConfigurationBase = self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configuration"] = \
            yaml.dump(amfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)

    def getANewNsiId(self) -> int:
        """
        get a new value for NSI ID (used by NSSF)
        """
        self.nsiIdCounter += 1
        return self.nsiIdCounter

    def amf_set_configuration(self, mcc: str, mnc: str, supportedTacList: list = None, amfId: str = None,
                              snssaiList: list = None, dnnList: list = None) -> str:
        """
        Configure AMF configMap
        :param supportedTacList: [24]
        :param amfId: "cafe01"
        :param mcc: "001"
        :param mnc: "01"
        :param snssaiList: ex. [{"sst": 1, "sd": "000001"}]
        :param dnnList: ex. [{"dnn": "internet", "dns": "8.8.8.8"}]
        :return: amfId
        """
        if mcc == None or mnc == None:
            raise ValueError("mcc () or mnc () is None".format(mcc, mnc))
        if amfId == None: amfId = "{0:06x}".format(random.randrange(0x000000, 0xFFFFFF))
        guamiItem = {"plmnId": {"mcc": mcc, "mnc": mnc}, "amfId": amfId}
        servedGuamiList = self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configurationBase"] \
            ["servedGuamiList"]
        if guamiItem not in servedGuamiList:
            servedGuamiList.append(guamiItem)

        supportTaiList = self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configurationBase"] \
            ["supportTaiList"]

        if supportedTacList != None:
            for tac in supportedTacList:
                supportTaiItem = {"plmnId": {"mcc": mcc, "mnc": mnc}, "tac": tac}
                if supportTaiItem not in supportTaiList:
                    supportTaiList.append(supportTaiItem)

        plmnSupportList = self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configurationBase"] \
            ["plmnSupportList"]
        plmnId = {"mcc": mcc, "mnc": mnc}
        plmnFound = False
        for plmnIdSupportItem in plmnSupportList:
            if plmnIdSupportItem["plmnId"] == plmnId:
                plmnFound = True
                if snssaiList != None:
                    for snssaiItem in snssaiList:
                        item = {"sst": snssaiItem["sst"], "sd": snssaiItem["sd"]}
                        if item not in plmnIdSupportItem["snssaiList"]:
                            plmnIdSupportItem["snssaiList"].append(item)
                break
        if plmnFound == False:
            plmnIdSupportItem = {"plmnId": plmnId, "snssaiList": []}
            if snssaiList != None:
                for snssaiItem in snssaiList:
                    item = {"sst": snssaiItem["sst"], "sd": snssaiItem["sd"]}
                    if item not in plmnIdSupportItem["snssaiList"]:
                        plmnIdSupportItem["snssaiList"].append(item)
            plmnSupportList.append(plmnIdSupportItem)

        supportDnnList = self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configurationBase"] \
            ["supportDnnList"]
        if dnnList != None:
            for dnnItem in dnnList:
                if dnnItem["dnn"] not in supportDnnList:
                    supportDnnList.append(dnnItem["dnn"])

        amfConfigurationBase = self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configuration"] = \
            yaml.dump(amfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)
        return amfId

    def amf_unset_configuration(self, mcc: str, mnc :str, snssaiList: list = None, dnnList: list = None) -> None:
        """
        AMF unset configuration
        """
        if mcc == None or mnc == None:
            raise ValueError("mcc () or mnc () is None".format(mcc, mnc))
        plmnId = {"mcc": mcc, "mnc": mnc}

        if snssaiList != None:
            plmnSupportList = self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configurationBase"] \
                ["plmnSupportList"]
            for plmnIdSupportIndex, plmnIdSupportItem in enumerate(plmnSupportList):
                if plmnIdSupportItem["plmnId"] == plmnId:
                    for snssaiIndex, snssaiItem in enumerate(plmnIdSupportItem["snssaiList"]):
                        if snssaiItem in snssaiList:
                            plmnIdSupportItem["snssaiList"].pop(snssaiIndex)

        if dnnList != None:
            supportDnnList = self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configurationBase"] \
                ["supportDnnList"]
            for dnnItem in dnnList:
                if dnnItem["dnn"] in supportDnnList:
                    index = supportDnnList.index(dnnItem["dnn"])
                    supportDnnList.pop(index)

        amfConfigurationBase = self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-amf"]["amf"]["configuration"]["configuration"] = \
            yaml.dump(amfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)

    def ausf_reset_configuration(self) -> None:
        """
        AUSF reset
        """
        self.running_free5gc_conf["free5gc-ausf"]["ausf"]["configuration"]["configurationBase"]["plmnSupportList"] = []
        ausfConfigurationBase = self.running_free5gc_conf["free5gc-ausf"]["ausf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-ausf"]["ausf"]["configuration"]["configuration"] = \
            yaml.dump(ausfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)

    def ausf_set_configuration(self, mcc: str, mnc: str) -> None:
        """
        AUSF configuration
        """
        if mcc == None or mnc == None:
            raise ValueError("mcc () or mnc () is None".format(mcc, mnc))
        plmnSupportItem = {"mcc": mcc, "mnc": mnc}
        plmnSupportList = self.running_free5gc_conf["free5gc-ausf"]["ausf"]["configuration"]["configurationBase"] \
            ["plmnSupportList"]
        if plmnSupportItem not in plmnSupportList:
            plmnSupportList.append(plmnSupportItem)
        ausfConfigurationBase = self.running_free5gc_conf["free5gc-ausf"]["ausf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-ausf"]["ausf"]["configuration"]["configuration"] = \
            yaml.dump(ausfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)

    def n3iwf_reset_configuration(self) -> None:
        """
        N3IWF configuration
        """
        self.running_free5gc_conf["free5gc-n3iwf"]["n3iwf"]["configuration"]["configurationBase"]["N3IWFInformation"] = \
            {"GlobalN3IWFID": {"PLMNID": {"MCC": "", "MNC": ""}, "N3IWFID": ""}, "Name": "",
             "SupportedTAList": []}
        n3iwfConfigurationBase = self.running_free5gc_conf["free5gc-n3iwf"]["n3iwf"]["configuration"][
            "configurationBase"]
        self.running_free5gc_conf["free5gc-n3iwf"]["n3iwf"]["configuration"]["configuration"] = \
            yaml.dump(n3iwfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)

    def n3iwf_set_configuration(self, mcc: str, mnc: str, name: str = None, tac: int = -1,
                                sliceSupportList: list = None, n3iwfId: int = -1) -> str:
        """
        N3IWF configuration
        """
        if mcc == None or mnc == None:
            raise ValueError("mcc () or mnc () is None".format(mcc, mnc))
        # if name == None: name = str(random.choice(string.ascii_lowercase) for i in range(6))
        if name == None: name = "{0:06x}".format(random.randrange(0x000000, 0xFFFFFF))
        if n3iwfId == -1: n3iwfId = random.randint(1, 9999)

        n3iwfInformation = self.running_free5gc_conf["free5gc-n3iwf"]["n3iwf"]["configuration"]["configurationBase"] \
            ["N3IWFInformation"]
        n3iwfInformation["GlobalN3IWFID"]["N3IWFID"] = n3iwfId
        n3iwfInformation["GlobalN3IWFID"]["PLMNID"]["MCC"] = mcc
        n3iwfInformation["GlobalN3IWFID"]["PLMNID"]["MNC"] = mnc
        n3iwfInformation["Name"] = name

        if tac != -1:
            taFound = False
            TAC = "{:06x}".format(tac)
            for supportedTAItem in n3iwfInformation["SupportedTAList"]:
                if supportedTAItem["TAC"] == TAC:
                    taFound = True
                    plmnIdFound = False
                    for item in supportedTAItem["BroadcastPLMNList"]:
                        if item["PLMNID"] == {"MCC": mcc, "MNC": mnc}:
                            plmnIdFound = True
                            if sliceSupportList != None:
                                for slice in sliceSupportList:
                                    sl = {"SNSSAI": {"SD": slice["sd"], "SST": slice["sst"]}}
                                    if sl not in item["TAISliceSupportList"]:
                                        item["TAISliceSupportList"].append(sl)
                    if plmnIdFound == False:
                        TAISliceSupportList = []
                        if sliceSupportList != None:
                            for slice in sliceSupportList:
                                sl = {"SNSSAI": {"SD": slice["sd"], "SST": slice["sst"]}}
                                TAISliceSupportList.append(sl)
                            sTAItem = [{"PLMNID": {"MCC": mcc, "MNC": mnc}, "TAC": TAC,
                                        "TAISliceSupportList": TAISliceSupportList}]
                            n3iwfInformation["SupportedTAList"].append(sTAItem)
            if taFound == False:
                TAISliceSupportList = []
                if sliceSupportList != None:
                    for slice in sliceSupportList:
                        TAISliceSupportList.append({"SNSSAI": {"SD": slice["sd"], "SST": slice["sst"]}})
                    n3iwfInformation["SupportedTAList"].append({"TAC": TAC, "BroadcastPLMNList":
                        [{"PLMNID": {"MCC": mcc, "MNC": mnc},
                          "TAISliceSupportList": TAISliceSupportList}]})

        n3iwfConfigurationBase = self.running_free5gc_conf["free5gc-n3iwf"]["n3iwf"]["configuration"][
            "configurationBase"]
        self.running_free5gc_conf["free5gc-n3iwf"]["n3iwf"]["configuration"]["configuration"] = \
            yaml.dump(n3iwfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)
        return name

    def n3iwf_unset_configuration(self, sliceSupportList: list = None) -> None:
        """
        N3IWF unset configuration
        """
        if sliceSupportList != None:
            n3iwfInformation = self.running_free5gc_conf["free5gc-n3iwf"]["n3iwf"]["configuration"]["configurationBase"] \
                ["N3IWFInformation"]
            if "SupportedTAList" in n3iwfInformation:
                for supportedTAItem in n3iwfInformation["SupportedTAList"]:
                    if "BroadcastPLMNList" in supportedTAItem:
                        for broadcastItem in supportedTAItem["BroadcastPLMNList"]:
                            if "TAISliceSupportList" in broadcastItem:
                                for taiSliceIndex, taiSliceItem in enumerate(broadcastItem["TAISliceSupportList"]):
                                    if "SNSSAI" in taiSliceItem:
                                        slice = {"sd": taiSliceItem["SNSSAI"]["SD"],
                                                 "sst": taiSliceItem["SNSSAI"]["SST"]}
                                        if slice in sliceSupportList:
                                            broadcastItem["TAISliceSupportList"].pop(taiSliceIndex)

        n3iwfConfigurationBase = self.running_free5gc_conf["free5gc-n3iwf"]["n3iwf"]["configuration"][
            "configurationBase"]
        self.running_free5gc_conf["free5gc-n3iwf"]["n3iwf"]["configuration"]["configuration"] = \
            yaml.dump(n3iwfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)

    def nrf_reset_configuration(self) -> None:
        """
        NRF reset configuration
        """
        self.running_free5gc_conf["free5gc-nrf"]["nrf"]["configuration"]["configurationBase"]["DefaultPlmnId"] = {}
        nrfConfigurationBase = self.running_free5gc_conf["free5gc-nrf"]["nrf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-nrf"]["nrf"]["configuration"]["configuration"] = \
            yaml.dump(nrfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)

    def nrf_set_configuration(self, mcc: str, mnc: str):
        """
        NRF configuration
        """
        if mcc == None or mnc == None:
            raise ValueError("mcc () or mnc () is None".format(mcc, mnc))
        self.running_free5gc_conf["free5gc-nrf"]["nrf"]["configuration"]["configurationBase"]["DefaultPlmnId"] = \
            {"mcc": mcc, "mnc": mnc}
        nrfConfigurationBase = self.running_free5gc_conf["free5gc-nrf"]["nrf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-nrf"]["nrf"]["configuration"]["configuration"] = \
            yaml.dump(nrfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)

    def nssf_reset_configuration(self) -> None:
        """
        NSSF configuration
        """
        self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"][
            "supportedPlmnList"] = []
        self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"]["nsiList"] = []
        self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"] \
            ["supportedNssaiInPlmnList"] = []
        self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"] \
            ["amfList"] = []
        self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"] \
            ["taList"] = []
        self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"] \
            ["supportedNssaiInPlmnList"] = []
        self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"] \
            ["mappingListFromPlmn"] = []
        nssfConfigurationBase = self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configuration"] = \
            yaml.dump(nssfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)

    def nssf_set_configuration(self, mcc: str, mnc: str, operatorName: str = "CNIT", nssfName: str = None,
                               sliceList: list = None, nfId: str = None, tac: int = -1) -> str:
        """
        NSSF configuration
        """
        if nssfName == None: nssfName = "{0:06x}".format(random.randrange(0x000000, 0xFFFFFF))
        if nfId == None: nfId = "{:035d}".format(random.randrange(0x0, 0x13426172C74D822B878FE7FFFFFFFF))
        sstSdList = []
        if sliceList != None:
            for slice in sliceList:
                sstSdList.append({"sst": slice["sst"], "sd": slice["sd"]})

        nrfUri = self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"]["nrfUri"]

        self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"]["nssfName"] = nssfName

        supportedPlmnList = self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"] \
            ["supportedPlmnList"]
        supportedPlmnItem = {"mcc": mcc, "mnc": mnc}
        if supportedPlmnItem not in supportedPlmnList:
            supportedPlmnList.append(supportedPlmnItem)

        nsiList = self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"]["nsiList"]
        if sliceList != None:
            for slice in sliceList:
                elem = {"snssai": {"sst": slice["sst"], "sd": slice["sd"]}, "nsiInformationList":
                    [{"nrfId": "{}/nnrf-nfm/v1/nf-instance".format(nrfUri), "nsiId": self.getANewNsiId()}]}
                nsiList.append(elem)

        if tac != -1:
            tai = {"plmnId": {"mcc": mcc, "mnc": mnc}, "tac": tac}

            supportedNssaiInPlmnList = self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"] \
                ["configurationBase"]["supportedNssaiInPlmnList"]
            plmnId = {"mcc": mcc, "mnc": mnc}
            plmnIdFound = False
            for supportedNssaiInPlmnItem in supportedNssaiInPlmnList:
                if supportedNssaiInPlmnItem["plmnId"] == plmnId:
                    plmnIdFound = True
                    if sliceList != None:
                        for slice in sliceList:
                            if {"sd": slice["sd"], "sst": slice["sst"]} not in supportedNssaiInPlmnItem[
                                "supportedSnssaiList"]:
                                supportedNssaiInPlmnItem["supportedSnssaiList"].append(
                                    {"sd": slice["sd"], "sst": slice["sst"]})
            if plmnIdFound == False:
                supportedNssaiInPlmnList.append({"plmnId": plmnId,
                                                 "supportedSnssaiList": sstSdList})

            amfList = self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"]["amfList"]
            nfIdFound = False
            taiFound = False
            for amfItem in amfList:
                supportedNssaiAvailabilityData = amfItem["supportedNssaiAvailabilityData"]
                for item in supportedNssaiAvailabilityData:
                    if item["tai"] == tai:
                        taiFound = True
                        if sliceList != None:
                            for slice in sliceList:
                                if slice not in item["supportedSnssaiList"]:
                                    item["supportedSnssaiList"].append({"sst": slice["sst"], "sd": slice["sd"]})
                        break
                if amfItem["nfId"] == nfId:
                    nfIdFound = True
                    if taiFound == False:
                        supportedNssaiAvailabilityData.append(
                            {"tai": "{}".format(tai), "supportedSnssaiList": sstSdList})
                        break

            if nfIdFound == False and taiFound == False:
                amfList.append({"nfId": nfId, "supportedNssaiAvailabilityData":
                    [{"tai": tai, "supportedSnssaiList": sstSdList}]})

            taiFound = False
            taList = self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"]["taList"]
            for taItem in taList:
                if taItem["tai"] == tai:
                    taiFound = True
                    if sliceList != None:
                        for slice in sliceList:
                            if slice not in taItem["supportedSnssaiList"]:
                                taItem["supportedSnssaiList"].append({"sst": slice["sst"], "sd": slice["sd"]})
            if taiFound == False:
                taList.append(
                    {"accessType": "3GPP_ACCESS", "supportedSnssaiList": sstSdList, "tai": tai})

            mappingListFromPlmn = \
            self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"] \
                ["mappingListFromPlmn"]
            homePlmnIdFound = False
            for item in mappingListFromPlmn:
                if item["homePlmnId"] == plmnId:
                    homePlmnIdFound = True
                    if sliceList != None:
                        for slice in sliceList:
                            mappingItem = {"homeSnssai": {"sst": slice["sst"], "sd": slice["sd"]},
                                           "servingSnssai": {"sst": slice["sst"], "sd": slice["sd"]}}
                            if mappingItem not in item["mappingOfSnssai"]:
                                item["mappingOfSnssai"].append(mappingItem)
            if homePlmnIdFound == False:
                mappingOfSnssai = []
                for slice in sliceList:
                    mappingOfSnssai.append({"homeSnssai": {"sst": slice["sst"], "sd": slice["sd"]},
                                            "servingSnssai": {"sst": slice["sst"], "sd": slice["sd"]}})
                mappingListFromPlmn.append(
                    {"homePlmnId": plmnId, "mappingOfSnssai": mappingOfSnssai,
                     "operatorName": operatorName})

        nssfConfigurationBase = self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configuration"] = \
            yaml.dump(nssfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)

        return nfId

    def nssf_unset_configuration(self, sliceList: list = None) -> None:
        """
        NSSF unset configuration
        """
        if sliceList != None:
            supportedNssaiInPlmnList = self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"] \
                ["configurationBase"]["supportedNssaiInPlmnList"]
            for supportedNssaiInPlmnItem in supportedNssaiInPlmnList:
                if "supportedSnssaiList" in supportedNssaiInPlmnItem:
                    for supportedSnssaiIndex, supportedSnssaiItem in \
                            enumerate(supportedNssaiInPlmnItem["supportedSnssaiList"]):
                        if supportedSnssaiItem in sliceList:
                            supportedNssaiInPlmnItem["supportedSnssaiList"].pop(supportedSnssaiIndex)
                            break

            amfList = self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"]["amfList"]
            for amfItem in amfList:
                if "supportedNssaiAvailabilityData" in amfItem:
                    for supportedNssaiItem in amfItem["supportedNssaiAvailabilityData"]:
                        if "supportedSnssaiList" in supportedNssaiItem:
                            for supportedSnssaiIndex, supportedSnssaiItem \
                                    in enumerate(supportedNssaiItem["supportedSnssaiList"]):
                                if supportedSnssaiItem in sliceList:
                                    supportedNssaiItem["supportedSnssaiList"].pop(supportedSnssaiIndex)

            taList = self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"]["taList"]
            for taItem in taList:
                if "supportedSnssaiList" in taItem:
                    for supportedSnssaiIndex, supportedSnssaiItem in enumerate(taItem["supportedSnssaiList"]):
                        if supportedSnssaiItem in sliceList:
                            taItem["supportedSnssaiList"].pop(supportedSnssaiIndex)

            mappingListFromPlmn = self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"] \
                ["configurationBase"]["mappingListFromPlmn"]
            for mappingListItem in mappingListFromPlmn:
                if "mappingOfSnssai" in mappingListItem:
                    for mappingOfSnssaiIndex, mappingOfSnssaiItem in enumerate(mappingListItem["mappingOfSnssai"]):
                        if "homeSnssai" in mappingOfSnssaiItem:
                            if mappingOfSnssaiItem["homeSnssai"] in sliceList:
                                mappingOfSnssaiItem.pop("homeSnssai")
                            if mappingOfSnssaiItem["servingSnssai"] in sliceList:
                                mappingOfSnssaiItem.pop("servingSnssai")
                            if "homeSnssai" not in mappingOfSnssaiItem and "servingSnssai" not in mappingOfSnssaiItem:
                                mappingListItem["mappingOfSnssai"].pop(mappingOfSnssaiIndex)

        nssfConfigurationBase = self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-nssf"]["nssf"]["configuration"]["configuration"] = \
            yaml.dump(nssfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)

    def pcf_reset_configuration(self) -> None:
        """
        PCF configuration
        """
        self.running_free5gc_conf["free5gc-pcf"]["pcf"]["configuration"]["pcfName"] = None
        pcfConfigurationBase = self.running_free5gc_conf["free5gc-pcf"]["pcf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-pcf"]["pcf"]["configuration"]["configuration"] = \
            yaml.dump(pcfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)

    def pcf_set_configuration(self, pcfName: str = None) -> str:
        """
        PCF configuration
        """
        if pcfName == None: pcfName = "{:06d}".format(random.randrange(0x000000, 0xFFFFFF))
        self.running_free5gc_conf["free5gc-pcf"]["pcf"]["configuration"]["pcfName"] = pcfName
        pcfConfigurationBase = self.running_free5gc_conf["free5gc-pcf"]["pcf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-pcf"]["pcf"]["configuration"]["configuration"] = \
            yaml.dump(pcfConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)
        return pcfName

    def smf_reset_configuration(self) -> None:
        """
        SMF configuration
        """
        self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["configurationBase"]["smfName"] = ""
        self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["configurationBase"]["snssaiInfos"] = []

        self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["configurationBase"]["plmnList"] = []
        self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["configurationBase"] \
            ["userplaneInformation"] = {"upNodes": {}, "links": []}

        # The empty lists of "upNodes" and "links" makes SMF instable to start. So don't start SMF ("deploySMF"=False)
        # before have a full configuration
        self.running_free5gc_conf["deploySMF"] = False

        smfConfigurationBase = self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["configuration"] = \
            yaml.dump(smfConfigurationBase, explicit_start=False, default_flow_style=False)
        smfUeRoutingInfoBase = self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["ueRoutingInfoBase"]
        self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["ueRoutingInfo"] = \
            yaml.dump(smfUeRoutingInfoBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)

    def smf_set_configuration(self, mcc: str, mnc: str, smfName: str = None, dnnList: list = None,
                              sliceList: list = None, links: list = None, upNodes: dict = None) -> str:
        """
        SMF set configuration
        :param mcc:
        :param mnc:
        :param smfName:
        :param dnnList: es. [{"dnn": "internet", "dns": "8.8.8.8"}]
        :param sliceList: es. [{"sst": 1, "sd": "000001"}]
        :param links:
        :param upNodes:
        :return:
        """
        if mcc == None or mnc == None:
            raise ValueError("mcc () or mnc () is None".format(mcc, mnc))
        plmnId = {"mcc": mcc, "mnc": mnc}
        if smfName == None: smfName = "SMF-{0:06X}".format(random.randrange(0x000000, 0xFFFFFF))

        self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["configurationBase"]["smfName"] = smfName

        plmnList = self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["configurationBase"]["plmnList"]
        if plmnId not in plmnList:
            plmnList.append(plmnId)

        snssaiInfos = self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"] \
            ["configurationBase"]["snssaiInfos"]
        if sliceList != None:
            for slice in sliceList:
                sNssaiFound = False
                for item in snssaiInfos:
                    if item["sNssai"] == slice:
                        sNssaiFound = True
                        if dnnList != None:
                            for dnn in dnnList:
                                dnnFound = False
                                for dnnInfo in item["dnnInfos"]:
                                    if dnn["dnn"] == dnnInfo["dnn"]:
                                        dnnFound = True
                                        break
                                if dnnFound == False:
                                    item["dnnInfos"].append({"dnn": dnn["dnn"], "dns": dnn["dns"]})
                                else:
                                    dnnFound = False
                if sNssaiFound == False:
                    dnnInfos = []
                    for dnn in dnnList:
                        dnnInfos.append({"dnn": dnn["dnn"], "dns": dnn["dns"]})
                    snssaiInfos.append({"dnnInfos": dnnInfos, "sNssai": slice})
                else:
                    sNssaiFound = False

        userplaneInformationLinks = self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"] \
            ["configurationBase"]["userplaneInformation"]["links"]
        userplaneInformationUpNodes = self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"] \
            ["configurationBase"]["userplaneInformation"]["upNodes"]

        if links != None:
            for link in links:
                if link not in userplaneInformationLinks:
                    userplaneInformationLinks.append(link)

        if upNodes != None:
            for key, value in upNodes.items():
                if key in userplaneInformationUpNodes:
                    if value["type"] == "AN":
                        userplaneInformationUpNodes[key] = value
                    if value["type"] == "UPF":
                        userplaneInformationUpNodes[key]["interfaces"] = value["interfaces"]
                        userplaneInformationUpNodes[key]["nodeID"] = value["nodeID"]
                        userplaneInformationUpNodes[key]["type"] = value["type"]
                        for newitem in value["sNssaiUpfInfos"]:
                            snssaiFound = False
                            for olditem in userplaneInformationUpNodes[key]["sNssaiUpfInfos"]:
                                if newitem["sNssai"] == olditem["sNssai"]:
                                    olditem["dnnUpfInfoList"] = newitem["dnnUpfInfoList"]
                                    snssaiFound = True
                                    break
                            if snssaiFound == False:
                                userplaneInformationUpNodes[key]["sNssaiUpfInfos"].append(newitem)
                else:
                    userplaneInformationUpNodes[key] = copy.deepcopy(value)

        # check if SMF modules is started. If a valid configuration exists, it starts SMF
        if len(userplaneInformationLinks) > 0 and len(userplaneInformationUpNodes) > 0:
            self.running_free5gc_conf["deploySMF"] = True

        smfConfigurationBase = self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["configuration"] = \
            yaml.dump(smfConfigurationBase, explicit_start=False, default_flow_style=False)
        smfUeRoutingInfoBase = self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["ueRoutingInfoBase"]
        self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["ueRoutingInfo"] = \
            yaml.dump(smfUeRoutingInfoBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)

        return smfName

    def smf_unset_configuration(self, dnnList: list = None, sliceList: list = None, tacList: list = None) -> None:
        """
        SMF unset configuration
        """
        snssaiInfos = self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"] \
            ["configurationBase"]["snssaiInfos"]
        userplaneInformationLinks = self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"] \
            ["configurationBase"]["userplaneInformation"]["links"]
        userplaneInformationUpNodes = self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"] \
            ["configurationBase"]["userplaneInformation"]["upNodes"]

        if sliceList != None:
            for snssiInfosIndex, snssiInfosItem in enumerate(snssaiInfos):
                if "sNssai" in snssiInfosItem:
                    if snssiInfosItem["sNssai"] in sliceList:
                        snssaiInfos.pop(snssiInfosIndex)
                        continue

                if dnnList != None:
                    if "dnnInfos" in snssiInfosItem:
                        for dnnInfosIndex, dnnInfosItem in enumerate(snssiInfosItem["dnnInfos"]):
                            if "dnn" in dnnInfosItem:
                                for dnnItem in dnnList:
                                    if dnnInfosItem["dnn"] == dnnItem["dnn"]:
                                        snssiInfosItem["dnnInfos"].pop(dnnInfosIndex)

            for nodeKey, nodeValue in userplaneInformationUpNodes.items():
                if "sNssaiUpfInfos" in nodeValue:
                    for sNssaiUpfInfosIndex, sNssaiUpfInfosItem in enumerate(nodeValue["sNssaiUpfInfos"]):
                        if "sNssai" in sNssaiUpfInfosItem:
                            if sNssaiUpfInfosItem["sNssai"] in sliceList:
                                nodeValue["sNssaiUpfInfos"].pop(sNssaiUpfInfosIndex)
                                continue
                        if dnnList != None:
                            if "dnnUpfInfoList" in sNssaiUpfInfosItem:
                                for dnnUpfInfoIndex, dnnUpfInfoItem in enumerate(sNssaiUpfInfosItem["dnnUpfInfoList"]):
                                    for dnnItem in dnnList:
                                        if dnnUpfInfoItem["dnn"] == dnnItem["dnn"]:
                                            sNssaiUpfInfosItem["dnnUpfInfoList"].pop(dnnUpfInfoIndex)

        if tacList != None:
            if tacList != None:
                for tac in tacList:
                    upfName = "UPF-{}".format(tac["id"])
                    gnbName = "gNB-{}".format(tac["id"])
                    for linkIndex, linkItem in enumerate(userplaneInformationLinks):
                        if upfName in linkItem.items() or gnbName in linkItem.items():
                            userplaneInformationLinks.pop(linkIndex)
                    for nodeIndex, nodeItem in enumerate(userplaneInformationUpNodes):
                        if upfName in nodeItem.keys() or gnbName in nodeItem.keys():
                            userplaneInformationUpNodes.pop(nodeIndex)

    def udm_reset_configuration(self) -> None:
        """
        UDM configuration
        """
        udmConfigurationBase = self.running_free5gc_conf["free5gc-udm"]["udm"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-udm"]["udm"]["configuration"]["configuration"] = \
            yaml.dump(udmConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)

    def udm_set_configuration(self) -> None:
        """
        UDM configuration
        """
        udmConfigurationBase = self.running_free5gc_conf["free5gc-udm"]["udm"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-udm"]["udm"]["configuration"]["configuration"] = \
            yaml.dump(udmConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)

    def udr_reset_configuration(self) -> None:
        """
        UDR configuration
        """
        udrConfigurationBase = self.running_free5gc_conf["free5gc-udr"]["udr"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-udr"]["udr"]["configuration"]["configuration"] = \
            yaml.dump(udrConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)

    def udr_set_configuration(self) -> None:
        """
        UDR configuration
        """
        udrConfigurationBase = self.running_free5gc_conf["free5gc-udr"]["udr"]["configuration"]["configurationBase"]
        self.running_free5gc_conf["free5gc-udr"]["udr"]["configuration"]["configuration"] = \
            yaml.dump(udrConfigurationBase, explicit_start=False, default_flow_style=False, Dumper=NoAliasDumper)

    def set_core_networking_parameters(self, subnetIP: str, gatewayIP: str, interfaceName: str = "ens3") -> None:
        self.running_free5gc_conf["global"]["n2network"]["masterIf"] = interfaceName
        self.running_free5gc_conf["global"]["n3network"]["masterIf"] = interfaceName
        self.running_free5gc_conf["global"]["n4network"]["masterIf"] = interfaceName
        self.running_free5gc_conf["global"]["n6network"]["masterIf"] = interfaceName
        self.running_free5gc_conf["global"]["n6network"]["subnetIP"] = subnetIP
        self.running_free5gc_conf["global"]["n6network"]["gatewayIP"] = gatewayIP
        self.running_free5gc_conf["global"]["n9network"]["masterIf"] = interfaceName
        # "POD_IP" is a value changed in runtime inside the container in k8s
        self.running_free5gc_conf["global"]["smf"]["n4if"]["interfaceIpAddress"] = "POD_IP"
        self.running_free5gc_conf["global"]["amf"]["n2if"]["interfaceIpAddress"] = "0.0.0.0"

    def reset_core_configuration(self) -> None:
        self.amf_reset_configuration()
        self.ausf_reset_configuration()
        self.n3iwf_reset_configuration()
        self.nrf_reset_configuration()
        self.nssf_reset_configuration()
        self.pcf_reset_configuration()
        self.smf_reset_configuration()
        self.udm_reset_configuration()
        self.udr_reset_configuration()

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

    def add_tacs_and_slices(self, conf: dict, smfName: string = None, n3iwfId: int = None,
            nssfName: string = None) -> None:
        """
        add_slice
        conf : it is the json message (dict) sent to Free5GC
        """
        if conf is None:
            logger.warn("Conf is None")
            return

        if "config" in conf and "plmn" in conf['config']:
            mcc = conf['config']['plmn'][:3]
            mnc = conf['config']['plmn'][3:]
        else:
            raise ValueError("config section is not in conf or plmn not specified in config section")

        # set configuration
        tacList = []
        sliceList = []
        dnnList = []

        if smfName is not None:
            self.smfName = smfName
        if n3iwfId is not None:
            self.n3iwfId = n3iwfId
        if nssfName is not None:
            self.nssfName = nssfName

        # add tac, slice and dnn ids to all tacs of all vims
        if "areas" in conf:
            # add tac id to tacList (area_id = tac)
            for area in conf["areas"]:
                tacList.append(area["id"])

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

                            self.smf_set_configuration(mcc=mcc, mnc=mnc, smfName=self.smfName, dnnList=dnnSliceList,
                                    sliceList=[s])

                    self.n3iwf_set_configuration(mcc=mcc, mnc=mnc, n3iwfId=self.n3iwfId, tac=area["id"],
                            sliceSupportList=tacSliceList)
                    self.nssf_set_configuration(mcc=mcc, mnc=mnc, nssfName=self.nssfName, sliceList=tacSliceList,
                            tac=area["id"])

            # if there are not "tac" or "slices" associated with tac (excluding default values),
            # it executes a default configuration
            if len(tacList) == 0 or len(sliceList) == 0:
                self.smf_set_configuration(mcc=mcc, mnc=mnc, smfName=self.smfName, dnnList=dnnList, sliceList=sliceList)
                self.n3iwf_set_configuration(mcc=mcc, mnc=mnc, n3iwfId=self.n3iwfId)
                self.nssf_set_configuration(mcc=mcc, mnc=mnc, nssfName=self.nssfName)

        self.amf_set_configuration(mcc=mcc, mnc=mnc, supportedTacList=tacList, snssaiList=sliceList, dnnList=dnnList)

        self.ausf_set_configuration(mcc=mcc, mnc=mnc)
        self.nrf_set_configuration(mcc=mcc, mnc=mnc)
        self.pcf_set_configuration()
        # SMF: "nodes" and "links" will be configured during "day2", because ip addresses are not known in this phase
        self.udm_set_configuration()
        self.udr_set_configuration()

    def smf_del_upf(self, conf: dict, tac: int, slice: dict = None, dnnInfoList: list = None):
        """
        Del UPF(s) data to the configuration of SMF and restart SMF module in Free5GC deployment

        :return: day2 object to add to "res" list for execution
        """
        if conf is None:
            logger.warn("Conf is None")
            return

        logger.info("upf_nodes: {}".format(conf["config"]["upf_nodes"]))

        self.smf_unset_configuration(dnnList=dnnInfoList, sliceList=[slice], tacList=[{"id": tac}])
        self.config_5g_core_for_reboot()
        #
        # msg2up = {'config': self.running_free5gc_conf}
        # return self.core_upXade(msg2up)

    def smf_add_upf(self, conf: dict, smfName: str, tac: int, links: list = None, slice: dict = None,
                    dnnInfoList: list = None):
        """
        Add UPF(s) data to the configuration of SMF and restart SMF module in Free5GC deployment

        :return: day2 object to add to "res" list for execution
        """
        if conf is None:
            logger.warn("Conf is None")
            return

        if "config" in conf and "plmn" in conf['config']:
            mcc = conf['config']['plmn'][:3]
            mnc = conf['config']['plmn'][3:]
        else:
            raise ValueError("config section is not in conf or plmn not specified in config section")

        logger.info("upf_nodes: {}".format(conf["config"]["upf_nodes"]))
        upNodes = {}
        # fill "upNodes" with UPFs
        # TODO complete with UPFs of core
        if "config" in conf:
            if "upf_nodes" in conf["config"]:
                upfList = conf["config"]["upf_nodes"]
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

        if "areas" in conf:
            for area in conf["areas"]:
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

        self.smf_set_configuration(mcc=mcc, mnc=mnc, smfName=smfName, links=links, upNodes=upNodes)
        self.config_5g_core_for_reboot()

    def day2_conf(self, msg: dict) -> List:
        tail_res = []
        smfName = self.running_free5gc_conf["free5gc-smf"]["smf"]["configuration"]["configurationBase"]["smfName"]

        if "areas" in msg:
            for area in msg["areas"]:
                dnnList = []
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
        return tail_res

    def add_tac_conf(self, msg: dict) -> list:
        res = []
        smfName = self.running_free5gc_conf["free5gc-smf"]["smf"] \
            ["configuration"]["configurationBase"]["smfName"]
        sliceList = []
        if 'areas' in msg:
            for area in msg['areas']:
                # add specific slices
                if "slices" in area:
                    for slice in area["slices"]:
                        res += self.smf_add_upf(conf=msg, smfName=smfName, tac=area["id"],
                                    slice={"sst": slice["sst"], "sd": slice["sd"]},dnnInfoList=slice["dnnList"])
                        sdSstDnnlist = [{"sd": s["sd"], "sst": s["sst"], "dnnList": s["dnnList"]} for s in sliceList]
                        if slice in sdSstDnnlist:
                            elem = sdSstDnnlist[sdSstDnnlist.index(slice)]
                            if "tacList" in elem:
                                if {"id": area["id"]} not in elem["tacList"]:
                                    elem["tacList"].append({"id": area["id"]})
                            else:
                                elem["tacList"] = [{"id": area["id"]}]
                        else:
                            slice["tacList"] = [{"id": area["id"]}]
                            sliceList.append(slice)

        if sliceList:
            message = {"config": {"slices": sliceList}}
            self.add_slice(message)

        return res

    def del_tac_conf(self, msg: dict) -> list:
        res = []
        sliceList = []
        if 'areas' in msg:
            for area in msg['areas']:
                res += self.smf_del_upf(conf=msg, tac=area["id"])
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
        if msg is None:
            logger.warn("Conf is None")
            return []

        if "config" in msg and "plmn" in msg['config']:
            mcc = msg['config']['plmn'][:3]
            mnc = msg['config']['plmn'][3:]
        else:
            raise ValueError("config section is not in conf or plmn not specified in config section")

        res = []
        tacList = []
        sliceList = []
        dnnList = []

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
                        self.n3iwf_set_configuration(mcc=mcc, mnc= mnc, n3iwfId=n3iwfId, tac=area["id"],
                                sliceSupportList=[slice])
                        self.nssf_set_configuration(mcc=mcc, mnc=mnc, nssfName=nssfName, sliceList=[slice],
                                tac=area["id"])
                        res += self.smf_add_upf(smfName=smfName, tac=area["id"], slice=slice,
                                dnnInfoList=extSlice["dnnList"])
                    self.amf_set_configuration(mcc=mcc, mnc=mnc, amfId=amfId, supportedTacList = tacList,
                                snssaiList = sliceList, dnnList = dnnList)

        return res

    def del_slice(self, msg: dict) -> None:
        if msg is None:
            logger.warn("Conf is None")
            return

        if "config" in msg and "plmn" in msg['config']:
            mcc = msg['config']['plmn'][:3]
            mnc = msg['config']['plmn'][3:]
        else:
            raise ValueError("config section is not in conf or plmn not specified in config section")

        if "areas" in msg:
            for area in msg["areas"]:
                if "slices" in area:
                    for extSlice in area["slices"]:
                        dnnSliceList = []
                        sliceList = [{"sd": extSlice["sd"], "sst": extSlice["sst"]}]
                        if "dnnList" in extSlice:
                            for dnn in extSlice["dnnList"]:
                                dnnSliceList.append(dnn)
                        self.amf_unset_configuration(mcc=mcc, mnc=mnc, snssaiList=sliceList,dnnList=dnnSliceList)
                        self.smf_unset_configuration(dnnList=dnnSliceList, sliceList=sliceList)
                        self.n3iwf_unset_configuration(sliceSupportList=sliceList)
                        self.nssf_unset_configuration(sliceList=sliceList)

                    # self.config_5g_core_for_reboot()
                    #
                    # msg2up = {'config': self.running_free5gc_conf}
                    # res += self.core_upXade(msg2up) + tail_res


    def getConfiguration(self) -> dict:
        return self.running_free5gc_conf