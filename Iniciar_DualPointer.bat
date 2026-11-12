@echo off
title DualPointer Pro
cd /d "%~dp0"
if exist "DualPointerPro.exe" (
    start "" "DualPointerPro.exe"
) else (
    start "" pythonw main.py
)
exit
