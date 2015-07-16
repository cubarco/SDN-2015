#!/usr/bin/env python
# coding=utf8


from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3


class BaseApp(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(BaseApp, self).__init__(*args, **kwargs)

    def add_flow(self, datapath, priority, match, actions, hard_timeout=0,
                 idle_timeout=0, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    hard_timeout=hard_timeout,
                                    idle_timeout=idle_timeout,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    hard_timeout=hard_timeout,
                                    idle_timeout=idle_timeout,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    def del_flow(self, datapath, table_id, match, actions,
                 out_port=ofproto_v1_3.OFPP_ANY):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]

        mod = parser.OFPFlowMod(datapath, command=ofproto.OFPFC_DELETE,
                                table_id=table_id, match=match,
                                instructions=inst, out_port=ofproto.OFPP_ANY,
                                out_group=ofproto.OFPG_ANY)
        datapath.send_msg(mod)
