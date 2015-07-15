#!/bin/env python3
import socket
import re
import sys
import os
from uuid import getnode
from scapy.all import *



def is_dns(p):
    try:
        return (p.haslayer(DNS) and p[UDP].dport == 53)
    except:
        return False

def handlepkt(p):
    dnsfield = p.getlayer(DNS)
    flag = True
    if (dnsfield == None) or (dnsfield.qr == 1) or (p.dst.upper() == localmac) or (p.src.upper() == localmac):
        return None
    for record in dnsfield.qd:
        for re_list in rules.re_list:
            if re_list[0].search(record.qname.decode()):
                print("url in blacklist,dropping.")
                flag = False
                break
        if not flag:
            break
    if flag:
        server = p.getlayer(IP).dst
        for record in dnsfield.qd:
            ret = sr1(IP(dst = server)/UDP(dport = 53)/DNS(rd = 1, qd = DNSQR(qname = record.qname)), iface = "h4-eth0", timeout = 2)
            if ret and ret.haslayer(DNS):
                dnsp = DNS(id = dnsfield.id, qr = 1, opcode = 0, rd = 1, ra = 1, rcode =0, qdcount = ret[DNS].qdcount, ancount = ret[DNS].ancount, nscount = ret[DNS].nscount, arcount = ret[DNS].arcount, qd = ret[DNS].qd, an = ret[DNS].an, ns = ret[DNS].ns, ar = ret[DNS].ar)
                retp = IP(src = server, dst = p[IP].src)/UDP(dport = p[UDP].sport)/dnsp
                send(retp)
    return record.qname


class ruleEngine:
    def __init__(self,file):
        self.re_list = []
        print('>>' , 'Parsing rules...')
        with open(file,'r') as rulefile:
            rules = rulefile.readlines()
            for rule in rules:
                splitrule = rule.split()

                # If the ip is 'self' transform it to local ip.
                if splitrule[1] == 'self':
                    ip = socket.gethostbyname(socket.gethostname())
                    splitrule[1] = ip

                self.re_list.append([re.compile(splitrule[0]),splitrule[1]])
                print ('>>', splitrule[0], '->', splitrule[1])
            print ('>>', str(len(rules)) + " rules parsed")

def get_mac():
    mac = getnode()
    return ':'.join(("%012X" % mac)[i:i+2] for i in range(0, 12, 2))

rules = None
localmac = get_mac()


if __name__ == '__main__':
    # Default config file path.
    path = 'dns.conf'

    # Specify a config path.
    if len(sys.argv) == 2:
        path = sys.argv[1]

    if not os.path.isfile(path):
        print ('>> Please create a "dns.conf" file or specify a config path: ./fakedns.py [configfile]')
        exit()
    rules = ruleEngine(path)
    re_list = rules.re_list
    sniff(store=0, iface = "h4-eth0", prn = handlepkt, lfilter = is_dns)
