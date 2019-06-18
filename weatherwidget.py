# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets
import resources_rc


class WeatherWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        WeatherWidget.setObjectName("WeatherWidget")
        WeatherWidget.resize(221, 135)
        WeatherWidget.setStyleSheet("QWidget#WeatherWidget {\n"
"border-image: url(:/weather_backgrounds/images/clear_day.jpg) 0 0 0 0 stretch stretch;\n"
"background-color: #000;\n"
"background-size: contain;\n"
"background-repeat: no-repeat;\n"
"}")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(WeatherWidget)
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.cityLabel = QtWidgets.QLabel(WeatherWidget)
        font = QtGui.QFont()
        font.setPointSize(22)
        font.setBold(True)
        font.setWeight(75)
        self.cityLabel.setFont(font)
        self.cityLabel.setStyleSheet("color: #fff")
        self.cityLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.cityLabel.setObjectName("cityLabel")
        self.verticalLayout.addWidget(self.cityLabel)
        self.weatherLabel = QtWidgets.QLabel(WeatherWidget)
        font = QtGui.QFont()
        font.setPointSize(14)
        self.weatherLabel.setFont(font)
        self.weatherLabel.setStyleSheet("color: #fff")
        self.weatherLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.weatherLabel.setObjectName("weatherLabel")
        self.verticalLayout.addWidget(self.weatherLabel)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem1)
        self.verticalLayout_3.addLayout(self.verticalLayout)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_3 = QtWidgets.QLabel(WeatherWidget)
        font = QtGui.QFont()
        font.setPointSize(50)
        self.label_3.setFont(font)
        self.label_3.setPixmap(QtGui.QPixmap(":/weather/images/weather/rainy-1.svg"))
        self.label_3.setAlignment(QtCore.Qt.AlignCenter)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout.addWidget(self.label_3)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label = QtWidgets.QLabel(WeatherWidget)
        font = QtGui.QFont()
        font.setPointSize(39)
        self.label.setFont(font)
        self.label.setStyleSheet("color: #fff")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")
        self.verticalLayout_2.addWidget(self.label)
        self.label_2 = QtWidgets.QLabel(WeatherWidget)
        font = QtGui.QFont()
        font.setPointSize(13)
        self.label_2.setFont(font)
        self.label_2.setStyleSheet("color: #fff")
        self.label_2.setAlignment(QtCore.Qt.AlignCenter)
        self.label_2.setObjectName("label_2")
        self.verticalLayout_2.addWidget(self.label_2)
        self.horizontalLayout.addLayout(self.verticalLayout_2)
        self.verticalLayout_3.addLayout(self.horizontalLayout)

        self.cityLabel.setText("WeatherWidget", "NEW YORK")
        self.weatherLabel.setText("WeatherWidget", "WEATHER")
        self.label.setText("WeatherWidget", "15°C")
        self.label_2.setText("WeatherWidget", "Light Rain")



