#!/usr/bin/env python3
"""
Oracle Database Schema Creation Script
Creates FND_LOOKUP_TYPES and FND_LOOKUP_VALUES tables
"""

import oracledb
import sys

# Database connection parameters
DB_HOST = "localhost"
DB_PORT = 1521
DB_SERVICE = "XEPDB1"
DB_USER = "SYSTEM"
DB_PASSWORD = "ADmin1234"  # Update if needed

# Connection string
dsn = f"{DB_HOST}:{DB_PORT}/{DB_SERVICE}"

try:
    # Create connection using oracledb
    connection = oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        service_name=DB_SERVICE
    )
    cursor = connection.cursor()
    
    print("✓ Connected to Oracle Database successfully")
    print(f"  Host: {DB_HOST}:{DB_PORT}")
    print(f"  Service: {DB_SERVICE}")
    print(f"  User: {DB_USER}\n")
    
    # Drop existing tables if they exist
    print("Dropping existing tables...")
    try:
        cursor.execute("DROP TABLE FND_LOOKUP_VALUES")
        print("  ✓ Dropped FND_LOOKUP_VALUES")
    except oracledb.DatabaseError as e:
        if "does not exist" in str(e):
            print("  - FND_LOOKUP_VALUES does not exist (OK)")
        else:
            print(f"  ! Error: {e}")
    
    try:
        cursor.execute("DROP TABLE FND_LOOKUP_TYPES")
        print("  ✓ Dropped FND_LOOKUP_TYPES")
    except oracledb.DatabaseError as e:
        if "does not exist" in str(e):
            print("  - FND_LOOKUP_TYPES does not exist (OK)")
        else:
            print(f"  ! Error: {e}")
    
    connection.commit()
    
    # Create FND_LOOKUP_TYPES table
    print("\nCreating FND_LOOKUP_TYPES table...")
    cursor.execute("""
        CREATE TABLE FND_LOOKUP_TYPES (
            LOOKUP_TYPE         VARCHAR2(30)    NOT NULL PRIMARY KEY,
            MEANING             VARCHAR2(80)    NOT NULL,
            DESCRIPTION         VARCHAR2(240),
            CREATED_BY          VARCHAR2(50)    NOT NULL,
            CREATION_DATE       DATE            NOT NULL,
            LAST_UPDATED_BY     VARCHAR2(50)    NOT NULL,
            LAST_UPDATE_DATE    DATE            NOT NULL
        )
    """)
    print("  ✓ Created FND_LOOKUP_TYPES")
    
    # Create indexes for FND_LOOKUP_TYPES
    cursor.execute("CREATE INDEX IDX_LOOKUP_TYPES_MEANING ON FND_LOOKUP_TYPES(MEANING)")
    print("  ✓ Created index on MEANING")
    
    # Add comments for FND_LOOKUP_TYPES
    cursor.execute("COMMENT ON TABLE FND_LOOKUP_TYPES IS 'Master lookup types for Oracle EBS lookup management'")
    cursor.execute("COMMENT ON COLUMN FND_LOOKUP_TYPES.LOOKUP_TYPE IS 'Unique lookup type identifier (uppercase)'")
    cursor.execute("COMMENT ON COLUMN FND_LOOKUP_TYPES.MEANING IS 'Display name for the lookup type'")
    cursor.execute("COMMENT ON COLUMN FND_LOOKUP_TYPES.DESCRIPTION IS 'Additional documentation for the lookup type'")
    cursor.execute("COMMENT ON COLUMN FND_LOOKUP_TYPES.CREATED_BY IS 'Audit: User ID who created the record'")
    cursor.execute("COMMENT ON COLUMN FND_LOOKUP_TYPES.CREATION_DATE IS 'Audit: Timestamp of record creation'")
    cursor.execute("COMMENT ON COLUMN FND_LOOKUP_TYPES.LAST_UPDATED_BY IS 'Audit: User ID who last updated the record'")
    cursor.execute("COMMENT ON COLUMN FND_LOOKUP_TYPES.LAST_UPDATE_DATE IS 'Audit: Timestamp of last update'")
    print("  ✓ Added table comments")
    
    connection.commit()
    
    # Create FND_LOOKUP_VALUES table
    print("\nCreating FND_LOOKUP_VALUES table...")
    cursor.execute("""
        CREATE TABLE FND_LOOKUP_VALUES (
            LOOKUP_TYPE         VARCHAR2(30)    NOT NULL,
            LOOKUP_CODE         VARCHAR2(30)    NOT NULL,
            MEANING             VARCHAR2(80)    NOT NULL,
            DESCRIPTION         VARCHAR2(240),
            ENABLED_FLAG        VARCHAR2(1)     NOT NULL,
            START_DATE_ACTIVE   DATE,
            END_DATE_ACTIVE     DATE,
            CREATED_BY          VARCHAR2(50)    NOT NULL,
            CREATION_DATE       DATE            NOT NULL,
            LAST_UPDATED_BY     VARCHAR2(50)    NOT NULL,
            LAST_UPDATE_DATE    DATE            NOT NULL,
            CONSTRAINT PK_LOOKUP_VALUES PRIMARY KEY (LOOKUP_TYPE, LOOKUP_CODE),
            CONSTRAINT FK_LOOKUP_VALUES_TYPE FOREIGN KEY (LOOKUP_TYPE) REFERENCES FND_LOOKUP_TYPES(LOOKUP_TYPE) ON DELETE CASCADE,
            CONSTRAINT CK_END_DATE_ACTIVE CHECK (END_DATE_ACTIVE IS NULL OR START_DATE_ACTIVE IS NULL OR END_DATE_ACTIVE >= START_DATE_ACTIVE)
        )
    """)
    print("  ✓ Created FND_LOOKUP_VALUES")
    
    # Create indexes for FND_LOOKUP_VALUES
    cursor.execute("CREATE INDEX IDX_LOOKUP_VALUES_TYPE ON FND_LOOKUP_VALUES(LOOKUP_TYPE)")
    cursor.execute("CREATE INDEX IDX_LOOKUP_VALUES_CODE ON FND_LOOKUP_VALUES(LOOKUP_CODE)")
    cursor.execute("CREATE INDEX IDX_LOOKUP_VALUES_MEANING ON FND_LOOKUP_VALUES(MEANING)")
    cursor.execute("CREATE INDEX IDX_LOOKUP_VALUES_ENABLED ON FND_LOOKUP_VALUES(ENABLED_FLAG)")
    print("  ✓ Created 4 indexes")
    
    # Add comments for FND_LOOKUP_VALUES
    cursor.execute("COMMENT ON TABLE FND_LOOKUP_VALUES IS 'Lookup values for Oracle EBS lookup management'")
    cursor.execute("COMMENT ON COLUMN FND_LOOKUP_VALUES.LOOKUP_TYPE IS 'Reference to FND_LOOKUP_TYPES (FK, uppercase)'")
    cursor.execute("COMMENT ON COLUMN FND_LOOKUP_VALUES.LOOKUP_CODE IS 'Unique code within lookup type (uppercase)'")
    cursor.execute("COMMENT ON COLUMN FND_LOOKUP_VALUES.MEANING IS 'Display value for the lookup code'")
    cursor.execute("COMMENT ON COLUMN FND_LOOKUP_VALUES.DESCRIPTION IS 'Additional documentation for the lookup code'")
    cursor.execute("COMMENT ON COLUMN FND_LOOKUP_VALUES.ENABLED_FLAG IS 'Status flag: Y=Active, N=Inactive'")
    cursor.execute("COMMENT ON COLUMN FND_LOOKUP_VALUES.START_DATE_ACTIVE IS 'Effective start date (inclusive)'")
    cursor.execute("COMMENT ON COLUMN FND_LOOKUP_VALUES.END_DATE_ACTIVE IS 'Effective end date (inclusive)'")
    cursor.execute("COMMENT ON COLUMN FND_LOOKUP_VALUES.CREATED_BY IS 'Audit: User ID who created the record'")
    cursor.execute("COMMENT ON COLUMN FND_LOOKUP_VALUES.CREATION_DATE IS 'Audit: Timestamp of record creation'")
    cursor.execute("COMMENT ON COLUMN FND_LOOKUP_VALUES.LAST_UPDATED_BY IS 'Audit: User ID who last updated the record'")
    cursor.execute("COMMENT ON COLUMN FND_LOOKUP_VALUES.LAST_UPDATE_DATE IS 'Audit: Timestamp of last update'")
    print("  ✓ Added table comments")
    
    connection.commit()
    
    # Verify table creation
    print("\n" + "="*60)
    print("SCHEMA CREATION COMPLETED SUCCESSFULLY")
    print("="*60)
    print("\nTables created:")
    cursor.execute("""
        SELECT table_name FROM user_tables 
        WHERE table_name IN ('FND_LOOKUP_TYPES', 'FND_LOOKUP_VALUES')
        ORDER BY table_name
    """)
    for row in cursor.fetchall():
        print(f"  ✓ {row[0]}")
    
    cursor.close()
    connection.close()
    print("\n✓ Database connection closed")
    
except oracledb.DatabaseError as e:
    print(f"\n✗ Database Error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n✗ Unexpected Error: {e}")
    sys.exit(1)
