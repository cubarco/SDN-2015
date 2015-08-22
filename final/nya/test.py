#!/bin/env python2
#coding=utf8

import libnya

class test(libnya.GlobalComputeNodeApp):

    def __init__(self):
        libnya.GlobalComputeNodeApp.__init__(self, 111, 1)


app = test()
