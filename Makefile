all : mainscreen.py settings.py weatherwidget.py resources_rc.py

mainscreen.py : mainscreen.ui
	pyuic5 mainscreen.ui -o mainscreen.py

settings.py : settings.ui
	pyuic5 settings.ui -o settings.py

weatherwidget.py : weatherwidget.ui
	pyuic5 weatherwidget.ui -o weatherwidget.py

resources_rc.py : resources.qrc
	pyrcc5 resources.qrc -o resources_rc.py

clean cleandir:
	rm -rf $(CLEANFILES)

CLEANFILES = mainscreen.py settings.py weatherwidget.py resources_rc.py *.pyc
