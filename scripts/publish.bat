@echo off
REM Script to publish toonpy on PyPI (Windows)

echo Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist toonpy.egg-info rmdir /s /q toonpy.egg-info
if exist *.egg-info (
    for /d %%d in (*.egg-info) do rmdir /s /q "%%d"
)

echo Running tests...
pytest tests/ -v
if errorlevel 1 (
    echo ERROR: Tests failed. Cannot publish.
    exit /b 1
)

echo Building package...
python -m build
if errorlevel 1 (
    echo ERROR: Failed to build the package.
    exit /b 1
)

echo Checking package...
twine check dist/*
if errorlevel 1 (
    echo ERROR: The package has issues.
    exit /b 1
)

echo.
echo Package ready to publish!
echo.
echo To publish on TestPyPI:
echo   twine upload --repository testpypi dist/*
echo.
echo To publish on PyPI:
echo   twine upload dist/*
echo.

