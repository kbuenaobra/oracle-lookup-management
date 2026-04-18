"""
Insert sample data into Oracle FND_LOOKUP_TYPES and FND_LOOKUP_VALUES tables
"""

import oracledb
from datetime import datetime

DB_HOST = "localhost"
DB_PORT = 1521
DB_SERVICE = "XEPDB1"
DB_USER = "SYSTEM"
DB_PASSWORD = "ADmin1234"

def insert_oracle_sample_data():
    """Insert sample lookup data into Oracle database"""
    
    conn = oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        service_name=DB_SERVICE
    )
    cursor = conn.cursor()
    
    now = datetime.now()
    
    # Sample Lookup Types
    lookup_types = [
        ("YES_NO", "Yes/No", "Standard Yes/No lookup", "SYSTEM", now, "SYSTEM", now),
        ("ORDER_STATUS", "Order Status", "Status values for orders", "SYSTEM", now, "SYSTEM", now),
        ("PAYMENT_METHOD", "Payment Method", "Available payment methods", "SYSTEM", now, "SYSTEM", now),
        ("CUSTOMER_TYPE", "Customer Type", "Classification of customers", "SYSTEM", now, "SYSTEM", now),
        ("GENDER", "Gender", "Gender classification", "SYSTEM", now, "SYSTEM", now),
        ("PRODUCT_CATEGORY", "Product Category", "Product categories", "SYSTEM", now, "SYSTEM", now),
    ]
    
    # Insert Lookup Types
    for lt in lookup_types:
        cursor.execute("""
            INSERT INTO FND_LOOKUP_TYPES 
            (LOOKUP_TYPE, MEANING, DESCRIPTION, CREATED_BY, CREATION_DATE, LAST_UPDATED_BY, LAST_UPDATE_DATE)
            VALUES (:1, :2, :3, :4, :5, :6, :7)
        """, lt)
    
    # Sample Lookup Values
    lookup_values = [
        # YES_NO values
        ("YES_NO", "Y", "Yes", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("YES_NO", "N", "No", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        
        # ORDER_STATUS values
        ("ORDER_STATUS", "PENDING", "Pending", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("ORDER_STATUS", "CONFIRMED", "Confirmed", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("ORDER_STATUS", "SHIPPED", "Shipped", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("ORDER_STATUS", "DELIVERED", "Delivered", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("ORDER_STATUS", "CANCELLED", "Cancelled", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("ORDER_STATUS", "REFUNDED", "Refunded", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        
        # PAYMENT_METHOD values
        ("PAYMENT_METHOD", "CREDIT_CARD", "Credit Card", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PAYMENT_METHOD", "DEBIT_CARD", "Debit Card", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PAYMENT_METHOD", "NET_BANKING", "Net Banking", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PAYMENT_METHOD", "UPI", "UPI", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PAYMENT_METHOD", "WALLET", "Digital Wallet", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PAYMENT_METHOD", "COD", "Cash on Delivery", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        
        # CUSTOMER_TYPE values
        ("CUSTOMER_TYPE", "INDIVIDUAL", "Individual", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("CUSTOMER_TYPE", "BUSINESS", "Business", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("CUSTOMER_TYPE", "CORPORATE", "Corporate", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("CUSTOMER_TYPE", "GOVERNMENT", "Government", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        
        # GENDER values
        ("GENDER", "M", "Male", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("GENDER", "F", "Female", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("GENDER", "O", "Other", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("GENDER", "U", "Undisclosed", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        
        # PRODUCT_CATEGORY values
        ("PRODUCT_CATEGORY", "ELECTRONICS", "Electronics", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PRODUCT_CATEGORY", "CLOTHING", "Clothing", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PRODUCT_CATEGORY", "BOOKS", "Books", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PRODUCT_CATEGORY", "HOME", "Home & Garden", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PRODUCT_CATEGORY", "SPORTS", "Sports", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PRODUCT_CATEGORY", "FOOD", "Food & Beverages", None, "Y", None, None, "SYSTEM", now, "SYSTEM", now),
    ]
    
    # Insert Lookup Values
    for lv in lookup_values:
        cursor.execute("""
            INSERT INTO FND_LOOKUP_VALUES 
            (LOOKUP_TYPE, LOOKUP_CODE, MEANING, DESCRIPTION, ENABLED_FLAG, START_DATE_ACTIVE, END_DATE_ACTIVE,
             CREATED_BY, CREATION_DATE, LAST_UPDATED_BY, LAST_UPDATE_DATE)
            VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11)
        """, lv)
    
    conn.commit()
    
    # Display what was inserted
    print("\n✅ Sample data inserted successfully into Oracle!\n")
    
    # Show Lookup Types
    print("=" * 70)
    print("FND_LOOKUP_TYPES")
    print("=" * 70)
    cursor.execute("SELECT LOOKUP_TYPE, MEANING, DESCRIPTION FROM FND_LOOKUP_TYPES ORDER BY LOOKUP_TYPE")
    for row in cursor.fetchall():
        print(f"  {row[0]:<20} | {row[1]:<20} | {row[2]}")
    
    # Show Lookup Values by Type
    print("\n" + "=" * 70)
    print("FND_LOOKUP_VALUES")
    print("=" * 70)
    cursor.execute("""
        SELECT LOOKUP_TYPE, LOOKUP_CODE, MEANING, ENABLED_FLAG 
        FROM FND_LOOKUP_VALUES 
        ORDER BY LOOKUP_TYPE, LOOKUP_CODE
    """)
    current_type = None
    for row in cursor.fetchall():
        if row[0] != current_type:
            print(f"\n  {row[0]}:")
            current_type = row[0]
        status = "✓" if row[3] == "Y" else "✗"
        print(f"    [{status}] {row[1]:<20} = {row[2]}")
    
    print("\n" + "=" * 70)
    print(f"Total Lookup Types: {len(lookup_types)}")
    print(f"Total Lookup Values: {len(lookup_values)}")
    print("=" * 70 + "\n")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    try:
        insert_oracle_sample_data()
        print("✨ Now go to SQL Developer and query the tables!")
    except Exception as e:
        print(f"❌ Error: {e}")
