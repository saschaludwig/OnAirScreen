#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, time, datetime, ConfigParser
from PyQt4 import QtGui, QtCore
from PyQt4.QtNetwork import QUdpSocket, QHostAddress
from mainscreen import Ui_MainScreen
from settings import Ui_Settings
import analogclock

class Settings(QtGui.QWidget, Ui_Settings):

    def __init__(self):
        QtGui.QWidget.__init__(self)
        Ui_Settings.__init__(self)
        self.setupUi(self)
        self._connectSlots()
        self.hide
        self.createConfigWithDefaults()
        self.readConfig()

    def _connectSlots(self):
        self.connect(self.ApplyButton, QtCore.SIGNAL("clicked()"), self.applySettings )
        self.connect(self.LED1BGColor, QtCore.SIGNAL("clicked()"), self.setLED1BGColor )
        self.connect(self.LED1FGColor, QtCore.SIGNAL("clicked()"), self.setLED1FGColor )
        self.connect(self.LED2BGColor, QtCore.SIGNAL("clicked()"), self.setLED2BGColor )
        self.connect(self.LED2FGColor, QtCore.SIGNAL("clicked()"), self.setLED2FGColor )
        self.connect(self.LED3BGColor, QtCore.SIGNAL("clicked()"), self.setLED3BGColor )
        self.connect(self.LED3FGColor, QtCore.SIGNAL("clicked()"), self.setLED3FGColor )
        self.connect(self.LED4BGColor, QtCore.SIGNAL("clicked()"), self.setLED4BGColor )
        self.connect(self.LED4FGColor, QtCore.SIGNAL("clicked()"), self.setLED4FGColor )

        self.connect(self.StationNameColor, QtCore.SIGNAL("clicked()"), self.setStationNameColor )
        self.connect(self.SloganColor, QtCore.SIGNAL("clicked()"), self.setSloganColor )

    def readConfig(self):
        self.config = ConfigParser.ConfigParser()
        self.config.read("onairscreen.ini")

    def createConfigWithDefaults(self):
        cfgfile = open('onairscreen.ini', 'w')
        self.config = ConfigParser.ConfigParser()
        self.config.add_section('general')
        self.config.set('general', 'stationname', 'RADIO ERIWAN')
        self.config.set('general', 'slogan', 'You question is our motivation')
        self.config.write(cfgfile)
        cfgfile.close()

    def applySettings(self):
        print "Apply settings here"

    def setLED1BGColor(self):
        palette = self.LED1Text.palette()
        oldcolor = palette.button().color()
        newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Base, newcolor)
        self.LED1Text.setPalette(palette)

    def setLED1FGColor(self):
        palette = self.LED1Text.palette()
        oldcolor = palette.text().color()
        newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Text, newcolor)
        self.LED1Text.setPalette(palette)

    def setLED2BGColor(self):
        palette = self.LED2Text.palette()
        oldcolor = palette.button().color()
        newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Base, newcolor)
        self.LED2Text.setPalette(palette)

    def setLED2FGColor(self):
        palette = self.LED2Text.palette()
        oldcolor = palette.text().color()
        newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Text, newcolor)
        self.LED2Text.setPalette(palette)

    def setLED3BGColor(self):
        palette = self.LED3Text.palette()
        oldcolor = palette.button().color()
        newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Base, newcolor)
        self.LED3Text.setPalette(palette)

    def setLED3FGColor(self):
        palette = self.LED3Text.palette()
        oldcolor = palette.text().color()
        newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Text, newcolor)
        self.LED3Text.setPalette(palette)

    def setLED4BGColor(self):
        palette = self.LED4Text.palette()
        oldcolor = palette.button().color()
        newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Base, newcolor)
        self.LED4Text.setPalette(palette)

    def setLED4FGColor(self):
        palette = self.LED4Text.palette()
        oldcolor = palette.text().color()
        newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Text, newcolor)
        self.LED4Text.setPalette(palette)

    def setStationNameColor(self):
        palette = self.StationName.palette()
        oldcolor = palette.text().color()
        newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Text, newcolor)
        self.StationName.setPalette(palette)

    def setSloganColor(self):
        palette = self.Slogan.palette()
        oldcolor = palette.text().color()
        newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Text, newcolor)
        self.Slogan.setPalette(palette)

    def openColorDialog(self, initcolor):
        colordialog = QtGui.QColorDialog()
        selectedcolor = colordialog.getColor(initcolor, None, 'Please select a color')
        if selectedcolor.isValid():
            return selectedcolor
        else:
            return initcolor


