@echo off
rem SPDX-License-Identifier: GPL-3.0-or-later

cd ../
SET VENV_DIR=uaaccess_env
IF NOT EXIST %VENV_DIR% (
echo Virtual environment not found. Creating...
python -m venv %VENV_DIR%
)
echo Activating virtual environment...
call %VENV_DIR%\Scripts\activate
echo Running build script...
cd builder
python build_uaaccess.py
deactivate
pause