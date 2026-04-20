"""
Insert sample data into FND_LOOKUP_TYPES and FND_LOOKUP_VALUES tables
"""

import sqlite3
from datetime import datetime

DB_FILE = "lookups.db"

def insert_sample_data():
    """Insert sample lookup data into the database"""
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
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
            INSERT OR IGNORE INTO FND_LOOKUP_TYPES 
            (LOOKUP_TYPE, MEANING, DESCRIPTION, CREATED_BY, CREATION_DATE, LAST_UPDATED_BY, LAST_UPDATE_DATE)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, lt)
    
    # Sample Lookup Values
    lookup_values = [
        # YES_NO values
        ("YES_NO", "Y", "Yes", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("YES_NO", "N", "No", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        
        # ORDER_STATUS values
        ("ORDER_STATUS", "PENDING", "Pending", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("ORDER_STATUS", "CONFIRMED", "Confirmed", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("ORDER_STATUS", "SHIPPED", "Shipped", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("ORDER_STATUS", "DELIVERED", "Delivered", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("ORDER_STATUS", "CANCELLED", "Cancelled", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("ORDER_STATUS", "REFUNDED", "Refunded", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        
        # PAYMENT_METHOD values
        ("PAYMENT_METHOD", "CREDIT_CARD", "Credit Card", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PAYMENT_METHOD", "DEBIT_CARD", "Debit Card", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PAYMENT_METHOD", "NET_BANKING", "Net Banking", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PAYMENT_METHOD", "UPI", "UPI", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PAYMENT_METHOD", "WALLET", "Digital Wallet", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PAYMENT_METHOD", "COD", "Cash on Delivery", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        
        # CUSTOMER_TYPE values
        ("CUSTOMER_TYPE", "INDIVIDUAL", "Individual", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("CUSTOMER_TYPE", "BUSINESS", "Business", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("CUSTOMER_TYPE", "CORPORATE", "Corporate", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("CUSTOMER_TYPE", "GOVERNMENT", "Government", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        
        # GENDER values
        ("GENDER", "M", "Male", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("GENDER", "F", "Female", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("GENDER", "O", "Other", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("GENDER", "U", "Undisclosed", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        
        # PRODUCT_CATEGORY values
        ("PRODUCT_CATEGORY", "ELECTRONICS", "Electronics", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PRODUCT_CATEGORY", "CLOTHING", "Clothing", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PRODUCT_CATEGORY", "BOOKS", "Books", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PRODUCT_CATEGORY", "HOME", "Home & Garden", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PRODUCT_CATEGORY", "SPORTS", "Sports", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
        ("PRODUCT_CATEGORY", "FOOD", "Food & Beverages", "Y", None, None, "SYSTEM", now, "SYSTEM", now),
    ]
    
    # Insert Lookup Values
    for lv in lookup_values:
        cursor.execute("""
            INSERT OR IGNORE INTO FND_LOOKUP_VALUES 
            (LOOKUP_TYPE, LOOKUP_CODE, MEANING, ENABLED_FLAG, START_DATE_ACTIVE, END_DATE_ACTIVE, 
             CREATED_BY, CREATION_DATE, LAST_UPDATED_BY, LAST_UPDATE_DATE)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, lv)
    
    conn.commit()
    
    # Display what was inserted
    print("\n✅ Sample data inserted successfully!\n")
    
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
    
    conn.close()

if __name__ == "__main__":
    try:
        insert_sample_data()
        print("✨ Ready to use! Check your Streamlit app at http://localhost:8501")
    except Exception as e:
        print(f"❌ Error: {e}")
