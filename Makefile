all : mainscreen.py settings.py

mainscreen.py : mainscreen.ui
	pyuic4 mainscreen.ui -o mainscreen.py

settings.py : settings.ui
	pyuic4 settings.ui -o settings.py

clean cleandir:
	rm -rf $(CLEANFILES)

CLEANFILES = mainscreen.py settings.py
