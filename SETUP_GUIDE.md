# Oracle Lookup Management System - Setup Guide

## Prerequisites

Before starting, ensure you have:
- ✅ Oracle 21c Express Edition running and accessible at `localhost:1521/XEPDB1`
- ✅ SQL Developer extension with XE_Local connection configured
- ✅ Python 3.8+ installed and added to PATH
- ✅ Administrator access to install packages

---

## ⚠️ Important: Python Installation

If you don't have Python installed, install it now:

### Option 1: Official Python Installer (Recommended)
1. Go to https://www.python.org/downloads/
2. Download Python 3.11+ (64-bit)
3. **IMPORTANT**: During installation, check **"Add Python to PATH"** ☑️
4. Click "Install Now"
5. After installation, **restart your terminal/PowerShell**

### Option 2: Chocolatey (if installed)
```powershell
choco install python
```

### Option 3: Windows Package Manager
```powershell
winget install Python.Python.3.11
# After installation, restart your terminal
```

### Verify Python Installation
```powershell
python --version
# Should output: Python 3.11.x or higher
```

---

## Quick Start (Recommended)

### Method 1: Use the Batch Setup Script (Easiest)

Double-click `setup.bat` in your project folder. This script will:
1. ✅ Create a virtual environment
2. ✅ Install all dependencies
3. ✅ Initialize the database schema
4. ✅ Launch the Streamlit application

---

## Manual Setup (Step-by-Step)

If `setup.bat` doesn't work, follow these steps:

### Step 1: Navigate to Project Folder
```powershell
cd "c:\Users\user\Documents\Working Folder\AI\Oracle Lookup Project"
```

### Step 2: Create Virtual Environment
```powershell
python -m venv venv
```

### Step 3: Activate Virtual Environment

**On Windows PowerShell:**
```powershell
.\venv\Scripts\Activate.ps1
```

**If you get an execution policy error:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Then try again:
.\venv\Scripts\Activate.ps1
```

**On Windows Command Prompt (cmd.exe):**
```cmd
venv\Scripts\activate.bat
```

### Step 4: Install Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

Expected output:
```
Successfully installed streamlit-1.31.1 oracledb-1.4.1 pandas-2.1.4
```

### Step 5: Initialize Database Schema
```powershell
python create_schema.py
```

You should see:
```
✓ Connected to Oracle Database successfully
  Database: localhost:1521/XEPDB1
  User: SYSTEM

Dropping existing tables...
Creating FND_LOOKUP_TYPES table...
  ✓ Created FND_LOOKUP_TYPES
Creating FND_LOOKUP_VALUES table...
  ✓ Created FND_LOOKUP_VALUES

SCHEMA CREATION COMPLETED SUCCESSFULLY
```

### Step 6: Launch Streamlit Application
```powershell
streamlit run app.py
```

You should see:
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://<YOUR_IP>:8501
```

The app will open automatically in your default browser. If not, manually visit `http://localhost:8501`.

---

## Testing the Application

Once the Streamlit app is running:

### Test 1: Create a Lookup Type
1. Go to **➕ Create New** tab
2. Enter:
   - Lookup Type: `TEST_TYPE`
   - Lookup Code: `CODE1`
   - Meaning: `Test Code 1`
3. Click **✅ Create Lookup Code**
4. You should see: `✅ Successfully created lookup code: CODE1`

### Test 2: Search
1. Go to **🔎 Search & Discovery** tab
2. Enter: `TEST_TYPE` in the search box
3. You should see your newly created code listed

### Test 3: View All
1. Go to **📊 View All** tab
2. Select **TEST_TYPE** from the dropdown
3. You should see `CODE1` with a green status badge (🟢 Active)

### Test 4: Bulk Upload
1. Create a CSV file named `test_data.csv`:
   ```csv
   LOOKUP_TYPE,LOOKUP_CODE,MEANING,DESCRIPTION,ENABLED_FLAG,START_DATE_ACTIVE,END_DATE_ACTIVE
   STATUS,ACTIVE,Active,Record is active,Y,2026-04-17,
   STATUS,INACTIVE,Inactive,Record is inactive,N,2026-04-17,
   ```

