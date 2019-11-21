#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2019 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# start.py
# This file is part of OnAirScreen
#
# You may use this file under the terms of the BSD license as follows:
#
# "Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
#
#############################################################################

import os
import sys

from PyQt5.QtGui import QCursor, QKeySequence, QIcon, QPixmap
from PyQt5.QtWidgets import QApplication, QWidget, QShortcut, QDialog
from PyQt5.QtCore import Qt, QSettings, QCoreApplication, QTimer, QVariant, QThread
from PyQt5.QtNetwork import QUdpSocket
from mainscreen import Ui_MainScreen
import signal
import socket
from settings_functions import Settings, versionString
from urllib.parse import unquote
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = '0.0.0.0'


class MainScreen(QWidget, Ui_MainScreen):
    getTimeWindow: QDialog
    ntpHadWarning: bool
    ntpWarnMessage: str

    def __init__(self):
        QWidget.__init__(self)
        Ui_MainScreen.__init__(self)
        self.setupUi(self)

        # load weather widget

        self.settings = Settings()
        self.restoreSettingsFromConfig()
        # quit app from settings window
        self.settings.sigExitOAS.connect(self.exitOAS)
        self.settings.sigRebootHost.connect(self.reboot_host)
        self.settings.sigShutdownHost.connect(self.shutdown_host)
        self.settings.sigConfigFinished.connect(self.configFinished)
        self.settings.sigConfigClosed.connect(self.configClosed)

        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("General")
        if settings.value('fullscreen', True, type=bool):
            self.showFullScreen()
            app.setOverrideCursor(QCursor(Qt.BlankCursor))
        settings.endGroup()
        print("Loading Settings from: ", settings.fileName())

        # add hotkey bindings
        QShortcut(QKeySequence("Ctrl+Q"), self, QCoreApplication.instance().quit)
        QShortcut(QKeySequence("Q"), self, QCoreApplication.instance().quit)
        QShortcut(QKeySequence("Ctrl+C"), self, QCoreApplication.instance().quit)
        QShortcut(QKeySequence("ESC"), self, QCoreApplication.instance().quit)
        QShortcut(QKeySequence("Ctrl+S"), self, self.showsettings)
        QShortcut(QKeySequence("Ctrl+,"), self, self.showsettings)
        QShortcut(QKeySequence("1"), self, self.manualToggleLED1)
        QShortcut(QKeySequence("2"), self, self.manualToggleLED2)
        QShortcut(QKeySequence("3"), self, self.manualToggleLED3)
        QShortcut(QKeySequence("M"), self, self.toggleAIR1)
        QShortcut(QKeySequence("/"), self, self.toggleAIR1)

        self.statusLED1 = False
        self.statusLED2 = False
        self.statusLED3 = False

        self.LED1on = False
        self.LED2on = False
        self.LED3on = False

        # LED timers
        self.timerLED1 = QTimer()
        self.timerLED1.timeout.connect(self.toggleLED1)
        self.timerLED2 = QTimer()
        self.timerLED2.timeout.connect(self.toggleLED2)
        self.timerLED3 = QTimer()
        self.timerLED3.timeout.connect(self.toggleLED3)

        # Setup OnAir Timers
        self.timerAIR1 = QTimer()
        self.timerAIR1.timeout.connect(self.updateAIR1Seconds)
        self.Air1Seconds = 0
        self.statusAIR1 = False

        # Setup UDP Socket
        self.udpsock = QUdpSocket()
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("Network")
        port = int(settings.value('udpport', 3310))
        settings.endGroup()
        self.udpsock.bind(port, QUdpSocket.ShareAddress)
        self.udpsock.readyRead.connect(self.cmdHandler)

        # Setup HTTP Server
        self.httpd = HttpDaemon(self)
        self.httpd.start()

    def showsettings(self):
        global app
        # un-hide mouse cursor
        app.setOverrideCursor(QCursor(Qt.ArrowCursor));
        self.settings.showsettings()

    def cmdHandler(self):
        while self.udpsock.hasPendingDatagrams():
            data, host, port = self.udpsock.readDatagram(self.udpsock.pendingDatagramSize())
            # print("DATA: ", data)
            lines = data.splitlines()
            for line in lines:
                # print("Line:", line)
                try:
                    (command, value) = line.decode('utf_8').split(':', 1)
                except ValueError:
                    return
                command = str(command)
                value = str(value)
                # print("command: >" + command + "<")
                # print("value: >" + value + "<")
                if command == "LED1":
                    if value == "OFF":
                        self.ledLogic(1, False)
                    else:
                        self.ledLogic(1, True)
                if command == "LED2":
                    if value == "OFF":
                        self.ledLogic(2, False)
                    else:
                        self.ledLogic(2, True)
                if command == "LED3":
                    if value == "OFF":
                        self.ledLogic(3, False)
                    else:
                        self.ledLogic(3, True)

                if command == "AIR1":
                    if value == "OFF":
                        self.setAIR1(False)
                    else:
                        self.setAIR1(True)

                if command == "CMD":
                    if value == "REBOOT":
                        self.reboot_host()
                    if value == "SHUTDOWN":
                        self.shutdown_host()
                    if value == "QUIT":
                        QApplication.quit()

                if command == "CONF":
                    # split group, config and values and apply them
                    try:
                        (group, paramvalue) = value.split(':', 1)
                        (param, content) = paramvalue.split('=', 1)
                        # print "CONF:", param, content
                    except ValueError:
                        return

                    if group == "General":
                        if param == "stationname":
                            self.settings.StationName.setText(content)
                        if param == "slogan":
                            self.settings.Slogan.setText(content)
                        if param == "stationcolor":
                            self.settings.setStationNameColor(self.settings.getColorFromName(content))
                        if param == "slogancolor":
                            self.settings.setSloganColor(self.settings.getColorFromName(content))

                    if group == "LED1":
                        if param == "used":
                            self.settings.LED1.setChecked(QVariant(content).toBool())
                        if param == "text":
                            self.settings.LED1Text.setText(content)
                        if param == "activebgcolor":
                            self.settings.setLED1BGColor(self.settings.getColorFromName(content))
                        if param == "activetextcolor":
                            self.settings.setLED1FGColor(self.settings.getColorFromName(content))
                        if param == "autoflash":
                            self.settings.LED1Autoflash.setChecked(QVariant(content).toBool())
                        if param == "timedflash":
                            self.settings.LED1Timedflash.setChecked(QVariant(content).toBool())

                    if group == "LED2":
                        if param == "used":
                            self.settings.LED2.setChecked(QVariant(content).toBool())
                        if param == "text":
                            self.settings.LED2Text.setText(content)
                        if param == "activebgcolor":
                            self.settings.setLED2BGColor(self.settings.getColorFromName(content))
                        if param == "activetextcolor":
                            self.settings.setLED2FGColor(self.settings.getColorFromName(content))
                        if param == "autoflash":
                            self.settings.LED2Autoflash.setChecked(QVariant(content).toBool())
                        if param == "timedflash":
                            self.settings.LED2Timedflash.setChecked(QVariant(content).toBool())

                    if group == "LED3":
                        if param == "used":
                            self.settings.LED3.setChecked(QVariant(content).toBool())
                        if param == "text":
                            self.settings.LED3Text.setText(content)
                        if param == "activebgcolor":
                            self.settings.setLED3BGColor(self.settings.getColorFromName(content))
                        if param == "activetextcolor":
                            self.settings.setLED3FGColor(self.settings.getColorFromName(content))
                        if param == "autoflash":
                            self.settings.LED3Autoflash.setChecked(QVariant(content).toBool())
                        if param == "timedflash":
                            self.settings.LED3Timedflash.setChecked(QVariant(content).toBool())

                    if group == "Network":
                        if param == "udpport":
                            self.settings.udpport.setText(content)

                    if group == "CONF":
                        if param == "APPLY":
                            if content == "TRUE":
                                # apply and save settings
                                self.settings.applySettings()

    def manualToggleLED1(self):
        if self.LED1on:
            self.ledLogic(1, False)
        else:
            self.ledLogic(1, True)

    def manualToggleLED2(self):
        if self.LED2on:
            self.ledLogic(2, False)
        else:
            self.ledLogic(2, True)

    def manualToggleLED3(self):
        if self.LED3on:
            self.ledLogic(3, False)
        else:
            self.ledLogic(3, True)

    def toggleLED1(self):
        if self.statusLED1:
            self.setLED1(False)
        else:
            self.setLED1(True)

    def toggleLED2(self):
        if self.statusLED2:
            self.setLED2(False)
        else:
            self.setLED2(True)

    def toggleLED3(self):
        if self.statusLED3:
            self.setLED3(False)
        else:
            self.setLED3(True)

    def toggleAIR1(self):
        if self.statusAIR1:
            self.setAIR1(False)
        else:
            self.setAIR1(True)

    def unsetLED1(self):
        self.ledLogic(1, False)

    def unsetLED2(self):
        self.ledLogic(2, False)

    def unsetLED3(self):
        self.ledLogic(3, False)


    def ledLogic(self, led, state):
        if state:
            if led == 1:
                if self.settings.LED1Autoflash.isChecked():
                    self.timerLED1.start(500)
                if self.settings.LED1Timedflash.isChecked():
                    self.timerLED1.start(500)
                    QTimer.singleShot(20000, self.unsetLED1)
                self.setLED1(state)
                self.LED1on = state
            if led == 2:
                if self.settings.LED2Autoflash.isChecked():
                    self.timerLED2.start(500)
                if self.settings.LED2Timedflash.isChecked():
                    self.timerLED2.start(500)
                    QTimer.singleShot(20000, self.unsetLED2)
                self.setLED2(state)
                self.LED2on = state
            if led == 3:
                if self.settings.LED3Autoflash.isChecked():
                    self.timerLED3.start(500)
                if self.settings.LED3Timedflash.isChecked():
                    self.timerLED3.start(500)
                    QTimer.singleShot(20000, self.unsetLED3)
                self.setLED3(state)
                self.LED3on = state

        if state == False:
            if led == 1:
                self.setLED1(state)
                self.timerLED1.stop()
                self.LED1on = state
            if led == 2:
                self.setLED2(state)
                self.timerLED2.stop()
                self.LED2on = state
            if led == 3:
                self.setLED3(state)
                self.timerLED3.stop()
                self.LED3on = state


    def restoreSettingsFromConfig(self):
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")

        settings.beginGroup("LED1")
        self.setLED1Text(settings.value('text', 'ON AIR'))
        settings.endGroup()

        settings.beginGroup("LED2")
        self.setLED2Text(settings.value('text', 'PHONE'))
        settings.endGroup()

        settings.beginGroup("LED3")
        self.setLED3Text(settings.value('text', 'DOORBELL'))
        settings.endGroup()

        settings.beginGroup("WeatherWidget")
        if settings.value('owmWidgetEnabled', False, type=bool):
            pass
        self.weatherWidget.setVisible(settings.value('owmWidgetEnabled', False, type=bool))
        settings.endGroup()

    def setAIR1(self, action):
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        if action:
            self.Air1Seconds = 0
            self.AirLabel_1.setStyleSheet("color: #000000; background-color: #FF0000")
            self.AirIcon_1.setStyleSheet("color: #000000; background-color: #FF0000")
            self.AirLabel_1.setText("Mic\n%d:%02d" % (self.Air1Seconds / 60, self.Air1Seconds % 60))
            self.statusAIR1 = True
            # AIR1 timer
            self.timerAIR1.start(1000)
        else:
            settings.beginGroup("LEDS")
            self.AirIcon_1.setStyleSheet("color:" + settings.value('inactivetextcolor',
                                                                   '#555555') + ";background-color:" + settings.value(
                'inactivebgcolor', '#222222'))
            self.AirLabel_1.setStyleSheet("color:" + settings.value('inactivetextcolor',
                                                                    '#555555') + ";background-color:" + settings.value(
                'inactivebgcolor', '#222222'))
            settings.endGroup()
            self.statusAIR1 = False
            self.timerAIR1.stop()

    def updateAIR1Seconds(self):
        self.Air1Seconds += 1
        self.AirLabel_1.setText("Mic\n%d:%02d" % (self.Air1Seconds / 60, self.Air1Seconds % 60))

    def setLED1(self, action):
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        if action:
            settings.beginGroup("LED1")
            self.buttonLED1.setStyleSheet("color:" + settings.value('activetextcolor',
                                                                    '#FFFFFF') + ";background-color:" + settings.value(
                'activebgcolor', '#FF0000'))
            settings.endGroup()
            self.statusLED1 = True
        else:
            settings.beginGroup("LEDS")
            self.buttonLED1.setStyleSheet("color:" + settings.value('inactivetextcolor',
                                                                    '#555555') + ";background-color:" + settings.value(
                'inactivebgcolor', '#222222'))
            settings.endGroup()
            self.statusLED1 = False

    def setLED2(self, action):
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        if action:
            settings.beginGroup("LED2")
            self.buttonLED2.setStyleSheet("color:" + settings.value('activetextcolor',
                                                                    '#FFFFFF') + ";background-color:" + settings.value(
                'activebgcolor', '#DCDC00'))
            settings.endGroup()
            self.statusLED2 = True
        else:
            settings.beginGroup("LEDS")
            self.buttonLED2.setStyleSheet("color:" + settings.value('inactivetextcolor',
                                                                    '#555555') + ";background-color:" + settings.value(
                'inactivebgcolor', '#222222'))
            settings.endGroup()
            self.statusLED2 = False

    def setLED3(self, action):
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        if action:
            settings.beginGroup("LED3")
            self.buttonLED3.setStyleSheet("color:" + settings.value('activetextcolor',
                                                                    '#FFFFFF') + ";background-color:" + settings.value(
                'activebgcolor', '#00C8C8'))
            settings.endGroup()
            self.statusLED3 = True
        else:
            settings.beginGroup("LEDS")
            self.buttonLED3.setStyleSheet("color:" + settings.value('inactivetextcolor',
                                                                    '#555555') + ";background-color:" + settings.value(
                'inactivebgcolor', '#222222'))
            settings.endGroup()
            self.statusLED3 = False

    def setLED1Text(self, text):
        self.buttonLED1.setText(text)

    def setLED2Text(self, text):
        self.buttonLED2.setText(text)

    def setLED3Text(self, text):
        self.buttonLED3.setText(text)

    def exitOAS(self):
        global app
        app.exit()

    def configClosed(self):
        global app
        pass

    def configFinished(self):
        self.restoreSettingsFromConfig()

    def reboot_host(self):
        self.addWarning("SYSTEM REBOOT IN PROGRESS", 2)
        if os.name == "posix":
            cmd = "sudo reboot"
            os.system(cmd)
        if os.name == "nt":
            cmd = "shutdown -f -r -t 0"
            pass

    def shutdown_host(self):
        self.addWarning("SYSTEM SHUTDOWN IN PROGRESS", 2)
        if os.name == "posix":
            cmd = "sudo halt"
            os.system(cmd)
        if os.name == "nt":
            cmd = "shutdown -f -t 0"
            pass

    def closeEvent(self, event):
        self.httpd.stop()


