# simulator/transaction_generator.py
#
# Yeh script automatically fake transactions generate karti hai
# random library use karke — har baar alag alag values aayengi
#
# random library Python mein already hai — install karne ki
# zaroorat nahi

import json
import random  # random numbers ke liye
import uuid    # unique IDs generate karne ke liye
from datetime import datetime  # current time ke liye

# ── Static data — in mein se randomly choose karega ──────────────
ACCOUNTS = [
    "ACC_ATHARVA_001",
    "ACC_RAHUL_002", 
    "ACC_PRIYA_003",
    "ACC_AMIT_004",
    "ACC_SNEHA_005",
]

TRANSACTION_TYPES = ["UPI", "IMPS", "NEFT", "CARD_CREDIT", "CARD_DEBIT"]

CITIES = ["Mumbai", "Pune", "Delhi", "Bangalore", "Chennai"]

# ── Function: ek normal transaction banao ─────────────────────────
def make_transaction():
    # Sender aur receiver alag hone chahiye
    sender   = random.choice(ACCOUNTS)
    receiver = random.choice([a for a in ACCOUNTS if a != sender])

    transaction = {
        "id":       f"TXN_{uuid.uuid4().hex[:8].upper()}",
        "time":     datetime.now().strftime("%H:%M:%S"),
        "type":     random.choice(TRANSACTION_TYPES),
        "amount":   round(random.uniform(100, 50000), 2),
        "sender":   sender,
        "receiver": receiver,
        "city":     random.choice(CITIES),
    }
    return transaction

# ── Function: ek fraud transaction banao ─────────────────────────
def make_fraud_transaction():
    txn = make_transaction()
    
    # Fraud pattern — amount bahut zyada karo
    txn["amount"]     = round(random.uniform(200000, 1000000), 2)
    txn["is_fraud"]   = True
    return txn

# ── Main: 10 transactions generate karo ──────────────────────────
print("=== Transaction Generator Started ===\n")

for i in range(10):
    # 20% chance of fraud
    if random.random() < 0.20:
        txn = make_fraud_transaction()
        label = "🚨 FRAUD"
    else:
        txn = make_transaction()
        label = "✅ NORMAL"

    print(f"{label} | {txn['id']} | {txn['type']} | "
          f"₹{txn['amount']:>10,.0f} | "
          f"{txn['sender'][:15]} → {txn['receiver'][:15]} | "
          f"{txn['city']}")
# ── JSON format mein print karo ───────────────────────────────────
print("\n=== Same transaction JSON format mein ===\n")
ek_transaction = make_transaction()
print(json.dumps(ek_transaction, indent=2))