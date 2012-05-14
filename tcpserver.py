#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import threading
import SocketServer

class ThreadedTCPRequestHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        data = self.request.recv(1024).rstrip()
        cur_thread = threading.current_thread()
        print "CMD IN: '" + data +"'"
        response = self.cmdHandler(data)
        print "OUT {}: {}".format(cur_thread.name, response)
        self.request.sendall(response)

    def cmdHandler(self, data):
        if data == "foo":
            return "bar"
        if data == "bar":
            return "baz"


class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

if __name__ == "__main__":
    # Port 0 means to select an arbitrary unused port
    HOST, PORT = "localhost", 3325

    cmdserver = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    ip, port = cmdserver.server_address

    # Start a thread with the server -- that thread will then start one
    # more thread for each request
    cmdserver_thread = threading.Thread(target=cmdserver.serve_forever)
    # Exit the server thread when the main thread terminates
    cmdserver_thread.daemon = True
    cmdserver_thread.start()
    print "Server loop running in thread:", cmdserver_thread.name

    while (True):
        pass

    cmdserver.shutdown()