class MainScreen(QtGui.QWidget, Ui_MainScreen):
    #LED1 = False
    #LED2 = False
    #LED3 = False
    #LED4 = False

    def __init__(self):
        QtGui.QWidget.__init__(self)
        Ui_MainScreen.__init__(self)
        self.setupUi(self)

        self.settings = Settings()

        self.fullScreen = True
        self.showFullScreen()

        # add hotkey bindings
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+F"), self, self.toggleFullScreen )
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Q"), self, QtCore.QCoreApplication.instance().quit )
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+C"), self, QtCore.QCoreApplication.instance().quit )
        QtGui.QShortcut(QtGui.QKeySequence("ESC"), self, QtCore.QCoreApplication.instance().quit )
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, self.settings.show )
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+,"), self, self.settings.show )


        # Setup and start timer
        self.ctimer = QtCore.QTimer()
        QtCore.QObject.connect(self.ctimer, QtCore.SIGNAL("timeout()"), self.constantUpdate)
        self.ctimer.start(100)

        # Setup UDP Socket
        self.sock = QUdpSocket()
        self.sock.bind(3310, QUdpSocket.ShareAddress)
        self.sock.readyRead.connect(self.cmdHandler)

        # some vars
        self.LEDsInactiveColor = '#222'
        self.LEDsInactiveTextColor = '#555'
        self.LEDsActiveTextColor = '#FFFFFF'
        self.LED1ActiveColor = '#FF0000'
        self.LED2ActiveColor = '#DCDC00'
        self.LED3ActiveColor = '#00C8C8'
        self.LED4ActiveColor = '#FF00FF'

        #add the analog clock
        self.addAnalogClock()


    def cmdHandler(self):
        while self.sock.hasPendingDatagrams():
            data, host, port = self.sock.readDatagram(self.sock.pendingDatagramSize())
            print "DATA: "+ data
            lines = data.splitlines()
            for line in lines:
                (command, value) = line.split(':',1)
                print "command: '" + command +"'"
                print "value: '" + value + "'"
                if command == "NOW":
                    self.setCurrentSongText(value)
                if command == "NEXT":
                    self.setNewsText("Next: %s" % value)
                if command == "LED1":
                    if value == "ON":
                        self.setLED1(True)
                    else:
                        self.setLED1(False)
                if command == "LED2":
                    if value == "ON":
                        self.setLED2(True)
                    else:
                        self.setLED2(False)
                if command == "LED3":
                    if value == "ON":
                        self.setLED3(True)
                    else:
                        self.setLED3(False)
                if command == "LED4":
                    if value == "ON":
                        self.setLED4(True)
                    else:
                        self.setLED4(False)
                if command == "WARN":
                    if value:
                        self.showWarning(value)
                    else:
                        self.hideWarning()


    def constantUpdate(self):
        # slot for constant timer timeout
        self.updateClock()
        #self.updateLEDs()
        self.updateDate()
        self.updateBacktimingText()
        self.updateBacktimingSeconds()

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

    def updateBacktimingSeconds(self):
        now = datetime.datetime.now()
        second = now.second
        remain_seconds = 60-second
        self.setBacktimingSecs(remain_seconds)

    #def updateLEDs(self):
    #    self.setLED1(self.LED1)
    #    self.setLED2(self.LED2)
    #    self.setLED3(self.LED3)
    #    self.setLED4(self.LED4)

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

    def hideWarning(self):
        self.labelWarning.setText( "" )
        self.labelWarning.hide()

    def addAnalogClock(self):
        self.analogClockPlaceholder.hide()
        self.analogClock = analogclock.AnalogClock(self)
        self.analogClock.setGeometry(QtCore.QRect(170, 90, 470, 470))
        self.analogClock.setObjectName("analogClock")
        self.analogClock.show()


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    mainscreen = MainScreen()

    mainscreen.setLED1Text("ON AIR")
    mainscreen.setLED2Text("PHONE")
    mainscreen.setLED3Text("DOORBELL")
    mainscreen.setLED4Text("ARI")

    mainscreen.setStation("RADIO WLR")
    mainscreen.setSlogan("Hier spielt die Musik")
    mainscreen.setCurrentSongText("The Clash - London Calling")
    mainscreen.setNewsText("hier stehen weitere Nachrichten")

    mainscreen.setVULeft(0)
    mainscreen.setVURight(0)

    mainscreen.setBacktimingSecs(15)

    mainscreen.hideWarning()
    mainscreen.setLED1(False)
    mainscreen.setLED2(False)
    mainscreen.setLED3(False)
    mainscreen.setLED4(False)

    mainscreen.show()
    sys.exit(app.exec_())
