#!/usr/bin/env python
# coding=utf8

import socket
import netifaces
import sys
import re
import fcntl
import struct
import time

from scapy.all import *


def getHwAddr(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', ifname[:15]))
    return ':'.join(['%02x' % ord(char) for char in info[18:24]])

ifaces = netifaces.interfaces()
for iface in ifaces:
    if re.findall('h\d*-eth\d*', iface):
        INTERFACE_NAME = iface
        break
else:
    print 'interface h*-eth* not found'
    sys.exit(-1)

MAC_ADDR = getHwAddr(INTERFACE_NAME)

s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
s.bind((INTERFACE_NAME, 0))

while True:
    raw_data = s.recv(1500)
    pkt = Ether(raw_data)
    if pkt.type == 0x9999:
        pkt.show()
        resp = Ether(src=MAC_ADDR, dst="ff:ff:ff:ff:ff:ff",
                     type=0x9999) / \
            ('{"func_id": 1234, "desc": "This is an example description.", \
            "mac": "%s"}' % MAC_ADDR)
        resp.show()
        print str(resp)
        s.send(str(resp))
        time.sleep(1)
