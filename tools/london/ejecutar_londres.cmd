@echo off
REM ICT 3.0 · snapshot Londres +15m (NO modifica la tarea de 07:45 Ecuador)
setlocal
set "REPO=C:\Users\v_jac\Desktop\MT5-POI-Compartido\SMC3.0"
set "PY=%REPO%\.venv\Scripts\python.exe"
set "LOG=%REPO%\data\londres_run.log"
if not exist "%PY%" (
  echo Falta el entorno virtual del proyecto >> "%LOG%" 2>&1
  exit /b 1
)
cd /d "%REPO%"
echo === %DATE% %TIME% >> "%LOG%" 2>&1
"%PY%" tools\london\run_daily.py --repo "%REPO%" >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
echo exit=%RC% >> "%LOG%" 2>&1
exit /b %RC%
