@echo off
setlocal

cd /d "G:\masters JU\Thesis\bpdb-intelligence"
if errorlevel 1 exit /b 1

if not exist "data\logs" mkdir "data\logs"

set "PYTHONPATH=%CD%\backend"

echo Daily collection started: %date% %time%>>"data\logs\collection-daily.log"

".venv\Scripts\python.exe" -u -m ingestion.collect_pdfs --daily >>"data\logs\collection-daily.log" 2>&1

set "COLLECT_EXIT=%ERRORLEVEL%"

echo Daily collection finished: %date% %time% Exit: %COLLECT_EXIT%>>"data\logs\collection-daily.log"

exit /b %COLLECT_EXIT%