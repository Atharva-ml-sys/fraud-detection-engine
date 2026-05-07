# gnn_engine/graph_builder.py
#
# Transaction graph banao:
# Nodes = bank accounts
# Edges = transactions between accounts
#
# Fraud ring example:
# ACC_007 → ACC_099 → ACC_X → ACC_007
# (circular money flow = suspicious!)

import networkx as nx
import sys
sys.path.insert(0, "../database")
from db_setup import get_connection

def build_transaction_graph() -> nx.DiGraph:
    """
    PostgreSQL se transactions fetch karo
    aur directed graph banao.
    
    DiGraph = Directed Graph
    (sender → receiver, direction matters!)
    """
    G = nx.DiGraph()
    
    conn = get_connection()
    cur  = conn.cursor()
    
    cur.execute("""
        SELECT 
            sender_account,
            receiver_account,
            amount,
            risk_tier,
            transaction_id
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
        
        # Node add karo agar nahi hai
        if not G.has_node(sender):
            G.add_node(sender, account=sender)
        if not G.has_node(receiver):
            G.add_node(receiver, account=receiver)
        
        # Edge add karo (transaction)
        G.add_edge(
            sender,
            receiver,
            amount    = amount,
            risk_tier = tier,
            txn_id    = txn_id,
            weight    = amount / 100000,  # normalized weight
        )
    
    return G

def get_account_features(G: nx.DiGraph, account: str) -> dict:
    """
    Ek account ke graph features nikalo.
    
    Features:
    - in_degree:  kitne accounts ne isko bheja
    - out_degree: kitne accounts ko usne bheja
    - pagerank:   account ka importance score
    - clustering: kitna circular flow hai
    """
    if account not in G:
        return {
            "in_degree":   0,
            "out_degree":  0,
            "pagerank":    0.0,
            "total_sent":  0.0,
            "total_recv":  0.0,
            "is_hub":      False,
        }
    
    # PageRank calculate karo
    pagerank = nx.pagerank(G, alpha=0.85)
    
    # In/Out edges
    in_edges  = list(G.in_edges(account,  data=True))
    out_edges = list(G.out_edges(account, data=True))
    
    total_sent = sum(e[2].get("amount", 0) for e in out_edges)
    total_recv = sum(e[2].get("amount", 0) for e in in_edges)
    
    in_deg  = G.in_degree(account)
    out_deg = G.out_degree(account)
    
    # Hub = bahut saare connections wala account
    is_hub = (in_deg + out_deg) > 5
    
    return {
        "in_degree":   in_deg,
        "out_degree":  out_deg,
        "pagerank":    round(pagerank.get(account, 0.0), 6),
        "total_sent":  round(total_sent, 2),
        "total_recv":  round(total_recv, 2),
        "is_hub":      is_hub,
    }

def detect_fraud_rings(G: nx.DiGraph) -> list:
    """
    Circular transactions detect karo.
    A → B → C → A = Fraud ring!
    """
    rings = []
    
    try:
        # Simple cycles dhundho
        cycles = list(nx.simple_cycles(G))
        
        for cycle in cycles:
            if len(cycle) >= 2:  # minimum 2 accounts
                # Cycle ka total amount nikalo
                total_amount = 0
                for i in range(len(cycle)):
                    sender   = cycle[i]
                    receiver = cycle[(i + 1) % len(cycle)]
                    if G.has_edge(sender, receiver):
                        edge_data = G[sender][receiver]
                        total_amount += edge_data.get("amount", 0)
                
                rings.append({
                    "accounts":     cycle,
                    "ring_size":    len(cycle),
                    "total_amount": round(total_amount, 2),
                    "risk":         "HIGH" if total_amount > 100000 else "MEDIUM",
                })
    except Exception:
        pass
    
    return rings

# ── Test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Transaction Graph Analysis ===\n")
    
    G = build_transaction_graph()
    
    print(f"📊 Graph Stats:")
    print(f"  Nodes (accounts):     {G.number_of_nodes()}")
    print(f"  Edges (transactions): {G.number_of_edges()}")
    
    if G.number_of_nodes() > 0:
        # Top accounts by connections
        degrees = dict(G.degree())
        top_accounts = sorted(
            degrees.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        print(f"\n🏆 Top 5 Most Connected Accounts:")
        for acc, deg in top_accounts:
            features = get_account_features(G, acc)
            print(f"  {acc}")
            print(f"    Connections: {deg}")
            print(f"    PageRank:    {features['pagerank']:.6f}")
            print(f"    Total Sent:  ₹{features['total_sent']:,.0f}")
            print(f"    Total Recv:  ₹{features['total_recv']:,.0f}")
            print(f"    Is Hub:      {'⚠️ YES' if features['is_hub'] else 'No'}")
        
        # Fraud rings
        rings = detect_fraud_rings(G)
        if rings:
            print(f"\n🚨 Fraud Rings Detected: {len(rings)}")
            for ring in rings[:3]:
                print(f"  Ring: {' → '.join(ring['accounts'])} → ...")
                print(f"  Amount: ₹{ring['total_amount']:,.0f}")
                print(f"  Risk: {ring['risk']}")
        else:
            print(f"\n✅ No fraud rings detected")
    else:
        print("\n⚠️ No transactions in database yet!")
        print("Submit some transactions first.")
    
    print("\n✅ Graph analysis complete!")