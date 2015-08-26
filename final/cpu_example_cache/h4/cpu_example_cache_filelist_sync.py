#!/usr/bin/env python
# coding=utf8

from scapy.all import *
import socket
import json
import urllib2
import os

ETHERTYPE_CACHE_FILELIST_SYNC = 0x9998
DPID = 3
CACHE_DIR = '/tmp/cache-server/h4/'
CACHE_FILELIST_ALL = CACHE_DIR + 'filelist_all'
CACHE_FILELIST = CACHE_DIR + 'list'
_CACHE_SERVER_LIST_STR = '10.0.0.1,10.0.0.4'
CACHE_SERVER_LIST = _CACHE_SERVER_LIST_STR.split(',')
CACHE_SERVER_STATIC_PORT = 8000

if not os.path.exists(os.path.dirname(CACHE_DIR)):
    os.makedirs(os.path.dirname(CACHE_DIR))

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
        try:
            opener = urllib2.urlopen('http://{}:{}/list'
                                     .format(server, CACHE_SERVER_STATIC_PORT)
                                     )
        except urllib2.HTTPError:
            pass
        except urllib2.URLError:
            pass
        else:
            filelist[server] = map(str.strip, opener.readlines())

    with open(CACHE_FILELIST_ALL, 'w') as f:
        f.write(json.dumps(filelist))
