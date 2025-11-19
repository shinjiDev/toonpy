@echo off
REM Script para publicar toonpy en PyPI (Windows)

echo Limpiando builds anteriores...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist toonpy.egg-info rmdir /s /q toonpy.egg-info
if exist *.egg-info (
    for /d %%d in (*.egg-info) do rmdir /s /q "%%d"
)

echo Ejecutando tests...
pytest tests/ -v
if errorlevel 1 (
    echo ERROR: Los tests fallaron. No se puede publicar.
    exit /b 1
)

echo Construyendo paquete...
python -m build
if errorlevel 1 (
    echo ERROR: Fallo al construir el paquete.
    exit /b 1
)

echo Verificando paquete...
twine check dist/*
if errorlevel 1 (
    echo ERROR: El paquete tiene errores.
    exit /b 1
)

echo.
echo Paquete listo para publicar!
echo.
echo Para publicar en TestPyPI:
echo   twine upload --repository testpypi dist/*
echo.
echo Para publicar en PyPI:
echo   twine upload dist/*
echo.

