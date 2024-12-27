@echo off
SET VENV_DIR=uaaccess_env
IF NOT EXIST %VENV_DIR% (
echo Virtual environment not found. Creating...
python -m venv %VENV_DIR%
)
echo Activating virtual environment...
call %VENV_DIR%\Scripts\activate
echo Running build script...
python build_uaaccess.py
deactivate
pause
