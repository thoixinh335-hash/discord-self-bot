@echo off
cd /d %~dp0
:loop
echo [%date% %time%] Starting bot...
C:\Users\klikl\AppData\Local\Python\pythoncore-3.14-64\python.exe main.py
echo [%date% %time%] Bot crashed or stopped. Restarting in 5 seconds...
timeout /t 5 >nul
goto loop
