# gnn_engine/graph_builder.py
import networkx as nx
import sys
import time
sys.path.insert(0, "../database")
from db_setup import get_connection

# ── Cache — 60 seconds mein rebuild mat karo ──────────────────────
_cache_time  = 0
_cache_graph = None

def build_transaction_graph() -> nx.DiGraph:
    global _cache_time, _cache_graph

    # 60 seconds cache
    if _cache_graph is not None and (time.time() - _cache_time) < 60:
        return _cache_graph

    G = nx.DiGraph()

    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        SELECT sender_account, receiver_account,
               amount, risk_tier, transaction_id
        FROM transactions
        ORDER BY created_at DESC
        LIMIT 1000
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    for row in rows:
        sender   = row[0]
        receiver = row[1]
        amount   = float(row[2])
        tier     = row[3] or "LOW"
        txn_id   = row[4]

        if not G.has_node(sender):
            G.add_node(sender, account=sender)
        if not G.has_node(receiver):
            G.add_node(receiver, account=receiver)

        G.add_edge(
            sender, receiver,
            amount    = amount,
            risk_tier = tier,
            txn_id    = txn_id,
            weight    = amount / 100000,
        )

    # Cache update karo
    _cache_time  = time.time()
    _cache_graph = G
    return G

def get_account_features(G: nx.DiGraph, account: str) -> dict:
    if account not in G:
        return {
            "in_degree":  0,
            "out_degree": 0,
            "pagerank":   0.0,
            "total_sent": 0.0,
            "total_recv": 0.0,
            "is_hub":     False,
        }

    pagerank  = nx.pagerank(G, alpha=0.85)
    in_edges  = list(G.in_edges(account,  data=True))
    out_edges = list(G.out_edges(account, data=True))

    total_sent = sum(e[2].get("amount", 0) for e in out_edges)
    total_recv = sum(e[2].get("amount", 0) for e in in_edges)

    in_deg  = G.in_degree(account)
    out_deg = G.out_degree(account)

    return {
        "in_degree":  in_deg,
        "out_degree": out_deg,
        "pagerank":   round(pagerank.get(account, 0.0), 6),
        "total_sent": round(total_sent, 2),
        "total_recv": round(total_recv, 2),
        "is_hub":     (in_deg + out_deg) > 5,
    }

def detect_fraud_rings(G: nx.DiGraph) -> list:
    rings = []
    try:
        cycles = list(nx.simple_cycles(G))
        for cycle in cycles:
            if len(cycle) >= 2:
                total_amount = 0
                for i in range(len(cycle)):
                    sender   = cycle[i]
                    receiver = cycle[(i + 1) % len(cycle)]
                    if G.has_edge(sender, receiver):
                        total_amount += G[sender][receiver].get("amount", 0)

                rings.append({
                    "accounts":     cycle,
                    "ring_size":    len(cycle),
                    "total_amount": round(total_amount, 2),
                    "risk":         "HIGH" if total_amount > 100000 else "MEDIUM",
                })
    except Exception:
        pass
    return rings

if __name__ == "__main__":
    print("=== Transaction Graph Analysis ===\n")

    G = build_transaction_graph()

    print(f"Graph Stats:")
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")

    if G.number_of_nodes() > 0:
        degrees     = dict(G.degree())
        top_accounts = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:5]

        print(f"\nTop 5 Most Connected Accounts:")
        for acc, deg in top_accounts:
            features = get_account_features(G, acc)
            print(f"  {acc}")
            print(f"    Connections: {deg}")
            print(f"    PageRank:    {features['pagerank']:.6f}")
            print(f"    Total Sent:  {features['total_sent']:,.0f}")
            print(f"    Total Recv:  {features['total_recv']:,.0f}")
            print(f"    Is Hub:      {'YES' if features['is_hub'] else 'No'}")

        rings = detect_fraud_rings(G)
        if rings:
            print(f"\nFraud Rings Detected: {len(rings)}")
            for ring in rings[:3]:
                print(f"  Ring: {' -> '.join(ring['accounts'])}")
                print(f"  Amount: {ring['total_amount']:,.0f}")
                print(f"  Risk: {ring['risk']}")
        else:
            print(f"\nNo fraud rings detected")
    else:
        print("\nNo transactions yet!")

    print("\nGraph analysis complete!")