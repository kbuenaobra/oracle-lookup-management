"""
Oracle Lookup Management System
A Streamlit web application for managing Oracle EBS lookup codes
"""

import streamlit as st
import pandas as pd
import oracledb
import pdfplumber
import cv2
import numpy as np
from datetime import datetime, date
import re
import sys
from io import StringIO
import traceback
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

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

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")

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

    def normalize_date(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        return value
    
    today = datetime.now().date()
    start_date = normalize_date(start_date)
    end_date = normalize_date(end_date)
    
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

def normalize_upload_column_name(column_name):
    """Normalize upload column names across CSV, Excel, and PDF sources."""
    normalized = re.sub(r"[^A-Z0-9]+", "_", str(column_name).strip().upper())
    return normalized.strip("_") or "COLUMN"


def make_unique_columns(column_names):
    """Keep repeated headers unique while preserving the original order."""
    seen_counts = {}
    unique_columns = []

    for column_name in column_names:
        normalized_name = normalize_upload_column_name(column_name)
        seen_counts[normalized_name] = seen_counts.get(normalized_name, 0) + 1

        if seen_counts[normalized_name] == 1:
            unique_columns.append(normalized_name)
        else:
            unique_columns.append(f"{normalized_name}_{seen_counts[normalized_name]}")

    return unique_columns


def normalize_upload_dataframe(df):
    """Apply a consistent column naming scheme to uploaded data."""
    normalized_df = df.copy()
    normalized_df.columns = make_unique_columns(normalized_df.columns)
    return normalized_df


@st.cache_resource
def get_ocr_engine():
    """Create and cache the OCR engine for image uploads."""
    return RapidOCR()


def image_file_to_array(uploaded_file):
    """Load an uploaded image file into an RGB numpy array."""
    uploaded_file.seek(0)
    image = Image.open(uploaded_file).convert("RGB")
    uploaded_file.seek(0)
    return np.array(image)


def run_ocr_on_image(image_array):
    """Run OCR on an image array and return extracted text items."""
    result, _ = get_ocr_engine()(image_array)

    if not result:
        return []

    extracted_items = []
    for item in result:
        points, text, confidence = item
        extracted_items.append({
            "points": points,
            "text": str(text).strip(),
            "confidence": float(confidence)
        })

    return extracted_items


def extract_text_from_crop(image_array):
    """Extract text from a cropped image and summarize confidence."""
    items = run_ocr_on_image(image_array)
    texts = [item["text"] for item in items if item["text"]]
    confidences = [item["confidence"] for item in items if item["text"]]

    if not texts:
        return "", None

    average_confidence = sum(confidences) / len(confidences) if confidences else None
    return " ".join(texts).strip(), average_confidence


def find_line_positions(line_mask, axis, minimum_ratio):
    """Find grouped horizontal or vertical line positions from a binary mask."""
    comparison_length = line_mask.shape[1] if axis == 1 else line_mask.shape[0]
    projection = np.sum(line_mask > 0, axis=axis)
    indices = np.where(projection >= comparison_length * minimum_ratio)[0]

    if len(indices) == 0:
        return []

    grouped_positions = []
    current_group = [indices[0]]

    for index in indices[1:]:
        if index - current_group[-1] <= 2:
            current_group.append(index)
        else:
            grouped_positions.append(int(sum(current_group) / len(current_group)))
            current_group = [index]

    grouped_positions.append(int(sum(current_group) / len(current_group)))
    return grouped_positions


def detect_table_cells(image_array):
    """Detect grid-like table cells in an uploaded image."""
    gray_image = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
    inverted = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    image_height, image_width = gray_image.shape
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(25, image_width // 18), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(25, image_height // 18)))

    horizontal_lines = cv2.morphologyEx(inverted, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    vertical_lines = cv2.morphologyEx(inverted, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    horizontal_positions = find_line_positions(horizontal_lines, axis=1, minimum_ratio=0.35)
    vertical_positions = find_line_positions(vertical_lines, axis=0, minimum_ratio=0.35)

    if len(horizontal_positions) < 2 or len(vertical_positions) < 2:
        return []

    rows = []
    for top_position, bottom_position in zip(horizontal_positions[:-1], horizontal_positions[1:]):
        current_row = []
        for left_position, right_position in zip(vertical_positions[:-1], vertical_positions[1:]):
            width = right_position - left_position
            height = bottom_position - top_position
            if width < 35 or height < 20:
                continue
            current_row.append((left_position, top_position, width, height))

        if current_row:
            rows.append(current_row)

    return rows


def extract_grid_table_from_image(image_array):
    """Extract table data from a grid-based screenshot or picture."""
    rows = detect_table_cells(image_array)
    if len(rows) < 2:
        return None

    ocr_confidences = []
    table_rows = []

    for row in rows:
        extracted_row = []
        for x_position, y_position, width, height in row:
            padding = 4
            cropped_image = image_array[
                max(0, y_position + padding):min(image_array.shape[0], y_position + height - padding),
                max(0, x_position + padding):min(image_array.shape[1], x_position + width - padding)
            ]
            extracted_text, confidence = extract_text_from_crop(cropped_image)
            extracted_row.append(extracted_text)
            if confidence is not None:
                ocr_confidences.append(confidence)

        if any(cell.strip() for cell in extracted_row if isinstance(cell, str)):
            table_rows.append(extracted_row)

    if len(table_rows) < 2:
        return None

    column_count = max(len(row) for row in table_rows)
    normalized_rows = [row + [""] * (column_count - len(row)) for row in table_rows]
    extracted_df = pd.DataFrame(normalized_rows[1:], columns=make_unique_columns(normalized_rows[0]))
    extracted_df = normalize_upload_dataframe(extracted_df)
    extracted_df.attrs["ocr_summary"] = {
        "method": "grid",
        "row_count": len(extracted_df),
        "average_confidence": (sum(ocr_confidences) / len(ocr_confidences)) if ocr_confidences else None
    }
    return extracted_df


def extract_lines_table_from_image(image_array):
    """Fallback OCR parser for images without a detectable grid."""
    extracted_items = run_ocr_on_image(image_array)
    if not extracted_items:
        raise ValueError("No text could be extracted from the image")

    rows = []
    for item in sorted(extracted_items, key=lambda current_item: min(point[1] for point in current_item["points"])):
        text = item["text"]
        if not text:
            continue

        split_values = [part.strip() for part in re.split(r"\s{2,}|\t|\|", text) if part.strip()]
        if len(split_values) <= 1:
            split_values = text.split()
        rows.append(split_values)

    if len(rows) < 2:
        raise ValueError("Could not detect multiple rows in the image. Use a clearer table screenshot or edit the extracted data manually.")

    column_count = max(len(row) for row in rows)
    normalized_rows = [row + [""] * (column_count - len(row)) for row in rows]
    extracted_df = pd.DataFrame(normalized_rows[1:], columns=make_unique_columns(normalized_rows[0]))
    extracted_df = normalize_upload_dataframe(extracted_df)
    confidences = [item["confidence"] for item in extracted_items if item["text"]]
    extracted_df.attrs["ocr_summary"] = {
        "method": "line",
        "row_count": len(extracted_df),
        "average_confidence": (sum(confidences) / len(confidences)) if confidences else None
    }
    return extracted_df


def extract_image_table(uploaded_file):
    """Extract tabular lookup data from a PNG or JPG upload."""
    image_array = image_file_to_array(uploaded_file)
    extracted_df = extract_grid_table_from_image(image_array)

    if extracted_df is None:
        extracted_df = extract_lines_table_from_image(image_array)

    return extracted_df


def extract_pdf_tables(uploaded_file):
    """Extract tabular lookup data from a PDF upload."""
    uploaded_file.seek(0)
    extracted_tables = []

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                if not table or len(table) < 2:
                    continue

                header = make_unique_columns(table[0])
                rows = [row for row in table[1:] if row and any(str(cell).strip() for cell in row if cell is not None)]

                if rows:
                    extracted_tables.append(pd.DataFrame(rows, columns=header))

    uploaded_file.seek(0)

    if not extracted_tables:
        raise ValueError("No tabular data could be extracted from the PDF")

    return normalize_upload_dataframe(pd.concat(extracted_tables, ignore_index=True))


def read_uploaded_file(uploaded_file):
    """Read supported upload file types into a normalized DataFrame."""
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif file_name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
    elif file_name.endswith(".pdf"):
        df = extract_pdf_tables(uploaded_file)
    elif file_name.endswith(IMAGE_EXTENSIONS):
        df = extract_image_table(uploaded_file)
    else:
        raise ValueError("Unsupported file type. Please upload a CSV, Excel, PDF, PNG, or JPG file.")

    return normalize_upload_dataframe(df)


def get_first_populated_value(row, candidate_columns):
    """Return the first non-empty value from a set of candidate columns."""
    for column_name in candidate_columns:
        if column_name not in row.index:
            continue

        value = row[column_name]
        if pd.isna(value):
            continue

        if isinstance(value, str):
            value = value.strip()
            if not value:
                continue

        return value

    return None


def normalize_enabled_flag(value):
    """Normalize common truthy and falsy values to Oracle-style Y/N flags."""
    if value is None or pd.isna(value):
        return "Y"

    normalized_value = str(value).strip().upper()
    if normalized_value in {"Y", "YES", "TRUE", "1"}:
        return "Y"
    if normalized_value in {"N", "NO", "FALSE", "0"}:
        return "N"

    raise ValueError(f"Unsupported ENABLED_FLAG value: {value}")


def parse_optional_date(value):
    """Parse optional upload dates into Python date values."""
    if value is None or pd.isna(value):
        return None

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    return pd.to_datetime(value).date()


def validate_upload_columns(df):
    """Check whether the uploaded data exposes the fields needed for import."""
    missing_fields = []
    available_columns = set(df.columns)

    if "LOOKUP_TYPE" not in available_columns:
        missing_fields.append("LOOKUP_TYPE")
    if "LOOKUP_CODE" not in available_columns:
        missing_fields.append("LOOKUP_CODE")
    if not available_columns.intersection({"MEANING", "MEANING_2", "VALUE_MEANING"}):
        missing_fields.append("MEANING")

    return missing_fields


def build_upload_payloads(df):
    """Convert uploaded rows into lookup type and lookup value payloads."""
    data_to_insert = []
    lookup_type_metadata = {}

    for index, row in df.iterrows():
        lookup_type = str(get_first_populated_value(row, ["LOOKUP_TYPE"]) or "").strip().upper()
        lookup_code = str(get_first_populated_value(row, ["LOOKUP_CODE"]) or "").strip().upper()
        meaning = get_first_populated_value(row, ["VALUE_MEANING", "MEANING_2", "MEANING"])
        type_meaning = get_first_populated_value(row, ["TYPE_MEANING", "LOOKUP_TYPE_MEANING", "MEANING"])

        if not lookup_type or lookup_type.lower() == "nan":
            raise ValueError(f"Row {index + 2}: LOOKUP_TYPE is required")
        if not lookup_code or lookup_code.lower() == "nan":
            raise ValueError(f"Row {index + 2}: LOOKUP_CODE is required")
        if meaning is None or str(meaning).strip().lower() == "nan":
            raise ValueError(f"Row {index + 2}: MEANING is required")

        data_to_insert.append((
            lookup_type,
            lookup_code,
            str(meaning).strip(),
            get_first_populated_value(row, ["DESCRIPTION"]),
            normalize_enabled_flag(get_first_populated_value(row, ["ENABLED_FLAG"])),
            parse_optional_date(get_first_populated_value(row, ["START_DATE_ACTIVE"])),
            parse_optional_date(get_first_populated_value(row, ["END_DATE_ACTIVE"]))
        ))

        if lookup_type not in lookup_type_metadata:
            lookup_type_metadata[lookup_type] = (
                lookup_type,
                str(type_meaning).strip() if type_meaning is not None else lookup_type,
                f"Bulk import type for {lookup_type}"
            )

    lookup_types_to_insert = [lookup_type_metadata[key] for key in sorted(lookup_type_metadata)]
    return lookup_types_to_insert, data_to_insert


def upload_lookup_dataframe(df):
    """Upload a reviewed DataFrame into Oracle lookup tables."""
    conn = get_db_connection()
    if not conn:
        raise RuntimeError(st.session_state.db_error or "Database connection failed")

    cursor = None
    try:
        cursor = conn.cursor()
        lookup_types_to_insert, data_to_insert = build_upload_payloads(df)

        cursor.executemany("""
            MERGE INTO FND_LOOKUP_TYPES target
            USING (
                SELECT :1 AS LOOKUP_TYPE, :2 AS MEANING, :3 AS DESCRIPTION FROM dual
            ) source
            ON (target.LOOKUP_TYPE = source.LOOKUP_TYPE)
            WHEN NOT MATCHED THEN
                INSERT (
                    LOOKUP_TYPE,
                    MEANING,
                    DESCRIPTION,
                    CREATED_BY,
                    CREATION_DATE,
                    LAST_UPDATED_BY,
                    LAST_UPDATE_DATE
                )
                VALUES (
                    source.LOOKUP_TYPE,
                    source.MEANING,
                    source.DESCRIPTION,
                    'SYSTEM',
                    SYSDATE,
                    'SYSTEM',
                    SYSDATE
                )
        """, lookup_types_to_insert)

        cursor.executemany("""
            MERGE INTO FND_LOOKUP_VALUES target
            USING (
                SELECT
                    :1 AS LOOKUP_TYPE,
                    :2 AS LOOKUP_CODE,
                    :3 AS MEANING,
                    :4 AS DESCRIPTION,
                    :5 AS ENABLED_FLAG,
                    :6 AS START_DATE_ACTIVE,
                    :7 AS END_DATE_ACTIVE
                FROM dual
            ) source
            ON (
                target.LOOKUP_TYPE = source.LOOKUP_TYPE
                AND target.LOOKUP_CODE = source.LOOKUP_CODE
            )
            WHEN MATCHED THEN
                UPDATE SET
                    target.MEANING = source.MEANING,
                    target.DESCRIPTION = source.DESCRIPTION,
                    target.ENABLED_FLAG = source.ENABLED_FLAG,
                    target.START_DATE_ACTIVE = source.START_DATE_ACTIVE,
                    target.END_DATE_ACTIVE = source.END_DATE_ACTIVE,
                    target.LAST_UPDATED_BY = 'SYSTEM',
                    target.LAST_UPDATE_DATE = SYSDATE
            WHEN NOT MATCHED THEN
                INSERT (
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
                )
                VALUES (
                    source.LOOKUP_TYPE,
                    source.LOOKUP_CODE,
                    source.MEANING,
                    source.DESCRIPTION,
                    source.ENABLED_FLAG,
                    source.START_DATE_ACTIVE,
                    source.END_DATE_ACTIVE,
                    'SYSTEM',
                    SYSDATE,
                    'SYSTEM',
                    SYSDATE
                )
        """, data_to_insert)

        conn.commit()
        return len(data_to_insert)
    except Exception:
        conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()


def dataframe_to_csv_bytes(df):
    """Convert a DataFrame to CSV bytes for Streamlit downloads."""
    return df.to_csv(index=False).encode("utf-8")


def build_lookup_report_datasets(conn, expiring_within_days):
    """Build the reporting datasets used by the reporting dashboard."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT
                LOOKUP_TYPE,
                LOOKUP_CODE,
                MEANING,
                DESCRIPTION,
                ENABLED_FLAG,
                START_DATE_ACTIVE,
                END_DATE_ACTIVE,
                CREATION_DATE,
                LAST_UPDATE_DATE
            FROM FND_LOOKUP_VALUES
            ORDER BY LOOKUP_TYPE, LOOKUP_CODE
        """)
        value_rows = cursor.fetchall()

        cursor.execute("""
            SELECT
                LOOKUP_TYPE,
                MEANING,
                DESCRIPTION,
                CREATION_DATE,
                LAST_UPDATE_DATE
            FROM FND_LOOKUP_TYPES
            ORDER BY LOOKUP_TYPE
        """)
        type_rows = cursor.fetchall()
    finally:
        cursor.close()

    values_data = []
    today = datetime.now().date()

    for row in value_rows:
        is_active = is_lookup_active(row[4], row[5], row[6])
        status = "Active" if is_active else "Inactive"
        values_data.append({
            "Lookup Type": row[0],
            "Lookup Code": row[1],
            "Meaning": row[2],
            "Description": row[3] or "",
            "Enabled Flag": row[4],
            "Start Date Active": row[5],
            "End Date Active": row[6],
            "Creation Date": row[7],
            "Last Update Date": row[8],
            "Status": status,
            "Days Until Expiry": (row[6] - today).days if row[6] else None
        })

    values_df = pd.DataFrame(values_data)
    types_df = pd.DataFrame([
        {
            "Lookup Type": row[0],
            "Type Meaning": row[1],
            "Description": row[2] or "",
            "Creation Date": row[3],
            "Last Update Date": row[4]
        }
        for row in type_rows
    ])

    total_values = len(values_df)
    active_values = int((values_df["Status"] == "Active").sum()) if not values_df.empty else 0
    inactive_values = total_values - active_values

    today_ts = pd.Timestamp(today)
    expiry_deadline_ts = today_ts + pd.Timedelta(days=expiring_within_days)
    end_dates = pd.to_datetime(values_df["End Date Active"], errors="coerce") if not values_df.empty else pd.Series(dtype="datetime64[ns]")
    start_dates = pd.to_datetime(values_df["Start Date Active"], errors="coerce") if not values_df.empty else pd.Series(dtype="datetime64[ns]")

    expired_values = int((end_dates.notna() & (end_dates < today_ts)).sum()) if not values_df.empty else 0
    future_dated_values = int((start_dates.notna() & (start_dates > today_ts)).sum()) if not values_df.empty else 0

    type_summary_df = pd.DataFrame()
    if not values_df.empty:
        grouped = values_df.groupby("Lookup Type", dropna=False)
        type_summary_df = grouped.agg(
            Total_Codes=("Lookup Code", "count"),
            Active_Codes=("Status", lambda series: int((series == "Active").sum())),
            Inactive_Codes=("Status", lambda series: int((series == "Inactive").sum())),
            Last_Updated=("Last Update Date", "max")
        ).reset_index()
        type_summary_df.columns = ["Lookup Type", "Total Codes", "Active Codes", "Inactive Codes", "Last Updated"]
        type_summary_df = type_summary_df.sort_values(["Total Codes", "Lookup Type"], ascending=[False, True])

    expiring_df = pd.DataFrame()
    if not values_df.empty:
        expiring_mask = (
            values_df["End Date Active"].notna()
            & (values_df["Status"] == "Active")
            & (end_dates >= today_ts)
            & (end_dates <= expiry_deadline_ts)
        )
        expiring_df = values_df.loc[expiring_mask, [
            "Lookup Type", "Lookup Code", "Meaning", "End Date Active", "Days Until Expiry", "Status"
        ]].sort_values(["Days Until Expiry", "Lookup Type", "Lookup Code"])

    recent_changes_df = pd.DataFrame()
    if not values_df.empty:
        recent_changes_df = values_df[[
            "Lookup Type", "Lookup Code", "Meaning", "Status", "Last Update Date", "Creation Date"
        ]].sort_values("Last Update Date", ascending=False).head(25)

    summary_metrics = {
        "total_types": len(types_df),
        "total_values": total_values,
        "active_values": active_values,
        "inactive_values": inactive_values,
        "expired_values": expired_values,
        "future_dated_values": future_dated_values
    }

    return {
        "summary_metrics": summary_metrics,
        "types_df": types_df,
        "values_df": values_df,
        "type_summary_df": type_summary_df,
        "expiring_df": expiring_df,
        "recent_changes_df": recent_changes_df
    }

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
    ["🔎 Search & Discovery", "➕ Create New", "📊 View All", "📈 Reports", "✏️ Edit", "⚡ Bulk Upload", "🔗 Dependencies"]
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
                    FETCH FIRST 1000 ROWS ONLY
                """, {"search": search_pattern})
                
                results = cursor.fetchall()[:search_limit]
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
                            (LOOKUP_TYPE, MEANING, DESCRIPTION, CREATED_BY, CREATION_DATE, LAST_UPDATED_BY, LAST_UPDATE_DATE)
                            VALUES (:lookup_type_value, :lookup_type_value, :description_value, 'SYSTEM', SYSDATE, 'SYSTEM', SYSDATE)
                        """, {
                            "lookup_type_value": lookup_type.upper(),
                            "description_value": f"Auto-created type for {lookup_type}"
                        })
                        conn.commit()
                        
                    except oracledb.IntegrityError:
                        pass  # Type already exists
                        
                    try:
                        cursor = conn.cursor()
                        
                        cursor.execute("""
                            INSERT INTO FND_LOOKUP_VALUES
                            (LOOKUP_TYPE, LOOKUP_CODE, MEANING, DESCRIPTION, ENABLED_FLAG, 
                             START_DATE_ACTIVE, END_DATE_ACTIVE, CREATED_BY, CREATION_DATE, LAST_UPDATED_BY, LAST_UPDATE_DATE)
                            VALUES (:lookup_type_value, :lookup_code_value, :meaning_value, :description_value, :enabled_value, 
                                    :start_date_value, :end_date_value, 'SYSTEM', SYSDATE, 'SYSTEM', SYSDATE)
                        """, {
                            "lookup_type_value": lookup_type.upper(),
                            "lookup_code_value": lookup_code.upper(),
                            "meaning_value": meaning,
                            "description_value": description or None,
                            "enabled_value": enabled,
                            "start_date_value": start_date,
                            "end_date_value": end_date if end_date else None
                        })
                        
                        conn.commit()
                        st.success(f"✅ Successfully created lookup code: {lookup_code.upper()}")
                        
                    except oracledb.IntegrityError as e:
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
                    WHERE LOOKUP_TYPE = :lookup_type_value
                    ORDER BY LOOKUP_CODE
                """, {"lookup_type_value": selected_type})
                
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
# PAGE: REPORTS
# ============================================================================

elif page == "📈 Reports":
    st.header("📈 Lookup Reports")
    st.markdown("Analyze lookup coverage, status, recent changes, and export report data")

    expiring_within_days = st.slider(
        "Expiring within (days)",
        min_value=7,
        max_value=180,
        value=30,
        step=1,
        help="Show active lookup codes that will expire within this many days."
    )

    conn = get_db_connection()
    if conn:
        try:
            report_data = build_lookup_report_datasets(conn, expiring_within_days)
            summary_metrics = report_data["summary_metrics"]
            type_summary_df = report_data["type_summary_df"]
            expiring_df = report_data["expiring_df"]
            recent_changes_df = report_data["recent_changes_df"]
            values_df = report_data["values_df"]
            types_df = report_data["types_df"]

            metric_columns = st.columns(6)
            metric_columns[0].metric("Lookup Types", summary_metrics["total_types"])
            metric_columns[1].metric("Lookup Codes", summary_metrics["total_values"])
            metric_columns[2].metric("Active", summary_metrics["active_values"])
            metric_columns[3].metric("Inactive", summary_metrics["inactive_values"])
            metric_columns[4].metric("Expired", summary_metrics["expired_values"])
            metric_columns[5].metric("Future Dated", summary_metrics["future_dated_values"])

            report_tab_1, report_tab_2, report_tab_3, report_tab_4 = st.tabs([
                "Type Summary",
                "Expiring Codes",
                "Recent Changes",
                "Exports"
            ])

            with report_tab_1:
                if type_summary_df.empty:
                    st.info("No lookup value data is available for reporting yet.")
                else:
                    top_types_df = type_summary_df.head(10).set_index("Lookup Type")
                    st.bar_chart(top_types_df[["Total Codes", "Active Codes", "Inactive Codes"]])
                    st.dataframe(type_summary_df, use_container_width=True)
                    st.download_button(
                        "Download Type Summary CSV",
                        data=dataframe_to_csv_bytes(type_summary_df),
                        file_name="lookup_type_summary.csv",
                        mime="text/csv"
                    )

            with report_tab_2:
                if expiring_df.empty:
                    st.success(f"No active lookup codes are expiring within the next {expiring_within_days} days.")
                else:
                    st.warning(f"Found {len(expiring_df)} active lookup codes expiring within {expiring_within_days} days.")
                    st.dataframe(expiring_df, use_container_width=True)
                    st.download_button(
                        "Download Expiring Codes CSV",
                        data=dataframe_to_csv_bytes(expiring_df),
                        file_name="expiring_lookup_codes.csv",
                        mime="text/csv"
                    )

            with report_tab_3:
                if recent_changes_df.empty:
                    st.info("No recent changes are available.")
                else:
                    st.dataframe(recent_changes_df, use_container_width=True)
                    st.download_button(
                        "Download Recent Changes CSV",
                        data=dataframe_to_csv_bytes(recent_changes_df),
                        file_name="recent_lookup_changes.csv",
                        mime="text/csv"
                    )

            with report_tab_4:
                export_col_1, export_col_2 = st.columns(2)
                with export_col_1:
                    st.subheader("Lookup Value Export")
                    if values_df.empty:
                        st.info("No lookup values available to export.")
                    else:
                        st.dataframe(values_df.head(20), use_container_width=True)
                        st.download_button(
                            "Download Full Lookup Values CSV",
                            data=dataframe_to_csv_bytes(values_df),
                            file_name="fnd_lookup_values_report.csv",
                            mime="text/csv"
                        )

                with export_col_2:
                    st.subheader("Lookup Type Export")
                    if types_df.empty:
                        st.info("No lookup types available to export.")
                    else:
                        st.dataframe(types_df, use_container_width=True)
                        st.download_button(
                            "Download Full Lookup Types CSV",
                            data=dataframe_to_csv_bytes(types_df),
                            file_name="fnd_lookup_types_report.csv",
                            mime="text/csv"
                        )

        except Exception as e:
            st.error(f"Error building reports: {str(e)}")

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
                    WHERE LOOKUP_TYPE = :lookup_type_value
                    ORDER BY LOOKUP_CODE
                """, {"lookup_type_value": selected_type})
                
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
                        WHERE LOOKUP_TYPE = :lookup_type_value AND LOOKUP_CODE = :lookup_code_value
                    """, {"lookup_type_value": selected_type, "lookup_code_value": selected_code})
                    
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
    st.markdown("Upload CSV, Excel, PDF, PNG, or JPG files to bulk import lookup codes")
    
    uploaded_file = st.file_uploader(
        "Choose a CSV, Excel, PDF, PNG, or JPG file",
        type=["csv", "xlsx", "pdf", "png", "jpg", "jpeg"],
        help="Files should contain columns such as LOOKUP_TYPE, LOOKUP_CODE, MEANING, DESCRIPTION, ENABLED_FLAG, START_DATE_ACTIVE, END_DATE_ACTIVE"
    )
    
    if uploaded_file:
        try:
            df = read_uploaded_file(uploaded_file)
            file_name = uploaded_file.name.lower()

            if file_name.endswith(IMAGE_EXTENSIONS):
                st.write("**Uploaded image preview:**")
                st.image(uploaded_file, caption=uploaded_file.name, use_column_width=True)

                ocr_summary = df.attrs.get("ocr_summary", {})
                summary_columns = st.columns(3)
                summary_columns[0].metric("OCR Mode", ocr_summary.get("method", "image").title())
                summary_columns[1].metric("Detected Rows", ocr_summary.get("row_count", len(df)))
                average_confidence = ocr_summary.get("average_confidence")
                summary_columns[2].metric(
                    "Avg OCR Confidence",
                    f"{average_confidence:.0%}" if average_confidence is not None else "N/A"
                )

                if average_confidence is not None and average_confidence < 0.80:
                    st.warning("OCR confidence is low. Review the extracted table carefully before confirming the upload.")
            
            st.write("**Review and edit extracted data before upload:**")
            reviewed_df = st.data_editor(
                df,
                num_rows="dynamic",
                use_container_width=True,
                key=f"bulk_upload_editor_{uploaded_file.name}_{uploaded_file.size}"
            )
            
            # Validation checks
            st.write("**Validation Checks:**")
            validation_passed = True
            
            missing_columns = validate_upload_columns(reviewed_df)
            
            if missing_columns:
                st.error(f"❌ Missing required columns: {', '.join(missing_columns)}")
                validation_passed = False
            
            if validation_passed:
                st.success(f"✅ File is valid. Contains {len(reviewed_df)} records")
                
                confirmation_text = "Confirm OCR Review and Upload" if file_name.endswith(IMAGE_EXTENSIONS) else "Confirm Upload"
                confirm_upload = st.checkbox(
                    confirmation_text,
                    help="Review the extracted table above before writing records to Oracle."
                )

                if st.button("🚀 Upload to Database", disabled=not confirm_upload):
                    with st.spinner("Uploading data..."):
                        try:
                            uploaded_count = upload_lookup_dataframe(reviewed_df)
                            st.success(f"✅ Successfully uploaded {uploaded_count} records!")
                        except Exception as e:
                            st.error(f"❌ Upload error: {str(e)}")
        
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
