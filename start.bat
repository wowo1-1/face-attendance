@echo off
cd /d D:\ai\wanzixijiance\face-attendance
echo [1/2] Starting backend (loading models, 10-20s first time)...
start /min cmd /c "python -m uvicorn main:app --host 0.0.0.0 --port 8000"
timeout /t 10 /nobreak >nul
echo [2/2] Starting frontend...
start cmd /c "python -m streamlit run ui/streamlit_app.py --server.port 8502 --client.toolbarMode minimal"
echo.
echo Backend : http://localhost:8000
echo Frontend: http://localhost:8502
echo.
pause
