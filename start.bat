@echo off
echo ========================================
echo    INEVITABILITY - Startup Script
echo    Structural Causal Goal Decompiler
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.9+
    pause
    exit /b 1
)

:: Install dependencies
echo [1/3] Installing Python dependencies...
pip install -r requirements.txt --quiet
echo      Done.
echo.

:: Start backend
echo [2/3] Starting backend API server on http://localhost:8000 ...
start /B cmd /c "python -m uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 3 /nobreak >nul

:: Start frontend
echo [3/3] Starting frontend on http://localhost:3000 ...
start /B cmd /c "python -m http.server 3000 --directory frontend"
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo    INEVITABILITY is running!
echo    Frontend: http://localhost:3000
echo    API:      http://localhost:8000/docs
echo ========================================
echo.
echo Press any key to stop all services...
pause >nul

:: Cleanup
taskkill /f /im uvicorn.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1
echo Services stopped.
