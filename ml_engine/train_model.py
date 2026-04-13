# ml_engine/train_model.py
#
# XGBoost fraud detection model train karo
#
# Steps:
# 1. Synthetic training data generate karo
# 2. Features engineer karo
# 3. XGBoost train karo
# 4. Model evaluate karo
# 5. Model save karo (pickle file)

import numpy as np
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score,
    classification_report,
    confusion_matrix
)
from xgboost import XGBClassifier

# ── Feature names — same order hamesha! ──────────────────────────
# Yeh 12 features har transaction ke liye compute honge
FEATURE_NAMES = [
    "amount_log",        # log(amount) — skewness reduce karta hai
    "amount_zscore",     # normal se kitna alag hai
    "hour_of_day",       # 0-23
    "is_late_night",     # 1 if 11PM-5AM
    "txn_type_enc",      # UPI=1, IMPS=2, NEFT=3, CARD=4
    "txn_count_1h",      # last 1h mein kitni transactions
    "amount_sum_1h",     # last 1h mein total amount
    "new_receiver",      # 1 if kabhi nahi bheja is receiver ko
    "amount_round",      # 1 if round number (10000, 50000)
    "geo_distance",      # last location se distance
    "device_seen",       # 1 if device pehle dekha hua
    "receiver_risk",     # receiver ka historical fraud rate
]

# ── Step 1: Training Data Generate karo ──────────────────────────
def generate_training_data(n_samples=5000):
    """
    Synthetic training data generate karo.
    
    Real project mein:
    → Kaggle IEEE-CIS Fraud dataset use karo
    → Link: kaggle.com/c/ieee-fraud-detection
    
    Abhi ke liye: fraud patterns manually define karo
    """
    np.random.seed(42)
    X = []
    y = []

    for _ in range(n_samples):
        # ── Normal transaction base ───────────────────────────────
        features = {
            "amount_log":    np.random.normal(8.5, 2.0),
            "amount_zscore": np.random.normal(0, 1),
            "hour_of_day":   np.random.randint(8, 22),
            "is_late_night": 0,
            "txn_type_enc":  np.random.choice([1, 2, 3, 4]),
            "txn_count_1h":  np.random.uniform(1, 4),
            "amount_sum_1h": np.random.uniform(1000, 30000),
            "new_receiver":  np.random.choice([0, 0, 0, 1]),
            "amount_round":  0,
            "geo_distance":  np.random.uniform(0, 30),
            "device_seen":   1,
            "receiver_risk": np.random.uniform(0, 0.05),
        }
        label = 0  # Normal

        # ── 10% fraud — patterns inject karo ─────────────────────
        if np.random.random() < 0.10:
            fraud_type = np.random.choice([
                "high_velocity",
                "impossible_travel",
                "large_amount",
                "new_device",
                "suspicious_receiver",
            ])

            if fraud_type == "high_velocity":
                features["txn_count_1h"]  = np.random.uniform(15, 40)
                features["amount_sum_1h"] = np.random.uniform(300000, 1000000)

            elif fraud_type == "impossible_travel":
                features["geo_distance"]  = np.random.uniform(800, 3000)
                features["is_late_night"] = 1

            elif fraud_type == "large_amount":
                features["amount_log"]    = np.random.uniform(12, 15)
                features["amount_zscore"] = np.random.uniform(4, 10)
                features["amount_round"]  = 1

            elif fraud_type == "new_device":
                features["device_seen"]   = 0
                features["new_receiver"]  = 1
                features["geo_distance"]  = np.random.uniform(100, 500)

            elif fraud_type == "suspicious_receiver":
                features["receiver_risk"] = np.random.uniform(0.3, 0.9)
                features["new_receiver"]  = 1

            label = 1

        X.append([features[k] for k in FEATURE_NAMES])
        y.append(label)

    return np.array(X), np.array(y)

