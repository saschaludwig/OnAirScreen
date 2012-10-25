all : mainscreen.py settings.py resources_rc.py

mainscreen.py : mainscreen.ui
	pyuic4 mainscreen.ui -o mainscreen.py

settings.py : settings.ui
	pyuic4 settings.ui -o settings.py

resources_rc.py : resources.qrc
	pyrcc4 resources.qrc -o resources_rc.py

clean cleandir:
	rm -rf $(CLEANFILES)

CLEANFILES = mainscreen.py settings.py resources_rc.py *.pyc