2. Go to **⚡ Bulk Upload** tab
3. Upload the CSV file
4. Click **🚀 Upload to Database**
5. You should see: `✅ Successfully uploaded 2 records!`

---

## Troubleshooting

### Error: "Python is not installed"
**Solution**: Install Python from https://www.python.org/downloads/ and add it to PATH. Restart your terminal.

### Error: "No module named 'streamlit'"
**Solution**: 
```powershell
pip install -r requirements.txt
```

### Error: "ORA-01017: invalid username/password"
**Solution**: Check your database credentials in `create_schema.py`:
```python
DB_USER = "SYSTEM"
DB_PASSWORD = "xe"  # Update if your password is different
```

### Error: "Cannot connect to localhost:1521/XEPDB1"
**Solution**: 
1. Verify Oracle is running: `lsnrctl status` or check Oracle Services
2. Verify XE_Local connection in SQL Developer extension
3. Update DB_HOST, DB_PORT, DB_SERVICE in `create_schema.py` if needed

### Error: "ExecutionPolicy" in PowerShell
**Solution**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Streamlit App Crashes
**Solution**:
1. Check terminal for error messages
2. Restart the app: Press Ctrl+C and run `streamlit run app.py` again
3. Check database connection: Run `python create_schema.py` to verify

---

## File Structure

```
Oracle Lookup Project/
├── app.py                   # Streamlit web application
├── create_schema.py         # Database schema initialization script
├── schema.sql               # SQL schema definitions
├── requirements.txt         # Python dependencies
├── setup.bat                # Automated setup script
├── Lookup.md                # Technical PRD
└── venv/                    # Virtual environment (created after setup)
```

---

## Database Schema Details

### Tables Created

**FND_LOOKUP_TYPES**
- `LOOKUP_TYPE` (PK): Unique lookup type identifier
- `MEANING`: Display name
- `DESCRIPTION`: Documentation
- Audit columns: CREATED_BY, CREATION_DATE, LAST_UPDATED_BY, LAST_UPDATE_DATE

**FND_LOOKUP_VALUES**
- `LOOKUP_TYPE` (PK, FK): Reference to FND_LOOKUP_TYPES
- `LOOKUP_CODE` (PK): Unique code within lookup type
- `MEANING`: Display value
- `ENABLED_FLAG`: 'Y' or 'N'
- `START_DATE_ACTIVE`, `END_DATE_ACTIVE`: Effective dates
- Audit columns: CREATED_BY, CREATION_DATE, LAST_UPDATED_BY, LAST_UPDATE_DATE

---

## Application Features

### 🔎 Search & Discovery
- Global search by Lookup Type, Meaning, or Code
- Real-time status badges (🟢 Active / 🔴 Inactive)
- Customizable result limit

### ➕ Create New
- Form to add individual lookup codes
- Automatic validation of dates
- Auto-conversion to uppercase for Type and Code

### 📊 View All
- Browse all codes by lookup type
- Status summary (Total, Active, Inactive)
- Date filtering support

### ⚡ Bulk Upload
- CSV/Excel import support
- Batch processing for high-volume data
- Pre-upload validation

### 🔗 Dependencies
- Framework for cross-reference analysis
- Impact warning system (extensible)

---

## Database Connection

The application uses `oracledb` in Thin mode (no Oracle Client needed).

Connection settings in `app.py`:
```python
DB_HOST = "localhost"
DB_PORT = 1521
DB_SERVICE = "XEPDB1"
DB_USER = "SYSTEM"
DB_PASSWORD = "xe"  # Update if needed
```

---

## Next Steps

1. ✅ Install Python and restart terminal
2. ✅ Run `setup.bat` or follow manual setup steps
3. ✅ Access the app at `http://localhost:8501`
4. ✅ Test all features with sample data
5. ✅ Configure for production use

---

## Support & Documentation

- **Streamlit Docs**: https://docs.streamlit.io
- **oracledb Python Driver**: https://python-oracledb.readthedocs.io
- **Oracle 21c Express**: https://www.oracle.com/database/technologies/xe-downloads.html

---

**Setup Guide Version**: 1.0  
**Date**: 2026-04-17  
**Status**: Ready for Deployment
