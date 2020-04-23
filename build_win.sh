#!/bin/bash
rm -rf ./dist/win/*
source venv/bin/activate
make && \
eval $(docker-machine env default) && \
docker run -v "$(pwd):/src/" cdrx/pyinstaller-windows "pip install -r requirements.txt && cp -v images/oas_icon.ico /tmp && pyinstaller -F --clean -y -w --icon='oas_icon.ico' --dist ./dist/win --workpath /tmp --specpath /tmp -n OnAirScreen start.py ; pyinstaller -F -y --clean -c --dist ./dist/win --workpath /tmp --specpath /tmp -n oas_send utils/oas_send.py" && \
mv -f ./dist/win/OnAirScreen.exe ./dist/win/OnAirScreen_$(git describe --abbrev=0 --tags)_$(git rev-parse --short HEAD).exe
mv -f ./dist/win/oas_send.exe ./dist/win/oas_send_$(git describe --abbrev=0 --tags)_$(git rev-parse --short HEAD).exe

open dist/win/