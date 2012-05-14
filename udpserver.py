#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import threading
import SocketServer

class ThreadedUDPRequestHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        data = self.request[0].strip()
        cur_thread = threading.current_thread()
        self.cmdHandler(data)

    def cmdHandler(self, data):
        print "cmdHandler called:"
        lines = data.splitlines()
        for line in lines:
            (command, value) = line.split(':',1)
            print "command: " + command
            print "value: " + value
            if command == "NOW":
                print "Setting NOW to: " + value
                #TODO:
                #setCurrentSongText(value)
            if command == "NEXT":
                print "Setting NEXT to: " + value

class ThreadedUDPServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):
    pass


def udpStartCmdServer(HOST, PORT):
    cmdserver = ThreadedUDPServer((HOST, PORT), ThreadedUDPRequestHandler)
    ip, port = cmdserver.server_address

    # Start a thread with the server -- that thread will then start one
    # more thread for each request
    cmdserver_thread = threading.Thread(target=cmdserver.serve_forever)
    # Exit the server thread when the main thread terminates
    cmdserver_thread.daemon = True
    cmdserver_thread.start()
    print "Server loop running in thread:", cmdserver_thread.name

if __name__ == "__main__":
    udpStartCmdServer('localhost', 3310)

    while (True):
        pass

    cmdserver.shutdown()
