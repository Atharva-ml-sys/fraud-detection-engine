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

# ── SHAP Explainability ───────────────────────────────────────────
def explain_transaction(model, txn: dict, velocity: dict) -> dict:
    """
    SHAP se explain karo — kyun yeh transaction flag hua?
    
    Returns top 5 reasons with human-readable descriptions
    """
    import shap
    import numpy as np

    # Features banao
    features = build_features(txn, velocity)

    # SHAP TreeExplainer — XGBoost ke liye best
    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(features)

    # SHAP values — har feature ka contribution
    shap_vals = shap_values[0]  # first (only) sample

    # Feature contributions sort karo
    contributions = []
    for i, (name, val) in enumerate(zip(FEATURE_NAMES, shap_vals)):
        contributions.append({
            "feature":      name,
            "shap_value":   round(float(val), 4),
            "feature_value": round(float(features[0][i]), 4),
            "direction":    "increases_fraud" if val > 0 else "decreases_fraud",
        })

    # Sort by absolute SHAP value
    contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

    # Human readable descriptions
    descriptions = {
        "amount_log":      "Transaction amount",
        "amount_zscore":   "Amount vs account average",
        "hour_of_day":     "Time of transaction",
        "is_late_night":   "Late night transaction (11PM-5AM)",
        "txn_type_enc":    "Transaction type",
        "txn_count_1h":    "Number of transactions in last 1 hour",
        "amount_sum_1h":   "Total amount in last 1 hour",
        "new_receiver":    "First time sending to this receiver",
        "amount_round":    "Suspicious round amount",
        "geo_distance":    "Geographic distance from last transaction",
        "device_seen":     "Device recognition",
        "receiver_risk":   "Receiver fraud history",
    }

    # Top 5 reasons
    top_reasons = []
    for c in contributions[:5]:
        name  = c["feature"]
        val   = c["shap_value"]
        fval  = c["feature_value"]
        desc  = descriptions.get(name, name)

        # Human readable value
        if name == "geo_distance":
            readable = f"{fval:.0f} km"
        elif name == "txn_count_1h":
            readable = f"{fval:.0f} transactions"
        elif name == "amount_sum_1h":
            readable = f"₹{fval:,.0f}"
        elif name == "is_late_night":
            readable = "Yes" if fval == 1 else "No"
        elif name == "device_seen":
            readable = "Known" if fval == 1 else "Unknown device"
        elif name == "new_receiver":
            readable = "Yes (first time)" if fval == 1 else "No"
        elif name == "receiver_risk":
            readable = f"{fval*100:.0f}% fraud history"
        elif name == "amount_round":
            readable = "Yes (suspicious)" if fval == 1 else "No"
        else:
            readable = f"{fval:.2f}"

        top_reasons.append({
            "rank":        len(top_reasons) + 1,
            "feature":     name,
            "description": desc,
            "value":       readable,
            "impact":      round(val * 100, 2),
            "direction":   "🔴 Increases fraud risk" if val > 0 else "🟢 Decreases fraud risk",
        })

    return {
        "top_reasons":     top_reasons,
        "total_features":  len(FEATURE_NAMES),
        "explanation":     f"Top {len(top_reasons)} factors driving this decision",
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