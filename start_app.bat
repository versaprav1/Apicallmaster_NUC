@echo off
REM Streamlit App Startup Script with __pycache__ Cleanup
REM This script activates venv, cleans cache, and starts Streamlit

echo.
echo === Starting Streamlit App ===
echo.

REM Step 1: Activate virtual environment
echo [1/4] Activating virtual environment...
if exist ".\.venv\Scripts\activate.bat" (
    call .\.venv\Scripts\activate.bat
    echo   Virtual environment activated (.venv)
) else if exist ".\apicallmaster\Scripts\activate.bat" (
    call .\apicallmaster\Scripts\activate.bat
    echo   Virtual environment activated (apicallmaster)
) else (
    echo   WARNING: venv not found
    echo   Continuing with system Python...
)

REM Step 2: Clean __pycache__ directories
echo.
echo [2/4] Cleaning __pycache__ directories...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
echo   Done!

REM Step 3: Clean .pyc files  
echo.
echo [3/4] Cleaning .pyc files...
del /s /q *.pyc >nul 2>&1
echo   Done!

echo.
echo === Workspace Cleaned ===
echo.

REM Step 4: Start Streamlit
echo [4/4] Starting Streamlit...
echo.

streamlit run app.py

REM Script will end when Streamlit is stopped (Ctrl+C)

