@echo off
setlocal

:: LaTeXSnipper WPS Plugin Installer Builder
:: Usage: build-wps-setup.bat [version]

set VERSION=%1
if "%VERSION%"=="" set VERSION=1.0.0

set SCRIPT_DIR=%~dp0
set PLUGIN_ROOT=%SCRIPT_DIR%..
set DIST_DIR=%PLUGIN_ROOT%\dist

echo ============================================
echo  LaTeXSnipper WPS Plugin Installer Builder
echo  Version: %VERSION%
echo ============================================

:: Step 1: Build WPS Plugin package first
echo [1/2] Building WPS Plugin package...
call "%PLUGIN_ROOT%\hosts\WpsAddIn\build-wps-plugin.bat" %VERSION%
if %ERRORLEVEL% neq 0 (
    echo ERROR: WPS Plugin package build failed.
    exit /b 1
)

:: Step 2: Run Inno Setup
echo [2/2] Building installer...
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"

:: Find Inno Setup ISCC.exe
set ISCC=
if exist "C:\Users\WangWenXuan\AppData\Local\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC=C:\Users\WangWenXuan\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
)
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6" (
    for %%d in ("%ProgramFiles(x86)%\Inno Setup 6") do (
        if exist "%%~d\ISCC.exe" set "ISCC=%%~d\ISCC.exe"
    )
)
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6" (
    for %%d in ("%ProgramFiles%\Inno Setup 6") do (
        if exist "%%~d\ISCC.exe" set "ISCC=%%~d\ISCC.exe"
    )
)
if not defined ISCC (
    for /f "delims=" %%i in ('where iscc 2^>nul') do set ISCC=%%i
)
if not defined ISCC (
    echo ERROR: Inno Setup 6 not found.
    echo Please install from https://jrsoftware.org/isinfo.php
    echo Or specify path in build-wps-setup.bat
    exit /b 1
)

echo Using Inno Setup: %ISCC%
"%ISCC%" /DVersion=%VERSION% "%SCRIPT_DIR%wps-setup.iss"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Installer build failed.
    exit /b 1
)

echo ============================================
echo  WPS Plugin Installer built successfully!
echo  Output: %DIST_DIR%\WPSPluginSetup-%VERSION%.exe
echo.
echo  Installation:
echo  1. Run WPSPluginSetup-%VERSION%.exe
echo  2. Follow the installation wizard
echo  3. Restart WPS Office
echo  4. Enable the plugin in WPS settings
echo ============================================
