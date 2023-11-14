@echo off

REM Get the current hour in 24-hour format
for /f "delims=" %%t in ('time /t') do set "currentHour=%%t"
set "currentHour=%currentHour:~0,2%"

REM Check if the current hour is between 9 and 10
if %currentHour% geq 09 if %currentHour% lss 10 (
    echo Running the parser...
    python "C:\Users\CemXokenc\Desktop\parser.py"
) else (
    echo Skipping parser execution outside the specified time range.
)

echo Parser completed. Terminating the bot...
taskkill /IM python.exe /F

REM Check if the script is already running
tasklist /FI "IMAGENAME eq cmd.exe" /FI "WINDOWTITLE eq Administrator:  cmd.exe - my_script.bat" 2>NUL | find /I /N "cmd.exe" >NUL
if "%ERRORLEVEL%"=="0" (
    REM Close the previous cmd window
    taskkill /FI "WINDOWTITLE eq Administrator:  cmd.exe - my_script.bat" /F
)

echo Running the bot...
start "Administrator:  cmd.exe - my_script.bat" cmd /c python "C:\Users\CemXokenc\Desktop\bot.py"

echo Script execution completed.