class HttpDaemon(QThread):
    def run(self):
        settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
        settings.beginGroup("Network")
        port = int(settings.value('httpport', 8010))
        settings.endGroup()

        handler = OASHTTPRequestHandler
        self._server = HTTPServer((HOST, port), handler)
        self._server.serve_forever()

    def stop(self):
        self._server.shutdown()
        self._server.socket.close()
        self.wait()


class OASHTTPRequestHandler(BaseHTTPRequestHandler):
    server_version = "OnAirScreen/%s" % versionString

    # handle HEAD request
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    # handle GET command
    def do_GET(self):
        print(self.path)
        if self.path.startswith('/?cmd'):
            try:
                cmd, message = unquote(str(self.path)[5:]).split("=", 1)
            except ValueError:
                self.send_error(400, 'no command was given')
                return

            if len(message) > 0:
                self.send_response(200)

                # send header first
                self.send_header('Content-type', 'text-html')
                self.end_headers()

                settings = QSettings(QSettings.UserScope, "astrastudio", "OnAirScreen")
                settings.beginGroup("Network")
                port = int(settings.value('udpport', 3310))
                settings.endGroup()

                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(message.encode(), ("127.0.0.1", port))

                # send file content to client
                self.wfile.write(message.encode())
                self.wfile.write("\n".encode())
                return
            else:
                self.send_error(400, 'no command was given')
                return

        self.send_error(404, 'file not found')


###################################
# App SIGINT handler
###################################
def sigint_handler(*args):
    # Handler for SIGINT signal
    sys.stderr.write("\n")
    QApplication.quit()


###################################
# App Init
###################################
if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigint_handler)
    app = QApplication(sys.argv)
    icon = QIcon()
    icon.addPixmap(QPixmap(":/oas_icon/oas_icon.png"), QIcon.Normal, QIcon.Off)
    app.setWindowIcon(icon)

    timer = QTimer()
    timer.start(100)
    timer.timeout.connect(lambda: None)

    mainscreen = MainScreen()
    mainscreen.setWindowIcon(icon)

    for i in range(1, 4):
        mainscreen.ledLogic(i, False)

    mainscreen.setAIR1(False)

    mainscreen.show()

    sys.exit(app.exec_())
