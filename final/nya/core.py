#!/usr/bin/env python
# coding=utf8

from __future__ import print_function

import jobs
import json
import time
import threading
import appmanager

from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.topology import event
from ryu.topology.api import get_link, get_switch
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, \
    DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.packet import packet, ethernet, arp, ipv4, udp


class NyaApp(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(NyaApp, self).__init__(*args, **kwargs)
        #self.name = 'NyaApp'
        self.scheduler = jobs.SchedulerWrapper()
        self.scheduler.add_job(self._hosts_topo_parse_job,
                               id='hosts topo parse job')
        self.scheduler.start()
        # hosts: {'xx:xx:xx:xx:xx:xx': {'dpid': int, 'port': int
        #                               'time': time.time()}, ...}
        self._hosts = {}
        # arp: {'xx:xx:xx:xx:xx:xx': {'dpid': int, 'ip': str,
        #                             'time': time.time()}, ...}
        self._arp = {}
        self._switches = []
        self._links = []
        self._hosts_expiry_time = 60*6  # 6mins
        self._arp_expiry_time = 60*60*4  # 4hrs
        self._last_clear_arp = time.time()
        self._last_clear_hosts = time.time()
        self._lock = threading.Lock()
        # switch_topo: {int: [int, int, ...], ...}
        self.switches_topo = {}
        # host_topo: {'xx:xx:xx:xx:xx:xx': {'ip': 'xxx.xxx.xxx.xxx',
        #                                   'dpid': int}, ...}
        self.hosts_topo = {}
        # func_table: {dpid: {'func_id': int, 'desc': str}, ...}
        self.func_table = {}
        # datapaths: {int: object, ...}
        self.datapaths = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def features_handler(self, ev):
        datapath = ev.msg.datapath
        # ofproto = datapath.ofproto
        # parser = datapath.ofproto_parser
        dpid = datapath.id
        self.datapaths[dpid] = datapath
        print('switch: %d connected' % dpid)
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(dst='ff:ff:ff:ff:ff:ff',
                                           src='00:00:00:00:00:00',
                                           ethertype=0x9999))
        self._send_packet(datapath, 1, pkt)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        in_port = msg.match['in_port']
        dpid = datapath.id
        ports = [int(link.to_dict()['src']['port_no'], 16)
                 for link in get_link(self, dpid)]

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        src = eth.src
        dst = eth.dst
        time_now = time.time()
        self.func_table.setdefault(dpid, {})
        if in_port not in ports:
            self._hosts[src] = {'dpid': dpid, 'time': time_now,
                                'port': in_port}

        if eth.ethertype == 0x9999:  # Nya func message
            raw_data = msg.data[14:]  # src(6) + dst(6) + type(2) + payload
            if not raw_data:
                return
            parsed_data = json.loads(raw_data)
            self.func_table[dpid] = dict(parsed_data)  # copy
            print(self.func_table)
        elif eth.ethertype == 0x0806:  # ARP packet
            arp_p = pkt.get_protocol(arp.arp)
            if arp_p.src_mac != '00:00:00:00:00:00':
                self._arp[arp_p.src_mac] = {'dpid': dpid, 'ip': arp_p.src_ip,
                                            'time': time_now}
            if arp_p.dst_mac != '00:00:00:00:00:00':
                self._arp[arp_p.dst_mac] = {'dpid': dpid, 'ip': arp_p.dst_ip,
                                            'time': time_now}
        elif eth.ethertype == 0x0800:  # IPv4 packet
            ip_p = pkt.get_protocol(ipv4.ipv4)
            if ip_p.proto == 17:
                udp_p = pkt.get_protocol(udp.udp)
                if udp_p.dst_port == 67 and udp_p.src_port == 68:  # DHCP
                    return
            self._arp[src] = {'dpid': dpid, 'ip': ip_p.src, 'time': time_now}
            self._arp[dst] = {'dpid': dpid, 'ip': ip_p.dst, 'time': time_now}

    @set_ev_cls(ofp_event.EventOFPStateChange, DEAD_DISPATCHER)
    def _connection_down(self, ev):
        dpid = ev.datapath.id
        if not dpid:
            return
        self._clear_arp(dpid)
        self._clear_hosts(dpid)

    @set_ev_cls([event.EventSwitchEnter, event.EventSwitchLeave])
    def _switch_change_handler(self, ev):
        switch_list = get_switch(self, None)
        switches = [switch.dp.id for switch in switch_list]
        links_list = get_link(self, None)
        links = [(link.src.dpid, link.dst.dpid) for link in links_list]
        with self._lock:
            self._switches = list(switches)  # copy
            self._links = list(links)  # copy
            switches_topo = {}
            gen = (link for link in links
                   if link[0] in switches and link[1] in switches)
            for link in gen:
                switches_topo.setdefault(link[0], [])
                # switches_topo.setdefault(link[1], [])
                switches_topo[link[0]].append(link[1])
                # switches_topo[link[1]].append(link[0])
            self.switches_topo = dict(switches_topo)  # copy
        # TODO Switches Topology changes here.
        print('switch:' + str(self.switches_topo))
        appmanager.coreapp.run(self)


    def _clear_arp(self, dpid=None):
        with self._lock:
            time_now = time.time()
            if not dpid and \
                    self._last_clear_arp + self._arp_expiry_time > time_now:
                return

            temp_list = []
            for src in self._arp:
                if self._arp[src]['time'] + \
                        self._arp_expiry_time < time_now or \
                   self._arp[src]['dpid'] == dpid:
                    temp_list.append(src)
            for src in temp_list:
                self._arp.pop(src)

            self._last_clear_arp = time_now

    def _clear_hosts(self, dpid=None):
        with self._lock:
            time_now = time.time()
            if not dpid and \
                    self._last_clear_hosts + \
                    self._hosts_expiry_time > time_now:
                return

            temp_list = []
            for src in self._hosts:
                if self._hosts[src]['time'] + \
                        self._hosts_expiry_time < time_now or \
                   self._hosts[src]['dpid'] == dpid:
                    temp_list.append(src)
            for src in temp_list:
                self._hosts.pop(src)

            self._last_clear_hosts = time_now

    def _hosts_topo_parse_job(self):
        self._clear_arp()
        self._clear_hosts()
        with self._lock:
            hosts = self._hosts
            arp = self._arp
            changed = False
            hosts_topo = {mac: {'ip': arp[mac]['ip'] if mac in arp else None,
                                'dpid': hosts[mac]['dpid'],
                                'port': hosts[mac]['port']} for mac in hosts}
            if set(hosts_topo.keys()) - set(self.hosts_topo.keys()):  # changed
                self.hosts_topo = dict(hosts_topo)  # copy
                changed = True
            else:
                for k in hosts_topo.keys():
                    if set(hosts_topo[k].values()) - \
                            set(self.hosts_topo[k].values()):  # changed
                        self.hosts_topo = dict(hosts_topo)
                        changed = True
                        break
            if changed:
                # TODO Hosts topo changed here
                print('hosts: ' + str(self.hosts_topo))
                appmanager.coreapp.run(self)


    def _add_flow(self, dpid, priority, match, actions, hard_timeout=0,
                  idle_timeout=0, buffer_id=None):
        datapath = self.get_datapath(dpid)
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    hard_timeout=hard_timeout,
                                    idle_timeout=idle_timeout,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    hard_timeout=hard_timeout,
                                    idle_timeout=idle_timeout,
                                    match=match, instructions=inst)
        print(mod)
        datapath.send_msg(mod)

    def _del_flow(self, dpid, table_id, match, actions,
                  out_port=ofproto_v1_3.OFPP_ANY):
        datapath = self.get_datapath(dpid)
        ofproto = ofproto_v1_3
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]

        mod = parser.OFPFlowMod(datapath, command=ofproto.OFPFC_DELETE,
                                table_id=table_id, match=match,
                                instructions=inst, out_port=ofproto.OFPP_ANY,
                                out_group=ofproto.OFPG_ANY)
        datapath.send_msg(mod)

    def _send_packet(self, datapath, out_port, pkt):
        ofproto = ofproto_v1_3
        parser = datapath.ofproto_parser
        pkt.serialize()
        data = pkt.data
        actions = [parser.OFPActionOutput(port=out_port)]
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=ofproto.OFPP_CONTROLLER,
                                  actions=actions,
                                  data=data)
        datapath.send_msg(out)

    def get_host_topology(self):
        return dict(self.hosts_topo)

    def get_switch_topology(self):
        return dict(self.switches_topo)

    def get_datapath(self, dpid):
        return self.datapaths.get(dpid, None)

    # need to modify the structure of func_table to produce usable return value
    def get_appids(self):
        pass

app_manager.require_app('./simple_switch_13.py', api_style=True)
