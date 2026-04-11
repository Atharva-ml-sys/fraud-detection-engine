# kafka_layer/kafka_producer.py
#
# Producer = transaction generator jo Kafka topic pe
# messages bhejta hai
#
# Topic = "raw-transactions"
# Yahan sab incoming transactions aate hain

import json
import sys
import time

sys.path.insert(0, "../simulator")
from transaction_generator import make_transaction, make_fraud_transaction

from kafka import KafkaProducer
import random

def create_producer():
    """Kafka producer banao"""
    producer = KafkaProducer(
        bootstrap_servers="localhost:9092",
        # Dict ko JSON string mein convert karo
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
    )
    print("✅ Kafka Producer connected!")
    return producer

def send_transaction(producer, txn: dict):
    """Ek transaction Kafka topic pe bhejo"""
    producer.send(
        topic="raw-transactions",      # topic naam
        key=txn["sender"],             # same sender = same partition
        value=txn                      # transaction data
    )

def main():
    print("=== Kafka Producer Starting ===\n")
    producer = create_producer()

    print("📡 Sending 10 transactions to Kafka...\n")

    for i in range(10):
        # 20% fraud chance
        if random.random() < 0.20:
            txn = make_fraud_transaction()
            label = "🚨 FRAUD "
        else:
            txn = make_transaction()
            label = "✅ NORMAL"

        send_transaction(producer, txn)
        print(f"{label} | Sent: {txn['id']} | "
              f"₹{txn['amount']:>9,.0f} | {txn['type']}")

        time.sleep(0.5)  # 0.5 second wait

    # Sab messages bhej do
    producer.flush()
    producer.close()
    print("\n✅ All transactions sent to Kafka!")

if __name__ == "__main__":
    main()