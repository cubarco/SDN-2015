#!/bin/env python2
# coding=utf8

import libnya

from ryu.lib.packet import packet, ethernet

CACHE_SYNC_ETHER_TYPE = 0x9998


def sync(nyaapp):
    for dpid, dp in nyaapp.datapaths.items():
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(src='00:00:00:00:00:00',
                                           dst='ff:ff:ff:ff:ff:ff',
                                           ethertype=CACHE_SYNC_ETHER_TYPE))
        nyaapp.send_packet(dp, 1, pkt)


class AppWebcache(libnya.GlobalComputeNodeApp):

    def __init__(self):
        flowmod = libnya.AppFlowMod(1)  # First hop
        flowmodgroup = libnya.AppFlowModGroup(default_match={'eth_type': 0x0800, 'ip_proto': 6, 'tcp_dst': 80}, action=1, macfix=True)
        flowmodgroup.append_mod(flowmod)
        text1 = libnya.AppUIText("name", "The Cache Test")
        row1 = libnya.AppUICols()
        row1.add_elem(text1)
        ui_elems = libnya.AppUIElement()
        ui_elems.add_row(row1)
        libnya.GlobalComputeNodeApp.__init__(self, 1, "This Application is used to set up a distributed cache", 1, flowmodgroup, ui_elems, sync, "cache_sync", taskinterval=10)


app = AppWebcache()
