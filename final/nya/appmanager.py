#!/bin/env python2
# coding=utf8

import ryu.app.ofctl.api
import importlib
from ryu.ofproto import ofproto_v1_3



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
config = open('app.config', 'r')
applist = config.readlines()
apps = []
for appname in applist:
    try:
        apps.append(importlib.import_module('..'++appname))
    except:
        pass

for app in apps:
    app.app.register()
