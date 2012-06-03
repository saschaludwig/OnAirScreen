#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, time, datetime, ConfigParser, os
from PyQt4 import QtGui, QtCore
from PyQt4.QtNetwork import QUdpSocket, QHostAddress
from mainscreen import Ui_MainScreen
from settings import Ui_Settings

class Settings(QtGui.QWidget, Ui_Settings):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        Ui_Settings.__init__(self)
        self.setupUi(self)
        self._connectSlots()
        self.hide()
        # read the config, add missing values, save config and re-read config
        self.readConfigFromFile()
        self.saveConfigToFile()
        self.readConfigFromFile()
        self.restoreSettingsFromConfig()
        self.configChanged = True

    def showsettings(self):
        global app
        # un-hide mousecursor
        app.setOverrideCursor( QtGui.QCursor( 0 ) );
        self.show()

    def hidesettings(self):
        global app
        # hide mousecursor
        app.setOverrideCursor( QtGui.QCursor( 10 ) );

    def closeEvent(self, event):
        global app
        # hide mousecursor
        app.setOverrideCursor( QtGui.QCursor( 10 ) );

    def exitOnAirScreen(self):
        global app
        app.exit()

    def _connectSlots(self):
        self.connect(self.ApplyButton, QtCore.SIGNAL("clicked()"), self.applySettings )
        self.connect(self.CloseButton, QtCore.SIGNAL("clicked()"), self.closeSettings )
        self.connect(self.ExitButton, QtCore.SIGNAL("clicked()"), self.exitOnAirScreen )
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

        self.connect(self, QtCore.SIGNAL("triggered()"), self.closeEvent )

    def readConfigFromFile(self):
        self.config = ConfigParser.ConfigParser()
        self.config.read(os.path.expanduser('~/.onairscreen.ini'))
        # test if sections and options exits, else create them with defaults
        self.createOptionWithDefault('general', 'stationname', 'RADIO ERIWAN')
        self.createOptionWithDefault('general', 'slogan', 'Your question is our motivation')
        self.createOptionWithDefault('general', 'stationcolor', '#FFAA00')
        self.createOptionWithDefault('general', 'slogancolor', '#FFAA00')
        self.createOptionWithDefault('general', 'fullscreen', 'True')

        self.createOptionWithDefault('vu', 'vumeters', 'False')
        self.createOptionWithDefault('vu', 'tooloud', 'True')
        self.createOptionWithDefault('vu', 'tooloudtext', "TOO LOUD")

        self.createOptionWithDefault('leds', 'inactivebgcolor', '#222222')
        self.createOptionWithDefault('leds', 'inactivetextcolor', '#555555')

        self.createOptionWithDefault('led1', 'used', 'True')
        self.createOptionWithDefault('led1', 'text', 'ON AIR')
        self.createOptionWithDefault('led1', 'activebgcolor', '#FF0000')
        self.createOptionWithDefault('led1', 'activetextcolor', '#FFFFFF')
        self.createOptionWithDefault('led1', 'autoflash', 'False')
        self.createOptionWithDefault('led1', 'timedflash', 'False')

        self.createOptionWithDefault('led2', 'used', 'True')
        self.createOptionWithDefault('led2', 'text', 'PHONE')
        self.createOptionWithDefault('led2', 'activebgcolor', '#DCDC00')
        self.createOptionWithDefault('led2', 'activetextcolor', '#FFFFFF')
        self.createOptionWithDefault('led2', 'autoflash', 'False')
        self.createOptionWithDefault('led2', 'timedflash', 'False')

        self.createOptionWithDefault('led3', 'used', 'True')
        self.createOptionWithDefault('led3', 'text', 'DOORBELL')
        self.createOptionWithDefault('led3', 'activebgcolor', '#00C8C8')
        self.createOptionWithDefault('led3', 'activetextcolor', '#FFFFFF')
        self.createOptionWithDefault('led3', 'autoflash', 'False')
        self.createOptionWithDefault('led3', 'timedflash', 'False')

        self.createOptionWithDefault('led4', 'used', 'True')
        self.createOptionWithDefault('led4', 'text', 'ARI')
        self.createOptionWithDefault('led4', 'activebgcolor', '#FF00FF')
        self.createOptionWithDefault('led4', 'activetextcolor', '#FFFFFF')
        self.createOptionWithDefault('led4', 'autoflash', 'False')
        self.createOptionWithDefault('led4', 'timedflash', 'False')

        self.createOptionWithDefault('network', 'udpport', '3310')


    def restoreSettingsFromConfig(self):
        self.StationName.setText(self.config.get('general', 'stationname'))
        self.Slogan.setText(self.config.get('general', 'slogan'))
        self.setStationNameColor(self.getColorFromName(self.config.get('general', 'stationcolor')))
        self.setSloganColor(self.getColorFromName(self.config.get('general', 'slogancolor')))

        self.checkBox_VU.setChecked(self.config.getboolean('vu', 'vumeters'))
        self.checkBox_TooLoud.setChecked(self.config.getboolean('vu', 'tooloud'))
        self.TooLoudText.setText(self.config.get('vu', 'tooloudtext'))

        #not implemented in ui
        #self.config.get('leds', 'inactivebgcolor')
        #self.config.get('leds', 'inactivetextcolor')

        self.LED1.setChecked(self.config.getboolean('led1', 'used'))
        self.LED1Text.setText(self.config.get('led1', 'text'))
        self.setLED1BGColor(self.getColorFromName(self.config.get('led1', 'activebgcolor')))
        self.setLED1FGColor(self.getColorFromName(self.config.get('led1', 'activetextcolor')))
        self.LED1Autoflash.setChecked(self.config.getboolean('led1', 'autoflash'))
        self.LED1Timedflash.setChecked(self.config.getboolean('led1', 'timedflash'))

        self.LED2.setChecked(self.config.getboolean('led2', 'used'))
        self.LED2Text.setText(self.config.get('led2', 'text'))
        self.setLED2BGColor(self.getColorFromName(self.config.get('led2', 'activebgcolor')))
        self.setLED2FGColor(self.getColorFromName(self.config.get('led2', 'activetextcolor')))
        self.LED2Autoflash.setChecked(self.config.getboolean('led2', 'autoflash'))
        self.LED2Timedflash.setChecked(self.config.getboolean('led2', 'timedflash'))

        self.LED3.setChecked(self.config.getboolean('led3', 'used'))
        self.LED3Text.setText(self.config.get('led3', 'text'))
        self.setLED3BGColor(self.getColorFromName(self.config.get('led3', 'activebgcolor')))
        self.setLED3FGColor(self.getColorFromName(self.config.get('led3', 'activetextcolor')))
        self.LED3Autoflash.setChecked(self.config.getboolean('led3', 'autoflash'))
        self.LED3Timedflash.setChecked(self.config.getboolean('led3', 'timedflash'))

        self.LED4.setChecked(self.config.getboolean('led4', 'used'))
        self.LED4Text.setText(self.config.get('led4', 'text'))
        self.setLED4BGColor(self.getColorFromName(self.config.get('led4', 'activebgcolor')))
        self.setLED4FGColor(self.getColorFromName(self.config.get('led4', 'activetextcolor')))
        self.LED4Autoflash.setChecked(self.config.getboolean('led4', 'autoflash'))
        self.LED4Timedflash.setChecked(self.config.getboolean('led4', 'timedflash'))

        self.udpport.setText(self.config.get('network', 'udpport'))

    def getSettingsFromDialog(self):
        #self.config.set(section, option, default)

        self.config.set('general', 'stationname', self.StationName.displayText())
        self.config.set('general', 'slogan', self.Slogan.displayText())
        self.config.set('general', 'stationcolor', self.getStationNameColor().name())
        self.config.set('general', 'slogancolor', self.getSloganColor().name())
        self.config.set('vu', 'vumeters', ('True','False')[not self.checkBox_VU.isChecked()] )
        self.config.set('vu', 'tooloud', ('True','False')[not self.checkBox_TooLoud.isChecked()])
        self.config.set('vu', 'tooloudtext', self.TooLoudText.displayText())
        #not implemented in ui
        #self.config.set('leds', 'inactivebgcolor')
        #self.config.set('leds', 'inactivetextcolor')

        self.config.set('led1', 'used', ('True','False')[not self.LED1.isChecked()])
        self.config.set('led1', 'text', self.LED1Text.displayText())
        self.config.set('led1', 'activebgcolor', self.getLED1BGColor().name())
        self.config.set('led1', 'activetextgcolor', self.getLED1FGColor().name())
        self.config.set('led1', 'autoflash', ('True','False')[not self.LED1Autoflash.isChecked()])
        self.config.set('led1', 'timedflash', ('True','False')[not self.LED1Timedflash.isChecked()])

        self.config.set('led2', 'used', ('True','False')[not self.LED2.isChecked()])
        self.config.set('led2', 'text', self.LED2Text.displayText())
        self.config.set('led2', 'activebgcolor', self.getLED2BGColor().name())
        self.config.set('led2', 'activetextgcolor', self.getLED2FGColor().name())
        self.config.set('led2', 'autoflash', ('True','False')[not self.LED2Autoflash.isChecked()])
        self.config.set('led2', 'timedflash', ('True','False')[not self.LED2Timedflash.isChecked()])

        self.config.set('led3', 'used', ('True','False')[not self.LED3.isChecked()])
        self.config.set('led3', 'text', self.LED3Text.displayText())
        self.config.set('led3', 'activebgcolor', self.getLED3BGColor().name())
        self.config.set('led3', 'activetextgcolor', self.getLED3FGColor().name())
        self.config.set('led3', 'autoflash', ('True','False')[not self.LED3Autoflash.isChecked()])
        self.config.set('led3', 'timedflash', ('True','False')[not self.LED3Timedflash.isChecked()])

        self.config.set('led4', 'used', ('True','False')[not self.LED4.isChecked()])
        self.config.set('led4', 'text', self.LED4Text.displayText())
        self.config.set('led4', 'activebgcolor', self.getLED4BGColor().name())
        self.config.set('led4', 'activetextgcolor', self.getLED4FGColor().name())
        self.config.set('led4', 'autoflash', ('True','False')[not self.LED4Autoflash.isChecked()])
        self.config.set('led4', 'timedflash', ('True','False')[not self.LED4Timedflash.isChecked()])

        self.config.set('network', 'udpport', self.udpport.displayText())

    def createOptionWithDefault(self, section, option, default):
        if not self.config.has_section(section):
            self.config.add_section(section)
        if not self.config.has_option(section, option):
            self.config.set(section, option, default)

    def saveConfigToFile(self):
        cfgfile = open(os.path.expanduser('~/.onairscreen.ini'), 'w')
        self.config.write(cfgfile)
        cfgfile.close()

    def applySettings(self):
        #apply settings button pressed
        self.getSettingsFromDialog()
        self.saveConfigToFile()
        self.configChanged = True
        #self.hidesettings()

    def closeSettings(self):
        #close settings button pressed
        self.restoreSettingsFromConfig()
        self.hidesettings()

    def setLED1BGColor(self, newcolor=False):
        palette = self.LED1Text.palette()
        oldcolor = palette.base().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Base, newcolor)
        self.LED1Text.setPalette(palette)

    def setLED1FGColor(self, newcolor=False):
        palette = self.LED1Text.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Text, newcolor)
        self.LED1Text.setPalette(palette)

    def setLED2BGColor(self, newcolor=False):
        palette = self.LED2Text.palette()
        oldcolor = palette.base().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Base, newcolor)
        self.LED2Text.setPalette(palette)

    def setLED2FGColor(self, newcolor=False):
        palette = self.LED2Text.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Text, newcolor)
        self.LED2Text.setPalette(palette)

    def setLED3BGColor(self, newcolor=False):
        palette = self.LED3Text.palette()
        oldcolor = palette.base().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Base, newcolor)
        self.LED3Text.setPalette(palette)

    def setLED3FGColor(self, newcolor=False):
        palette = self.LED3Text.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Text, newcolor)
        self.LED3Text.setPalette(palette)

    def setLED4BGColor(self, newcolor=False):
        palette = self.LED4Text.palette()
        oldcolor = palette.base().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Base, newcolor)
        self.LED4Text.setPalette(palette)

    def setLED4FGColor(self, newcolor=False):
        palette = self.LED4Text.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Text, newcolor)
        self.LED4Text.setPalette(palette)

    def setStationNameColor(self, newcolor=False):
        palette = self.StationName.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Text, newcolor)
        self.StationName.setPalette(palette)

    def setSloganColor(self, newcolor=False):
        palette = self.Slogan.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QtGui.QPalette.Text, newcolor)
        self.Slogan.setPalette(palette)

    def getStationNameColor(self):
        palette = self.StationName.palette()
        color = palette.text().color()
        return color

    def getSloganColor(self):
        palette = self.Slogan.palette()
        color = palette.text().color()
        return color

    def getLED1BGColor(self):
        palette = self.LED1Text.palette()
        color = palette.base().color()
        return color

    def getLED2BGColor(self):
        palette = self.LED2Text.palette()
        color = palette.base().color()
        return color

    def getLED3BGColor(self):
        palette = self.LED3Text.palette()
        color = palette.base().color()
        return color

    def getLED4BGColor(self):
        palette = self.LED4Text.palette()
        color = palette.base().color()
        return color

    def getLED1FGColor(self):
        palette = self.LED1Text.palette()
        color = palette.text().color()
        return color

    def getLED2FGColor(self):
        palette = self.LED2Text.palette()
        color = palette.text().color()
        return color

    def getLED3FGColor(self):
        palette = self.LED3Text.palette()
        color = palette.text().color()
        return color

    def getLED4FGColor(self):
        palette = self.LED4Text.palette()
        color = palette.text().color()
        return color

    def openColorDialog(self, initcolor):
        colordialog = QtGui.QColorDialog()
        selectedcolor = colordialog.getColor(initcolor, None, 'Please select a color')
        if selectedcolor.isValid():
            return selectedcolor
        else:
            return initcolor

    def getColorFromName(self, colorname):
        color = QtGui.QColor()
        color.setNamedColor( colorname )
        return color


