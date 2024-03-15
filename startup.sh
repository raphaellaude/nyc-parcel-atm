#!/bin/bash

xset s noblank
xset s off
xset -dpms

unclutter -idle 0.5 -root &

USER=fishmulch

cd "/home/$USER/Documents/github/pluto-hist"

sed -i 's/"exited_cleanly":false/"exited_cleanly":true/' "/home/$USER/.config/chromium/Default/Preferences"
sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/' "/home/$USER/.config/chromium/Default/Preferences"

cd backend
poetry run uvicorn main:app --reload & # start backend
cd ..

cd pluto-hist
VITE_KIOSK=true npm run dev &
cd ..

/usr/bin/chromium-browser --noerrdialogs --disable-infobars --kiosk --kiosk-printing http://localhost:5173

