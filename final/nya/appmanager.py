#!/bin/env python2
# coding=utf8

import ryu.app.ofctl.api
import importlib
from ryu.ofproto import ofproto_v1_3


class simpleflow(object):
    def __init__(self, action, from_mac=None, to_mac=None):
        self.__from_mac = from_mac
        self.__to_mac = to_mac
        self.__action = action

    def get_from_mac(self):
        return self.__from_mac

    def get_to_mac(self):
        return self.__to_mac

    def get_action(self):
        return self.__action

class AppManager(object):

    '''用于管理用户app，在初始化及网路拓扑改变时应当调用run方法重新下发流表'''

    def __init__(self):
        self.flow_table = {}
        self.apps = []

    def bfs(self, level, host, f_switches, switches, h_s_map, searched):
        nf_switches = []
        for f_switch in f_switches:
            for n_switch in switches[f_switch]:
                if n_switch not in searched:
                    searched.append(n_switch)
                    nf_switches.append(n_switch)
                    h_s_map[host].setdefault(level, []).append(n_switch)
        if len(nf_switches) != 0:
            self.bfs(level+1, host, nf_switches, switches, h_s_map, searched)

    def find_levels(self, hosts, switches, h_s_map):
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
            self.bfs(2, host, [n_switch], switches, h_s_map, searched)

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
                if flow_mod_group.state == 0:
                    continue
                for hop in flow_mod_group.flow_mod:
                    if hop.hop > 0:
                        for host in hosts:
                            for sw in h_s_map[host][hop.hop]:
                                temp_flow_table.setdefault(sw, set([])).add(simpleflow(from_mac=host, action=flow_mod_group.action))
                    elif hop.hop < 0:
                        for host in hosts:
                            for sw in h_s_map[host][-hop.hop]:
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
            if self.flow_table.get(sw) == temp_flow_table.get(sw):
                continue
            if self.flow_table.get(sw) is not None:
                if temp_flow_table.get(sw) is not None:
                    for flow in self.flow_table[sw]:
                        if flow not in temp_flow_table[sw]:
                            flow_table_mod.append((sw, flow, 'del'))
                else:
                    for flow in self.flow_table[sw]:
                        flow_table_mod.append((sw, flow, 'del'))
            if temp_flow_table.get(sw) is not None:
                if self.flow_table.get(sw) is not None:
                    for flow in temp_flow_table[sw]:
                        if flow not in self.flow_table[sw]:
                            flow_table_mod.append((sw, flow, 'add'))
                else:
                    for flow in temp_flow_table[sw]:
                        flow_table_mod.append((sw, flow, 'add'))
                        
        self.flow_table = temp_flow_table
        
        for sw, sflow, act in flow_table_mod:
            print "sw %d flow from %s to %s action %d %sed"%(sw, sflow.get_from_mac(), sflow.get_to_mac(), sflow.get_action(), act)

        for sw, flow, operation in flow_table_mod:
            datapath = ryu.app.ofctl.api.get_datapath(nyaapp.get_ryu(), sw)
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            action = None
            if flow.action == 2:#AppFlowModGroup.ACTION_DROP
                pass
            # Mirror function incomplete, missing multiple flow table
        elif flow.action == 0 || flow.action == 1:#AppFlowModGroup.ACTION_MIRROR | AppFlowModGroup.ACTION_REDIRECT_IN:
                action = [parser.OFPActionOutput(1)]
            match = parser.OFPMatch(eth_src=flow.get_from_mac(), eth_dst=flow.get_to_mac())
            if operation == 'add':
                nyaapp.add_flow(datapath, 2, match, action)
            else:
                nyaapp.del_flow(datapath, 0, match, action)


coreapp = AppManager()
config = open('./app.config', 'r')
applist = config.readlines()
apps = []
for appname in applist:
    try:
        apps.append(importlib.import_module(appname.rstrip('\n')))
    except:
        print 'import failed'
for app in apps:
    app.app.register(coreapp)
