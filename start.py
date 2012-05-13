#!/usr/bin/env python

import sys
from PyQt4 import QtGui, QtCore
from mainscreen import Ui_MainScreen


class MainScreen(QtGui.QWidget, Ui_MainScreen):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        Ui_MainScreen.__init__(self)
        self.setupUi(self)
       
        self.fullScreen = True
        self.showFullScreen()
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+F"), self, self.toggleFullScreen )
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Q"), self, self.close )

    def toggleFullScreen(self):
        if not self.fullScreen :
            self.showFullScreen()
        else:
            self.showNormal()
        self.fullScreen = not (self.fullScreen)


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    mainscreen = MainScreen()
    mainscreen.show()
    sys.exit(app.exec_())
