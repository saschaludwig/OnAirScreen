all : mainscreen.py dynscreen.py settings.py

mainscreen.py : mainscreen.ui
	pyuic4 mainscreen.ui -o mainscreen.py

dynscreen.py : dynscreen.ui
	pyuic4 dynscreen.ui -o dynscreen.py

settings.py : settings.ui
	pyuic4 settings.ui -o settings.py

clean cleandir:
	rm -rf $(CLEANFILES)

CLEANFILES = mainscreen.py dynscreen.py settings.py *.pyc
