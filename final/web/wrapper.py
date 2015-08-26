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

TEMPLATE_TIP = '''\
<div class="col-sm-6 col-md-4">
  <div class="thumbnail">
    <div class="caption">
      <h3>{title}</h3>
      <p>
        {tip}
      </p>
      <p>
        <a href="#" class="btn btn-default" role="button" data-toggle="modal" data-target="{target}" >More &raquo;</a>
      </p>
    </div>
  </div>
</div>
'''

TEMPLATE_MODAL = '''\
<div class="modal fade" id="{id}" tabindex="-1" role="dialog" aria-labelledby="myModalLabel" aria-hidden="true">
  <div class="modal-dialog">
    <div class="modal-content">
      <div class="modal-header">
        <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
        <h4 class="modal-title" id="myModalLabel">{title}</h4>
      </div>
      <div class="modal-body">
        {modal_body}
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
      </div>
    </div>
  </div>
</div>
'''

METHODS = ['mirrored', 'redirected', 'droped']

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


@route('/status-tip')
def status_thum():
    if not os.path.exists('/tmp/webui.json'):
        return

    data = json.loads(open('/tmp/webui.json').read())
    tips = []
    for k, v in data.items():
        tips.append(TEMPLATE_TIP.format(title=k, tip=v['tip'],
                                        target='#%s_target' % k))
    return '\n'.join(tips)


@route('/status-modal')
def status_modal():
    if not os.path.exists('/tmp/webui.json'):
        return

    data = json.loads(open('/tmp/webui.json').read())
    modals = []
    for k, v in data.items():
        hop_src = ','.join([str(i) for i in v['hop'] if i > 0])
        if not hop_src:
            hop_src = '0'

        hop_dst = ','.join([str(abs(i)) for i in v['hop'] if i < 0])
        if not hop_dst:
            hop_dst = '0'

        match = ', '.join([
            ': '.join(map(str, kv)) for kv in v['match'].items()])

        content = '''\
<p>The appid of this application is {appid}.</p>
<p>The current state of this application is {state}. There are {flow_tables} flow entries for this app. It requires packet that {hop_src} hop(s) from the source hosts and {hop_dst} hop(s) from the destination hosts that matches the following conditions to be {method} to cpu for further processing:</p>
<p><code>{match}</code></p>'''\
    .format(appid=v['appid'], state='<font color="green">ON</font>'
            if v['enabled'] else '<font color="red">OFF</font>',
            hop_src=hop_src, hop_dst=hop_dst, match=match,
            method=METHODS[v['method']], flow_tables=v['flow_tables'])

        modals.append(TEMPLATE_MODAL.format(title=k, modal_body=content,
                                            id='%s_target' % k))
    return '\n'.join(modals)

run(host="localhost", port=8000, debut=True)
