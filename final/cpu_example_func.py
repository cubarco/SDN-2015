#!/usr/bin/env python
# coding=utf8

import socket

s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
# From the docs: "For raw packet
# sockets the address is a tuple (ifname, proto [,pkttype [,hatype]])"
s.bind(('h1-eth0', 0))
while True:
    print(', '.join(map(lambda x: hex(ord(x)), s.recv(2048))))
    done = 1
    if not done:
        s.send('\x00' * 6 + '\xFF' * 6 + '\x99\x99' +
               '{"func_id": 1234, "desc": "This is an example description."}')
