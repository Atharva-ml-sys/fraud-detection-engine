# kafka_layer/ml_pipeline.py
#
# Yeh full_pipeline.py ka ML-powered version hai!
#
# Fark:
# full_pipeline.py  → rules se score (if amount > 100000)
# ml_pipeline.py    → XGBoost ML model se score
#
# Flow:
# Kafka (raw-transactions)
#   → Validate
#   → Redis velocity
#   → ML inference (XGBoost!)
#   → PostgreSQL save
#   → scored-transactions topic

import json
import sys
import os

# Paths set karo
sys.path.insert(0, "../database")
sys.path.insert(0, "../redis_layer")
sys.path.insert(0, "../ml_engine")

from kafka import KafkaConsumer, KafkaProducer
from db_setup    import create_tables, insert_transaction
from redis_setup import track_transaction, get_velocity, check_duplicate
from inference   import load_model, score_transaction

# ── Config ────────────────────────────────────────────────────────
KAFKA_SERVER  = "localhost:9092"
TOPIC_RAW     = "raw-transactions"
TOPIC_SCORED  = "scored-transactions"
TOPIC_ALERTS  = "fraud-alerts"

# ── Kafka setup ───────────────────────────────────────────────────
def create_consumer():
    return KafkaConsumer(
        TOPIC_RAW,
        bootstrap_servers=KAFKA_SERVER,
        group_id="ml-pipeline",
        auto_offset_reset="latest",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

def create_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_SERVER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
    )

# ── Validation ────────────────────────────────────────────────────
def validate(txn: dict) -> tuple:
    if txn.get("amount", 0) <= 0:
        return False, "Invalid amount"
    if not txn.get("sender"):
        return False, "Missing sender"
    if txn.get("sender") == txn.get("receiver"):
        return False, "Sender = Receiver"
    return True, None

# ── Process ───────────────────────────────────────────────────────
def process(txn: dict, model, producer) -> dict:
    result = {
        "id":         txn.get("id", "unknown"),
        "amount":     txn.get("amount", 0),
        "type":       txn.get("type", "unknown"),
        "status":     None,
        "risk_score": None,
        "risk_tier":  None,
        "fraud_prob": None,
    }

    # Step 1: Duplicate check
    if check_duplicate(txn["id"]):
        result["status"] = "DUPLICATE"
        return result

    # Step 2: Validate
    is_valid, error = validate(txn)
    if not is_valid:
        result["status"] = f"INVALID: {error}"
        return result

    # Step 3: Redis velocity track + fetch
    track_transaction(txn["sender"], txn["amount"])
    vel = get_velocity(txn["sender"])

    # Step 4: ML Score — yeh nayi cheez hai!
    # Velocity data ML features mein pass karo
    velocity_for_ml = {
        "txn_count_1h":  vel["txn_count_1h"],
        "amount_sum_1h": vel["amount_sum_1h"],
        "avg_amount":    10000,   # default — baad mein DB se lena
        "std_amount":    5000,
    }

    # Transaction mein extra features add karo
    txn_for_ml = {
        **txn,
        "new_receiver":  0,   # simplified — baad mein Redis se
        "geo_distance":  0,   # simplified — baad mein location se
        "device_seen":   1,   # simplified — baad mein device history
        "receiver_risk": 0.01,# simplified — baad mein DB se
    }

    # ML model se score lo!
    ml_result = score_transaction(model, txn_for_ml, velocity_for_ml)

    result["risk_score"] = ml_result["risk_score"]
    result["risk_tier"]  = ml_result["risk_tier"]
    result["fraud_prob"] = ml_result["fraud_prob"]
    result["status"]     = "PROCESSED"

    # Step 5: DB save
    txn["risk_score"] = ml_result["risk_score"]
    txn["risk_tier"]  = ml_result["risk_tier"]
    insert_transaction(txn)

    # Step 6: Scored topic pe bhejo
    producer.send(TOPIC_SCORED, key=txn["id"], value=txn)

    # Step 7: Alert — HIGH/CRITICAL ke liye
    if ml_result["risk_tier"] in ["HIGH", "CRITICAL"]:
        producer.send(TOPIC_ALERTS, key=txn["id"], value=txn)

    return result

# ── Main ──────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("   ML-POWERED FRAUD DETECTION PIPELINE")
    print("   Rules Engine → XGBoost ML Model")
    print("=" * 60)

    # DB ready karo
    create_tables()

    # ML Model load karo — ek baar!
    print("\n🤖 Loading ML model...")
    model = load_model()

    # Kafka setup
    consumer = create_consumer()
    producer = create_producer()

    print(f"👂 Listening: {TOPIC_RAW}")
    print(f"🤖 Scoring:   XGBoost ML Model")
    print(f"🗄️  Saving:    PostgreSQL")
    print(f"⚡ Tracking:  Redis")
    print("\nPress Ctrl+C to stop\n")
    print("-" * 60)

    icons = {
        "LOW":      "🟢",
        "MEDIUM":   "🟡",
        "HIGH":     "🟠",
        "CRITICAL": "🔴",
    }
    counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    total  = 0

    try:
        for message in consumer:
            txn    = message.value
            result = process(txn, model, producer)
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
                    f"ML Score: {result['risk_score']:>5.1f} | "
                    f"Prob: {result['fraud_prob']:.3f} | "
                    f"{tier}"
                )
            else:
                print(f"❌ #{total:>3} | {result['id'][:12]} | "
                      f"{result['status']}")

            # Har 10 pe summary
            if total % 10 == 0:
                print(f"\n  🤖 ML Stats: "
                      f"🟢{counts['LOW']} "
                      f"🟡{counts['MEDIUM']} "
                      f"🟠{counts['HIGH']} "
                      f"🔴{counts['CRITICAL']} "
                      f"| Total: {total}\n")

    except KeyboardInterrupt:
        print(f"\n{'=' * 60}")
        print("📊 FINAL ML PIPELINE SUMMARY")
        print(f"{'=' * 60}")
        print(f"  🟢 LOW:      {counts['LOW']}")
        print(f"  🟡 MEDIUM:   {counts['MEDIUM']}")
        print(f"  🟠 HIGH:     {counts['HIGH']}")
        print(f"  🔴 CRITICAL: {counts['CRITICAL']}")
        print(f"\n  Total: {total}")
        print("✅ ML Pipeline stopped!")

    consumer.close()
    producer.close()

if __name__ == "__main__":
    main()