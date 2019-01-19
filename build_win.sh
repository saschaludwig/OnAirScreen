#!/bin/bash
rm -rf ./dist/win/*
make && \
eval $(docker-machine env default) && \
docker run -v "$(pwd):/src/" cdrx/pyinstaller-windows "pip install -r requirements.txt && pyinstaller -F -y -w --clean -i images/oas_icon.ico --dist ./dist/win --workpath /tmp --specpath /tmp -n OnAirScreen start.py" && \
mv -f ./dist/win/OnAirScreen.exe ./dist/win/OnAirScreen_$(git rev-parse --short HEAD)_$(git describe --abbrev=0 --tags).exe

open dist/win/
