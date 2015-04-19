# Copyright (C) 2013 Nippon Telegraph and Telephone Corporation.
# Copyright (C) 2014 UniqueSDNStudio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import time
from webob import Response

from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.base import app_manager
from ryu.lib import dpid as dpid_lib
from ryu.topology.api import get_switch, get_link
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, arp

# REST API for switch configuration
#
# get all the switches
# GET /v1.0/topology/switches
#
# get the switch
# GET /v1.0/topology/switches/<dpid>
#
# get all the links
# GET /v1.0/topology/links
#
# get the links of a switch
# GET /v1.0/topology/links/<dpid>
#
# get all the hosts
# GET /v1.0/topology/hosts
#
# where
# <dpid>: datapath id in 16 hex


class TopologyAPI(app_manager.RyuApp):
    _CONTEXTS = {
        'wsgi': WSGIApplication
    }
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    
    def __init__(self, *args, **kwargs):
        super(TopologyAPI, self).__init__(*args, **kwargs)

        wsgi = kwargs['wsgi']
        wsgi.register(TopologyController, {'topology_api_app': self})
        # hosts: {'xx:xx:xx:xx:xx:xx': {'dpid': int, 'time': time.time()}, ...}
        self.hosts = {}
        # arp: {'xx:xx:xx:xx:xx:xx': {'dpid': int, 'ip': str,
        #                             'time': time.time()}, ...}
        self.arp = {}
        self.hosts_expiry_time = 60*6 # 6mins
        self.arp_expiry_time = 60*60*4 # 4hrs
        self.last_clear_arp = time.time()
        self.last_clear_hosts = time.time()
    
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id
        ports = [int(link.to_dict()['src']['port_no'], 16)
                 for link in get_link(self, dpid)]

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        src = eth.src
        time_now = time.time()
        if eth.ethertype == 0x0806: # ARP packet
            arp_p = pkt.get_protocols(arp.arp)[0]
            if arp_p.src_mac != '00:00:00:00:00:00':
                self.arp[arp_p.src_mac] = {'dpid': dpid, 'ip': arp_p.src_ip,
                                           'time': time_now}
            if arp_p.dst_mac != '00:00:00:00:00:00':
                self.arp[arp_p.dst_mac] = {'dpid': dpid, 'ip': arp_p.dst_ip,
                                           'time': time_now}
            return

        if in_port not in ports:
            self.hosts[src] = {'dpid': dpid, 'time': time_now}

    @set_ev_cls(ofp_event.EventOFPStateChange, DEAD_DISPATCHER)
    def _connection_down(self, ev):
        dpid = ev.datapath.id
        if not dpid:
            return
        self.clear_arp(dpid)
        self.clear_hosts(dpid)

    def clear_arp(self, dpid=None):
        time_now = time.time()
        if not dpid and self.last_clear_arp + self.arp_expiry_time > time_now:
            return

        temp_list = []
        for src in self.arp:
            if self.arp[src]['time'] + self.arp_expiry_time < time_now or \
               self.arp[src]['dpid'] == dpid:
                temp_list.append(src)
        for src in temp_list:
            self.arp.pop(src)

        self.last_clear_arp = time_now

    def clear_hosts(self, dpid=None):
        time_now = time.time()
        if not dpid and self.last_clear_hosts + self.hosts_expiry_time > time_now:
            return

        temp_list = []
        for src in self.hosts:
            if self.hosts[src]['time'] + self.hosts_expiry_time < time_now or \
               self.hosts[src]['dpid'] == dpid:
                temp_list.append(src)
        for src in temp_list:
            self.hosts.pop(src)

        self.last_clear_hosts = time_now

    def get_hosts(self):
        self.clear_arp()
        self.clear_hosts()
        hosts = self.hosts
        arp = self.arp
        return json.dumps({arp[src]['ip']: hosts[src]['dpid']
                           for src in hosts if src in arp})


class TopologyController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(TopologyController, self).__init__(req, link, data, **config)
        self.topology_api_app = data['topology_api_app']

    @route('topology', '/v1.0/topology/switches',
           methods=['GET'])
    def list_switches(self, req, **kwargs):
        return self._switches(req, **kwargs)

    @route('topology', '/v1.0/topology/switches/{dpid}',
           methods=['GET'], requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_switch(self, req, **kwargs):
        return self._switches(req, **kwargs)

    @route('topology', '/v1.0/topology/links',
           methods=['GET'])
    def list_links(self, req, **kwargs):
        return self._links(req, **kwargs)

    @route('topology', '/v1.0/topology/links/{dpid}',
           methods=['GET'], requirements={'dpid': dpid_lib.DPID_PATTERN})
    def get_links(self, req, **kwargs):
        return self._links(req, **kwargs)

    @route('topology', '/v1.0/topology/hosts',
           methods=['GET'])
    def get_hosts(self, req, **kwargs):
        return self.topology_api_app.get_hosts()

    def _switches(self, req, **kwargs):
        dpid = None
        if 'dpid' in kwargs:
            dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        switches = get_switch(self.topology_api_app, dpid)
        body = json.dumps([switch.to_dict() for switch in switches])
        return Response(content_type='application/json', body=body)

    def _links(self, req, **kwargs):
        dpid = None
        if 'dpid' in kwargs:
            dpid = dpid_lib.str_to_dpid(kwargs['dpid'])
        links = get_link(self.topology_api_app, dpid)
        body = json.dumps([link.to_dict() for link in links])
        return Response(content_type='application/json', body=body)
