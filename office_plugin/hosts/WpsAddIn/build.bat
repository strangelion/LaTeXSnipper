@echo off
setlocal

:: LaTeXSnipper WPS Plugin Builder
:: Usage: build.bat [version]

set VERSION=%1
if "%VERSION%"=="" set VERSION=1.0.0

set SCRIPT_DIR=%~dp0
set PLUGIN_ROOT=%SCRIPT_DIR%..
set DIST_DIR=%PLUGIN_ROOT%\dist
set PLUGIN_NAME=LaTeXSnipper-WPS

echo ============================================
echo  LaTeXSnipper WPS Plugin Builder
echo  Version: %VERSION%
echo ============================================

:: Step 1: Create distribution directory
echo [1/3] Creating distribution directory...
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"
if not exist "%DIST_DIR%\%PLUGIN_NAME%" mkdir "%DIST_DIR%\%PLUGIN_NAME%"

:: Step 2: Copy plugin files
echo [2/3] Copying plugin files...

:: Copy main plugin files
copy /Y "%SCRIPT_DIR%ribbon.xml" "%DIST_DIR%\%PLUGIN_NAME%\"
copy /Y "%SCRIPT_DIR%main.js" "%DIST_DIR%\%PLUGIN_NAME%\"
copy /Y "%SCRIPT_DIR%taskpane.html" "%DIST_DIR%\%PLUGIN_NAME%\"

:: Copy assets
xcopy /E /I /Y "%SCRIPT_DIR%assets" "%DIST_DIR%\%PLUGIN_NAME%\assets"

:: Copy shared components
xcopy /E /I /Y "%PLUGIN_ROOT%\shared\*" "%DIST_DIR%\%PLUGIN_NAME%\shared\"

:: Step 3: Create ZIP package
echo [3/3] Creating ZIP package...

:: Check for PowerShell compression
where powershell >nul 2>&1
if %ERRORLEVEL% equ 0 (
    powershell -Command "Compress-Archive -Path '%DIST_DIR%\%PLUGIN_NAME%' -DestinationPath '%DIST_DIR%\%PLUGIN_NAME%-%VERSION%.zip' -Force"
    echo.
    echo ============================================
    echo  WPS Plugin built successfully!
    echo  Output: %DIST_DIR%\%PLUGIN_NAME%-%VERSION%.zip
    echo.
    echo  Installation:
    echo  1. Extract the ZIP file
    echo  2. Copy to WPS plugin directory:
    echo     %%APPDATA%%\kingsoft\wps\jsaddons\%PLUGIN_NAME%\
    echo  3. Restart WPS Office
    echo ============================================
) else (
    echo ERROR: PowerShell not found. Cannot create ZIP file.
    echo Plugin files are available at: %DIST_DIR%\%PLUGIN_NAME%
    exit /b 1
)
