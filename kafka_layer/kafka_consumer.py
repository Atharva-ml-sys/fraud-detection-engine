# kafka_layer/kafka_consumer.py
#
# Consumer = jo Kafka topic pe messages SUNTA hai
# aur process karta hai
#
# Yeh validator ka role karega — transactions
# "raw-transactions" topic se padhega

import json
import sys

from kafka import KafkaConsumer

def create_consumer():
    """Kafka consumer banao"""
    consumer = KafkaConsumer(
        "raw-transactions",            # is topic ko suno
        bootstrap_servers="localhost:9092",
        group_id="fraud-validator",    # consumer group naam
        auto_offset_reset="earliest",  # pehle se saved messages bhi padho
        # JSON bytes ko dict mein convert karo
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )
    print("✅ Kafka Consumer connected!")
    return consumer

def process_message(txn: dict) -> str:
    """
    Transaction process karo — basic validation
    Returns: status string
    """
    # Basic fraud check
    if txn["amount"] > 100000:
        return "🚨 HIGH RISK"
    elif txn["amount"] > 50000:
        return "⚠️  MEDIUM RISK"
    else:
        return "✅ LOW RISK"

def main():
    print("=== Kafka Consumer Starting ===")
    print("👂 Listening on topic: raw-transactions")
    print("Press Ctrl+C to stop\n")

    consumer = create_consumer()
    count = 0

    # Messages continuously suno
    for message in consumer:
        txn    = message.value
        status = process_message(txn)
        count += 1

        print(
            f"#{count:>3} | {status} | "
            f"{txn['id']} | "
            f"₹{txn['amount']:>9,.0f} | "
            f"{txn['type']:<12} | "
            f"{txn.get('city', 'N/A')}"
        )

        # 10 messages ke baad band karo
        if count >= 10:
            print(f"\n✅ Processed {count} messages!")
            break

    consumer.close()

if __name__ == "__main__":
    main()