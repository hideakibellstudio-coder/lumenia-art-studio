@echo off
title Lumenia Brush Engine 2.0
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================================
echo   🎨 Inicializando Lumenia Brush Engine 2.0...
echo ========================================================
echo.

where pythonw >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    start "" pythonw main.py %*
    exit /b 0
)

where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    start "" python main.py %*
    exit /b 0
)

echo [ERRO] Python não foi encontrado no PATH do sistema.
echo Por favor, certifique-se de que o Python está instalado.
echo.
pause
