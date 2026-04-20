"""
Oracle Lookup Management System - SQLite Testing Version
A Streamlit web application for managing lookup codes (uses SQLite for testing)
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import sys
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="Oracle Lookup Manager",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .stDataFrame { width: 100%; }
    .status-active { color: green; font-weight: bold; }
    .status-inactive { color: red; font-weight: bold; }
    .warning-box { background-color: #fff3cd; padding: 10px; border-radius: 5px; }
    .success-box { background-color: #d4edda; padding: 10px; border-radius: 5px; }
    .error-box { background-color: #f8d7da; padding: 10px; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DB_FILE = "lookups.db"

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if "connection" not in st.session_state:
    st.session_state.connection = None

if "schema_initialized" not in st.session_state:
    st.session_state.schema_initialized = False

if "db_error" not in st.session_state:
    st.session_state.db_error = None

# ============================================================================
# DATABASE CONNECTION FUNCTIONS
# ============================================================================

@st.cache_resource
def get_db_connection():
    """Create and cache database connection"""
    try:
        connection = sqlite3.connect(DB_FILE, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection
    except Exception as e:
        st.session_state.db_error = f"Database connection failed: {str(e)}"
        return None

def init_schema():
    """Initialize database schema if not exists"""
    conn = get_db_connection()
    if not conn:
        st.error(f"Cannot initialize schema: {st.session_state.db_error}")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('FND_LOOKUP_TYPES', 'FND_LOOKUP_VALUES')
        """)
        existing_tables = len(cursor.fetchall())
        
        if existing_tables >= 2:
            st.session_state.schema_initialized = True
            return True
        
        # Create FND_LOOKUP_TYPES table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS FND_LOOKUP_TYPES (
                LOOKUP_TYPE         TEXT PRIMARY KEY,
                MEANING             TEXT NOT NULL,
                DESCRIPTION         TEXT,
                CREATED_BY          TEXT NOT NULL,
                CREATION_DATE       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                LAST_UPDATED_BY     TEXT NOT NULL,
                LAST_UPDATE_DATE    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create FND_LOOKUP_VALUES table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS FND_LOOKUP_VALUES (
                LOOKUP_TYPE         TEXT NOT NULL,
                LOOKUP_CODE         TEXT NOT NULL,
                MEANING             TEXT NOT NULL,
                DESCRIPTION         TEXT,
                ENABLED_FLAG        TEXT NOT NULL DEFAULT 'Y' CHECK (ENABLED_FLAG IN ('Y', 'N')),
                START_DATE_ACTIVE   DATE,
                END_DATE_ACTIVE     DATE,
                CREATED_BY          TEXT NOT NULL,
                CREATION_DATE       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                LAST_UPDATED_BY     TEXT NOT NULL,
                LAST_UPDATE_DATE    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (LOOKUP_TYPE, LOOKUP_CODE),
                FOREIGN KEY (LOOKUP_TYPE) REFERENCES FND_LOOKUP_TYPES(LOOKUP_TYPE)
            )
        """)
        
        conn.commit()
        st.session_state.schema_initialized = True
        return True
        
    except Exception as e:
        st.error(f"Schema initialization error: {str(e)}")
        return False
    finally:
        cursor.close()

def parse_lookup_date(value):
    """Parse lookup dates from SQLite rows or uploads into a date object."""
    if value is None:
        return None

    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if isinstance(value, datetime):
        return value.date()

    text = str(value).strip()
    if not text or text.lower() == "none" or text.lower() == "nan":
        return None

    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%m/%d/%Y",
        "%m/%d/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M:%S",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    return None

def format_lookup_date(value):
    """Normalize lookup dates to ISO format for SQLite storage."""
    parsed_date = parse_lookup_date(value)
    return parsed_date.isoformat() if parsed_date else None

def is_lookup_active(enabled_flag, start_date, end_date):
    """Check if a lookup is currently active"""
    if enabled_flag != 'Y':
        return False
    
    today = datetime.now().date()
    
    if start_date:
        start = parse_lookup_date(start_date)
        if start and start > today:
            return False
    
    if end_date:
        end = parse_lookup_date(end_date)
        if end and end < today:
            return False
    
    return True

def update_lookup_value(lookup_type, lookup_code, meaning, description, enabled_flag, start_date, end_date, updated_by="SYSTEM"):
    """Update an existing lookup value"""
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"

    cursor = None
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE FND_LOOKUP_VALUES
            SET 
                MEANING = ?,
                DESCRIPTION = ?,
                ENABLED_FLAG = ?,
                START_DATE_ACTIVE = ?,
                END_DATE_ACTIVE = ?,
                LAST_UPDATED_BY = ?,
                LAST_UPDATE_DATE = CURRENT_TIMESTAMP
            WHERE LOOKUP_TYPE = ? AND LOOKUP_CODE = ?
        """, (
            meaning,
            description or None,
            enabled_flag,
            format_lookup_date(start_date),
            format_lookup_date(end_date),
            updated_by,
            lookup_type,
            lookup_code
        ))
        
        conn.commit()
        
        if cursor.rowcount == 0:
            return False, "Lookup code not found"
        
        cursor.close()
        return True, "Lookup updated successfully"
        
    except Exception as e:
        return False, f"Update error: {str(e)}"
    finally:
        if cursor:
            cursor.close()

