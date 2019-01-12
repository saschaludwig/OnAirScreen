#!/usr/bin/env bash
#pyinstaller -F -y -w -i images/oas_icon.icns -n OnAirScreen --distpath ./dist/osx/ "$@" start.py
pyinstaller --distpath ./dist/osx/ OnAirScreen_osx.spec