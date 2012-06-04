#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, time, datetime, ConfigParser, os
from PyQt4 import QtGui, QtCore
from PyQt4.QtMultimedia import QAudio, QAudioDeviceInfo, QAudioFormat, QAudioInput

print "pyqt QtMultimedia test"


inputDevices = QAudioDeviceInfo.availableDevices(QAudio.AudioInput)

print "Available Audio Input Devices:"
for deviceInfo in inputDevices:
    print "---------------------------------------------------"
    print "Name:   " + deviceInfo.deviceName()
    print "Ch:     " + str(deviceInfo.supportedChannelCounts())
    print "Codecs: " + deviceInfo.supportedCodecs().join(',')
    print "Rates:  " + str(deviceInfo.supportedSampleRates())
    print "Sizes:  " + str(deviceInfo.supportedSampleSizes())
    print "Types:  " + str(deviceInfo.supportedSampleTypes())


print "==================================================="
print "System default Audio Input Device:"
print "---------------------------------------------------"
deviceInfo = QAudioDeviceInfo.defaultInputDevice()
print "Name:   " + deviceInfo.deviceName()
print "Ch:     " + str(deviceInfo.supportedChannelCounts())
print "Codecs: " + deviceInfo.supportedCodecs().join(',')
print "Rates:  " + str(deviceInfo.supportedSampleRates())
print "Sizes:  " + str(deviceInfo.supportedSampleSizes())
print "Types:  " + str(deviceInfo.supportedSampleTypes())
print "---------------------------------------------------"

audioFormat = QAudioFormat()
audioFormat.setChannels(2)
audioFormat.setSampleRate(8000)
audioFormat.setCodec("audio/pcm")
audioFormat.setSampleSize(16)
audioFormat.setByteOrder(QAudioFormat.LittleEndian)
audioFormat.setSampleType(QAudioFormat.SignedInt)

if (not deviceInfo.isFormatSupported(audioFormat)):
    print "default format not supported, try to use nearest"
    audioFormat = deviceInfo.nearestFormat(audioFormat)

print "***************************************************"
print "open Default Audio Input Device:"
audioInput = QAudioInput(audioFormat)
print "BufSize: " + str(audioInput.bufferSize())

#device = audioInput.start()

#audioInput.stop()

