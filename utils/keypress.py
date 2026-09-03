#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#############################################################################
#
# OnAirScreen Keypress Tool
# tool to display keyboard keycodes
# Copyright (c) 2012-2026 Sascha Ludwig, astrastudio.de
# All rights reserved.
#
# keypress.py
# This file is part of OnAirScreen
#
# Licensed under the OnAirScreen Source-Available License (OASL 1.0).
# You may use, modify, and redistribute the source code.
# Redistribution of compiled or executable versions requires prior
# written permission from the copyright holder. See LICENSE.
#
#############################################################################


import sys

from PySide6.QtGui import *
from PySide6.QtWidgets import *


class myWin(QLineEdit):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.setText("    KEYCODE    ")
        self.setReadOnly(True)

    def keyPressEvent(self, event):
        if type(event) == QKeyEvent:
            # here accept the event and do something
            self.setText("%s = '%s'" % (str(event.key()), event.text()))

            event.accept()
        else:
            event.ignore()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainW = myWin()
    mainW.show()
    sys.exit(app.exec())
