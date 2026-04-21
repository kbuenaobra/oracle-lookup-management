# Oracle Lookup Management System

A Streamlit web application for managing Oracle EBS lookup codes with search, create, view, and bulk upload capabilities.

## Features

- 🔎 **Search & Discovery** - Global search by Lookup Type, Code, or Meaning
- ➕ **Create New** - Form-based lookup creation with validation
- 📊 **View All** - Browse and filter lookups by type
- 📈 **Reports** - Type summaries, expiring code tracking, recent changes, and CSV exports
- ⚡ **Bulk Upload** - CSV/Excel/PDF/image import with batch processing
- 🔗 **Dependencies** - Cross-reference analysis framework

## Quick Start

### Default Run Mode (Oracle)

Double-click `run_app.bat` for the normal Oracle startup path.

```bash
# Navigate to project
cd "c:\Users\user\Documents\Working Folder\AI\Oracle Lookup Project"

# Activate virtual environment
.\venv\Scripts\Activate.bat

# Install dependencies
pip install -r requirements.txt

# Run the app
python create_schema.py
streamlit run app.py
```

Visit: http://localhost:8501

### Prerequisites

- Oracle 21c Express Edition running at localhost:1521/XEPDB1
- C++ Build Tools (for cx-Oracle compilation)
- Oracle Client libraries (optional)

## Project Structure

```
Oracle Lookup Project/
├── app.py                    # Streamlit app (Oracle version)
├── create_schema.py          # Database schema initialization
├── schema.sql                # SQL schema definitions
├── requirements.txt          # Python dependencies (Oracle)
├── requirements_clean.txt    # Clean requirements file
├── run_app.bat               # One-click Oracle app launcher
├── setup.bat                 # Automated setup script
├── Lookup.md                 # Technical PRD
├── SETUP_GUIDE.md            # Detailed setup instructions
├── QUICK_START.md            # Quick reference checklist
├── README.md                 # This file
└── venv/                     # Virtual environment (created during setup)
```

## Database Schema

### FND_LOOKUP_TYPES
- `LOOKUP_TYPE` (PK): Unique lookup type identifier
- `MEANING`: Display name
- `DESCRIPTION`: Documentation
- Audit columns: CREATED_BY, CREATION_DATE, LAST_UPDATED_BY, LAST_UPDATE_DATE

### FND_LOOKUP_VALUES
- `LOOKUP_TYPE` (PK, FK): Reference to FND_LOOKUP_TYPES
- `LOOKUP_CODE` (PK): Unique code within lookup type
- `MEANING`: Display value
- `ENABLED_FLAG`: 'Y' or 'N'
- `START_DATE_ACTIVE`, `END_DATE_ACTIVE`: Effective date range
- Audit columns: CREATED_BY, CREATION_DATE, LAST_UPDATED_BY, LAST_UPDATE_DATE

## Technology Stack

- **Frontend**: Streamlit 1.31.1
- **Database**: Oracle 21c
- **Data Processing**: Pandas 1.3.5
- **Oracle Driver**: python-oracledb
- **OCR**: RapidOCR with OpenCV and Pillow
- **Python**: 3.8+

## Installation Issues & Fixes

### Python Not Found
Install Python from https://www.python.org/downloads/ and add to PATH.

### Virtual Environment Issues
```bash
# Delete and recreate
rmdir /s /q venv
python -m venv venv
.\venv\Scripts\Activate.bat
```

### Streamlit Not Found
Ensure `(venv)` appears in your terminal prompt before running commands.

### Oracle Connection Issues
- Verify Oracle is running
- Check connection credentials in `create_schema.py` and `app.py`
- Test with SQL Developer extension first

### Pandas Build Errors
Upgrade pip and install wheels:
```bash
python -m pip install --upgrade pip
pip install --only-binary :all: pandas
```

## Development

### Running Tests
```bash
# Test database connection
python create_schema.py

# Test Oracle version
streamlit run app.py
```

### Sample Data

Create `sample_data.csv`:
```csv
LOOKUP_TYPE,LOOKUP_CODE,MEANING,DESCRIPTION,ENABLED_FLAG,START_DATE_ACTIVE,END_DATE_ACTIVE
YES_NO,Y,Yes,Affirmative,Y,2026-04-18,
YES_NO,N,No,Negative,Y,2026-04-18,
STATUS,ACTIVE,Active,Record is active,Y,2026-04-18,
STATUS,INACTIVE,Inactive,Record is inactive,Y,2026-04-18,
```

Then upload via the **⚡ Bulk Upload** tab. PDF files that contain the same tabular columns can also be imported directly.

### Image Uploads

The bulk upload page also accepts `PNG`, `JPG`, and `JPEG` files.

- Best results come from screenshots or pictures of clear tables with visible rows and columns.
- The app runs OCR on the image, converts the result into a table, and opens an editable preview before anything is written to Oracle.
- Review the extracted values carefully. OCR can miss short codes or flags in low-quality images, but the review grid lets you correct them before confirming the upload.

## Deployment

### Local Testing
```bash
streamlit run app.py
```

### Cloud Deployment (Streamlit Cloud)
1. Push to GitHub
2. Create account at https://streamlit.io/cloud
3. Deploy from repository
4. Configure secrets for database credentials

## Documentation

- [Lookup.md](Lookup.md) - Technical Product Requirements Document
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Detailed setup and troubleshooting
- [QUICK_START.md](QUICK_START.md) - Quick reference checklist

## Support & Resources

- **Streamlit Docs**: https://docs.streamlit.io
- **python-oracledb Docs**: https://python-oracledb.readthedocs.io
- **Oracle 21c Express**: https://www.oracle.com/database/technologies/xe-downloads.html

## License

MIT License - Feel free to use and modify

## Author

Created: 2026-04-18

---

**Status**: ✅ Oracle version is the default application entrypoint

**Ready to Deploy**: Yes - Oracle is the primary database target