# ============================================================================
# PAGE LAYOUT
# ============================================================================

st.title("🔍 Oracle Lookup Management System")
st.markdown("**Testing Version (SQLite Database)**")
st.markdown("---")

# Initialize schema
if not st.session_state.schema_initialized:
    with st.spinner("Initializing database..."):
        init_schema()

if st.session_state.db_error:
    st.error(f"⚠️ **Database Error**: {st.session_state.db_error}")
    st.stop()

# Sidebar for navigation
st.sidebar.title("📋 Navigation")
page = st.sidebar.radio(
    "Select a page:",
    ["🔎 Search & Discovery", "➕ Create New", "✏️ Edit & Update", "📊 View All", "⚡ Bulk Upload"]
)

# ============================================================================
# PAGE: SEARCH & DISCOVERY
# ============================================================================

if page == "🔎 Search & Discovery":
    st.header("🔎 Search & Discovery")
    st.markdown("Find lookup codes using global search")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_term = st.text_input(
            "Search by Lookup Type or Meaning",
            placeholder="Enter search term...",
            key="search_input"
        )
    
    with col2:
        search_limit = st.number_input("Limit results", min_value=10, max_value=1000, value=100)
    
    if search_term:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                
                search_pattern = f"%{search_term.upper()}%"
                
                cursor.execute("""
                    SELECT 
                        LOOKUP_TYPE,
                        LOOKUP_CODE,
                        MEANING,
                        DESCRIPTION,
                        ENABLED_FLAG,
                        START_DATE_ACTIVE,
                        END_DATE_ACTIVE
                    FROM FND_LOOKUP_VALUES
                    WHERE UPPER(LOOKUP_TYPE) LIKE ?
                       OR UPPER(MEANING) LIKE ?
                       OR UPPER(LOOKUP_CODE) LIKE ?
                    ORDER BY LOOKUP_TYPE, LOOKUP_CODE
                    LIMIT ?
                """, (search_pattern, search_pattern, search_pattern, search_limit))
                
                results = cursor.fetchall()
                cursor.close()
                
                if results:
                    st.success(f"Found {len(results)} matching records")
                    
                    df_data = []
                    for row in results:
                        is_active = is_lookup_active(row[4], row[5], row[6])
                        status = "🟢 Active" if is_active else "🔴 Inactive"
                        df_data.append({
                            "Lookup Type": row[0],
                            "Code": row[1],
                            "Meaning": row[2],
                            "Description": row[3] or "-",
                            "Status": status,
                            "Enabled": row[4],
                            "Start Date": row[5],
                            "End Date": row[6]
                        })
                    
                    df = pd.DataFrame(df_data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No records found matching your search criteria.")
                    
            except Exception as e:
                st.error(f"Search error: {str(e)}")
    else:
        st.info("👉 Enter a search term to find lookup codes")

# ============================================================================
# PAGE: CREATE NEW
# ============================================================================

elif page == "➕ Create New":
    st.header("➕ Create New Lookup Code")
    
    with st.form("create_lookup_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            lookup_type = st.text_input(
                "Lookup Type (e.g., YES_NO)",
                help="Will be converted to uppercase"
            )
            lookup_code = st.text_input(
                "Lookup Code (e.g., Y)",
                help="Will be converted to uppercase"
            )
        
        with col2:
            meaning = st.text_input(
                "Meaning (Display Name)",
                help="How this code appears to users"
            )
            enabled = st.selectbox("Enabled", ["Y", "N"], index=0)
        
        description = st.text_area(
            "Description",
            help="Optional description or notes",
            height=80
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            start_date = st.date_input(
                "Start Date Active",
                value=date.today(),
                help="Date when this code becomes active"
            )
        
        with col2:
            end_date = st.date_input(
                "End Date Active",
                value=None,
                help="Leave empty for no end date"
            )
        
        submitted = st.form_submit_button("✅ Create Lookup Code", type="primary")
        
        if submitted:
            errors = []
            
            if not lookup_type:
                errors.append("Lookup Type is required")
            if not lookup_code:
                errors.append("Lookup Code is required")
            if not meaning:
                errors.append("Meaning is required")
            if end_date and start_date and end_date < start_date:
                errors.append("End Date cannot be earlier than Start Date")
            
            if errors:
                st.error("❌ Validation errors:")
                for error in errors:
                    st.write(f"  • {error}")
            else:
                conn = get_db_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        
                        # Insert or ignore lookup type
                        cursor.execute("""
                            INSERT OR IGNORE INTO FND_LOOKUP_TYPES 
                            (LOOKUP_TYPE, MEANING, DESCRIPTION, CREATED_BY, LAST_UPDATED_BY)
                            VALUES (?, ?, ?, 'SYSTEM', 'SYSTEM')
                        """, (lookup_type.upper(), lookup_type.upper(), f"Auto-created type for {lookup_type}"))
                        
                        cursor.execute("""
                            INSERT INTO FND_LOOKUP_VALUES
                            (LOOKUP_TYPE, LOOKUP_CODE, MEANING, DESCRIPTION, ENABLED_FLAG, 
                             START_DATE_ACTIVE, END_DATE_ACTIVE, CREATED_BY, LAST_UPDATED_BY)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 'SYSTEM', 'SYSTEM')
                        """, (
                            lookup_type.upper(),
                            lookup_code.upper(),
                            meaning,
                            description or None,
                            enabled,
                            format_lookup_date(start_date),
                            format_lookup_date(end_date)
                        ))
                        
                        conn.commit()
                        st.success(f"✅ Successfully created lookup code: {lookup_code.upper()}")
                        
                    except sqlite3.IntegrityError as e:
                        if "UNIQUE constraint failed" in str(e):
                            st.error(f"❌ This lookup code already exists")
                        else:
                            st.error(f"❌ Error: {str(e)}")
                    except Exception as e:
                        st.error(f"❌ Error creating lookup code: {str(e)}")
                    finally:
                        cursor.close()

# ============================================================================
# PAGE: EDIT & UPDATE
# ============================================================================

elif page == "✏️ Edit & Update":
    st.header("✏️ Edit & Update Lookup Code")
    st.markdown("Modify existing lookup codes")
    
    # Step 1: Search for lookup to edit
    st.subheader("Step 1: Find Lookup to Edit")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_term = st.text_input(
            "Search by Lookup Type or Code",
            placeholder="Enter lookup type or code...",
            key="edit_search"
        )
    
    with col2:
        search_limit = st.number_input("Results limit", min_value=5, max_value=500, value=50, key="edit_limit")
    
    selected_lookup = None
    
    if search_term:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                search_pattern = f"%{search_term.upper()}%"
                
                cursor.execute("""
                    SELECT 
                        LOOKUP_TYPE,
                        LOOKUP_CODE,
                        MEANING,
                        ENABLED_FLAG
                    FROM FND_LOOKUP_VALUES
                    WHERE UPPER(LOOKUP_TYPE) LIKE ?
                       OR UPPER(LOOKUP_CODE) LIKE ?
                    ORDER BY LOOKUP_TYPE, LOOKUP_CODE
                    LIMIT ?
                """, (search_pattern, search_pattern, search_limit))
                
                results = cursor.fetchall()
                cursor.close()
                
                if results:
                    st.success(f"Found {len(results)} matching records")
                    
                    # Create display options
                    display_options = [
                        f"{row[0]} - {row[1]} ({row[2]})" 
                        for row in results
                    ]
                    
                    selected_display = st.selectbox(
                        "Select a lookup to edit:",
                        display_options,
                        key="edit_select"
                    )
                    
                    if selected_display:
                        # Find the selected lookup
                        selected_index = display_options.index(selected_display)
                        selected_row = results[selected_index]
                        selected_lookup = {
                            'lookup_type': selected_row[0],
                            'lookup_code': selected_row[1],
                            'meaning': selected_row[2],
                            'enabled': selected_row[3]
                        }
                else:
                    st.info("No records found matching your search.")
            except Exception as e:
                st.error(f"Search error: {str(e)}")
    else:
        st.info("👉 Enter a search term to find a lookup code to edit")
    
    # Step 2: Edit form
    if selected_lookup:
        st.markdown("---")
        st.subheader("Step 2: Edit Lookup Details")
        
        # Fetch full current details
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        LOOKUP_TYPE,
                        LOOKUP_CODE,
                        MEANING,
                        DESCRIPTION,
                        ENABLED_FLAG,
                        START_DATE_ACTIVE,
                        END_DATE_ACTIVE,
                        LAST_UPDATED_BY,
                        LAST_UPDATE_DATE
                    FROM FND_LOOKUP_VALUES
                    WHERE LOOKUP_TYPE = ? AND LOOKUP_CODE = ?
                """, (selected_lookup['lookup_type'], selected_lookup['lookup_code']))
                
                row = cursor.fetchone()
                cursor.close()
                
                if row:
                    # Display current metadata
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"📝 Last updated by: {row[7]}")
                    with col2:
                        st.info(f"🕐 Last updated: {row[8]}")
                    
                    submitted = False
                    
                    # Edit form
                    with st.form(key="edit_lookup_form", clear_on_submit=False):
                        st.write("**Current Values** (Read-only)")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.text_input("Lookup Type", value=row[0], disabled=True)
                        with col2:
                            st.text_input("Lookup Code", value=row[1], disabled=True)
                        
                        st.markdown("---")
                        st.write("**Update Values** (Editable)")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            new_meaning = st.text_input(
                                "Meaning",
                                value=row[2],
                                help="Display name for this code"
                            )
                        with col2:
                            new_enabled = st.selectbox(
                                "Enabled",
                                ["Y", "N"],
                                index=0 if row[4] == "Y" else 1
                            )
                        
                        new_description = st.text_area(
                            "Description",
                            value=row[3] if row[3] else "",
                            help="Optional description or notes",
                            height=80
                        )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            new_start_date = st.date_input(
                                "Start Date Active",
                                value=parse_lookup_date(row[5]) or date.today(),
                                help="Date when this code becomes active"
                            )
                        with col2:
                            new_end_date = st.date_input(
                                "End Date Active",
                                value=parse_lookup_date(row[6]),
                                help="Leave empty for no end date"
                            )

                        submit_col, _ = st.columns([1, 3])
                        with submit_col:
                            submitted = st.form_submit_button("💾 Save Changes", type="primary")

                    if submitted:
                        errors = []

                        if not new_meaning:
                            errors.append("Meaning is required")
                        if new_end_date and new_start_date and new_end_date < new_start_date:
                            errors.append("End Date cannot be earlier than Start Date")

                        if errors:
                            st.error("❌ Validation errors:")
                            for error in errors:
                                st.write(f"  • {error}")
                        else:
                            success, message = update_lookup_value(
                                lookup_type=row[0],
                                lookup_code=row[1],
                                meaning=new_meaning,
                                description=new_description if new_description else None,
                                enabled_flag=new_enabled,
                                start_date=new_start_date,
                                end_date=new_end_date if new_end_date else None
                            )

                            if success:
                                st.success(f"✅ {message}")
                                st.balloons()
                            else:
                                st.error(f"❌ {message}")
            except Exception as e:
                st.error(f"Error loading lookup details: {str(e)}")

# ============================================================================
# PAGE: VIEW ALL
# ============================================================================

elif page == "📊 View All":
    st.header("📊 View All Lookups")
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT LOOKUP_TYPE FROM FND_LOOKUP_TYPES ORDER BY LOOKUP_TYPE")
            lookup_types = [row[0] for row in cursor.fetchall()]
            
            if lookup_types:
                selected_type = st.selectbox("Select Lookup Type", lookup_types)
                
                if selected_type:
                    cursor.execute("""
                        SELECT 
                            LOOKUP_TYPE,
                            LOOKUP_CODE,
                            MEANING,
                            DESCRIPTION,
                            ENABLED_FLAG,
                            START_DATE_ACTIVE,
                            END_DATE_ACTIVE,
                            CREATED_BY,
                            CREATION_DATE,
                            LAST_UPDATED_BY,
                            LAST_UPDATE_DATE
                        FROM FND_LOOKUP_VALUES
                        WHERE LOOKUP_TYPE = ?
                        ORDER BY LOOKUP_CODE
                    """, (selected_type,))
                    
                    results = cursor.fetchall()
                    
                    if results:
                        df_data = []
                        for row in results:
                            is_active = is_lookup_active(row[4], row[5], row[6])
                            status = "🟢 Active" if is_active else "🔴 Inactive"
                            df_data.append({
                                "Code": row[1],
                                "Meaning": row[2],
                                "Description": row[3] or "-",
                                "Status": status,
                                "Enabled": row[4],
                                "Start Date": row[5],
                                "End Date": row[6],
                                "Last Updated": row[10]
                            })
                        
                        df = pd.DataFrame(df_data)
                        st.dataframe(df, use_container_width=True)
                        
                        col1, col2, col3 = st.columns(3)
                        active_count = sum(1 for d in df_data if "🟢" in d["Status"])
                        inactive_count = len(df_data) - active_count
                        
                        with col1:
                            st.metric("Total Codes", len(df_data))
                        with col2:
                            st.metric("Active", active_count)
                        with col3:
                            st.metric("Inactive", inactive_count)
                    else:
                        st.info("No lookup values found for this type.")
            else:
                st.info("No lookup types created yet. Go to **➕ Create New** to add one.")
            
            cursor.close()
            
        except Exception as e:
            st.error(f"Error retrieving lookups: {str(e)}")

# ============================================================================
# PAGE: BULK UPLOAD
# ============================================================================

elif page == "⚡ Bulk Upload":
    st.header("⚡ Bulk Upload Lookup Data")
    st.markdown("Upload CSV or Excel files to bulk import lookup codes")
    
    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=["csv", "xlsx"],
        help="File should contain columns: LOOKUP_TYPE, LOOKUP_CODE, MEANING, DESCRIPTION, ENABLED_FLAG, START_DATE_ACTIVE, END_DATE_ACTIVE"
    )
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.write("**Preview of uploaded data:**")
            st.dataframe(df, use_container_width=True)
            
            st.write("**Validation Checks:**")
            validation_passed = True
            
            required_columns = ["LOOKUP_TYPE", "LOOKUP_CODE", "MEANING"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                st.error(f"❌ Missing required columns: {', '.join(missing_columns)}")
                validation_passed = False
            
            if validation_passed:
                st.success(f"✅ File is valid. Contains {len(df)} records")
                
                if st.button("🚀 Upload to Database"):
                    with st.spinner("Uploading data..."):
                        conn = get_db_connection()
                        if conn:
                            try:
                                cursor = conn.cursor()
                                uploaded_count = 0
                                
                                for _, row in df.iterrows():
                                    lookup_type = str(row.get("LOOKUP_TYPE", "")).upper()
                                    lookup_code = str(row.get("LOOKUP_CODE", "")).upper()
                                    meaning = str(row.get("MEANING", ""))
                                    description = row.get("DESCRIPTION", None)
                                    enabled_flag = row.get("ENABLED_FLAG", "Y")
                                    start_date = format_lookup_date(row.get("START_DATE_ACTIVE", None))
                                    end_date = format_lookup_date(row.get("END_DATE_ACTIVE", None))
                                    
                                    # Insert type if not exists
                                    cursor.execute("""
                                        INSERT OR IGNORE INTO FND_LOOKUP_TYPES 
                                        (LOOKUP_TYPE, MEANING, DESCRIPTION, CREATED_BY, LAST_UPDATED_BY)
                                        VALUES (?, ?, ?, 'SYSTEM', 'SYSTEM')
                                    """, (lookup_type, lookup_type, f"Bulk import type"))
                                    
                                    # Insert value
                                    cursor.execute("""
                                        INSERT INTO FND_LOOKUP_VALUES
                                        (LOOKUP_TYPE, LOOKUP_CODE, MEANING, DESCRIPTION, ENABLED_FLAG, 
                                         START_DATE_ACTIVE, END_DATE_ACTIVE, CREATED_BY, LAST_UPDATED_BY)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, 'SYSTEM', 'SYSTEM')
                                    """, (lookup_type, lookup_code, meaning, description, enabled_flag, start_date, end_date))
                                    
                                    uploaded_count += 1
                                
                                conn.commit()
                                st.success(f"✅ Successfully uploaded {uploaded_count} records!")
                                
                            except Exception as e:
                                st.error(f"❌ Upload error: {str(e)}")
                                conn.rollback()
                            finally:
                                cursor.close()
        
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style="text-align: center; font-size: 12px; color: #666;">
    <p>Oracle Lookup Management System | Built with Streamlit</p>
    <p>✨ Testing Version (SQLite) | Production Version uses Oracle 21c</p>
</div>
""", unsafe_allow_html=True)
