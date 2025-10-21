@echo off
REM Windows batch script to clean up __pycache__ directories
REM Run this before starting Streamlit to avoid file watcher issues

title Python __pycache__ Cleanup Script
color 0A

echo.
echo 🧹 Python __pycache__ Cleanup Script
echo =====================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

REM Run the Python cleanup script
echo Running cleanup script...
python cleanup_pycache.py

echo.
echo ✅ Cleanup completed!
echo.
echo 💡 Next steps:
echo    1. Start Streamlit: streamlit run app.py
echo    2. Ask questions to test the application
echo.

REM Pause to show results
echo Press any key to close this window...
pause >nul
3