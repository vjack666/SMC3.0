@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Falta instalar las dependencias. Consulta README.md.
  pause
  exit /b 1
)
powershell -NoProfile -Command "$c = [Net.Sockets.TcpClient]::new(); try { $c.Connect('127.0.0.1',8766) } catch { Start-Process -WindowStyle Hidden -FilePath '.venv\Scripts\python.exe' -ArgumentList 'smc.py','serve' -WorkingDirectory (Get-Location).Path; Start-Sleep -Milliseconds 1000 } finally { $c.Dispose() }"
start "" "http://127.0.0.1:8766"
