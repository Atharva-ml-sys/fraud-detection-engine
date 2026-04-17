# database/db_setup.py
#
# Yeh file do kaam karti hai:
# 1. PostgreSQL se connect karti hai
# 2. Transactions table banati hai

import psycopg2

# Database connection details
# Yeh wahi values hain jo docker run mein diye the
DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "frauddb",
    "user":     "frauduser",
    "password": "fraudpass123",
}

def get_connection():
    """Database connection banao"""
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

def create_tables():
    """Transactions table banao — agar pehle se nahi hai toh"""
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id               SERIAL PRIMARY KEY,
            transaction_id   VARCHAR(100) UNIQUE NOT NULL,
            transaction_type VARCHAR(20) NOT NULL,
            amount           DECIMAL(15,2) NOT NULL,
            sender_account   VARCHAR(100) NOT NULL,
            receiver_account VARCHAR(100) NOT NULL,
            city             VARCHAR(100),
            risk_score       DECIMAL(5,2),
            risk_tier        VARCHAR(10),
            created_at       TIMESTAMP DEFAULT NOW()
        )
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Table 'transactions' ready hai!")

def insert_transaction(txn: dict):
    """Ek transaction database mein save karo"""
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        INSERT INTO transactions
            (transaction_id, transaction_type, amount,
             sender_account, receiver_account, city)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (transaction_id) DO NOTHING
    """, (
        txn["id"],
        txn["type"],
        txn["amount"],
        txn["sender"],
        txn["receiver"],
        txn.get("city"),
    ))

    conn.commit()
    cur.close()
    conn.close()

def get_all_transactions():
    """Sab transactions fetch karo"""
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        SELECT transaction_id, transaction_type,
               amount, sender_account, city, created_at
        FROM transactions
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# Main — test karo
if __name__ == "__main__":
    print("=== Database Setup ===\n")

    # Step 1: Table banao
    create_tables()

    # Step 2: 3 transactions insert karo
    print("\n📝 Transactions insert kar rahe hain...")

    transactions = [
        {"id": "TXN_DB_001", "type": "UPI",  "amount": 15000,
         "sender": "ACC_ATHARVA", "receiver": "ACC_RAHUL",   "city": "Pune"},
        {"id": "TXN_DB_002", "type": "NEFT", "amount": 250000,
         "sender": "ACC_RAHUL",   "receiver": "ACC_PRIYA",   "city": "Mumbai"},
        {"id": "TXN_DB_003", "type": "IMPS", "amount": 800,
         "sender": "ACC_PRIYA",   "receiver": "ACC_ATHARVA", "city": "Delhi"},
    ]

    for txn in transactions:
        insert_transaction(txn)
        print(f"  ✅ Inserted: {txn['id']} | ₹{txn['amount']:,}")

    # Step 3: Fetch karo aur dikhao
    print("\n📊 Database se fetch kar rahe hain...")
    rows = get_all_transactions()

    print(f"\n{'ID':<15} {'Type':<12} {'Amount':>10} {'City':<12}")
    print("-" * 55)
    for row in rows:
        print(f"{row[0]:<15} {row[1]:<12} ₹{row[2]:>9,.0f} {row[4] or '-':<12}")

    print(f"\n✅ Total {len(rows)} transactions database mein hain!")
    # Feedback table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS analyst_feedback (
            id             SERIAL PRIMARY KEY,
            transaction_id VARCHAR(100),
            analyst_id     VARCHAR(100),
            verdict        VARCHAR(30),
            notes          TEXT,
            created_at     TIMESTAMP DEFAULT NOW()
        )
    """)
