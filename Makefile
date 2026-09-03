all : mainscreen.py settings.py resources_rc.py

mainscreen.py : mainscreen.ui
	pyside6-uic mainscreen.ui -o mainscreen.py
	@echo "import resources_rc  # noqa: F401" | cat - mainscreen.py > temp && mv temp mainscreen.py || true

settings.py : settings.ui
	pyside6-uic settings.ui -o settings.py
	@echo "import resources_rc  # noqa: F401" | cat - settings.py > temp && mv temp settings.py || true

resources_rc.py : resources.qrc
	@if command -v pyside6-rcc >/dev/null 2>&1; then \
		pyside6-rcc resources.qrc -o resources_rc.py; \
	elif command -v rcc >/dev/null 2>&1; then \
		rcc -g python -o resources_rc.py resources.qrc; \
	else \
		rcc_path=""; \
		if [ -d /usr/local/Cellar/qt ]; then \
			rcc_path=$$(find -L /usr/local/Cellar/qt -name rcc -type f 2>/dev/null | head -1); \
		fi; \
		if [ -z "$$rcc_path" ] && [ -d /opt/homebrew/Cellar/qt ]; then \
			rcc_path=$$(find -L /opt/homebrew/Cellar/qt -name rcc -type f 2>/dev/null | head -1); \
		fi; \
		if [ -n "$$rcc_path" ]; then \
			$$rcc_path -g python -o resources_rc.py resources.qrc; \
		else \
			echo "Warning: rcc tool not found. Using existing resources_rc.py if available."; \
		fi; \
	fi

clean cleandir:
	rm -rf $(CLEANFILES)

CLEANFILES = mainscreen.py settings.py resources_rc.py *.pyc
