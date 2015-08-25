#!/bin/env python2
# coding=utf8

import libnya


class appcrypto(libnya.GlobalComputeNodeApp):

    def __init__(self):
        flowmod1 = libnya.AppFlowMod(1)  # First hop
        flowmod2 = libnya.AppFlowMod(-1)  # Last hop
        flowmodgroup = libnya.AppFlowModGroup(default_match=0x0800, action=1)
        flowmodgroup.append_mod(flowmod1)
        flowmodgroup.append_mod(flowmod2)
        text1 = libnya.AppUIText("name", "Crypto Test")
        row1 = libnya.AppUICols()
        row1.add_elem(text1)
        ui_elems = libnya.AppUIElement()
        ui_elems.add_row(row1)
        libnya.GlobalComputeNodeApp.__init__(self, 1, 1, flowmodgroup, ui_elems)


app = appcrypto()
