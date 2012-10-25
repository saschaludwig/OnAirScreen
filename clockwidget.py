#!/usr/bin/env python

#############################################################################
##
## OnAirScreen Analog Clock implementation
## Copyright (C) 2012 Sascha Ludwig
## All rights reserved.
##
## contains code from Riverbank Computing Limited and Nokia Corporation
## for details: see copyright notice below
##

#############################################################################
##
## Copyright (C) 2010 Riverbank Computing Limited.
## Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).
## All rights reserved.
##
## This file is part of the examples of PyQt.
##
## $QT_BEGIN_LICENSE:BSD$
## You may use this file under the terms of the BSD license as follows:
##
## "Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are
## met:
##   * Redistributions of source code must retain the above copyright
##     notice, this list of conditions and the following disclaimer.
##   * Redistributions in binary form must reproduce the above copyright
##     notice, this list of conditions and the following disclaimer in
##     the documentation and/or other materials provided with the
##     distribution.
##   * Neither the name of Nokia Corporation and its Subsidiary(-ies) nor
##     the names of its contributors may be used to endorse or promote
##     products derived from this software without specific prior written
##     permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
## "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
## LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
## A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
## OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
## SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
## LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
## DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
## $QT_END_LICENSE$
##
#############################################################################


from PyQt4 import QtCore, QtGui


class ClockWidget(QtGui.QWidget):

    __pyqtSignals__ = ("timeChanged(QTime)", "timeZoneChanged(int)")

    hourColor = QtGui.QColor(200, 200, 200, 255)
    minuteColor = QtGui.QColor(220, 220, 220, 255)
    circleColor = QtGui.QColor(220, 220, 220, 255)

    timeZoneOffset = 0

    def __init__(self, parent=None):
        super(ClockWidget, self).__init__(parent)

        timer = QtCore.QTimer(self)
        self.connect(timer, QtCore.SIGNAL("timeout()"), self, QtCore.SLOT("update()"))
        self.connect(timer, QtCore.SIGNAL("timeout()"), self.updateTime)
        timer.start(1000)

    def updateTime(self):
        self.emit(QtCore.SIGNAL("timeChanged(QTime)"), QtCore.QTime.currentTime())

    def getTimeZone(self):
        return self.timeZoneOffset

    @QtCore.pyqtSignature("setTimeZone(int)")
    def setTimeZone(self, value):
        if value != self.timeZoneOffset:
            self.timeZoneOffset = value
            self.emit(QtCore.SIGNAL("timeZoneChanged(int)"), value)
            self.update()

    def resetTimeZone(self):
        if self.timeZoneOffset != 0:
            self.timeZoneOffset = 0
            self.emit(QtCore.SIGNAL("timeZoneChanged(int)"), 0)
            self.update()

    timeZone = QtCore.pyqtProperty("int", getTimeZone, setTimeZone, resetTimeZone)

    def paintEvent(self, event):
        side = min(self.width(), self.height())
        time = QtCore.QTime.currentTime()

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(side / 200.0, side / 200.0)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(ClockWidget.hourColor)

        # set hour hand length and minute hand length
        hhl = -65 #-50
        mhl = -85 #-75
        # draw hour hand
        painter.save()
        painter.rotate(30.0 * ((time.hour() + time.minute() / 60.0)))
        painter.drawRoundedRect(-4,4,8,hhl,4.0,4.0)
        painter.restore()

        painter.setPen(ClockWidget.hourColor)

        for i in range(12):
            painter.drawRoundedRect(88,-1,8,2,1.0,1.0)
            painter.rotate(30.0)

        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(ClockWidget.minuteColor)

        #draw minute hand
        sizefactor = 1.3
        painter.save()
        painter.rotate(6.0 * (time.minute() + time.second() / 60.0))
        painter.drawRoundedRect(-4/sizefactor,4/sizefactor,8/sizefactor,mhl,4.0/sizefactor,4.0/sizefactor)
        painter.restore()

        #draw center circle
        painter.setBrush(ClockWidget.circleColor)
        painter.save()
        painter.drawEllipse(-6,-6,12,12)
        painter.restore()

        painter.setPen(ClockWidget.minuteColor)

        for j in range(60):
            if (j % 5) != 0:
                painter.drawLine(92, 0, 96, 0)
            painter.rotate(6.0)


if __name__ == '__main__':

    import sys

    app = QtGui.QApplication(sys.argv)
    widget = ClockWidget()
    widget.setStyleSheet("background-color:black;")
    widget.resize(500,500)
    widget.show()
    sys.exit(app.exec_())
