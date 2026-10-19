@echo off
setlocal
title Stop STOCK Screener
pushd "%~dp0"
docker compose --project-name stock-local --file compose.yaml stop
if errorlevel 1 (
  echo Could not stop the screener. Check that Docker Desktop is running.
) else (
  echo Screener stopped. Your saved stock database has been kept.
)
popd
echo.
pause
