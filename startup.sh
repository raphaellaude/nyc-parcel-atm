#!/bin/bash

xset s noblank
xset s off
xset -dpms

cd backend
poetry run uvicorn main:app --reload --log-config log.conf & # start backend
cd ..

cd pluto-hist
http-server . --cors &
VITE_KIOSK=true pnpm dev &
cd ..

/usr/bin/chromium-browser --noerrdialogs --disable-infobars --kiosk --kiosk-printing http://localhost:5173
