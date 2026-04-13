# ml_engine/inference.py
#
# Inference = trained model se prediction karna
#
# Yeh file:
# 1. Saved model load karti hai
# 2. Transaction ka feature vector banati hai
# 3. XGBoost se risk score predict karti hai
# 4. Result return karti hai

import pickle
import numpy as np
import sys
import os

# Feature names — same order as training!
FEATURE_NAMES = [
    "amount_log",
    "amount_zscore",
    "hour_of_day",
    "is_late_night",
    "txn_type_enc",
    "txn_count_1h",
    "amount_sum_1h",
    "new_receiver",
    "amount_round",
    "geo_distance",
    "device_seen",
    "receiver_risk",
]

# ── Model Load karo ───────────────────────────────────────────────
def load_model():
    """
    Saved model load karo.
    Ek baar load karo — baar baar use karo!
    """
    model_path = os.path.join(
        os.path.dirname(__file__),
        "models/xgboost_fraud_v1.pkl"
    )

    with open(model_path, "rb") as f:
        model = pickle.load(f)

    print("✅ Model loaded!")
    return model

# ── Feature Engineering ───────────────────────────────────────────
def build_features(txn: dict, velocity: dict) -> np.ndarray:
    """
    Transaction + velocity data se feature vector banao.

    Yeh exactly wahi features hain jo training mein use kiye the!
    Order same hona chahiye — warna galat prediction aayega!
    """
    import math

    amount   = float(txn.get("amount", 0))
    avg_amt  = velocity.get("avg_amount", 10000)
    std_amt  = velocity.get("std_amount", 5000)

    # Amount features
    amount_log    = math.log1p(amount)
    amount_zscore = (amount - avg_amt) / max(std_amt, 1)

    # Time features
    from datetime import datetime
    try:
        ts = datetime.fromisoformat(
            txn.get("time", datetime.now().isoformat())
        )
        hour = ts.hour
    except Exception:
        hour = datetime.now().hour

    is_late_night = 1 if (hour >= 23 or hour <= 5) else 0

    # Transaction type encoding
    type_map = {
        "UPI": 1, "IMPS": 2, "NEFT": 3,
        "CARD_CREDIT": 4, "CARD_DEBIT": 4
    }
    txn_type_enc = type_map.get(txn.get("type", "UPI"), 1)

    # Velocity features
    txn_count_1h = float(velocity.get("txn_count_1h", 1))
    amount_sum_1h = float(velocity.get("amount_sum_1h", amount))

    # Risk features
    new_receiver = int(txn.get("new_receiver", 0))
    amount_round = 1 if amount % 10000 == 0 and amount >= 10000 else 0
    geo_distance = float(txn.get("geo_distance", 0))
    device_seen  = int(txn.get("device_seen", 1))
    receiver_risk= float(txn.get("receiver_risk", 0.01))

    features = [
        amount_log,
        amount_zscore,
        hour,
        is_late_night,
        txn_type_enc,
        txn_count_1h,
        amount_sum_1h,
        new_receiver,
        amount_round,
        geo_distance,
        device_seen,
        receiver_risk,
    ]

    return np.array(features).reshape(1, -1)

# ── Score karo ────────────────────────────────────────────────────
def score_transaction(model, txn: dict, velocity: dict) -> dict:
    """
    Ek transaction ko score karo.

    Returns:
        risk_score: 0-100
        risk_tier:  LOW/MEDIUM/HIGH/CRITICAL
        fraud_prob: 0.0-1.0 (raw probability)
    """
    # Features banao
    features = build_features(txn, velocity)

    # ML model se probability lo
    # predict_proba returns [P(normal), P(fraud)]
    fraud_prob = float(model.predict_proba(features)[0][1])

    # 0-1 probability → 0-100 score
    risk_score = round(fraud_prob * 100, 2)

    # Tier assign karo
    if risk_score < 30:   tier = "LOW"
    elif risk_score < 60: tier = "MEDIUM"
    elif risk_score < 86: tier = "HIGH"
    else:                 tier = "CRITICAL"

    return {
        "risk_score": risk_score,
        "risk_tier":  tier,
        "fraud_prob": round(fraud_prob, 4),
    }

# ── Test karo ─────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("   ML Inference Engine — Test")
    print("=" * 55)

    # Model load karo
    model = load_model()

    # Test transactions — different scenarios
    test_cases = [
        {
            "name": "Normal UPI payment",
            "txn": {
                "id":           "TEST_001",
                "amount":       5000,
                "type":         "UPI",
                "new_receiver": 0,
                "geo_distance": 5,
                "device_seen":  1,
                "receiver_risk":0.01,
            },
            "velocity": {
                "txn_count_1h": 2,
                "amount_sum_1h":8000,
                "avg_amount":   6000,
                "std_amount":   2000,
            }
        },
        {
            "name": "High velocity attack",
            "txn": {
                "id":           "TEST_002",
                "amount":       25000,
                "type":         "UPI",
                "new_receiver": 1,
                "geo_distance": 10,
                "device_seen":  1,
                "receiver_risk":0.05,
            },
            "velocity": {
                "txn_count_1h": 18,
                "amount_sum_1h":450000,
                "avg_amount":   6000,
                "std_amount":   2000,
            }
        },
        {
            "name": "Impossible travel",
            "txn": {
                "id":           "TEST_003",
                "amount":       150000,
                "type":         "NEFT",
                "new_receiver": 1,
                "geo_distance": 1400,
                "device_seen":  0,
                "receiver_risk":0.02,
            },
            "velocity": {
                "txn_count_1h": 3,
                "amount_sum_1h":150000,
                "avg_amount":   8000,
                "std_amount":   3000,
            }
        },
        {
            "name": "Suspicious receiver",
            "txn": {
                "id":           "TEST_004",
                "amount":       500000,
                "type":         "IMPS",
                "new_receiver": 1,
                "geo_distance": 200,
                "device_seen":  0,
                "receiver_risk":0.78,
            },
            "velocity": {
                "txn_count_1h": 5,
                "amount_sum_1h":500000,
                "avg_amount":   10000,
                "std_amount":   4000,
            }
        },
        {
            "name": "Round amount fraud",
            "txn": {
                "id":           "TEST_005",
                "amount":       100000,
                "type":         "UPI",
                "new_receiver": 1,
                "geo_distance": 50,
                "device_seen":  0,
                "receiver_risk":0.45,
            },
            "velocity": {
                "txn_count_1h": 8,
                "amount_sum_1h":300000,
                "avg_amount":   5000,
                "std_amount":   1500,
            }
        },
    ]

    # Icons
    icons = {
        "LOW":      "🟢",
        "MEDIUM":   "🟡",
        "HIGH":     "🟠",
        "CRITICAL": "🔴",
    }

    print(f"\n{'─'*55}")
    print(f"  {'Test Case':<25} {'Score':>6} {'Tier':<10} {'Prob':>6}")
    print(f"{'─'*55}")

    for case in test_cases:
        result = score_transaction(model, case["txn"], case["velocity"])
        icon   = icons[result["risk_tier"]]
        print(
            f"  {icon} {case['name']:<23} "
            f"{result['risk_score']:>5.1f}  "
            f"{result['risk_tier']:<10} "
            f"{result['fraud_prob']:>5.3f}"
        )

    print(f"{'─'*55}")
    print("\n✅ Inference engine working!")
    print("\nNext: Yeh model full_pipeline.py mein replace karega rules engine!")