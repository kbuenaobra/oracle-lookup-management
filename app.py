"""
Oracle Lookup Management System
A Streamlit web application for managing Oracle EBS lookup codes
"""

import streamlit as st
import pandas as pd
import oracledb
from datetime import datetime, date
import sys
from io import StringIO
import traceback

# Page configuration
st.set_page_config(
    page_title="Oracle Lookup Manager",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
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

DB_HOST = "localhost"
DB_PORT = 1521
DB_SERVICE = "XEPDB1"
DB_USER = "SYSTEM"
DB_PASSWORD = "ADmin1234"  # Update if needed

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
        connection = oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            service_name=DB_SERVICE
        )
        return connection
    except oracledb.DatabaseError as e:
        st.session_state.db_error = f"Database connection failed: {str(e)}"
        return None
    except Exception as e:
        st.session_state.db_error = f"Unexpected error: {str(e)}"
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
            SELECT COUNT(*) FROM user_tables 
            WHERE table_name IN ('FND_LOOKUP_TYPES', 'FND_LOOKUP_VALUES')
        """)
        existing_tables = cursor.fetchone()[0]
        
        if existing_tables >= 2:
            st.session_state.schema_initialized = True
            return True
        
        # Create FND_LOOKUP_TYPES table
        cursor.execute("""
            CREATE TABLE FND_LOOKUP_TYPES (
                LOOKUP_TYPE         VARCHAR2(30)    NOT NULL PRIMARY KEY,
                MEANING             VARCHAR2(80)    NOT NULL,
                DESCRIPTION         VARCHAR2(240),
                CREATED_BY          VARCHAR2(50)    NOT NULL,
                CREATION_DATE       DATE            NOT NULL DEFAULT SYSDATE,
                LAST_UPDATED_BY     VARCHAR2(50)    NOT NULL,
                LAST_UPDATE_DATE    DATE            NOT NULL DEFAULT SYSDATE
            )
        """)
        
        cursor.execute("CREATE INDEX IDX_LOOKUP_TYPES_MEANING ON FND_LOOKUP_TYPES(MEANING)")
        
        # Create FND_LOOKUP_VALUES table
        cursor.execute("""
            CREATE TABLE FND_LOOKUP_VALUES (
                LOOKUP_TYPE         VARCHAR2(30)    NOT NULL,
                LOOKUP_CODE         VARCHAR2(30)    NOT NULL,
                MEANING             VARCHAR2(80)    NOT NULL,
                DESCRIPTION         VARCHAR2(240),
                ENABLED_FLAG        VARCHAR2(1)     NOT NULL DEFAULT 'Y' CHECK (ENABLED_FLAG IN ('Y', 'N')),
                START_DATE_ACTIVE   DATE,
                END_DATE_ACTIVE     DATE,
                CREATED_BY          VARCHAR2(50)    NOT NULL,
                CREATION_DATE       DATE            NOT NULL DEFAULT SYSDATE,
                LAST_UPDATED_BY     VARCHAR2(50)    NOT NULL,
                LAST_UPDATE_DATE    DATE            NOT NULL DEFAULT SYSDATE,
                CONSTRAINT PK_LOOKUP_VALUES PRIMARY KEY (LOOKUP_TYPE, LOOKUP_CODE),
                CONSTRAINT FK_LOOKUP_VALUES_TYPE FOREIGN KEY (LOOKUP_TYPE) REFERENCES FND_LOOKUP_TYPES(LOOKUP_TYPE) ON DELETE CASCADE,
                CONSTRAINT CK_END_DATE_ACTIVE CHECK (END_DATE_ACTIVE IS NULL OR START_DATE_ACTIVE IS NULL OR END_DATE_ACTIVE >= START_DATE_ACTIVE)
            )
        """)
        
        cursor.execute("CREATE INDEX IDX_LOOKUP_VALUES_TYPE ON FND_LOOKUP_VALUES(LOOKUP_TYPE)")
        cursor.execute("CREATE INDEX IDX_LOOKUP_VALUES_CODE ON FND_LOOKUP_VALUES(LOOKUP_CODE)")
        cursor.execute("CREATE INDEX IDX_LOOKUP_VALUES_MEANING ON FND_LOOKUP_VALUES(MEANING)")
        cursor.execute("CREATE INDEX IDX_LOOKUP_VALUES_ENABLED ON FND_LOOKUP_VALUES(ENABLED_FLAG)")
        
        conn.commit()
        st.session_state.schema_initialized = True
        return True
        
    except Exception as e:
        st.error(f"Schema initialization error: {str(e)}")
        return False
    finally:
        cursor.close()

def is_lookup_active(enabled_flag, start_date, end_date):
    """Check if a lookup is currently active"""
    if enabled_flag != 'Y':
        return False
    
    today = datetime.now().date()
    
    if start_date and start_date > today:
        return False
    
    if end_date and end_date < today:
        return False
    
    return True

def get_status_badge(enabled_flag, start_date, end_date):
    """Return status badge HTML"""
    if is_lookup_active(enabled_flag, start_date, end_date):
        return '<span style="background-color: #90EE90; padding: 5px 10px; border-radius: 3px; color: white;">🟢 Active</span>'
    else:
        return '<span style="background-color: #FFB6C6; padding: 5px 10px; border-radius: 3px; color: white;">🔴 Inactive</span>'

# ============================================================================
# PAGE LAYOUT
# ============================================================================

st.title("🔍 Oracle Lookup Management System")
st.markdown("---")

# Initialize connection and schema
if not st.session_state.schema_initialized:
    with st.spinner("Initializing database schema..."):
        init_schema()

if st.session_state.db_error:
    st.error(f"⚠️ **Database Connection Error**: {st.session_state.db_error}")
    st.stop()

# Sidebar for navigation
st.sidebar.title("📋 Navigation")
page = st.sidebar.radio(
    "Select a page:",
    ["🔎 Search & Discovery", "➕ Create New", "📊 View All", "✏️ Edit", "⚡ Bulk Upload", "🔗 Dependencies"]
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
                        lv.LOOKUP_TYPE,
                        lv.LOOKUP_CODE,
                        lv.MEANING,
                        lv.DESCRIPTION,
                        lv.ENABLED_FLAG,
                        lv.START_DATE_ACTIVE,
                        lv.END_DATE_ACTIVE
                    FROM FND_LOOKUP_VALUES lv
                    WHERE UPPER(lv.LOOKUP_TYPE) LIKE :search
                       OR UPPER(lv.MEANING) LIKE :search
                       OR UPPER(lv.LOOKUP_CODE) LIKE :search
                    ORDER BY lv.LOOKUP_TYPE, lv.LOOKUP_CODE
                    FETCH FIRST :limit ROWS ONLY
                """, {"search": search_pattern, "limit": search_limit})
                
                results = cursor.fetchall()
                cursor.close()
                
                if results:
                    st.success(f"Found {len(results)} matching records")
                    
                    # Create DataFrame
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
            # Validation
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
                        
                        # First, ensure lookup type exists
                        cursor.execute("""
                            INSERT INTO FND_LOOKUP_TYPES 
                            (LOOKUP_TYPE, MEANING, DESCRIPTION, CREATED_BY, LAST_UPDATED_BY)
                            VALUES (:lt, :lt, :desc, 'SYSTEM', 'SYSTEM')
                        """, {
                            "lt": lookup_type.upper(),
                            "desc": f"Auto-created type for {lookup_type}"
                        })
                        conn.commit()
                        
                    except cx_Oracle.IntegrityError:
                        pass  # Type already exists
                        
                    try:
                        cursor = conn.cursor()
                        
                        cursor.execute("""
                            INSERT INTO FND_LOOKUP_VALUES
                            (LOOKUP_TYPE, LOOKUP_CODE, MEANING, DESCRIPTION, ENABLED_FLAG, 
                             START_DATE_ACTIVE, END_DATE_ACTIVE, CREATED_BY, LAST_UPDATED_BY)
                            VALUES (:lt, :lc, :meaning, :desc, :enabled, 
                                    :start_date, :end_date, 'SYSTEM', 'SYSTEM')
                        """, {
                            "lt": lookup_type.upper(),
                            "lc": lookup_code.upper(),
                            "meaning": meaning,
                            "desc": description or None,
                            "enabled": enabled,
                            "start_date": start_date,
                            "end_date": end_date if end_date else None
                        })
                        
                        conn.commit()
                        st.success(f"✅ Successfully created lookup code: {lookup_code.upper()}")
                        
                    except cx_Oracle.IntegrityError as e:
                        st.error(f"❌ Integrity Error: This lookup code may already exist")
                    except Exception as e:
                        st.error(f"❌ Error creating lookup code: {str(e)}")
                    finally:
                        cursor.close()

