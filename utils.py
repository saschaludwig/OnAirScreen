#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen
# Copyright (c) 2012-2023 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# utils.py
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

import webbrowser

from PyQt5 import QtCore
from PyQt5 import QtWidgets


class TimerUpdateMessageBox(QtWidgets.QMessageBox):
    def __init__(self, timeout=10, json_reply=None, parent=None):
        super(TimerUpdateMessageBox, self).__init__(parent)
        self.json_reply = json_reply
        self.time_to_wait = timeout
        self.setIcon(QtWidgets.QMessageBox.Information)
        self.setWindowTitle("OnAirScreen Update Check")
        self.setText("OnAirScreen Update Check")
        self.setFixedWidth(200)
        self.setInformativeText(f"{self.json_reply['Message']}\n"
                                f"{self.json_reply['Version']}\n"
                                f"(closing in {timeout} seconds)")
        download_button = QtWidgets.QPushButton('Download')
        close_button = QtWidgets.QPushButton('Close')
        download_button.clicked.connect(self.download_latest_version)
        self.addButton(close_button, QtWidgets.QMessageBox.NoRole)
        self.addButton(download_button, QtWidgets.QMessageBox.ActionRole)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.change_content)
        self.timer.start()

    def change_content(self):
        self.time_to_wait -= 1
        self.setInformativeText(f"{self.json_reply['Message']}\n"
                                f"{self.json_reply['Version']}\n"
                                f"(closing in {self.time_to_wait} seconds)")
        if self.time_to_wait <= 0:
            self.close()

    def closeEvent(self, event):
        self.timer.stop()
        event.accept()

    def download_latest_version(self):
        if self.json_reply['URL']:
            webbrowser.open(self.json_reply['URL'])
