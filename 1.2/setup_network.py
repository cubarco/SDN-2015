#!/usr/bin/env python
from mininet.cli import CLI
from mininet.link import Link
from mininet.net import Mininet
from mininet.node import RemoteController

if __name__ == '__main__':
    """
        Topology:
            c0    c0
            |     |
            s1 -- s2
            |     |
            h1    h2
    """
    net = Mininet(controller=RemoteController)

    c0 = net.addController('c0')

    s1 = net.addSwitch('s1')
    s2 = net.addSwitch('s2')

    h1 = net.addHost('h1')
    h2 = net.addHost('h2')

    print "Links: ",
    links = [(s1, h1), (s1, s2), (s2, h2)]
    for node1, node2 in links:
        print '({0}, {1})'.format(node1.name, node2.name), 
        Link(node1, node2)
    print
    
    net.build()
    c0.start()
    s1.start([c0])
    s2.start([c0])
    print "Setting protocols..."
    s1.cmd("ovs-vsctl set bridge s1 protocols=OpenFlow13")
    s2.cmd("ovs-vsctl set bridge s2 protocols=OpenFlow13")

    CLI(net)

    net.stop()
