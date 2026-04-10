# redis_layer/redis_setup.py
#
# Redis se connect karo aur velocity features
# compute karo — last 1 hour mein kitni transactions?
#
# Velocity features fraud detection mein bahut important hain:
# "Ek account ne last 1 hour mein 15 transactions ki" = suspicious!

import redis
import time

# Redis connection
r = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True  # bytes ki jagah string return karo
)

def test_connection():
    """Redis connected hai?"""
    r.ping()
    print("✅ Redis connected!")

def track_transaction(sender: str, amount: float):
    """
    Har transaction ke liye Redis counters update karo.
    
    Keys jo store karenge:
    - vel:{sender}:count  → kitni transactions last 1hr mein
    - vel:{sender}:amount → total amount last 1hr mein
    """
    # Current hour ka bucket
    import datetime
    hour_bucket = datetime.datetime.now().strftime("%Y%m%d%H")

    count_key  = f"vel:{sender}:count:{hour_bucket}"
    amount_key = f"vel:{sender}:amount:{hour_bucket}"

    # INCR = increment by 1 (atomic operation)
    new_count = r.incr(count_key)

    # Amount add karo
    r.incrbyfloat(amount_key, amount)

    # 2 ghante baad automatically delete ho jaaye
    r.expire(count_key,  7200)
    r.expire(amount_key, 7200)

    return new_count

def get_velocity(sender: str) -> dict:
    """Last 1 hour mein sender ki velocity fetch karo"""
    import datetime
    hour_bucket = datetime.datetime.now().strftime("%Y%m%d%H")

    count_key  = f"vel:{sender}:count:{hour_bucket}"
    amount_key = f"vel:{sender}:amount:{hour_bucket}"

    count  = int(r.get(count_key)  or 0)
    amount = float(r.get(amount_key) or 0)

    return {
        "sender":       sender,
        "txn_count_1h": count,
        "amount_sum_1h": amount,
        "is_suspicious": count > 5 or amount > 100000
    }

def check_duplicate(transaction_id: str) -> bool:
    """
    Duplicate transaction check karo.
    Agar same TXN_ID 5 minute mein dobara aaye = replay attack!
    """
    key = f"txn:seen:{transaction_id}"

    # SET NX = sirf tab set karo jab key exist na kare
    is_new = r.set(key, "1", nx=True, ex=300)  # 5 min expiry
    return not is_new  # True = duplicate hai

# ── Main: sab test karo ───────────────────────────────────────────
if __name__ == "__main__":

    print("=== Redis Velocity Tracking ===\n")
    test_connection()

    # Simulate karo: ACC_RAHUL ne 7 transactions ki last 1 hour mein
    print("\n📡 ACC_RAHUL ki transactions track kar rahe hain...")
    sender = "ACC_RAHUL"
    amounts = [15000, 25000, 8000, 50000, 12000, 75000, 30000]

    for i, amount in enumerate(amounts, 1):
        count = track_transaction(sender, amount)
        print(f"  Transaction {i}: ₹{amount:,} → Total count this hour: {count}")

    # Velocity check karo
    print("\n📊 Velocity check:")
    velocity = get_velocity(sender)
    print(f"  Sender:          {velocity['sender']}")
    print(f"  Transactions 1h: {velocity['txn_count_1h']}")
    print(f"  Total amount 1h: ₹{velocity['amount_sum_1h']:,.0f}")
    print(f"  Suspicious:      {'🚨 YES' if velocity['is_suspicious'] else '✅ NO'}")

    # Normal account test karo
    print("\n📊 Normal account check:")
    track_transaction("ACC_PRIYA", 5000)
    normal = get_velocity("ACC_PRIYA")
    print(f"  Sender:          {normal['sender']}")
    print(f"  Transactions 1h: {normal['txn_count_1h']}")
    print(f"  Suspicious:      {'🚨 YES' if normal['is_suspicious'] else '✅ NO'}")

    # Duplicate check test karo
    print("\n🔍 Duplicate transaction check:")
    txn_id = "TXN_TEST_999"

    result1 = check_duplicate(txn_id)
    print(f"  First time:  duplicate = {result1}  → {'❌ REJECT' if result1 else '✅ ALLOW'}")

    result2 = check_duplicate(txn_id)
    print(f"  Second time: duplicate = {result2}  → {'❌ REJECT' if result2 else '✅ ALLOW'}")

    print("\n✅ Redis velocity tracking working perfectly!")