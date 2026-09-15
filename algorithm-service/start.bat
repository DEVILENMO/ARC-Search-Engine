@echo off
REM Activate the conda environment created by scripts/setup_python_env.bat
call activate Python311-ARCSearchEngine
call python app.py
