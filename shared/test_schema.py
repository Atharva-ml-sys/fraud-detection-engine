# shared/test_schema.py
# Schema test karte hain — valid aur invalid dono

from schemas import Transaction, TransactionType
from datetime import datetime

print("=== Test 1: Valid Transaction ===")
valid_txn = Transaction(
    transaction_id   = "TXN_001",
    timestamp        = datetime.now(),
    transaction_type = TransactionType.UPI,
    amount           = 15000,
    sender_account   = "ACC_ATHARVA",
    receiver_account = "ACC_RAHUL",
    city             = "Pune",
)
print(f"ID: {valid_txn.transaction_id}")
print(f"Amount: ₹{valid_txn.amount}")
print(f"Type: {valid_txn.transaction_type}")
print("✅ Valid transaction accepted!\n")

print("=== Test 2: Invalid Amount ===")
try:
    invalid_txn = Transaction(
        transaction_id   = "TXN_002",
        timestamp        = datetime.now(),
        transaction_type = TransactionType.UPI,
        amount           = -500,        # ← negative amount!
        sender_account   = "ACC_AMIT",
        receiver_account = "ACC_PRIYA",
    )
except Exception as e:
    print(f"❌ Error caught: {e}")
    print("✅ Pydantic ne galat data reject kar diya!\n")

print("=== Test 3: Invalid Type ===")
try:
    invalid_txn2 = Transaction(
        transaction_id   = "TXN_003",
        timestamp        = datetime.now(),
        transaction_type = "BITCOIN",   # ← allowed nahi hai!
        amount           = 5000,
        sender_account   = "ACC_X",
        receiver_account = "ACC_Y",
    )
except Exception as e:
    print(f"❌ Error caught: BITCOIN is not a valid transaction type")
    print("✅ Pydantic ne unknown type reject kar diya!")