#!/bin/env python2
# coding=utf8

import ryu.app.ofctl.api
from ryu.ofproto import ofproto_v1_3


class AppFlowMod(object):

    '''用于标识该规则组需要将拓扑中的哪一跳送入CPU'''

    LAST_HOOP = -1
    FIRST_HOP = 1
    EVERY_HOP = 0

    def __init__(self, hop_num):
        self.hop = hop_num


class AppFlowModGroup(object):

    '''用于标识在一个app要求的需要送入CPU的点以及送入方式，default_flow_table和action只能使用其中之一'''

    ACTION_MIRROR = 0
    ACTION_REDIRECT_IN = 1
    ACTION_DROP = 2
    OFF = 0
    ON = 1

    def __init__(self, default_state=ON, default_match=None, action=ACTION_MIRROR):
        self.flow_mod = []
        self.default_match = default_match
        self.state = default_state
        self.action = action

    def append_mod(self, i):
        self.flow_mod.append(i)


class AppUIText(object):

    '''表示在webUI上显示一串文字'''

    UI_ID = 0

    def __init__(self, text):
        self.text = text


class AppUIEntry(object):

    '''表示在webUI上显示一个文本框'''

    UI_ID = 1

    def __init__(self, default_text):
        self.text = default_text


class AppUICols(object):

    '''表示webUI上的一行元素，由前两个类的列表组成'''

    def __init__(self):
        self.cols = []

    def add_elem(self, i):
        self.cols.append(i)

    def del_elem(self, num):
        del self.cols[num]


class AppUIElement(object):

    '''表示一个app需要在webUI上显示的所有东西，由上一个类的列表组成'''

    def __init__(self):
        self.rows = []

    def add_row(self, row):
        self.rows.append(row)

    def del_row(self, num):
        del self.rows[num]

# 尚未实现webUI，应当对coreapp中注册的每一个app生成一个页面，页面内容由该app的UIElement决定


class simpleflow(object):

    '''辅助类'''

    def __init__(self, action, from_mac=None, to_mac=None):
        self.from_mac = from_mac
        self.to_mac = to_mac
        self.action = action


class GlobalComputeNodeApp(object):

    '''所有用户app应继承自此类，并定义好其中的flow_mod_group和UIElemnt，然后调用register注册到coreapp'''

    def __init__(self, appid, enable=0, flow_mod_group=None, ui_elem=None):
        self.appid = appid
        self.enable = enable
        self.flow_mod_groups = [flow_mod_group]
        self.ui_elems = [ui_elem]
        self.flow_table = {}
        if self.flow_mod_groups[0] == None:
            self.flow_mod_groups = []
        if self.ui_elems[0] == None:
                self.ui_elems = []

    def add_flow_mod_group(self, group):
        self.flow_mod_groups.append(group)

    def del_flow_mod_group(self, num):
        del self.flow_mod_groups[num]

    def add_ui_elem(self, ui_elem):
        self.ui_elems.append(ui_elem)

    def del_ui_elem(self, num):
        del self.ui_elems[num]

    def register(self):
        global coreapp
        coreapp.apps.append(self)

    # This function is called when value of webUI of this app changed
    # must be implemented by user.
    def update_state(self):
        pass
