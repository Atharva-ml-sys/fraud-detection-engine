# If/Else — condition check karna
# Fraud detection ka basic logic yehi hai

transactions = [
    {"id": "TXN_001", "amount": 15000,  "type": "UPI",  "sender": "Atharva"},
    {"id": "TXN_002", "amount": 250000, "type": "NEFT", "sender": "Rahul"},
    {"id": "TXN_003", "amount": 800,    "type": "UPI",  "sender": "Priya"},
    {"id": "TXN_004", "amount": 500000, "type": "IMPS", "sender": "Rahul"},
]

# Function — reusable code block
# Ek baar likho, baar baar use karo
def check_fraud(txn):
    # Rule 1: Amount bahut zyada hai?
    if txn["amount"] > 100000:
        return "🚨 FRAUD - Amount too high"
    
    # Rule 2: IMPS se bada amount?
    elif txn["type"] == "IMPS" and txn["amount"] > 50000:
        return "⚠️  SUSPICIOUS - Large IMPS"
    
    # Rule 3: Normal transaction
    else:
        return "✅ LEGITIMATE"

# Har transaction check karo
print("=== Fraud Detection Results ===\n")
for txn in transactions:
    result = check_fraud(txn)
    print(f"ID: {txn['id']} | ₹{txn['amount']:,} | {txn['type']} → {result}")