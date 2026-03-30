@echo off
echo Starting pymobiledevice3 tunnel (requires admin)...
echo Make sure your iPhone is connected via USB and you have tapped "Trust".
echo.
powershell -Command "Start-Process python -ArgumentList '-m pymobiledevice3 remote tunneld' -Verb RunAs"
echo.
echo Tunnel is starting in a separate admin window.
echo Once it says "tunnel created", run: python main.py
pause
