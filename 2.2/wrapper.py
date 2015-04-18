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
    except URLError:
        response.status = 500
        return
    g = nx.Graph()

    for switch in switches:
        dpid = "dpid: %d" % eval('0x' + switch['dpid'])
        g.add_node(dpid)

    for link in links:
#        src = link['src']['dpid'].split('-')[0]
#        dst = link['dst']['name'].split('-')[0]
        src = "dpid: %d" % eval('0x' + link['src']['dpid'])
        dst = "dpid: %d" % eval('0x' + link['dst']['dpid'])
#        src = link['src']['hw_addr']
#        dst = link['dst']['hw_addr']
        g.add_edge(src, dst)
    data = json_graph.node_link_data(g)
    response.set_header('Content-Type', 'application/json')
    return data

@route('/flow')
def flow():
    switches = json.loads(urlopen("http://localhost:8080/stats/switches").read())
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
        r = requests.post(url, data=payload, headers=headers)

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