# ── Step 2: Model Train karo ──────────────────────────────────────
def train_model():
    print("=" * 55)
    print("   XGBoost Fraud Detection Model Training")
    print("=" * 55)

    # Data generate karo
    print("\n📊 Generating training data (5000 samples)...")
    X, y = generate_training_data(5000)

    fraud_count  = y.sum()
    normal_count = len(y) - fraud_count
    print(f"  Total samples:  {len(y)}")
    print(f"  Normal (0):     {normal_count} ({normal_count/len(y)*100:.1f}%)")
    print(f"  Fraud  (1):     {fraud_count}  ({fraud_count/len(y)*100:.1f}%)")

    # Train/test split
    print("\n✂️  Splitting: 80% train, 20% test...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y         # fraud ratio same rakho dono mein
    )
    print(f"  Train: {len(X_train)} samples")
    print(f"  Test:  {len(X_test)} samples")

    # XGBoost model
    print("\n🤖 Training XGBoost model...")
    model = XGBClassifier(
        n_estimators=200,      # 200 trees
        max_depth=6,           # har tree kitna deep
        learning_rate=0.1,     # har step kitna bada
        scale_pos_weight=9,    # fraud class ko 9x weight
                               # (90:10 imbalance handle karo)
        use_label_encoder=False,
        eval_metric="auc",
        random_state=42,
        verbosity=0,
    )

    model.fit(X_train, y_train)
    print("  ✅ Training complete!")

    # ── Step 3: Evaluate karo ────────────────────────────────────
    print("\n📈 Evaluating model...")
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred       = (y_pred_proba > 0.5).astype(int)

    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"\n  AUC-ROC Score: {auc:.4f}")

    if auc >= 0.95:
        print("  🔥 Excellent model!")
    elif auc >= 0.90:
        print("  ✅ Good model!")
    else:
        print("  ⚠️  Model needs improvement")

    print("\n  Classification Report:")
    print(classification_report(
        y_test, y_pred,
        target_names=["Normal", "Fraud"]
    ))

    # Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    print(f"  Confusion Matrix:")
    print(f"  ┌─────────────┬──────────┬──────────┐")
    print(f"  │             │ Pred: 0  │ Pred: 1  │")
    print(f"  ├─────────────┼──────────┼──────────┤")
    print(f"  │ Actual: 0   │ TN={cm[0][0]:>4}  │ FP={cm[0][1]:>4}  │")
    print(f"  │ Actual: 1   │ FN={cm[1][0]:>4}  │ TP={cm[1][1]:>4}  │")
    print(f"  └─────────────┴──────────┴──────────┘")
    print(f"\n  TN = True Negative  (normal, correctly approved)")
    print(f"  FP = False Positive (normal, wrongly flagged)")
    print(f"  FN = False Negative (fraud, missed!)")
    print(f"  TP = True Positive  (fraud, correctly caught)")

    # Feature Importance
    print("\n🎯 Top 5 Most Important Features:")
    importances = model.feature_importances_
    feat_imp = sorted(
        zip(FEATURE_NAMES, importances),
        key=lambda x: x[1],
        reverse=True
    )[:5]
    for i, (name, imp) in enumerate(feat_imp, 1):
        bar = "█" * int(imp * 100)
        print(f"  {i}. {name:<20} {bar} {imp:.4f}")

    # ── Step 4: Model save karo ───────────────────────────────────
    os.makedirs("models", exist_ok=True)
    model_path = "models/xgboost_fraud_v1.pkl"

    with open(model_path, "wb") as f:
        pickle.dump(model, f)

    # Feature names bhi save karo
    with open("models/feature_names.pkl", "wb") as f:
        pickle.dump(FEATURE_NAMES, f)

    print(f"\n💾 Model saved: {model_path}")
    print(f"💾 Features saved: models/feature_names.pkl")
    print("\n✅ Training complete! Model ready for inference.")

    return model

if __name__ == "__main__":
    train_model()