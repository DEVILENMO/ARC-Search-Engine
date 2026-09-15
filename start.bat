@echo off
REM ARC Search Engine one-click launcher (Windows)
REM
REM Prerequisites:
REM   1. MongoDB reachable at localhost:27017   -> docker compose up -d
REM   2. Backend deps installed                 -> pip install -r backend/requirements.txt
REM   3. Frontend deps installed (Node 14-16)   -> cd frontend ^&^& npm install
REM
REM Optional:
REM   set LLM_API_KEY=sk-xxx                    (enables the remote LLM channel)

cd /d "%~dp0"

echo Starting backend (FastAPI, port 8899)...
start "ARC backend" cmd /c "cd backend && python main.py"

echo Starting frontend (webpack dev server, port 8080)...
start "ARC frontend" cmd /c "cd frontend && npm run dev"

echo.
echo Backend  ready when you see: Uvicorn running on http://0.0.0.0:8899
echo Frontend ready at: http://localhost:8080/
