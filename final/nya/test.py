#!/bin/env python2
#coding=utf8

import libnya

class test(libnya.GlobalComputeNodeApp):

    def __init__(self):
        flowmodgroup = libnya.AppFlowModGroup(action=1)
        flowmodgroup.append_mod(libnya.AppFlowMod(1))
        libnya.GlobalComputeNodeApp.__init__(self, 111, 1, flowmodgroup)


app = test()