# ============================================================================
# PAGE: VIEW ALL
# ============================================================================

elif page == "📊 View All":
    st.header("📊 View All Lookups")
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Get all lookup types
            cursor.execute("SELECT LOOKUP_TYPE FROM FND_LOOKUP_TYPES ORDER BY LOOKUP_TYPE")
            lookup_types = [row[0] for row in cursor.fetchall()]
            
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
                    WHERE LOOKUP_TYPE = :type
                    ORDER BY LOOKUP_CODE
                """, {"type": selected_type})
                
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
                    
                    # Summary statistics
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
            
            cursor.close()
            
        except Exception as e:
            st.error(f"Error retrieving lookups: {str(e)}")

# ============================================================================
# PAGE: EDIT
# ============================================================================

elif page == "✏️ Edit":
    st.header("✏️ Edit Lookup Values")
    st.markdown("Modify existing lookup codes and their properties")
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Get all lookup types and codes
            cursor.execute("""
                SELECT LOOKUP_TYPE FROM FND_LOOKUP_TYPES ORDER BY LOOKUP_TYPE
            """)
            lookup_types = [row[0] for row in cursor.fetchall()]
            
            col1, col2 = st.columns(2)
            
            with col1:
                selected_type = st.selectbox("Select Lookup Type", lookup_types, key="edit_type")
            
            if selected_type:
                cursor.execute("""
                    SELECT LOOKUP_CODE, MEANING FROM FND_LOOKUP_VALUES
                    WHERE LOOKUP_TYPE = :type
                    ORDER BY LOOKUP_CODE
                """, {"type": selected_type})
                
                codes = cursor.fetchall()
                code_options = [f"{code[0]} - {code[1]}" for code in codes]
                
                with col2:
                    selected_code_display = st.selectbox("Select Lookup Code", code_options, key="edit_code")
                
                if selected_code_display:
                    selected_code = selected_code_display.split(" - ")[0]
                    
                    # Fetch current values
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
                        WHERE LOOKUP_TYPE = :type AND LOOKUP_CODE = :code
                    """, {"type": selected_type, "code": selected_code})
                    
                    row = cursor.fetchone()
                    
                    if row:
                        st.divider()
                        st.subheader("Current Details")
                        
                        # Display current values
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.text(f"**Lookup Type**: {row[0]}")
                        with col2:
                            st.text(f"**Lookup Code**: {row[1]}")
                        with col3:
                            st.text(f"**Status**: {'🟢 Active' if row[4] == 'Y' else '🔴 Inactive'}")
                        
                        st.divider()
                        st.subheader("Edit Details")
                        
                        with st.form("edit_lookup_form"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                new_meaning = st.text_input(
                                    "Meaning",
                                    value=row[2] or "",
                                    help="Display name for this lookup code"
                                )
                            
                            with col2:
                                new_enabled = st.selectbox(
                                    "Enabled Flag",
                                    ["Y", "N"],
                                    index=0 if row[4] == "Y" else 1,
                                    help="Y = Active, N = Inactive"
                                )
                            
                            new_description = st.text_area(
                                "Description",
                                value=row[3] or "",
                                height=100,
                                help="Additional details about this lookup code"
                            )
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                new_start_date = st.date_input(
                                    "Start Date Active",
                                    value=row[5] if row[5] else None,
                                    help="Date when this code becomes active"
                                )
                            
                            with col2:
                                new_end_date = st.date_input(
                                    "End Date Active",
                                    value=row[6] if row[6] else None,
                                    help="Date when this code expires"
                                )
                            
                            st.divider()
                            
                            col1, col2, col3 = st.columns([2, 1, 1])
                            
                            with col1:
                                submit = st.form_submit_button("💾 Save Changes", use_container_width=True)
                            
                            with col2:
                                st.form_submit_button("❌ Cancel", use_container_width=True)
                            
                            if submit:
                                try:
                                    # Validate dates
                                    if new_end_date and new_start_date and new_end_date < new_start_date:
                                        st.error("❌ End Date cannot be before Start Date")
                                    else:
                                        update_cursor = conn.cursor()
                                        
                                        update_cursor.execute("""
                                            UPDATE FND_LOOKUP_VALUES
                                            SET MEANING = :1,
                                                DESCRIPTION = :2,
                                                ENABLED_FLAG = :3,
                                                START_DATE_ACTIVE = :4,
                                                END_DATE_ACTIVE = :5,
                                                LAST_UPDATED_BY = :6,
                                                LAST_UPDATE_DATE = :7
                                            WHERE LOOKUP_TYPE = :8 AND LOOKUP_CODE = :9
                                        """, [
                                            new_meaning,
                                            new_description if new_description else None,
                                            new_enabled,
                                            new_start_date,
                                            new_end_date if new_end_date else None,
                                            "SYSTEM",
                                            datetime.now(),
                                            selected_type,
                                            selected_code
                                        ])
                                        
                                        conn.commit()
                                        update_cursor.close()
                                        
                                        st.success(f"✅ Successfully updated {selected_code}")
                                        st.balloons()
                                        
                                except Exception as e:
                                    st.error(f"❌ Error updating record: {str(e)}")
            
            cursor.close()
            
        except Exception as e:
            st.error(f"Error loading edit page: {str(e)}")

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
            
            # Validation checks
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
                                
                                # Convert DataFrame to list of tuples
                                data_to_insert = []
                                for _, row in df.iterrows():
                                    data_to_insert.append((
                                        str(row.get("LOOKUP_TYPE", "")).upper(),
                                        str(row.get("LOOKUP_CODE", "")).upper(),
                                        str(row.get("MEANING", "")),
                                        row.get("DESCRIPTION", None),
                                        row.get("ENABLED_FLAG", "Y"),
                                        pd.to_datetime(row.get("START_DATE_ACTIVE")).date() if pd.notna(row.get("START_DATE_ACTIVE")) else None,
                                        pd.to_datetime(row.get("END_DATE_ACTIVE")).date() if pd.notna(row.get("END_DATE_ACTIVE")) else None
                                    ))
                                
                                # Batch insert
                                cursor.executemany("""
                                    INSERT INTO FND_LOOKUP_VALUES
                                    (LOOKUP_TYPE, LOOKUP_CODE, MEANING, DESCRIPTION, ENABLED_FLAG, 
                                     START_DATE_ACTIVE, END_DATE_ACTIVE, CREATED_BY, LAST_UPDATED_BY)
                                    VALUES (:1, :2, :3, :4, :5, :6, :7, 'SYSTEM', 'SYSTEM')
                                """, data_to_insert)
                                
                                conn.commit()
                                st.success(f"✅ Successfully uploaded {len(data_to_insert)} records!")
                                
                            except Exception as e:
                                st.error(f"❌ Upload error: {str(e)}")
                                conn.rollback()
                            finally:
                                cursor.close()
        
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

# ============================================================================
# PAGE: DEPENDENCIES
# ============================================================================

elif page == "🔗 Dependencies":
    st.header("🔗 Dependency & Impact Analysis")
    st.markdown("Analyze which modules depend on lookup codes")
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            
            # Get all lookup types
            cursor.execute("SELECT LOOKUP_TYPE FROM FND_LOOKUP_TYPES ORDER BY LOOKUP_TYPE")
            lookup_types = [row[0] for row in cursor.fetchall()]
            
            selected_type = st.selectbox("Select Lookup Type to analyze", lookup_types)
            
            st.info("""
            **Note:** This view is designed to display dependent objects such as:
            - Concurrent Programs using this lookup
            - Value Sets referencing this lookup
            - Reports that depend on this lookup
            
            In a production environment, this would query from the appropriate EBS tables
            (FND_CONCURRENT_PROGRAMS, FND_FLEX_VALUE_SETS, etc.)
            """)
            
            st.write(f"Selected Lookup Type: **{selected_type}**")
            
            # Placeholder for dependencies (would connect to actual EBS data in production)
            st.dataframe(
                pd.DataFrame({
                    "Dependent Object": ["EXAMPLE_PROGRAM_1", "EXAMPLE_VALUESET_1"],
                    "Type": ["Concurrent Program", "Value Set"],
                    "Owner": ["FND", "CUSTOM"],
                    "Status": ["Active", "Active"],
                    "Last Used": ["2026-04-15", "2026-04-10"]
                }),
                use_container_width=True
            )
            
        except Exception as e:
            st.error(f"Error retrieving dependencies: {str(e)}")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style="text-align: center; font-size: 12px; color: #666;">
    <p>Oracle Lookup Management System | Built with Streamlit</p>
    <p>Database: Oracle 21c Express Edition (XE_Local)</p>
</div>
""", unsafe_allow_html=True)
