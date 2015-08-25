#!/usr/bin/env python2
# coding=utf-8

import socket
import thread
import sys
import os
import json

MAX_DATA_RECV = 81920
SERVER_ADDR = '10.0.0.1'
SERVER_PORT = 80
REDIRECT_ADDR = '10.0.0.1'
REDIRECT_PORT = 8000
CACHE_DIR = '/tmp/cache-server/h1/'
CACHE_SIZE = 50 * 1024  # 50KB
CACHE_FILELIST = CACHE_DIR + 'list'
CACHE_FILELIST_ALL = CACHE_DIR + 'filelist_all'

if not os.path.exists(os.path.dirname(CACHE_DIR)):
    os.makedirs(os.path.dirname(CACHE_DIR))
if os.path.exists(CACHE_FILELIST_ALL):
    os.remove(CACHE_FILELIST_ALL)
if os.path.exists(CACHE_FILELIST):
    os.remove(CACHE_FILELIST)


def main():
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((SERVER_ADDR, SERVER_PORT))
        server.listen(5)
    except socket.error, (value, message):
        if server:
            server.close()
        print "Could not open socket:", message
        sys.exit(1)

    while 1:
        conn, client_addr = server.accept()
        #create a BP socket
        thread.start_new_thread(BPS, (server, conn, client_addr))

    server.close()


def BPS(server, conn, client_addr):
    request = conn.recv(MAX_DATA_RECV)
    print request
    got = getaddr_port(request)
    (firstline, webserver, port, url) = (got[0], got[1], got[2], got[3])
    thread.start_new_thread(SPB, (request, conn, webserver, port, url))


def SPB(request, conn, webserver, port, url):
    try:
        proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        proxy.connect((webserver, port))
        proxy.sendall(request)
        cache_filename = webserver + url
        if cache_filename[-1] == '/':
            cache_filename = cache_filename + 'index.html'
        full_filename = CACHE_DIR + cache_filename
        print 'cache_filename: ' + cache_filename
        print 'full_filename: ' + full_filename

        with open(CACHE_FILELIST_ALL) as f:
            filelist_all = json.loads(f.read())
        for k, v in filelist_all.items():
            if cache_filename in v:
                conn.send('HTTP/1.1 302 Found\r\nLocation: http://{}:{}/{}\r\n'
                          .format(k, REDIRECT_PORT, cache_filename))
                break
        else:  # no break then else
            to_cache = False
            data = proxy.recv(MAX_DATA_RECV)
            double_crlf_pos = data.find('\r\n\r\n')
            headers_data = data[0:double_crlf_pos]
            for line in headers_data.split('\r\n'):
                if 'Content-Length' in line:
                    content_length = int(line[16:])
                    print "Content-Length: " + str(content_length)
                    if content_length >= CACHE_SIZE:
                        to_cache = True
                        break

            conn.send(data)
            if to_cache:
                if not os.path.exists(os.path.dirname(full_filename)):
                    os.makedirs(os.path.dirname(full_filename))
                padding_data = data[double_crlf_pos + 4:]
                with open(full_filename, 'wb') as cache_file:
                    cache_file.write(padding_data)
                    while True:
                        data = proxy.recv(MAX_DATA_RECV)
                        if data:
                            cache_file.write(data)
                            try:
                                conn.send(data)
                            except socket.error:
                                cache_file.close()
                                os.remove(full_filename)
                                raise socket.error, (503, 'custom error')
                        else:
                            print 'appending'
                            with open(CACHE_FILELIST, 'a') as f:
                                f.write(cache_filename + '\n')
                            break
            else:
                while True:
                    data = proxy.recv(MAX_DATA_RECV)
                    if data:
                        conn.send(data)
                    else:
                        break
        proxy.close()
        conn.close()
    except socket.error, (value, message):
        if proxy:
            proxy.close()
        if conn:
            conn.close()
        print message
        print ('peer reset')
        sys.exit(1)

def getaddr_port(request):
    firstline = request.split('\n')[0]
    temp = ''
    port = 80
    for line in request.split('\n'):
        if line.find('Host:') > -1:
            temp = line[6:].strip('\r')
    if temp.find(':') > -1:
        webserver = temp.split(':')[0]
        port = int(temp.split(':')[1])
    else:
        webserver = temp

    url = firstline.split(' ')[1]
    if url.find('://') > -1:
        url = url[7:]
    #http_pos = url.find('://')

    #if (http_pos==-1):
        #temp = url
    #else:
        #temp = url[(http_pos+3):]

    #port_pos = temp.find(':')
    #webserver_pos = temp.find('/')

    #if webserver_pos== -1:
        #webserver_pos = len(temp)

    #webserver = ''
    #port = -1

    #if port_pos == -1 or webserver_pos < port_pos:
        #webserver = temp[:webserver_pos]
        #port = 80
    #else:
        #port = int((temp[(port_pos+1):])[:webserver_pos-port_pos-1])
        #webserver = temp[:(port_pos)]

    return [firstline, webserver, port, url]



if __name__ == '__main__':
    main()

