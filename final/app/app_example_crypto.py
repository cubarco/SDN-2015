#!/bin/env python2
# coding=utf8

import libnya


class AppCrypto(libnya.GlobalComputeNodeApp):

    def __init__(self):
        flowmod1 = libnya.AppFlowMod(1)  # First hop
        flowmod2 = libnya.AppFlowMod(-1)  # Last hop
        flowmodgroup = libnya.AppFlowModGroup(default_match={'eth_type': 0x0800}, action=1)
        flowmodgroup.append_mod(flowmod1)
        flowmodgroup.append_mod(flowmod2)
        text1 = libnya.AppUIText("name", "Crypto Test")
        row1 = libnya.AppUICols()
        row1.add_elem(text1)
        ui_elems = libnya.AppUIElement()
        ui_elems.add_row(row1)
        libnya.GlobalComputeNodeApp.__init__(self, 2, "This Application is used to encrypt the IP packets when they come into the network and decrypt them when are to leave the network", 1, flowmodgroup, ui_elems)


app = AppCrypto()
