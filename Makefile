all : mainscreen.py settings.py resources_rc.py

mainscreen.py : mainscreen.ui
	pyuic6 mainscreen.ui -o mainscreen.py
	@echo "import resources_rc  # noqa: F401" | cat - mainscreen.py > temp && mv temp mainscreen.py || true

settings.py : settings.ui
	pyuic6 settings.ui -o settings.py
	@echo "import resources_rc  # noqa: F401" | cat - settings.py > temp && mv temp settings.py || true

resources_rc.py : resources.qrc
	@if command -v rcc >/dev/null 2>&1; then \
		rcc -g python -o resources_rc.py resources.qrc && \
		sed -i '' 's/from PySide6/from PyQt6/g' resources_rc.py; \
	elif [ -f /usr/local/Cellar/qt/*/share/qt/libexec/rcc ]; then \
		rcc_path=$$(find /usr/local/Cellar/qt -name rcc -type f | head -1); \
		$$rcc_path -g python -o resources_rc.py resources.qrc && \
		sed -i '' 's/from PySide6/from PyQt6/g' resources_rc.py; \
	else \
		echo "Warning: rcc tool not found. Using existing resources_rc.py if available."; \
	fi

clean cleandir:
	rm -rf $(CLEANFILES)

CLEANFILES = mainscreen.py settings.py resources_rc.py *.pyc
