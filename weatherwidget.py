# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets, QtSvg
import resources_rc


class WeatherWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(WeatherWidget, self).__init__(parent)

        self.setObjectName("WeatherWidget")
        self.resize(221, 135)
        self.setStyleSheet("QWidget#WeatherWidget {\n"
                           #"border-image: url(:/weather_backgrounds/images/clear_day.jpg) 0 0 0 0 stretch stretch;\n"
                           "background-image: url(:/weather_backgrounds/images/clear_day.jpg) 0 0 0 0 stretch stretch;\n"
                           "background-color: #000;\n"
                           "background-repeat: no-repeat;\n"
                           "}")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self)
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.cityLabel = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setPointSize(22)
        font.setBold(True)
        font.setWeight(75)

        self.cityLabel.setFont(font)
        self.cityLabel.setStyleSheet("color: #fff")
        self.cityLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.cityLabel.setObjectName("cityLabel")
        self.verticalLayout.addWidget(self.cityLabel)

        self.weatherLabel = QtWidgets.QLabel(self)
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

        self.weatherIcon = QtWidgets.QLabel(self)
        self.weatherIcon.setPixmap(QtGui.QPixmap(':/weather/images/weather/rainy-1.svg'))
        self.weatherIcon.setAlignment(QtCore.Qt.AlignCenter)
        self.weatherIcon.setObjectName("weatherIcon")

        self.horizontalLayout.addWidget(self.weatherIcon)

        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.temperatureLabel = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setPointSize(39)
        self.temperatureLabel.setFont(font)
        self.temperatureLabel.setStyleSheet("color: #fff")
        self.temperatureLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.temperatureLabel.setObjectName("label")
        self.verticalLayout_2.addWidget(self.temperatureLabel)
        self.conditionLabel = QtWidgets.QLabel(self)
        font = QtGui.QFont()
        font.setPointSize(13)
        self.conditionLabel.setFont(font)
        self.conditionLabel.setStyleSheet("color: #fff")
        self.conditionLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.conditionLabel.setObjectName("label_2")
        self.verticalLayout_2.addWidget(self.conditionLabel)
        self.horizontalLayout.addLayout(self.verticalLayout_2)
        self.verticalLayout_3.addLayout(self.horizontalLayout)

        self.cityLabel.setText("NEW YORK")
        self.weatherLabel.setText("WEATHER")
        self.temperatureLabel.setText("15°C")
        self.conditionLabel.setText("Light Rain")


if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    widget = WeatherWidget()
    # widget.setStyleSheet("background-color:black;")
    # widget.resize(500, 500)
    # widget.setClockMode(1)
    # widget.setAmPm(False)
    # widget.setShowSeconds(True)
    widget.show()
    sys.exit(app.exec_())
