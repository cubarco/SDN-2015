from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, tcp

PROTO_IP = 0x0800
PROTO_TCP = 6

class RestrictedHTTPRequest(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(RestrictedHTTPRequest, self).__init__(*args, **kwargs)
        self.macs = []

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_feature_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        self.logger.info("Switch %d connected, adding flow entries.", dpid)
        match = parser.OFPMatch(in_port=1)
        actions = [parser.OFPActionOutput(2, ofproto.OFPCML_NO_BUFFER)]
        # Flow entry match structure: priority=0,in_port=1 actions=output:2
        self.add_flow(datapath, 0, match, actions)

        match = parser.OFPMatch(in_port=2)
        actions = [parser.OFPActionOutput(1, ofproto.OFPCML_NO_BUFFER)]
        # Flow entry match structure: priority=0,in_port=2 actions=output:1
        self.add_flow(datapath, 0, match, actions)

        if dpid == 2:
            match = parser.OFPMatch(in_port=1, eth_type=PROTO_IP,
                                    ip_proto=PROTO_TCP, tcp_dst=80)
            actions = [parser.OFPActionOutput(2, ofproto.OFPCML_NO_BUFFER),
                       parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                              ofproto.OFPCML_NO_BUFFER)]
            # Flow entry match structure: 
            # priority=1,tcp,in_port=1,tp_dst=80 actions=output:2,CONTROLLER:65535
            self.add_flow(datapath, 1, match, actions)
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src
        tcp_p = pkt.get_protocols(tcp.tcp)[0]

        if dpid != 2 or src in self.macs:
            return
        
        if tcp_p.ack <= 1: # TCP three-way handshake and HTTP request
            return

        self.logger.info("First HTTP request from %s, adding flow entry.", src)

        self.macs.append(src) 
        actions = []
        match = parser.OFPMatch(in_port=in_port, eth_src=src, eth_dst=dst, 
                                eth_type=PROTO_IP, ip_proto=PROTO_TCP, tcp_dst=80)
        # Flow entry match structure:
        # priority=2,tcp,in_port=1,dl_src=xx:xx:xx:xx:xx:xx,
        # dl_dst=xx:xx:xx:xx:xx:xx,tp_dst=80 actions=drop
        self.add_flow(datapath, 2, match, actions, hard_timeout=60)

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
