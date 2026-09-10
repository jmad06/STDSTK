@echo off
setlocal enabledelayedexpansion

:: Cambiar al directorio donde está este .bat (y main.py)
cd /d "%~dp0"

:: Verificar si se arrastró un archivo
if "%~1"=="" (
    echo.
    echo  [ERROR] No se ha arrastrado ningún archivo.
    echo  Arrastra un archivo .csv o .xlsx sobre este .bat.
    echo.
    pause
    exit /b 1
)

set "ARCHIVO=%~1"

:: Verificar que la extensión sea válida
set "EXT=%~x1"
if /i not "!EXT!"==".csv" if /i not "!EXT!"==".xlsx" (
    echo.
    echo  [ERROR] El archivo arrastrado no es .csv ni .xlsx.
    echo  Archivo: !ARCHIVO!
    echo.
    pause
    exit /b 1
)

:: Verificar que Python esté disponible
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Python no esta instalado o no se encuentra en el PATH.
    echo  Instala Python y asegurate de que el comando 'python' funcione.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Ejecutando Data Profiling sobre:
echo  !ARCHIVO!
echo ============================================================
echo.

:: Ejecutar main.py con el archivo como argumento
python main.py "!ARCHIVO!"

:: Pausa para ver el resultado (opcional, puedes quitarla si no quieres esperar)
echo.
echo Proceso finalizado.
pause