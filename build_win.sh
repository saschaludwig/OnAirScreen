#!/bin/bash

eval $(docker-machine env default)
docker run -v "$(pwd):/src/" cdrx/pyinstaller-windows "pip install -r requirements.txt && pyinstaller -F -y -w --clean -i images/oas_icon.ico --dist ./dist/windows --workpath /tmp --specpath /tmp -n OnAirScreen start.py"
