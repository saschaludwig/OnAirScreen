#!/usr/bin/env python
# -*- coding: utf-8 -*-

# OnAirScreen
# Copyright 2012, Sascha Ludwig <sascha@astrastudio.de>
# settings_functions.py
#
#    This file is part of OnAirScreen
#
#    OnAirScreen is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    OnAirScreen is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with OnAirScreen.  If not, see <http://www.gnu.org/licenses/>.
#
from PyQt4.QtGui import QApplication, QWidget, QCursor, QPalette, QColorDialog, QColor, QShortcut, QKeySequence
from PyQt4.QtCore import SIGNAL, QSettings, QCoreApplication, QTimer, QObject, QVariant, pyqtSignal
from PyQt4.QtNetwork import QUdpSocket, QHostAddress, QHostInfo, QNetworkInterface
from settings import Ui_Settings

versionString = "0.6"

class Settings(QWidget, Ui_Settings):
    sigConfigChanged = pyqtSignal(int, unicode)
    sigExitOAS = pyqtSignal()
    sigConfigFinished = pyqtSignal()
    def __init__(self):
        self.row = -1
        QWidget.__init__(self)
        Ui_Settings.__init__(self)
        self.setupUi(self)
        self._connectSlots()
        self.hide()
        # read the config, add missing values, save config and re-read config
        self.restoreSettingsFromConfig()
        self.configChanged = True
        # set version string
        self.versionLabel.setText("Version %s" % versionString)

    def showsettings(self):
        self.show()

    def closeEvent(self, event):
        #emit config finished signal
        self.sigConfigFinished.emit()

    def exitOnAirScreen(self):
        #emit app close signal
        self.sigExitOAS.emit()

    def _connectSlots(self):
        self.connect(self.ApplyButton, SIGNAL("clicked()"), self.applySettings )
        self.connect(self.CloseButton, SIGNAL("clicked()"), self.closeSettings )
        self.connect(self.ExitButton, SIGNAL("clicked()"), self.exitOnAirScreen )
        self.connect(self.LEDInactiveBGColor, SIGNAL("clicked()"), self.setLEDInactiveBGColor )
        self.connect(self.LEDInactiveFGColor, SIGNAL("clicked()"), self.setLEDInactiveFGColor )
        self.connect(self.LED1BGColor, SIGNAL("clicked()"), self.setLED1BGColor )
        self.connect(self.LED1FGColor, SIGNAL("clicked()"), self.setLED1FGColor )
        self.connect(self.LED2BGColor, SIGNAL("clicked()"), self.setLED2BGColor )
        self.connect(self.LED2FGColor, SIGNAL("clicked()"), self.setLED2FGColor )
        self.connect(self.LED3BGColor, SIGNAL("clicked()"), self.setLED3BGColor )
        self.connect(self.LED3FGColor, SIGNAL("clicked()"), self.setLED3FGColor )
        self.connect(self.LED4BGColor, SIGNAL("clicked()"), self.setLED4BGColor )
        self.connect(self.LED4FGColor, SIGNAL("clicked()"), self.setLED4FGColor )

        self.connect(self.DigitalHourColorButton, SIGNAL("clicked()"), self.setDigitalHourColor )
        self.connect(self.DigitalSecondColorButton, SIGNAL("clicked()"), self.setDigitalSecondColor )
        self.connect(self.DigitalDigitColorButton, SIGNAL("clicked()"), self.setDigitalDigitColor )

        self.connect(self.StationNameColor, SIGNAL("clicked()"), self.setStationNameColor )
        self.connect(self.SloganColor, SIGNAL("clicked()"), self.setSloganColor )

        self.connect(self, SIGNAL("triggered()"), self.closeEvent )

    def restoreSettingsFromConfig(self):
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")

        settings.beginGroup("General")
        self.StationName.setText(settings.value('stationname', 'Radio Eriwan').toString())
        self.Slogan.setText(settings.value('slogan', 'Your question is our motivation').toString())
        self.setStationNameColor(self.getColorFromName(settings.value('stationcolor', '#FFAA00').toString()))
        self.setSloganColor(self.getColorFromName(settings.value('slogancolor', '#FFAA00').toString()))
        settings.endGroup()

        settings.beginGroup("VU")
        self.checkBox_TooLoud.setChecked(settings.value('tooloud', True).toBool())
        self.TooLoudText.setText(settings.value('tooloudtext', 'TOO LOUD').toString())
        settings.endGroup()

        settings.beginGroup("NTP")
        self.checkBox_NTPCheck.setChecked(settings.value('ntpcheck', True).toBool())
        self.NTPCheckServer.setText(settings.value('ntpcheckserver', 'ptbtime1.ptb.de').toString())
        settings.endGroup()

        settings.beginGroup("LEDS")
        self.setLEDInactiveBGColor(self.getColorFromName(settings.value('inactivebgcolor', '#222222').toString()))
        self.setLEDInactiveFGColor(self.getColorFromName(settings.value('inactivetextcolor', '#555555').toString()))
        settings.endGroup()

        settings.beginGroup("LED1")
        self.LED1.setChecked(settings.value('used', True).toBool())
        self.LED1Text.setText(settings.value('text', 'ON AIR').toString())
        self.setLED1BGColor(self.getColorFromName(settings.value('activebgcolor', '#FF0000').toString()))
        self.setLED1FGColor(self.getColorFromName(settings.value('activetextcolor', '#FFFFFF').toString()))
        self.LED1Autoflash.setChecked(settings.value('autoflash', False).toBool())
        self.LED1Timedflash.setChecked(settings.value('timedflash', False).toBool())
        settings.endGroup()

        settings.beginGroup("LED2")
        self.LED2.setChecked(settings.value('used', True).toBool())
        self.LED2Text.setText(settings.value('text', 'PHONE').toString())
        self.setLED2BGColor(self.getColorFromName(settings.value('activebgcolor', '#DCDC00').toString()))
        self.setLED2FGColor(self.getColorFromName(settings.value('activetextcolor', '#FFFFFF').toString()))
        self.LED2Autoflash.setChecked(settings.value('autoflash', False).toBool())
        self.LED2Timedflash.setChecked(settings.value('timedflash', False).toBool())
        settings.endGroup()

        settings.beginGroup("LED3")
        self.LED3.setChecked(settings.value('used', True).toBool())
        self.LED3Text.setText(settings.value('text', 'DOORBELL').toString())
        self.setLED3BGColor(self.getColorFromName(settings.value('activebgcolor', '#00C8C8').toString()))
        self.setLED3FGColor(self.getColorFromName(settings.value('activetextcolor', '#FFFFFF').toString()))
        self.LED3Autoflash.setChecked(settings.value('autoflash', False).toBool())
        self.LED3Timedflash.setChecked(settings.value('timedflash', False).toBool())
        settings.endGroup()

        settings.beginGroup("LED4")
        self.LED4.setChecked(settings.value('used', True).toBool())
        self.LED4Text.setText(settings.value('text', 'ARI').toString())
        self.setLED4BGColor(self.getColorFromName(settings.value('activebgcolor', '#FF00FF').toString()))
        self.setLED4FGColor(self.getColorFromName(settings.value('activetextcolor', '#FFFFFF').toString()))
        self.LED4Autoflash.setChecked(settings.value('autoflash', False).toBool())
        self.LED4Timedflash.setChecked(settings.value('timedflash', False).toBool())
        settings.endGroup()

        settings.beginGroup("Clock")
        self.clockDigital.setChecked(settings.value('digital', True).toBool())
        self.clockAnalog.setChecked(not settings.value('digital', True).toBool())
        self.setDigitalHourColor(self.getColorFromName(settings.value('digitalhourcolor', '#3232FF').toString()))
        self.setDigitalSecondColor(self.getColorFromName(settings.value('digitalsecondcolor', '#FF9900').toString()))
        self.setDigitalDigitColor(self.getColorFromName(settings.value('digitaldigitcolor', '#3232FF').toString()))
        settings.endGroup()

        settings.beginGroup("Network")
        self.udpport.setText(settings.value('udpport', '3310').toString())
        self.tcpport.setText(settings.value('tcpport', '3310').toString())
        settings.endGroup()

    def getSettingsFromDialog(self):
        settings = QSettings( QSettings.UserScope, "astrastudio", "OnAirScreen")

        settings.beginGroup("General")
        settings.setValue('stationname', self.StationName.displayText())
        settings.setValue('slogan', self.Slogan.displayText())
        settings.setValue('stationcolor', self.getStationNameColor().name())
        settings.setValue('slogancolor', self.getSloganColor().name())
        settings.endGroup()

        settings.beginGroup("VU")
        settings.setValue('tooloud', self.checkBox_TooLoud.isChecked())
        settings.setValue('tooloudtext', self.TooLoudText.displayText())
        settings.endGroup()

        settings.beginGroup("NTP")
        settings.setValue('ntpcheck', self.checkBox_NTPCheck.isChecked())
        settings.setValue('ntpcheckserver', self.NTPCheckServer.displayText())
        settings.endGroup()

        settings.beginGroup("LEDS")
        settings.setValue('inactivebgcolor', self.getLEDInactiveBGColor().name())
        settings.setValue('inactivetextcolor', self.getLEDInactiveFGColor().name())
        settings.endGroup()

        settings.beginGroup("LED1")
        settings.setValue('used', self.LED1.isChecked())
        settings.setValue('text', self.LED1Text.displayText())
        settings.setValue('activebgcolor', self.getLED1BGColor().name())
        settings.setValue('activetextcolor', self.getLED1FGColor().name())
        settings.setValue('autoflash', self.LED1Autoflash.isChecked())
        settings.setValue('timedflash', self.LED1Timedflash.isChecked())
        settings.endGroup()

        settings.beginGroup("LED2")
        settings.setValue('used', self.LED2.isChecked())
        settings.setValue('text', self.LED2Text.displayText())
        settings.setValue('activebgcolor', self.getLED2BGColor().name())
        settings.setValue('activetextcolor', self.getLED2FGColor().name())
        settings.setValue('autoflash', self.LED2Autoflash.isChecked())
        settings.setValue('timedflash', self.LED2Timedflash.isChecked())
        settings.endGroup()

        settings.beginGroup("LED3")
        settings.setValue('used', self.LED3.isChecked())
        settings.setValue('text', self.LED3Text.displayText())
        settings.setValue('activebgcolor', self.getLED3BGColor().name())
        settings.setValue('activetextcolor', self.getLED3FGColor().name())
        settings.setValue('autoflash', self.LED3Autoflash.isChecked())
        settings.setValue('timedflash', self.LED3Timedflash.isChecked())
        settings.endGroup()

        settings.beginGroup("LED4")
        settings.setValue('used', self.LED4.isChecked())
        settings.setValue('text', self.LED4Text.displayText())
        settings.setValue('activebgcolor', self.getLED4BGColor().name())
        settings.setValue('activetextcolor', self.getLED4FGColor().name())
        settings.setValue('autoflash', self.LED4Autoflash.isChecked())
        settings.setValue('timedflash', self.LED4Timedflash.isChecked())
        settings.endGroup()

        settings.beginGroup("Clock")
        settings.setValue('digital', self.clockDigital.isChecked())
        settings.setValue('digitalhourcolor', self.getDigitalHourColor().name())
        settings.setValue('digitalsecondcolor', self.getDigitalSecondColor().name())
        settings.setValue('digitaldigitcolor', self.getDigitalDigitColor().name())
        settings.endGroup()

        settings.beginGroup("Network")
        settings.setValue('udpport', self.udpport.displayText())
        settings.setValue('tcpport', self.tcpport.displayText())
        settings.endGroup()

    def applySettings(self):
        #apply settings button pressed
        self.getSettingsFromDialog()
        self.configChanged = True

    def closeSettings(self):
        #close settings button pressed
        self.restoreSettingsFromConfig()

    def setLED1BGColor(self, newcolor=False):
        palette = self.LED1Text.palette()
        oldcolor = palette.base().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Base, newcolor)
        self.LED1Text.setPalette(palette)

    def setLEDInactiveBGColor(self, newcolor=False):
        palette = self.LEDInactive.palette()
        oldcolor = palette.base().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Base, newcolor)
        self.LEDInactive.setPalette(palette)

    def setLEDInactiveFGColor(self, newcolor=False):
        palette = self.LEDInactive.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Text, newcolor)
        self.LEDInactive.setPalette(palette)

    def setLED1FGColor(self, newcolor=False):
        palette = self.LED1Text.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Text, newcolor)
        self.LED1Text.setPalette(palette)

    def setLED2BGColor(self, newcolor=False):
        palette = self.LED2Text.palette()
        oldcolor = palette.base().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Base, newcolor)
        self.LED2Text.setPalette(palette)

    def setLED2FGColor(self, newcolor=False):
        palette = self.LED2Text.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Text, newcolor)
        self.LED2Text.setPalette(palette)

    def setLED3BGColor(self, newcolor=False):
        palette = self.LED3Text.palette()
        oldcolor = palette.base().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Base, newcolor)
        self.LED3Text.setPalette(palette)

    def setLED3FGColor(self, newcolor=False):
        palette = self.LED3Text.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Text, newcolor)
        self.LED3Text.setPalette(palette)

    def setLED4BGColor(self, newcolor=False):
        palette = self.LED4Text.palette()
        oldcolor = palette.base().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Base, newcolor)
        self.LED4Text.setPalette(palette)

    def setLED4FGColor(self, newcolor=False):
        palette = self.LED4Text.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Text, newcolor)
        self.LED4Text.setPalette(palette)

    def setStationNameColor(self, newcolor=False):
        palette = self.StationName.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Text, newcolor)
        self.StationName.setPalette(palette)

    def setSloganColor(self, newcolor=False):
        palette = self.Slogan.palette()
        oldcolor = palette.text().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Text, newcolor)
        self.Slogan.setPalette(palette)

    def getStationNameColor(self):
        palette = self.StationName.palette()
        color = palette.text().color()
        return color

    def getSloganColor(self):
        palette = self.Slogan.palette()
        color = palette.text().color()
        return color

    def getLEDInactiveBGColor(self):
        palette = self.LEDInactive.palette()
        color = palette.base().color()
        return color

    def getLEDInactiveFGColor(self):
        palette = self.LEDInactive.palette()
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

    def getDigitalHourColor(self):
        palette = self.DigitalHourColor.palette()
        color = palette.window().color()
        return color

    def getDigitalSecondColor(self):
        palette = self.DigitalSecondColor.palette()
        color = palette.window().color()
        return color

    def getDigitalDigitColor(self):
        palette = self.DigitalDigitColor.palette()
        color = palette.window().color()
        return color

    def setDigitalHourColor(self, newcolor=False):
        palette = self.DigitalHourColor.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Window, newcolor)
        self.DigitalHourColor.setPalette(palette)

    def setDigitalSecondColor(self, newcolor=False):
        palette = self.DigitalSecondColor.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Window, newcolor)
        self.DigitalSecondColor.setPalette(palette)

    def setDigitalDigitColor(self, newcolor=False):
        palette = self.DigitalDigitColor.palette()
        oldcolor = palette.window().color()
        if not newcolor:
            newcolor = self.openColorDialog( oldcolor )
        palette.setColor(QPalette.Window, newcolor)
        self.DigitalDigitColor.setPalette(palette)

    def openColorDialog(self, initcolor):
        colordialog = QColorDialog()
        selectedcolor = colordialog.getColor(initcolor, None, 'Please select a color')
        if selectedcolor.isValid():
            return selectedcolor
        else:
            return initcolor

    def getColorFromName(self, colorname):
        color = QColor()
        color.setNamedColor( colorname )
        return color

