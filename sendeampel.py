#!/usr/bin/env python
import sys, serial, os
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from subprocess import *

class MyForm(QDialog):
  def __init__(self, parent = None):
    super(MyForm, self).__init__(parent)
    self.setWindowTitle('AstraStudio Sendeampel')
    self.setMinimumSize(300, 100)
    self.att_laststate = "foo"
    self.air_laststate = "foo"
    # widgets
    self.DTRlabel, self.RTSlabel = QLabel(), QLabel()
    self.DTRbutton = QPushButton('ATTENTION')
    self.RTSbutton = QPushButton('ON AIR')
    self.DTRcheckbox = QCheckBox('blink')
    self.RTScheckbox = QCheckBox('blink')
    self.OFFbutton = QPushButton('ALL OFF')
    # layout
    layout = QGridLayout()
    layout.addWidget(self.DTRlabel, 0, 0)
    layout.addWidget(self.RTSlabel, 0, 1)
    layout.addWidget(self.DTRbutton, 1, 0)
    layout.addWidget(self.RTSbutton, 1, 1)
    layout.addWidget(self.DTRcheckbox, 2, 0)
    layout.addWidget(self.RTScheckbox, 2, 1)
    layout.addWidget(self.OFFbutton, 3, 0)
    self.setLayout(layout)
    # serial port
    try:
        self.port = serial.Serial('/dev/ttyS0') #S0')
    except:
        print "could not open serial port"
    self.DTRlabel.setText("<font size = 5 color = darkgreen><b>OFF</b></font>")
    self.RTSlabel.setText("<font size = 5 color = darkgreen><b>OFF</b></font>")
    self.DTRlogic, self.RTSlogic = False, False
    self.port.setDTR(self.DTRlogic)
    self.port.setRTS(self.RTSlogic)
    # events
    self.connect(self.DTRbutton, SIGNAL('clicked()'), self.toggleDTR)
    self.connect(self.RTSbutton, SIGNAL('clicked()'), self.toggleRTS)
    self.connect(self.OFFbutton, SIGNAL('clicked()'), self.clickOFF)
    self.DTRtimer , self.RTStimer, self.FileTimer = QTimer(), QTimer(), QTimer()
    self.connect(self.DTRtimer, SIGNAL('timeout()'), self.eventDTRtimer)
    self.DTRtimer.start(250) # in milliseconds
    self.connect(self.RTStimer, SIGNAL('timeout()'), self.eventRTStimer)
    self.RTStimer.start(250) # in milliseconds
    self.connect(self.FileTimer, SIGNAL('timeout()'), self.checkFiles)
    self.FileTimer.start(50) # in milliseconds

  def toggleDTR(self):
    if self.DTRlogic:
        self.DTRlabel.setText("<font size = 5 color = darkgreen><b>OFF</b></font>")
    else:
        self.DTRlabel.setText("<font size = 5 color = darkred><b>ON</b></font>")
    self.DTRlogic = not self.DTRlogic # invert logic
    self.port.setDTR(self.DTRlogic)

  def toggleRTS(self):
    if self.RTSlogic:
        self.RTSlabel.setText("<font size = 5 color = darkgreen><b>OFF</b></font>")
    else:
        self.RTSlabel.setText("<font size = 5 color = darkred><b>ON</b></font>")
    self.RTSlogic = not self.RTSlogic # invert logic
    self.port.setRTS(self.RTSlogic)

  def clickOFF(self):
    self.DTRlabel.setText("<font size = 5 color = darkgreen><b>OFF</b></font>")
    self.RTSlabel.setText("<font size = 5 color = darkgreen><b>OFF</b></font>")
    self.DTRlogic = False
    self.port.setDTR(self.DTRlogic)
    self.RTSlogic = False
    self.port.setRTS(self.RTSlogic)

  def eventDTRtimer(self):
    if self.DTRcheckbox.isChecked():
      self.toggleDTR()
  def eventRTStimer(self):
    if self.RTScheckbox.isChecked():
      self.toggleRTS()

  def checkFiles(self):
    self.checkFileAir()
    self.checkFileAtt()

  def checkFileAir(self):
    if os.path.isfile("/tmp/rivendell_onair"):
        if self.air_laststate == True:
            return
        call ("echo LED1:ON | nc -b -q0 -u 192.168.42.255 3310 ",shell=True)
        self.RTSlabel.setText("<font size = 5 color = darkred><b>ON</b></font>")
        self.RTSlogic = True
        self.port.setRTS(self.RTSlogic)
        self.air_laststate = True
    else:
        if self.air_laststate == False:
            return
        call ("echo LED1:OFF | nc -b -q0 -u 192.168.42.255 3310 ",shell=True)
        self.RTSlabel.setText("<font size = 5 color = darkgreen><b>OFF</b></font>")
        self.RTSlogic = False
        self.port.setRTS(self.RTSlogic)
        self.air_laststate = False

  def checkFileAtt(self):
    if os.path.isfile("/tmp/rivendell_attention"):
        if self.att_laststate == True:
            return
        call ("echo LED3:ON | nc -b -q0 -u 192.168.42.255 3310 ",shell=True)
        self.DTRlabel.setText("<font size = 5 color = darkred><b>ON</b></font>")
        self.DTRlogic = True
        self.port.setDTR(self.DTRlogic)
        self.att_laststate = True
    else:
        if self.att_laststate == False:
            return
        call ("echo LED3:OFF | nc -b -q0 -u 192.168.42.255 3310 ",shell=True)
        self.DTRlabel.setText("<font size = 5 color = darkgreen><b>OFF</b></font>")
        self.DTRlogic = False
        self.port.setDTR(self.DTRlogic)
        self.att_laststate = False

if __name__ == '__main__':
  app = QApplication(sys.argv)
  form = MyForm()
  form.show()
  sys.exit(app.exec_())

