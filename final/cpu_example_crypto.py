#!/usr/bin/env python
# coding=utf8

from scapy.all import *
from Crypto.Cipher import AES
import socket
import netifaces
import re
import sys

ifaces = netifaces.interfaces()
for iface in ifaces:
    if re.findall('h\d*-eth\d*', iface):
        INTERFACE_NAME = iface
        break
else:
    print 'interface h*-eth* not found'
    sys.exit(-1)


# from /usr/include/linux/if_ether.h
ETH_P_IP = 0x0800

# for cipher object, must be 16, 24 or 32 for AES
BLOCK_SIZE = 32
SECRET_KEY = '1' * BLOCK_SIZE

# the character used for padding--with a block cipher such as AES, the value
# you encrypt must be a multiple of BLOCK_SIZE in length.  This character is
# used to ensure that your value is always a multiple of BLOCK_SIZE
PADDING = '{'

ENCODED_IDENTIFIER = 'yooo'


# pad the text to be encrypted
def pad(s):
    return s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING


def EncodeAES(c, s):
    return c.encrypt(pad(s))


def DecodeAES(c, e):
    return c.decrypt(e).rstrip(PADDING)

cipher = AES.new(SECRET_KEY)
sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_IP))
while True:
    raw_data = sock.recv(1500)
    pkt = Ether(raw_data)
    # Encode the whole layer 3(IP)
    ip = str(pkt.payload)
    if ip[:len(ENCODED_IDENTIFIER)] == ENCODED_IDENTIFIER:  # this is encoded
        decoded = DecodeAES(cipher, ip[len(ENCODED_IDENTIFIER):])
        pkt.payload = decoded
        print 'decoded size: ' + str(len(str(pkt)))
        sendp(pkt, iface=INTERFACE_NAME)
    else:  # this packet is not encoded
        encoded = ENCODED_IDENTIFIER + EncodeAES(cipher, ip)
        pkt.payload = encoded
        # drop bytes over 1500(MTU)
        pkt = Ether(str(pkt)[:1500])
        print 'encoded size: ' + str(len(str(pkt)))
        sendp(pkt, iface=INTERFACE_NAME)
