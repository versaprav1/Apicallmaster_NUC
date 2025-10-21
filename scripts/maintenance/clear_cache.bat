@echo off
REM Windows batch script to clear knowledge cache
REM Run this to force fresh API calls and entity string extraction

title Clear Knowledge Cache
color 0C

echo.
echo 🧹 Clear Knowledge Cache
echo ========================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python and try again
    pause
    exit /b 1
)

REM Run the cache clearing script
echo Running cache clearing script...
python clear_cache.py

echo.
echo ✅ Cache cleared successfully!
echo.
echo 💡 Next steps:
echo    1. Start Streamlit: streamlit run app.py
echo    2. Ask a new question to trigger fresh API calls
echo    3. Entity strings will be extracted and saved
echo.

REM Pause to show results
echo Press any key to close this window...
pause >nul


