@echo off
REM ARC search engine backend (FastAPI). Requires MongoDB on localhost:27017
REM (see docker-compose.yml at the repo root) and dependencies from requirements.txt
cd /d "%~dp0"
python main.py
