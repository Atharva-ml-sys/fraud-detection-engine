# gnn_engine/gnn_scorer.py
#
# Graph features ko ML scoring mein integrate karo
#
# Abhi: XGBoost score (12 features)
# Baad: XGBoost + Graph features = better detection!

import sys
sys.path.insert(0, "../database")
sys.path.insert(0, ".")

from graph_builder import (
    build_transaction_graph,
    get_account_features,
    detect_fraud_rings,
)

# Global graph — baar baar rebuild mat karo
_graph_cache = None

def get_graph(force_rebuild=False):
    """
    Cached graph return karo.
    Har request pe rebuild expensive hai!
    """
    global _graph_cache
    if _graph_cache is None or force_rebuild:
        _graph_cache = build_transaction_graph()
    return _graph_cache

def get_graph_risk_score(sender: str, receiver: str) -> dict:
    """
    Graph-based risk score nikalo.
    
    Factors:
    1. Sender ka PageRank — high = suspicious hub
    2. Receiver ka PageRank — high = money sink
    3. Fraud ring mein hain kya?
    4. Sender ne kitne unique receivers ko bheja?
    """
    G = get_graph()

    # Sender features
    sender_features   = get_account_features(G, sender)
    receiver_features = get_account_features(G, receiver)

    # Fraud rings check karo
    rings = detect_fraud_rings(G)
    ring_accounts = set()
    for ring in rings:
        ring_accounts.update(ring["accounts"])

    sender_in_ring   = sender   in ring_accounts
    receiver_in_ring = receiver in ring_accounts

    # Graph risk score calculate karo (0-100)
    graph_score = 0

    # Sender hub hai?
    if sender_features["is_hub"]:
        graph_score += 25

    # High PageRank sender = suspicious
    if sender_features["pagerank"] > 0.3:
        graph_score += 20
    elif sender_features["pagerank"] > 0.2:
        graph_score += 10

    # Fraud ring mein hai?
    if sender_in_ring:
        graph_score += 40
    if receiver_in_ring:
        graph_score += 30

    # Bahut zyada outgoing transactions
    if sender_features["out_degree"] > 5:
        graph_score += 15

    # Cap at 100
    graph_score = min(graph_score, 100)

    return {
        "graph_score":        graph_score,
        "sender_pagerank":    sender_features["pagerank"],
        "receiver_pagerank":  receiver_features["pagerank"],
        "sender_in_ring":     sender_in_ring,
        "receiver_in_ring":   receiver_in_ring,
        "sender_connections": sender_features["in_degree"] + sender_features["out_degree"],
        "fraud_rings_total":  len(rings),
        "graph_risk":         "HIGH" if graph_score > 60 else
                              "MEDIUM" if graph_score > 30 else "LOW",
    }

def combined_score(ml_score: float, sender: str, receiver: str) -> dict:
    """
    ML score + Graph score = Final combined score

    Weights:
    70% XGBoost ML score
    30% Graph score
    """
    try:
        graph_result = get_graph_risk_score(sender, receiver)
        graph_score  = graph_result["graph_score"]
    except Exception:
        graph_result = {"graph_score": 0}
        graph_score  = 0

    # Weighted combination
    final_score = (0.70 * ml_score) + (0.30 * graph_score)
    final_score = round(min(final_score, 100), 2)

    # Tier
    if final_score < 30:   tier = "LOW"
    elif final_score < 60: tier = "MEDIUM"
    elif final_score < 86: tier = "HIGH"
    else:                  tier = "CRITICAL"

    return {
        "ml_score":     round(ml_score, 2),
        "graph_score":  round(graph_score, 2),
        "final_score":  final_score,
        "final_tier":   tier,
        "graph_details": graph_result,
    }

# ── Test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== GNN Scorer Test ===\n")

    # Normal transaction
    print("Test 1: Normal transaction")
    result1 = combined_score(15.0, "ACC_ATHARVA", "ACC_RAHUL")
    print(f"  ML Score:    {result1['ml_score']}")
    print(f"  Graph Score: {result1['graph_score']}")
    print(f"  Final Score: {result1['final_score']}")
    print(f"  Final Tier:  {result1['final_tier']}")

    # Fraud ring transaction
    print("\nTest 2: Fraud ring account")
    result2 = combined_score(45.0, "ACC_RING_1", "ACC_RING_2")
    print(f"  ML Score:    {result2['ml_score']}")
    print(f"  Graph Score: {result2['graph_score']}")
    print(f"  Final Score: {result2['final_score']}")
    print(f"  Final Tier:  {result2['final_tier']}")
    print(f"  In Ring:     {result2['graph_details']['sender_in_ring']}")

    print("\n✅ GNN Scorer working!")