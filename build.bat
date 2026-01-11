@echo off
echo Building SCORM Wrapper Wizard...
echo.

REM Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install requirements
echo Installing requirements...
pip install -r requirements.txt

REM Clean previous builds
echo.
echo Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

REM Build executable
echo.
echo Building executable...
pyinstaller --onefile --windowed --name "SCORM_Wrapper_Wizard" --icon="scorm-wizard-icon.ico" ^
    --add-data "working_scorm_zip_example;working_scorm_zip_example" ^
    --collect-all qt_material ^
    --collect-all PySide6 ^
    --hidden-import=qt_material ^
    --hidden-import=PySide6.QtCore ^
    --hidden-import=PySide6.QtGui ^
    --hidden-import=PySide6.QtWidgets ^
    --hidden-import=PySide6.QtOpenGL ^
    --hidden-import=PySide6.QtSvg ^
    --noconfirm ^
    --clean ^
    main.py

echo.
echo Build complete! Executable is in the 'dist' folder.
pause


