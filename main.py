from utils.util import *
from blueprints import LCMWorkers
from nfvo import PNFmanager, NbiUtil
from multiprocessing import Process
from utils import persistency
from topology import topology_worker, topology_lock, topology_msg_queue


logger = create_logger('Main')
nbiUtil = NbiUtil(username=osm_user, password=osm_passwd, project=osm_proj, osm_ip=osm_ip, osm_port=osm_port)
db = persistency.db()
workers = LCMWorkers(topology_lock)
pnf_manager = PNFmanager()

Process(target=topology_worker, args=(db, nbiUtil, topology_msg_queue, topology_lock)).start()
# topology = Topology.from_db(db=db, nbiutil=nbiUtil)

blueprint_type_catalog = []
pdu_type_catalog = []
