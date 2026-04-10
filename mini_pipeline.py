# mini_pipeline.py
#
# Yeh Week 2 ka final piece hai —
# sab kuch ek saath jodta hai:
#
# Simulator → Validation → Redis → PostgreSQL
#
# Yahi logic aage Kafka ke saath production
# mein chalega — bas zyada powerful hoga!

import sys
import random
import uuid
from datetime import datetime

# Apni files import karo
sys.path.insert(0, "./simulator")
sys.path.insert(0, "./shared")
sys.path.insert(0, "./database")
sys.path.insert(0, "./redis_layer")

from transaction_generator import make_transaction, make_fraud_transaction
from db_setup   import create_tables, insert_transaction, get_all_transactions
from redis_setup import track_transaction, get_velocity, check_duplicate

# ── Step 1: Validation ────────────────────────────────────────────
def validate(txn: dict) -> tuple:
    """
    Basic validation — VAL-001 to VAL-003
    Returns: (is_valid, error_message)
    """
    # VAL-001: Amount positive hona chahiye
    if txn["amount"] <= 0:
        return False, "Amount must be > 0"

    # VAL-002: Amount limit
    if txn["amount"] > 10_000_000:
        return False, "Amount exceeds limit"

    # VAL-003: Sender aur receiver alag hone chahiye
    if txn["sender"] == txn["receiver"]:
        return False, "Sender and receiver cannot be same"

    return True, None

# ── Step 2: Simple Risk Score ─────────────────────────────────────
def calculate_risk(txn: dict, velocity: dict) -> tuple:
    """
    Simple rule-based risk score — ML model se pehle ka version
    Aage XGBoost yeh replace karega!

    Returns: (score, tier)
    """
    score = 0

    # Rule 1: High amount
    if txn["amount"] > 100000:
        score += 40

    # Rule 2: High velocity — bahut saari transactions
    if velocity["txn_count_1h"] > 5:
        score += 30

    # Rule 3: High total amount this hour
    if velocity["amount_sum_1h"] > 200000:
        score += 20

    # Rule 4: Round amount — suspicious pattern
    if txn["amount"] % 10000 == 0:
        score += 10

    # Tier assign karo
    if score < 30:
        tier = "LOW"
    elif score < 60:
        tier = "MEDIUM"
    elif score < 86:
        tier = "HIGH"
    else:
        tier = "CRITICAL"

    return score, tier

# ── Main Pipeline ─────────────────────────────────────────────────
def process_transaction(txn: dict) -> dict:
    """
    Ek transaction ko poori pipeline se guzaaro
    """
    result = {
        "id":     txn["id"],
        "amount": txn["amount"],
        "type":   txn["type"],
        "status": None,
        "risk_score": None,
        "risk_tier":  None,
    }

    # ── STEP 1: Duplicate check ───────────────────────────────────
    if check_duplicate(txn["id"]):
        result["status"] = "REJECTED_DUPLICATE"
        return result

    # ── STEP 2: Validate ──────────────────────────────────────────
    is_valid, error = validate(txn)
    if not is_valid:
        result["status"] = f"REJECTED: {error}"
        return result

    # ── STEP 3: Redis velocity track karo ────────────────────────
    track_transaction(txn["sender"], txn["amount"])
    velocity = get_velocity(txn["sender"])

    # ── STEP 4: Risk score calculate karo ────────────────────────
    score, tier = calculate_risk(txn, velocity)
    result["risk_score"] = score
    result["risk_tier"]  = tier

    # ── STEP 5: PostgreSQL mein save karo ────────────────────────
    txn["risk_score"] = score
    txn["risk_tier"]  = tier
    insert_transaction(txn)
    result["status"] = "PROCESSED"

    return result

# ── Run karo ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("   MINI FRAUD DETECTION PIPELINE")
    print("=" * 60)

    # DB table ready karo
    create_tables()

    # 10 transactions generate karo — kuch fraud, kuch normal
    transactions = []
    for i in range(8):
        transactions.append(make_transaction())
    for i in range(2):
        transactions.append(make_fraud_transaction())

    # Shuffle karo — mixed order mein aayein
    random.shuffle(transactions)

    print(f"\n🚀 Processing {len(transactions)} transactions...\n")

    # Tier colors for display
    tier_icons = {
        "LOW":      "🟢",
        "MEDIUM":   "🟡",
        "HIGH":     "🟠",
        "CRITICAL": "🔴",
    }

    results = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}

    for txn in transactions:
        result = process_transaction(txn)

        if result["status"] == "PROCESSED":
            icon = tier_icons.get(result["risk_tier"], "⚪")
            results[result["risk_tier"]] += 1
            print(
                f"{icon} {result['id'][:12]} | "
                f"₹{result['amount']:>9,.0f} | "
                f"{result['type']:<12} | "
                f"Score: {result['risk_score']:>3} | "
                f"{result['risk_tier']}"
            )
        else:
            print(f"❌ {result['id'][:12]} | {result['status']}")

    # Summary
    print("\n" + "=" * 60)
    print("📊 PIPELINE SUMMARY")
    print("=" * 60)
    print(f"  🟢 LOW:      {results['LOW']} transactions")
    print(f"  🟡 MEDIUM:   {results['MEDIUM']} transactions")
    print(f"  🟠 HIGH:     {results['HIGH']} transactions")
    print(f"  🔴 CRITICAL: {results['CRITICAL']} transactions")
    print(f"\n  Total processed: {sum(results.values())}")
    print("\n✅ Mini pipeline complete!")