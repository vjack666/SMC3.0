@echo off
REM Instala la automatizacion Londres +15m (NO toca la tarea de 07:45 Ecuador).
REM Zona local de la maquina: America/Guayaquil (UTC-05:00, sin DST).
REM 08:15 Europe/London = 03:15 GYE en GMT (invierno) = 02:15 GYE en BST (verano).
REM Se crean dos disparadores; run_daily.py decide cual es valido con Europe/London.
setlocal
set "REPO=C:\Users\v_jac\Desktop\MT5-POI-Compartido\SMC3.0"
set "RUNNER=%REPO%\tools\london\ejecutar_londres.cmd"
if not exist "%RUNNER%" (
  echo Falta %RUNNER%
  exit /b 1
)
schtasks /create /tn "ICT3_Londres_0815_BST" /tr "\"%RUNNER%\"" /sc daily /st 02:20 /f
schtasks /create /tn "ICT3_Londres_0815_GMT" /tr "\"%RUNNER%\"" /sc daily /st 03:20 /f
echo Tareas creadas: ICT3_Londres_0815_BST (02:20) e ICT3_Londres_0815_GMT (03:20), hora Guayaquil.
echo La tarea existente de 07:45 no se modifica.
