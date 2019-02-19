#!/usr/bin/env bash
#pyinstaller -F -y -w -i images/oas_icon.icns -n OnAirScreen --distpath ./dist/osx/ "$@" start.py
rm -rf ./dist/osx/*
source venv/bin/activate
make && \
pyinstaller -y --distpath ./dist/osx/ "$@" OnAirScreen_osx.spec && \
mv -f ./dist/osx/OnAirScreen.app ./dist/osx/OnAirScreen_$(git describe --abbrev=0 --tags)_$(git rev-parse --short HEAD).app

open dist/osx/
