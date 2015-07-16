#!/usr/bin/env python
# coding=utf8

from nya import core
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
import time


class testmodulewrapper(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        testmodule.__init__(*args, **kwargs)


class testmodule(core.BaseApp):

    def __init__(self, *args, **kwargs):
        super(testmodule, self).__init__(*args, **kwargs)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        print "Adding flow entry."
        self.add_flow(datapath, 0, match, actions)
        time.sleep(10)
        print "Deleting flow entry."
        self.del_flow(datapath, table_id=0, match=match, actions=actions)
