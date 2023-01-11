#! /bin/bash
BASE_URL=`cat base`
BASE_URL=${BASE_URL} AUTH_ENABLED=true screen -d -m -L -Logfile spokeserver.log -S spokeserver python3 server/server.py
