# Streamlit App Startup Script with __pycache__ Cleanup
# This script activates venv, cleans cache, and starts Streamlit

Write-Host "`n=== Starting Streamlit App ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Activate virtual environment
Write-Host "[1/4] Activating virtual environment..." -ForegroundColor Yellow
if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    & .\.venv\Scripts\Activate.ps1
    Write-Host "  Virtual environment activated (.venv)" -ForegroundColor Green
} elseif (Test-Path ".\apicallmaster\Scripts\Activate.ps1") {
    & .\apicallmaster\Scripts\Activate.ps1
    Write-Host "  Virtual environment activated (apicallmaster)" -ForegroundColor Green
} else {
    Write-Host "  WARNING: venv not found" -ForegroundColor Red
    Write-Host "  Continuing with system Python..." -ForegroundColor Yellow
}

# Step 2: Clean __pycache__ directories
Write-Host "`n[2/4] Cleaning __pycache__ directories..." -ForegroundColor Yellow
$pycacheCount = 0

Get-ChildItem -Path . -Recurse -Filter "__pycache__" -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item -Path $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
    $pycacheCount++
}

if ($pycacheCount -gt 0) {
    Write-Host "  Removed $pycacheCount __pycache__ directories" -ForegroundColor Green
} else {
    Write-Host "  No __pycache__ directories found" -ForegroundColor Gray
}

# Step 3: Clean .pyc files
Write-Host "`n[3/4] Cleaning .pyc files..." -ForegroundColor Yellow
$pycCount = 0

Get-ChildItem -Path . -Recurse -Filter "*.pyc" -File -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item -Path $_.FullName -Force -ErrorAction SilentlyContinue
    $pycCount++
}

if ($pycCount -gt 0) {
    Write-Host "  Removed $pycCount .pyc files" -ForegroundColor Green
} else {
    Write-Host "  No .pyc files found" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== Workspace Cleaned ===" -ForegroundColor Green
Write-Host ""

# Step 4: Start Streamlit
Write-Host "[4/4] Starting Streamlit..." -ForegroundColor Yellow
Write-Host ""

streamlit run app.py

# Note: Script will end when Streamlit is stopped (Ctrl+C)

