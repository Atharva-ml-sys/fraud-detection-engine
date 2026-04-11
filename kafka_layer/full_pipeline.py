# kafka_layer/full_pipeline.py
#
# Yeh poora fraud detection pipeline hai — Kafka ke saath!
#
# Flow:
# Kafka (raw-transactions)
#   → Validate
#   → Redis velocity track
#   → Risk score
#   → PostgreSQL save
#   → Result print

import json
import sys
import time

sys.path.insert(0, "../database")
sys.path.insert(0, "../redis_layer")

from kafka import KafkaConsumer, KafkaProducer
from db_setup import create_tables, insert_transaction
from redis_setup import track_transaction, get_velocity, check_duplicate

# ── Config ────────────────────────────────────────────────────────
KAFKA_SERVER    = "localhost:9092"
TOPIC_RAW       = "raw-transactions"
TOPIC_SCORED    = "scored-transactions"
TOPIC_ALERTS    = "fraud-alerts"

# ── Kafka setup ───────────────────────────────────────────────────
def create_consumer():
    return KafkaConsumer(
        TOPIC_RAW,
        bootstrap_servers=KAFKA_SERVER,
        group_id="full-pipeline",
        auto_offset_reset="latest",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

def create_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_SERVER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
    )

# ── Step 1: Validation ────────────────────────────────────────────
def validate(txn: dict) -> tuple:
    if txn.get("amount", 0) <= 0:
        return False, "Invalid amount"
    if not txn.get("sender"):
        return False, "Missing sender"
    if txn.get("sender") == txn.get("receiver"):
        return False, "Sender = Receiver"
    return True, None

# ── Step 2: Risk Score ────────────────────────────────────────────
def calculate_risk(txn: dict, velocity: dict) -> tuple:
    score = 0

    # Amount based rules
    if txn["amount"] > 500000:
        score += 50
    elif txn["amount"] > 100000:
        score += 30
    elif txn["amount"] > 50000:
        score += 15

    # Velocity rules
    if velocity["txn_count_1h"] > 8:
        score += 35
    elif velocity["txn_count_1h"] > 5:
        score += 20

    # Amount sum rule
    if velocity["amount_sum_1h"] > 500000:
        score += 25
    elif velocity["amount_sum_1h"] > 200000:
        score += 15

    # Round amount
    if txn["amount"] % 10000 == 0:
        score += 10

    # Tier
    score = min(score, 100)
    if score < 30:   tier = "LOW"
    elif score < 60: tier = "MEDIUM"
    elif score < 86: tier = "HIGH"
    else:            tier = "CRITICAL"

    return score, tier

# ── Step 3: Process ───────────────────────────────────────────────
def process(txn: dict, producer) -> dict:
    result = {
        "id":         txn.get("id", "unknown"),
        "amount":     txn.get("amount", 0),
        "type":       txn.get("type", "unknown"),
        "status":     None,
        "risk_score": None,
        "risk_tier":  None,
    }

    # Duplicate check
    if check_duplicate(txn["id"]):
        result["status"] = "DUPLICATE"
        return result

    # Validate
    is_valid, error = validate(txn)
    if not is_valid:
        result["status"] = f"INVALID: {error}"
        return result

    # Redis velocity
    track_transaction(txn["sender"], txn["amount"])
    velocity = get_velocity(txn["sender"])

    # Risk score
    score, tier = calculate_risk(txn, velocity)
    result["risk_score"] = score
    result["risk_tier"]  = tier
    result["status"]     = "PROCESSED"

    # DB save
    txn["risk_score"] = score
    txn["risk_tier"]  = tier
    insert_transaction(txn)

    # Scored topic pe bhejo
    producer.send(TOPIC_SCORED, key=txn["id"], value=txn)

    # Alert topic — HIGH/CRITICAL
    if tier in ["HIGH", "CRITICAL"]:
        producer.send(TOPIC_ALERTS, key=txn["id"], value=txn)

    return result

# ── Main ──────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("   FULL FRAUD DETECTION PIPELINE — Kafka Edition")
    print("=" * 65)

    create_tables()

    consumer = create_consumer()
    producer = create_producer()

    print(f"\n👂 Listening on: {TOPIC_RAW}")
    print("📤 Outputting to: scored-transactions, fraud-alerts")
    print("🗄️  Saving to: PostgreSQL")
    print("⚡ Tracking in: Redis")
    print("\nPress Ctrl+C to stop\n")
    print("-" * 65)

    # Icons
    icons = {
        "LOW":      "🟢",
        "MEDIUM":   "🟡",
        "HIGH":     "🟠",
        "CRITICAL": "🔴",
    }
    counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0,
              "INVALID": 0, "DUPLICATE": 0}
    total = 0

    try:
        for message in consumer:
            txn    = message.value
            result = process(txn, producer)
            total += 1

            if result["status"] == "PROCESSED":
                tier = result["risk_tier"]
                counts[tier] += 1
                icon = icons[tier]
                print(
                    f"{icon} #{total:>3} | "
                    f"{result['id'][:12]} | "
                    f"₹{result['amount']:>9,.0f} | "
                    f"{result['type']:<12} | "
                    f"Score: {result['risk_score']:>3} | "
                    f"{tier}"
                )
            else:
                counts[result["status"]] = counts.get(result["status"], 0) + 1
                print(f"❌ #{total:>3} | {result['id'][:12]} | "
                      f"{result['status']}")

            # Har 10 transactions pe summary
            if total % 10 == 0:
                print(f"\n  📊 Stats: "
                      f"🟢{counts['LOW']} "
                      f"🟡{counts['MEDIUM']} "
                      f"🟠{counts['HIGH']} "
                      f"🔴{counts['CRITICAL']} "
                      f"| Total: {total}\n")

    except KeyboardInterrupt:
        print(f"\n\n{'=' * 65}")
        print("📊 FINAL SUMMARY")
        print(f"{'=' * 65}")
        print(f"  🟢 LOW:       {counts['LOW']}")
        print(f"  🟡 MEDIUM:    {counts['MEDIUM']}")
        print(f"  🟠 HIGH:      {counts['HIGH']}")
        print(f"  🔴 CRITICAL:  {counts['CRITICAL']}")
        print(f"  ❌ Invalid:   {counts.get('INVALID', 0)}")
        print(f"  🔄 Duplicate: {counts.get('DUPLICATE', 0)}")
        print(f"\n  Total processed: {total}")
        print("✅ Pipeline stopped cleanly!")

    consumer.close()
    producer.close()

if __name__ == "__main__":
    main()