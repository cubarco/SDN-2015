#!/usr/bin/env python
# coding=utf8

from scapy.all import *
import socket
import json
import urllib2

ETHERTYPE_CACHE_FILELIST_SYNC = 0x9998
DPID = 1
CACHE_FILELIST_ALL = '/tmp/proxy-out/filelist_all'
CACHE_FILELIST = '/tmp/proxy-out/list'
_CACHE_SERVER_LIST_STR = '10.0.0.1,10.0.0.2,10.0.0.3'
CACHE_SERVER_LIST = _CACHE_SERVER_LIST_STR.split(',')
CACHE_SERVER_STATIC_PORT = 8000

# capture every packet
sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
while True:
    data = sock.recv(65535)
    pkt = Ether(data)
    # TODO write scheduled job on the controller side
    if pkt.type != ETHERTYPE_CACHE_FILELIST_SYNC:
        continue

    filelist = {}
    for server in CACHE_SERVER_LIST:
        filelist.setdefault(server, [])
        opener = urllib2.urlopen('http://{}:{}/list'
                                 .format(server, CACHE_SERVER_STATIC_PORT)
                                 )
        filelist[server] = map(str.strip, opener.readlines())

    with open(CACHE_FILELIST_ALL, 'w') as f:
        f.write(json.dumps(filelist))
