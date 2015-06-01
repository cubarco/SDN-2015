from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3


class RestrictedHTTPRequest(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(RestrictedHTTPRequest, self).__init__(*args, **kwargs)
        self.h2_mac = '00:00:00:00:00:02'
        self.h4_mac = '00:00:00:00:00:04'

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_feature_handler(self, ev):
        datapath = ev.msg.datapath
        parser = datapath.ofproto_parser
        dpid = datapath.id

        print 'Switch s%d connected.' % dpid
        if dpid == 3:
            match = parser.OFPMatch(in_port=1,
                                    eth_src=self.h2_mac, eth_dst=self.h4_mac)
            actions = []  # Drop
            # Flow entry:
            # table=0, priority=65535,in_port=1,dl_src=00:00:00:00:00:02,
            # dl_dst=00:00:00:00:00:04
            # actions=drop
            self.add_flow(datapath, 65535, match, actions)

    def add_flow(self, datapath, priority, match, actions, hard_timeout=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if hard_timeout:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst,
                                    hard_timeout=hard_timeout)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)
