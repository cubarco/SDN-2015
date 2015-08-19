#!/usr/bin/env python
# coding=utf8

import socket

s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
# From the docs: "For raw packet
# sockets the address is a tuple (ifname, proto [,pkttype [,hatype]])"
s.bind(('h1-eth0', 0))
s.send('\x00' * 6 + '\xFF' * 6 + '\x99\x99' +
       '{"func_id": 1234, "desc": "This is an example description."}')
