#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt4.QtGui import *
from PyQt4.QtCore import *
import sys

class myWin(QLineEdit):
     def __init__(self, parent=None):
         QWidget.__init__(self, parent)
         self.setText("    KEYCODE    ")
         self.setReadOnly(True)


     def keyPressEvent(self, event):
         if type(event) == QKeyEvent:
             #here accept the event and do something
             self.setText("%s = '%s'" %( str(event.key()), str(event.text()) ) )

             event.accept()
         else:
             event.ignore()


if __name__ == "__main__":
     app = QApplication(sys.argv)
     mainW = myWin()
     mainW.show()
     sys.exit(app.exec_())

