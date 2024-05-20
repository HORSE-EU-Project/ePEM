from typing import Annotated, Optional

import httpx
from fastapi import APIRouter, status, Body, Query, HTTPException
from httpx import ConnectTimeout
from pydantic import BaseModel
from blueprints_ng.providers.configurators.ansible_utils import run_ansible_playbook
from blueprints_ng.resources import VmResource
from rest_endpoints.blue_ng_router import get_blueprint_manager
from utils.database import insert_extra, get_extra
from utils.util import IP_PORT_PATTERN, PATH_PATTERN, IP_PATTERN, PORT_PATTERN

horse_router = APIRouter(
    prefix="/v2/horse",
    tags=["Horse"],
    responses={status.HTTP_404_NOT_FOUND: {"description": "Not found"}},
)

class RTRRestAnswer(BaseModel):
    description: str = 'operation submitted'
    status: str = 'submitted'
    status_code: int = 202 # OK

@horse_router.post("/rtr_request_demo1", response_model=RTRRestAnswer)
def rtr_request_demo1(host: str, username: str, password: str, forward_to_doc: bool, payload: str = Body(None, media_type="application/yaml")):
    """
    Allows running an ansible playbook on a remote host.
    Integration for HORSE Project. Allow applying mitigation action on a target. This function is implemented as a workaround since in the first demo
    targets are not managed by ePEM, but they are static. In this way it is possible to apply playbooks on targets, having usr and pwd.

    Args:

        host: The host on witch the playbook is applied ('192.168.X.X' format)

        username: str, the user that is used on the remote machine to apply the playbook

        password: str, the user that is used on the remote machine to apply the playbook

        forward_to_doc: str, if true the request is forwarded to DOC module, otherwise the playbook is applied by ePEM on the target.

        payload: body (yaml), The ansible playbook in yaml format to be applied on the remote target
    """
    if forward_to_doc is False:
        ansible_runner_result, fact_cache = run_ansible_playbook(host, username, password, payload)
        if ansible_runner_result.status == "failed":
            raise HTTPException(status_code=500, detail="Execution of Playbook failed. See ePEM DEBUG log for more info.")
        return RTRRestAnswer(description="Playbook applied", status="success")
    else:
        doc_mod_info = get_extra("doc_module")
        if doc_mod_info is None:
            return RTRRestAnswer(description="The request has NOT been forwarded to DOC module cause there is no DOC MODULE info. Please use /set_doc_ip_port to set the IP.", status="error", status_code=404)
        else:
            if 'url' in doc_mod_info:
                doc_module_url = doc_mod_info['url']
                body = {"actionID": "0", "target": host, "actionType": "0", "service": "0", "action": payload} # TODO define what to do. The format has not been fixed
                try:
                    httpx.post(f"http://{doc_module_url}", data=body, headers={"Content-Type": "application/json"}, timeout=10) # TODO TEST
                except ConnectTimeout:
                    raise HTTPException(status_code=408, detail=f"Cannot contact DOC module at http://{doc_module_url}")
                return RTRRestAnswer(description="The request has been forwarded to DOC module.", status="forwarded", status_code=404)
            else:
                return RTRRestAnswer(description="The request has NOT been forwarded to DOC module cause there is NO DOC module URL. Please use /set_doc_ip_port to set the URL.", status="error", status_code=404)


@horse_router.post("/rtr_request", response_model=RTRRestAnswer)
def rtr_request(target_ip: Annotated[str, Query(pattern=IP_PATTERN)], target_port: Optional[Annotated[str, Query(pattern=PORT_PATTERN)]], service: str, actionType: str, actionID: str, payload: str = Body(None, media_type="application/yaml")):
    """
    Integration for HORSE Project. Allow applying mitigation action on a target managed by the NFVCL (ePEM).
    Allows running an ansible playbook on a remote host. The host NEEDS to be managed by nfvcl.

    See Also:

        [HORSE_Demo3_Components_Specification_v0.1](https://tntlabunigeit-my.sharepoint.com/:w:/r/personal/horse-cloud_tnt-lab_unige_it/_layouts/15/Doc.aspx?sourcedoc=%7B34097F2D-C0F8-4E06-B34C-0BA0B3D81DE0%7D&file=HORSE_Demo3_Components_Specification_v0.1.docx&action=default&mobileredirect=true)

    Args:

        target_ip: The IP of the host on witch the Ansible playbook is applied ('1.52.65.25' format)

        target_port: The port used by Ansible on the host in witch the playbook is applied. This is for optional for future use.

        service: str, Service type for our demo 3 "DNS", should be obtained from RTR request

        actionType: str, For this first iteration is always going to be a "Service modification" but for second iteration should be others type of actions

        actionID: str, this field should be provided by RTR, I think that is really important for second iteration since we need to control the life cycle of actions, so we should implement it now but could be a dummy parameter for this iteration

        payload: body (yaml), The ansible playbook in yaml format to be applied on the remote target
    """
    bm = get_blueprint_manager()
    vm: VmResource = bm.get_VM_target_by_ip(target_ip)
    if vm is None:
        doc_mod_info = get_extra("doc_module")
        if doc_mod_info is None:
            return RTRRestAnswer(description="The Target has not been found in VMs managed by the ePEM. The request will NOT been forwarded to DOC module cause there is no DOC MODULE info. Please use /set_doc_ip_port to set the DOC IP.", status="error", status_code=404)
        else:
            if 'url' in doc_mod_info:
                doc_module_url = doc_mod_info['url']
                body = {"actionID": actionID, "target_ip": target_ip, "target_port": target_port, "actionType": actionType, "service": service, "action": payload}
                try:
                    httpx.post(f"http://{doc_module_url}", data=body, headers={"Content-Type": "application/json"}, timeout=10) # TODO test
                except ConnectTimeout:
                    raise HTTPException(status_code=408, detail=f"Cannot contact DOC module at http://{doc_module_url}")
                return RTRRestAnswer(description="The Target has not been found in VMs managed by the NFVCL, the request has been forwarded to DOC module.", status="forwarded", status_code=404)
            else:
                return RTRRestAnswer(description="The Target has not been found in VMs managed by the NFVCL. The request has NOT been forwarded to DOC module cause there is NO DOC module URL. Please use /set_doc_ip_port to set the DOC URL.", status="error", status_code=404)
    else:
        ansible_runner_result, fact_cache = run_ansible_playbook(target_ip, vm.username, vm.password, payload)
        if ansible_runner_result.status == "failed":
            raise HTTPException(status_code=500, detail="Execution of Playbook failed. See NFVCL DEBUG log for more info.")
        return RTRRestAnswer(description="Playbook applied", status="success")

@horse_router.post("/set_doc_ip_port", response_model=RTRRestAnswer)
def set_doc_ip_port(doc_ip: Annotated[str, Query(pattern=IP_PORT_PATTERN)], url_path: Annotated[str, Query(pattern=PATH_PATTERN)]):
    """
    Set up and save the IP of HORSE DOC module
    """
    insert_extra("doc_module", {"url": f"{doc_ip}{url_path}"})
    return RTRRestAnswer(description="DOC module IP has been set", status="success")
