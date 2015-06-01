#!/usr/bin/env python
# Copyright (C) 2015 UniqueSDNStudio
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

import os
import json
import requests
import networkx as nx
from networkx.readwrite import json_graph
from bottle import route, post, run, static_file, response, request
from urllib2 import urlopen, URLError

CURDIR = os.curdir
pop_list = ['duration_sec', 'duration_nsec', 'packet_count', 'byte_count',
            'actions', 'length']


@route('/static/<filename>')
def server_static(filename):
    return static_file(filename, root=CURDIR + '/static/')


@route('/topo')
def topo():
    try:
        links = json.loads(urlopen("http://localhost:8080/v1.0/topology/links")
                           .read())
        switches = json.loads(urlopen(
                        "http://localhost:8080/v1.0/topology/switches").read())
        hosts = json.loads(urlopen(
                        "http://localhost:8080/v1.0/topology/hosts").read())
    except URLError:
        response.status = 500
        return
    g = nx.Graph()

    for switch in switches:
        dpid = "dpid: %d" % int(switch['dpid'], 16)
        g.add_node(dpid, group=1)

    for host in hosts:
        g.add_node(host, group=2)

    for link in links:
        src = "dpid: %d" % int(link['src']['dpid'], 16)
        dst = "dpid: %d" % int(link['dst']['dpid'], 16)
        g.add_edge(src, dst, value=9)

    for host in hosts:
        src = host
        dst = "dpid: %d" % hosts[host]
        g.add_edge(host, dst, value=1)

    data = json_graph.node_link_data(g)
    response.set_header('Content-Type', 'application/json')
    return data


@route('/flow')
def flow():
    switches = json.loads(urlopen("http://localhost:8080/stats/switches")
                          .read())
    resp_j = []
    known_flows = []
    for dpid in switches:
        orig_j = json.loads(urlopen("http://localhost:8080/stats/flow/%d" %
                                    dpid).read())
        orig_j = orig_j[str(dpid)]
        for flow in orig_j:
            flow['dpid'] = str(dpid)

            flow_tmp = flow.copy()
            for pop_item in pop_list:
                if pop_item in flow_tmp:
                    flow_tmp.pop(pop_item)
            known_flows.append(flow_tmp)

            flow['actions'] = ','.join(flow['actions']).replace('4294967293',
                                                                'CONTROLLER')
            flow['match'] = ','.join(['{0}={1}'.format(field, value)
                                      for field, value
                                      in flow['match'].iteritems()])
            resp_j.append(flow)
    with open('known_flows', 'w') as f:
        f.write(json.dumps(known_flows))
    response.set_header('Content-Type', 'application/json')
    return json.dumps(resp_j, indent=2)


@post('/delete')
def delete():
    keys = request.json
    with open('known_flows') as f:
        known_flows = json.loads(f.read())
    if not keys or len(known_flows) < len(keys):
        response.status = 500
        return

    url = "http://localhost:8080/stats/flowentry/delete_strict"
    headers = {'Content-Type': 'application/json'}
    for i in keys:
        payload = json.dumps(known_flows[i])
        requests.post(url, data=payload, headers=headers)


@post('/add')
def add():
    items = request.forms.allitems()
    req = {}
    for key, value in items:
        if len(value) != 0:
            req.setdefault(key, value)
    matches = req.get('match', str)
    actions = req.get('actions', str)
    req['match'] = {}
    req['actions'] = []

    for match in matches.split(','):
        kv = map(str.strip, match.split(':'))
        if len(kv) != 2:
            kv = map(str.strip, match.split('='))
        if len(kv) == 2:
            req['match'].setdefault(kv[0], kv[1])

    for action in actions.split(';'):
        action_toappend = {}
        for kv_s in action.split(','):
            kv = map(str.strip, kv_s.split(':'))
            if len(kv) != 2:
                kv = map(str.strip, kv_s.split('='))
            if len(kv) == 2:
                if kv[0] == 'type':
                    kv[1] = kv[1].upper()
                action_toappend.setdefault(kv[0], kv[1])
        req['actions'].append(action_toappend)

    url = "http://localhost:8080/stats/flowentry/add"
    headers = {'Content-Type': 'application/json'}
    payload = json.dumps(req)
    requests.post(url, data=payload, headers=headers)

run(host="localhost", port=8000, debut=True)
