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
        if self.ui_elemsp0[0] == None:
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



class AppManager(object):

    '''用于管理用户app，在初始化及网路拓扑改变时应当调用run方法重新下发流表'''

    def __init__(self):
        self.flow_table = {}
        self.apps = []

    def dfs(self, level, host, switch, switches, level_map, h_s_map, searched):
        for n_switch in switches[switch]:
            if n_switch not in searched:
                searched.append(n_switch)
                if n_switch in level_map[host]:
                    if level < level_map[host][n_switch]:
                        h_s_map[host][level_map[host][n_switch]].remove(n_switch)
                        level_map[host][n_switch] = level
                        h_s_map[host][level].append(n_switch)
                else:
                    level_map[host][n_switch] = level
                    h_s_map[host][level].append(n_switch)
                self.dfs(level + 1, host, n_switch, switches, level_map, h_s_map, searched)

    def find_levels(self, hosts, switches, h_s_map):
        level_map = {}
        for host in hosts.keys():
            n_switch = hosts[host]
            searched = [n_switch]
            if host not in h_s_map:
                h_s_map[host] = {1: [n_switch]}
            else:
                if host in level_map:
                    if n_switch in level_map[host]:
                        h_s_map[host][level_map[host][n_switch]].remove(n_switch)
                h_s_map[host][1].append(n_switch)
            if host not in level_map:
                level_map[host] = {n_switch: 1}
            else:
                level_map[host][n_switch] = 1
            self.dfs(2, host, n_switch, switches, level_map, h_s_map, searched)

    def run(self, nyaapp):
        hosts = nyaapp.get_host_topology()
        switches = nyaapp.get_switch_topology()
        supported_apps = nyaapp.get_appids()
        temp_flow_table = {}
        h_s_map = {}
        self.find_levels(hosts, switches, h_s_map)
        for app in self.apps:
            if app.appid not in supported_apps:
                continue
            for flow_mod_group in app.flow_mod_groups:
                if flow_mod_group.state == AppFlowModGroup.OFF:
                    continue
                for hop in flow_mod_group:
                    if hop > 0:
                        for host in hosts:
                            for sw in h_s_map[host][hop]:
                                if temp_flow_table[sw] is None:
                                    temp_flow_table[sw] = set([])
                                temp_flow_table[sw].add(simpleflow(from_mac=host, action=flow_mod_group.action))
                    elif hop < 0:
                        for host in hosts:
                            for sw in h_s_map[host][-hop]:
                                if temp_flow_table[sw] is None:
                                    temp_flow_table[sw] = set([])
                                temp_flow_table[sw].add(simpleflow(to_mac=host, action=flow_mod_group.action))
                    else:
                        for sw in switches.keys():
                            if temp_flow_table[sw] is None:
                                temp_flow_table[sw] = set([])
                            temp_flow_table[sw].add(simpleflow(action=flow_mod_group.action))
            flow_table_mod = []

        for sw in switches:
            if self.flow_table[sw] == temp_flow_table[sw]:
                continue
            if self.flow_table[sw] is not None:
                if temp_flow_table[sw] is not None:
                    for flow in self.flow_table[sw]:
                        if flow not in temp_flow_table[sw]:
                            flow_table_mod.append((sw, flow, 'del'))
                else:
                    for flow in self.flow_table[sw]:
                        flow_table_mod.append((sw, flow, 'del'))
            if temp_flow_table[sw] is not None:
                if self.flow_table[sw] is not None:
                    for flow in temp_flow_table[sw]:
                        if flow not in self.flow_table[sw]:
                            flow_table_mod.append((sw, flow, 'add'))
                else:
                    for flow in temp_flow_table[sw]:
                        flow_table_mod.append((sw, flow, 'add'))

        for sw, flow, operation in flow_table_mod:
            datapath = ryu.app.ofctl.api.get_datapath(nyaapp, sw)
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            action = None
            if flow.action == AppFlowModGroup.ACTION_DROP:
                pass
            # Mirror function incomplete, missing multiple flow table
            elif flow.action == AppFlowModGroup.ACTION_MIRROR | flow.action == AppFlowModGroup.ACTION_REDIRECT_IN:
                action = [parser.OFPActionOutput(1)]
            match = parser.OFPMatch(eth_src=flow.from_mac, eth_dst=flow.to_mac)
            nyaapp.add_flow(datapath, 2, match, action)


coreapp = AppManager()