class MainScreen(QtGui.QWidget, Ui_MainScreen):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        Ui_MainScreen.__init__(self)
        self.setupUi(self)

        self.settings = Settings()
        self.restoreSettingsFromConfig()

        if self.settings.config.getboolean('general', 'fullscreen'):
            self.showFullScreen()

        # add hotkey bindings
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+F"), self, self.toggleFullScreen )
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Q"), self, QtCore.QCoreApplication.instance().quit )
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+C"), self, QtCore.QCoreApplication.instance().quit )
        QtGui.QShortcut(QtGui.QKeySequence("ESC"), self, QtCore.QCoreApplication.instance().quit )
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self, self.settings.showsettings )
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+,"), self, self.settings.showsettings )

        # Setup and start timer
        self.ctimer = QtCore.QTimer()
        QtCore.QObject.connect(self.ctimer, QtCore.SIGNAL("timeout()"), self.constantUpdate)
        self.ctimer.start(100)

        # Setup UDP Socket
        self.sock = QUdpSocket()
        self.sock.bind(self.settings.config.getint('network', 'udpport'), QUdpSocket.ShareAddress)
        self.sock.readyRead.connect(self.cmdHandler)

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

    def setStationColor(self, newcolor):
        palette = self.labelStation.palette()
        palette.setColor(QtGui.QPalette.WindowText, newcolor)
        self.labelStation.setPalette(palette)

    def setSloganColor(self, newcolor):
        palette = self.labelSlogan.palette()
        palette.setColor(QtGui.QPalette.WindowText, newcolor)
        self.labelSlogan.setPalette(palette)

    def restoreSettingsFromConfig(self):
        self.labelStation.setText(self.settings.config.get('general', 'stationname'))
        self.labelSlogan.setText(self.settings.config.get('general', 'slogan'))
        self.setStationColor(self.settings.getColorFromName(self.settings.config.get('general', 'stationcolor')))
        self.setSloganColor(self.settings.getColorFromName(self.settings.config.get('general', 'slogancolor')))
        self.setLED1Text(self.settings.config.get('led1', 'text'))
        self.setLED2Text(self.settings.config.get('led2', 'text'))
        self.setLED3Text(self.settings.config.get('led3', 'text'))
        self.setLED4Text(self.settings.config.get('led4', 'text'))

    def constantUpdate(self):
        # slot for constant timer timeout
        self.updateClock()
        self.updateDate()
        self.updateBacktimingText()
        self.updateBacktimingSeconds()
        if self.settings.configChanged == True:
            self.restoreSettingsFromConfig()
            self.settings.configChanged = False

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

        if minute >= 0 and minute < 15:
            string = "%d Minute%s nach %d" % (minute, 'n' if minute>1 else '', hour)

        if minute >= 15 and minute < 30:
            string = "%d Minute%s vor halb %d" % (remain_min-30, 'n' if remain_min-30>1 else '', hour)

        if minute >= 30 and minute < 45:
            string = "%d Minute%s nach halb %d" % (30-remain_min, 'n' if 30-remain_min>1 else '', hour)

        if minute >= 45 and minute <= 59:
            string = "%d Minute%s vor %d" % (remain_min, 'n' if remain_min>1 else '', hour+1)

        self.setRightText( string )

    def updateBacktimingSeconds(self):
        now = datetime.datetime.now()
        second = now.second
        remain_seconds = 60-second
        self.setBacktimingSecs(remain_seconds)

    def toggleFullScreen(self):
        if not self.settings.config.getboolean('general', 'fullscreen'):
            self.showFullScreen()
            self.settings.config.set('general', 'fullscreen', 'True')
            self.settings.saveConfigToFile()
        else:
            self.showNormal()
            self.settings.config.set('general', 'fullscreen', 'False')
            self.settings.saveConfigToFile()

    def setLED1(self, action):
        if action:
            self.buttonLED1.setStyleSheet("color:"+self.settings.config.get('led1','activetextcolor')+";background-color:"+self.settings.config.get('led1', 'activebgcolor'))
        else:
            self.buttonLED1.setStyleSheet("color:"+self.settings.config.get('leds','inactivetextcolor')+";background-color:"+self.settings.config.get('leds', 'inactivebgcolor'))

    def setLED2(self, action):
        if action:
            self.buttonLED2.setStyleSheet("color:"+self.settings.config.get('led2','activetextcolor')+";background-color:"+self.settings.config.get('led2', 'activebgcolor'))
        else:
            self.buttonLED2.setStyleSheet("color:"+self.settings.config.get('leds','inactivetextcolor')+";background-color:"+self.settings.config.get('leds', 'inactivebgcolor'))

    def setLED3(self, action):
        if action:
            self.buttonLED3.setStyleSheet("color:"+self.settings.config.get('led3','activetextcolor')+";background-color:"+self.settings.config.get('led3', 'activebgcolor'))
        else:
            self.buttonLED3.setStyleSheet("color:"+self.settings.config.get('leds','inactivetextcolor')+";background-color:"+self.settings.config.get('leds', 'inactivebgcolor'))

    def setLED4(self, action):
        if action:
            self.buttonLED4.setStyleSheet("color:"+self.settings.config.get('led4','activetextcolor')+";background-color:"+self.settings.config.get('led4', 'activebgcolor'))
        else:
            self.buttonLED4.setStyleSheet("color:"+self.settings.config.get('leds','inactivetextcolor')+";background-color:"+self.settings.config.get('leds', 'inactivebgcolor'))

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
        pass
        #self.labelSeconds.setText( str(value) )

    def showWarning(self, text):
        self.labelWarning.setText( text )
        self.labelWarning.show()

    def hideWarning(self):
        self.labelWarning.setText( "" )
        self.labelWarning.hide()

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    mainscreen = MainScreen()

    mainscreen.setCurrentSongText("-")
    mainscreen.setNewsText("-")

    mainscreen.setVULeft(0)
    mainscreen.setVURight(0)

    #mainscreen.hideWarning()
    mainscreen.setLED1(False)
    mainscreen.setLED2(False)
    mainscreen.setLED3(False)
    mainscreen.setLED4(False)

    mainscreen.show()
    # hide mousecursor
    app.setOverrideCursor( QtGui.QCursor( 10 ) );

    sys.exit(app.exec_())
