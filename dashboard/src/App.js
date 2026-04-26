// App.js — Fraud Detection Dashboard
//
// React concepts used:
// - useState: data store karna
// - useEffect: API calls karna
// - Components: reusable UI pieces
// - fetch: API se data laana

import { useState, useEffect } from 'react';
import './App.css';

// ── API URL ──────────────────────────────────────────────────────
const API_URL = 'http://localhost:8000';

// ── KPI Card Component ───────────────────────────────────────────
// Ek reusable card — label, value, sub text dikhata hai
function KPICard({ label, value, sub, color }) {
  return (
    <div className="kpi-card" style={{ borderTopColor: color }}>
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}

// ── Risk Badge Component ──────────────────────────────────────────
// Colored badge — LOW/MEDIUM/HIGH/CRITICAL
function RiskBadge({ tier }) {
  return (
    <span className={`badge badge-${tier}`}>
      {tier}
    </span>
  );
}

// ── Main App Component ────────────────────────────────────────────
function App() {
  // useState — yeh data screen pe dikhayega
  const [transactions, setTransactions] = useState([]);
  const [stats, setStats]               = useState(null);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState(null);
  const [lastUpdated, setLastUpdated]   = useState(null);

  // API se data fetch karo
  const fetchData = async () => {
    try {
      setError(null);

      // Dono API calls ek saath karo (parallel)
      const [txnRes, statsRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/transactions?limit=50`),
        fetch(`${API_URL}/api/v1/stats`),
      ]);

      const txnData   = await txnRes.json();
      const statsData = await statsRes.json();

      setTransactions(txnData.transactions || []);
      setStats(statsData);
      setLastUpdated(new Date().toLocaleTimeString());
      setLoading(false);

    } catch (err) {
      setError('API se connect nahi ho paya. API chal rahi hai?');
      setLoading(false);
    }
  };

  // useEffect — component load hone pe fetchData chalao
  useEffect(() => {
    fetchData();
    // Har 30 seconds mein auto-refresh
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval); // cleanup
  }, []);

  // Tier counts calculate karo
  const tierCounts = transactions.reduce((acc, txn) => {
    const tier = txn.risk_tier || 'LOW';
    acc[tier] = (acc[tier] || 0) + 1;
    return acc;
  }, {});

  // ── Render ──────────────────────────────────────────────────────
  return (
    <div>
      {/* Header */}
      <div className="header">
        <h1>🛡️ Fraud Detection Engine</h1>
        <div className="status">
          <div className="status-dot"></div>
          <span>Live</span>
          {lastUpdated && <span>· Updated {lastUpdated}</span>}
        </div>
      </div>

      <div className="main">

        {/* Error Banner */}
        {error && <div className="error">⚠️ {error}</div>}

        {/* KPI Cards */}
        <div className="kpi-grid">
          <KPICard
            label="Total Transactions"
            value={stats?.total_transactions || transactions.length}
            sub="All time"
            color="#3B82F6"
          />
          <KPICard
            label="🟢 Low Risk"
            value={tierCounts.LOW || 0}
            sub="Auto approved"
            color="#22C55E"
          />
          <KPICard
            label="🟡 Medium Risk"
            value={tierCounts.MEDIUM || 0}
            sub="Review needed"
            color="#EAB308"
          />
          <KPICard
            label="🟠 High Risk"
            value={tierCounts.HIGH || 0}
            sub="Hold transaction"
            color="#F97316"
          />
          <KPICard
            label="🔴 Critical"
            value={tierCounts.CRITICAL || 0}
            sub="Block immediately"
            color="#EF4444"
          />
          <KPICard
            label="ML Model"
            value="XGBoost"
            sub="v1.0 — Active"
            color="#8B5CF6"
          />
        </div>

        {/* Transactions Table */}
        <div className="section">
          <div className="section-header">
            <h2>Recent Transactions</h2>
            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <span className="count">
                {transactions.length} transactions
              </span>
              <button className="refresh-btn" onClick={fetchData}>
                🔄 Refresh
              </button>
            </div>
          </div>

          {loading ? (
            <div className="loading">Loading transactions...</div>
          ) : transactions.length === 0 ? (
            <div className="empty">
              No transactions yet. API se koi transaction submit karo!
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Transaction ID</th>
                  <th>Type</th>
                  <th>Amount (₹)</th>
                  <th>Sender</th>
                  <th>City</th>
                  <th>Risk Tier</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((txn, index) => (
                  <tr key={txn.transaction_id || index}>
                    <td className="txn-id">
                      {txn.transaction_id?.substring(0, 16)}...
                    </td>
                    <td>
                      <span style={{
                        background: '#1E3A5F',
                        color: '#60A5FA',
                        padding: '2px 8px',
                        borderRadius: 6,
                        fontSize: 12
                      }}>
                        {txn.transaction_type}
                      </span>
                    </td>
                    <td className="amount">
                      {parseFloat(txn.amount || 0).toLocaleString('en-IN')}
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: 12 }}>
                      {txn.sender?.substring(0, 15)}
                    </td>
                    <td>{txn.city || '—'}</td>
                    <td>
                      <RiskBadge tier={txn.risk_tier || 'LOW'} />
                    </td>
                    <td style={{ color: '#64748B', fontSize: 12 }}>
                      {txn.created_at
                        ? new Date(txn.created_at).toLocaleTimeString()
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

      </div>
    </div>
  );
}

export default App;