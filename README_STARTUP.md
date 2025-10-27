# App Startup Guide

## 🚀 Quick Start (With Auto-Cleanup)

Instead of running `streamlit run app.py` directly, use these scripts that **automatically clean `__pycache__`** before starting:

### **Windows PowerShell** (Recommended):
```powershell
.\start_app.ps1
```

### **Windows Command Prompt**:
```cmd
start_app.bat
```

---

## ✨ What These Scripts Do:

1. **Clean `__pycache__` directories** - Removes stale Python bytecode
2. **Clean `.pyc` files** - Removes compiled Python files
3. **Start Streamlit** - Runs `streamlit run app.py`

This ensures you always start with fresh imports!

---

## 🔧 If Scripts Don't Run:

### **PowerShell Execution Policy Issue?**

If you get an error like "cannot be loaded because running scripts is disabled":

```powershell
# Allow scripts for current user (safe)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then run the script
.\start_app.ps1
```

### **Still Issues?**

Just run the commands manually:
```powershell
# Clean cache
Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force

# Start app
streamlit run app.py
```

---

## 📝 Manual Cleanup Commands:

### **PowerShell:**
```powershell
# Remove __pycache__ directories
Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force

# Remove .pyc files
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force

# Start Streamlit
streamlit run app.py
```

### **Command Prompt:**
```cmd
REM Remove __pycache__
for /d /r . %d in (__pycache__) do @if exist "%d" rd /s /q "%d"

REM Remove .pyc files
del /s /q *.pyc

REM Start Streamlit
streamlit run app.py
```

### **Linux/Mac:**
```bash
# Remove __pycache__ and .pyc files
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Start Streamlit
streamlit run app.py
```

---

## 🎯 Why Clean __pycache__?

- **Stale imports** - Old bytecode can cause import errors
- **Code changes** - Ensures latest code is loaded
- **Fresh start** - Eliminates caching issues
- **Debugging** - Removes a common source of bugs

---

## 💡 Best Practice:

**Always use the startup scripts** instead of running `streamlit run app.py` directly:

```powershell
# ✅ Good (with cleanup)
.\start_app.ps1

# ❌ Not recommended (no cleanup)
streamlit run app.py
```

---

## 🔄 After Code Changes:

Whenever you:
- Update Python files
- Pull new code from git
- Switch branches
- Experience weird import errors

**Always restart using the cleanup script!**

```powershell
# Stop Streamlit (Ctrl+C)
# Then restart with cleanup:
.\start_app.ps1
```

---

## ✅ Your Clean Startup Workflow:

```powershell
# 1. Stop any running Streamlit (Ctrl+C)

# 2. Start with cleanup
.\start_app.ps1

# 3. App opens in browser
# 4. Fresh imports, no cache issues!
```

---

**Happy coding with a clean workspace!** 🎉

