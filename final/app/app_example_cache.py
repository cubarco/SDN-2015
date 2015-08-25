#!/bin/env python2
# coding=utf8

import libnya

def sync(nya):
    pass

class appcrypto(libnya.GlobalComputeNodeApp):

    def __init__(self):
        flowmod = libnya.AppFlowMod(1)  # First hop
        flowmodgroup = libnya.AppFlowModGroup(default_match=0x0800, port=80, action=1)
        flowmodgroup.append_mod(flowmod)
        text1 = libnya.AppUIText("name", "The Cache Test")
        row1 = libnya.AppUICols()
        row1.add_elem(text1)
        ui_elems = libnya.AppUIElement()
        ui_elems.add_row(row1)
        libnya.GlobalComputeNodeApp.__init__(self, 1, 1, flowmodgroup, ui_elems, sync, "cache_sync", interval=10)


app = appcrypto()
