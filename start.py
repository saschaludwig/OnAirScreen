#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, time, datetime
from PyQt4 import QtGui, QtCore
from mainscreen import Ui_MainScreen

class MainScreen(QtGui.QWidget, Ui_MainScreen):
    LED1 = True
    LED2 = False
    LED3 = False
    LED4 = False

    def __init__(self):
        QtGui.QWidget.__init__(self)
        Ui_MainScreen.__init__(self)
        self.setupUi(self)

        self.fullScreen = True
        self.showFullScreen()
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+F"), self, self.toggleFullScreen )
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Q"), self, QtCore.QCoreApplication.instance().quit )
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+C"), self, QtCore.QCoreApplication.instance().quit )

        self.ctimer = QtCore.QTimer()
        QtCore.QObject.connect(self.ctimer, QtCore.SIGNAL("timeout()"), self.constantUpdate)

        # some vars
        self.LEDsInactiveColor = '#222'
        self.LEDsInactiveTextColor = '#555'
        self.LEDsActiveTextColor = '#FFF'
        self.LED1ActiveColor = '#F00'
        self.LED2ActiveColor = '#FF0'
        self.LED3ActiveColor = '#0FF'
        self.LED4ActiveColor = '#F0F'

        # Start the constant timer
        self.ctimer.start(100)

    def constantUpdate(self):
        # slot for constant timer timeout
        self.updateClock()
        self.updateLEDs()
        self.updateDate()
        self.updateBacktimingText()

    def updateClock(self):
        now = datetime.datetime.now()
        self.setClock( now.strftime("%H:%M:%S") )

    def updateDate(self):
        now = datetime.datetime.now()
        self.setLeftText( now.strftime("%A, %d. %B %Y") )

    def updateBacktimingText(self):
        now = datetime.datetime.now()
        hour = now.hour
        minute = now.minute
        second = now.second
        remain_min = 60-minute
        if hour > 12:
            hour -= 12
        if remain_min > 29:
            string = "%d Minuten vor halb %d" % (remain_min-30, hour+1)
        else:
            string = "%d Minuten vor %d" % (remain_min, hour+1)
        self.setRightText( string )

    def updateLEDs(self):
        self.setLED1(self.LED1)
        self.setLED2(self.LED2)
        self.setLED3(self.LED3)
        self.setLED4(self.LED4)

    def toggleFullScreen(self):
        if not self.fullScreen :
            self.showFullScreen()
        else:
            self.showNormal()
        self.fullScreen = not (self.fullScreen)

    def setLED1(self, action):
        if action:
            self.buttonLED1.setStyleSheet("color: "+self.LEDsActiveTextColor+"; background-color: " + self.LED1ActiveColor)
        else:
            self.buttonLED1.setStyleSheet("color: "+self.LEDsInactiveTextColor+"; background-color: " + self.LEDsInactiveColor)

    def setLED2(self, action):
        if action:
            self.buttonLED2.setStyleSheet("color: "+self.LEDsActiveTextColor+"; background-color: " + self.LED2ActiveColor)
        else:
            self.buttonLED2.setStyleSheet("color: "+self.LEDsInactiveTextColor+"; background-color: " + self.LEDsInactiveColor)

    def setLED3(self, action):
        if action:
            self.buttonLED3.setStyleSheet("color: "+self.LEDsActiveTextColor+"; background-color: " + self.LED3ActiveColor)
        else:
            self.buttonLED3.setStyleSheet("color: "+self.LEDsInactiveTextColor+"; background-color: " + self.LEDsInactiveColor)

    def setLED4(self, action):
        if action:
            self.buttonLED4.setStyleSheet("color: "+self.LEDsActiveTextColor+"; background-color: " + self.LED4ActiveColor)
        else:
            self.buttonLED4.setStyleSheet("color: "+self.LEDsInactiveTextColor+"; background-color: " + self.LEDsInactiveColor)

    def setClock(self, text):
        self.labelClock.setText(text)

    def setStation(self, text):
        self.labelStation.setText(text)

    def setSlogan(self, text):
        self.labelSlogan.setText(text)

    def setLeftText(self, text):
        self.labelTextLeft.setText(text)

    def setRightText(self, text):
        self.labelTextRight.setText(text)

    def setLED1Text(self, text):
        self.buttonLED1.setText(text)

    def setLED2Text(self, text):
        self.buttonLED2.setText(text)

    def setLED3Text(self, text):
        self.buttonLED3.setText(text)

    def setLED4Text(self, text):
        self.buttonLED4.setText(text)

    def setCurrentSongText(self, text):
        self.labelCurrentSong.setText(text)

    def setNewsText(self, text):
        self.labelNews.setText(text)

    def setVULeft(self, value):
        self.progressL.setValue(value)

    def setVURight(self, value):
        self.progressR.setValue(value)

    def setBacktimingSecs(self, value):
        self.labelSeconds.setText( str(value) )

    def showWarning(self, text):
        self.labelWarning.setText( text )
        self.labelWarning.show()

    def hideWarning(self, text):
        self.labelWarning.setText("")
        self.labelWarning.hide()


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    mainscreen = MainScreen()
    mainscreen.show()

    mainscreen.setLED1Text("ON AIR")
    mainscreen.setLED2Text("PHONE")
    mainscreen.setLED3Text("DOORBELL")
    mainscreen.setLED4Text("ARI")

    mainscreen.setStation("RADIO WLR")
    mainscreen.setSlogan("Hier spielt die Musik")
    mainscreen.setCurrentSongText("The Clash - London Calling")
    mainscreen.setNewsText("hier stehen weitere Nachrichten")

    mainscreen.setVULeft(70)
    mainscreen.setVURight(75)

    mainscreen.setBacktimingSecs(15)

    #mainscreen.showWarning("STREAM OFFLINE")
    mainscreen.hideWarning()

    sys.exit(app.exec_())
