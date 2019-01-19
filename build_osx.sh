#!/usr/bin/env bash
#pyinstaller -F -y -w -i images/oas_icon.icns -n OnAirScreen --distpath ./dist/osx/ "$@" start.py
rm -rf ./dist/osx/*
make && \
pyinstaller -y --distpath ./dist/osx/ "$@" OnAirScreen_osx.spec && \
mv -f ./dist/osx/OnAirScreen.app ./dist/osx/OnAirScreen_$(git rev-parse --short HEAD)_$(git describe --abbrev=0 --tags).app

open dist/osx/