// App.js — Fraud Detection Dashboard v2
// New features:
// - Transaction submit form
// - Cases tab
// - Tab navigation

import { useState, useEffect } from 'react';
import './App.css';

const API_URL = 'http://localhost:8000';

// ── Components ────────────────────────────────────────────────────

function KPICard({ label, value, sub, color }) {
  return (
    <div className="kpi-card" style={{ borderTopColor: color }}>
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}

function RiskBadge({ tier }) {
  return (
    <span className={`badge badge-${tier}`}>{tier}</span>
  );
}

// ── Transaction Submit Form ───────────────────────────────────────
function SubmitForm({ onSuccess }) {
  const [form, setForm] = useState({
    transaction_type: 'UPI',
    amount:           '',
    sender_account:   '',
    receiver_account: '',
    city:             '',
    new_receiver:     0,
    geo_distance:     0,
    device_seen:      1,
    receiver_risk:    0.01,
  });
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(`${API_URL}/api/v1/score`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          ...form,
          amount:        parseFloat(form.amount),
          new_receiver:  parseInt(form.new_receiver),
          geo_distance:  parseFloat(form.geo_distance),
          device_seen:   parseInt(form.device_seen),
          receiver_risk: parseFloat(form.receiver_risk),
        }),
      });

      const data = await res.json();
      setResult(data);
      if (onSuccess) onSuccess();

    } catch (err) {
      setError('API error — chal rahi hai?');
    } finally {
      setLoading(false);
    }
  };

  const tierColors = {
    LOW:      '#22C55E',
    MEDIUM:   '#EAB308',
    HIGH:     '#F97316',
    CRITICAL: '#EF4444',
  };

  return (
    <div className="section">
      <div className="section-header">
        <h2>Submit Transaction for Scoring</h2>
      </div>

      <div style={{ padding: 24 }}>
        <form onSubmit={handleSubmit}>
          <div className="form-grid">

            {/* Transaction Type */}
            <div className="form-group">
              <label>Transaction Type</label>
              <select name="transaction_type"
                value={form.transaction_type}
                onChange={handleChange}>
                {['UPI','IMPS','NEFT','CARD_CREDIT','CARD_DEBIT']
                  .map(t => <option key={t}>{t}</option>)}
              </select>
            </div>

            {/* Amount */}
            <div className="form-group">
              <label>Amount (₹)</label>
              <input type="number" name="amount"
                value={form.amount}
                onChange={handleChange}
                placeholder="e.g. 15000"
                required />
            </div>

            {/* Sender */}
            <div className="form-group">
              <label>Sender Account</label>
              <input type="text" name="sender_account"
                value={form.sender_account}
                onChange={handleChange}
                placeholder="ACC_001"
                required />
            </div>

            {/* Receiver */}
            <div className="form-group">
              <label>Receiver Account</label>
              <input type="text" name="receiver_account"
                value={form.receiver_account}
                onChange={handleChange}
                placeholder="ACC_002"
                required />
            </div>

            {/* City */}
            <div className="form-group">
              <label>City</label>
              <input type="text" name="city"
                value={form.city}
                onChange={handleChange}
                placeholder="Mumbai" />
            </div>

            {/* Geo Distance */}
            <div className="form-group">
              <label>Geo Distance (km)</label>
              <input type="number" name="geo_distance"
                value={form.geo_distance}
                onChange={handleChange}
                placeholder="0" />
            </div>

            {/* Device Seen */}
            <div className="form-group">
              <label>Device Seen Before?</label>
              <select name="device_seen"
                value={form.device_seen}
                onChange={handleChange}>
                <option value={1}>Yes</option>
                <option value={0}>No (New Device)</option>
              </select>
            </div>

            {/* New Receiver */}
            <div className="form-group">
              <label>New Receiver?</label>
              <select name="new_receiver"
                value={form.new_receiver}
                onChange={handleChange}>
                <option value={0}>No</option>
                <option value={1}>Yes (First time)</option>
              </select>
            </div>

            {/* Receiver Risk */}
            <div className="form-group">
              <label>Receiver Risk (0-1)</label>
              <input type="number" name="receiver_risk"
                value={form.receiver_risk}
                onChange={handleChange}
                step="0.01" min="0" max="1"
                placeholder="0.01" />
            </div>

          </div>

          {/* Submit Button */}
          <button type="submit"
            className="refresh-btn"
            disabled={loading}
            style={{ marginTop: 16, padding: '10px 24px', fontSize: 14 }}>
            {loading ? '⏳ Scoring...' : '🔍 Score Transaction'}
          </button>
        </form>

        {/* Error */}
        {error && (
          <div className="error" style={{ marginTop: 16 }}>
            ⚠️ {error}
          </div>
        )}

        {/* Result */}
        {result && (
          <div style={{
            marginTop: 20,
            padding: 20,
            background: '#0F172A',
            borderRadius: 12,
            border: `2px solid ${tierColors[result.risk_tier] || '#334155'}`,
          }}>
            <div style={{
              fontSize: 18,
              fontWeight: 700,
              color: tierColors[result.risk_tier],
              marginBottom: 12,
            }}>
              {result.risk_tier === 'CRITICAL' ? '🔴' :
               result.risk_tier === 'HIGH'     ? '🟠' :
               result.risk_tier === 'MEDIUM'   ? '🟡' : '🟢'}
              {' '}{result.recommendation} — {result.risk_tier} RISK
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr 1fr 1fr',
              gap: 12
            }}>
              {[
                ['Transaction ID', result.transaction_id?.substring(0,16) + '...'],
                ['Risk Score',     `${result.risk_score?.toFixed(1)} / 100`],
                ['Fraud Prob',     `${(result.fraud_prob * 100)?.toFixed(2)}%`],
                ['Processing',     `${result.processing_ms}ms`],
              ].map(([label, value]) => (
                <div key={label} style={{
                  background: '#1E293B',
                  padding: '10px 14px',
                  borderRadius: 8,
                }}>
                  <div style={{ fontSize: 11, color: '#64748B', marginBottom: 4 }}>
                    {label}
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#F1F5F9' }}>
                    {value}
                  </div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 12, fontSize: 13, color: '#94A3B8' }}>
              {result.message}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Cases Tab ─────────────────────────────────────────────────────
function CasesTab() {
  const [cases, setCases]   = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchCases = async () => {
    try {
      const res  = await fetch(`${API_URL}/api/v1/cases`);
      const data = await res.json();
      setCases(data.cases || []);
      setLoading(false);
    } catch (err) {
      setLoading(false);
    }
  };

  useEffect(() => { fetchCases(); }, []);

  return (
    <div className="section">
      <div className="section-header">
        <h2>🚨 Fraud Cases</h2>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <span className="count">{cases.length} cases</span>
          <button className="refresh-btn" onClick={fetchCases}>
            🔄 Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading">Loading cases...</div>
      ) : cases.length === 0 ? (
        <div className="empty">
          No HIGH/CRITICAL cases yet!
          Submit a suspicious transaction to see cases here.
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Transaction ID</th>
              <th>Type</th>
              <th>Amount (₹)</th>
              <th>Sender</th>
              <th>Risk Score</th>
              <th>Risk Tier</th>
              <th>Action Required</th>
              <th>SLA</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c, i) => (
              <tr key={c.transaction_id || i}>
                <td className="txn-id">
                  {c.transaction_id?.substring(0, 16)}...
                </td>
                <td>
                  <span style={{
                    background: '#1E3A5F',
                    color: '#60A5FA',
                    padding: '2px 8px',
                    borderRadius: 6,
                    fontSize: 12,
                  }}>
                    {c.transaction_type}
                  </span>
                </td>
                <td className="amount">
                  {parseFloat(c.amount || 0).toLocaleString('en-IN')}
                </td>
                <td style={{ fontFamily: 'monospace', fontSize: 12 }}>
                  {c.sender?.substring(0, 15)}
                </td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{
                      width: 60,
                      height: 6,
                      background: '#334155',
                      borderRadius: 3,
                      overflow: 'hidden',
                    }}>
                      <div style={{
                        width: `${c.risk_score}%`,
                        height: '100%',
                        background: c.risk_tier === 'CRITICAL' ? '#EF4444' : '#F97316',
                        borderRadius: 3,
                      }} />
                    </div>
                    <span style={{ fontSize: 12, color: '#94A3B8' }}>
                      {c.risk_score?.toFixed(0)}
                    </span>
                  </div>
                </td>
                <td>
                  <RiskBadge tier={c.risk_tier || 'HIGH'} />
                </td>
                <td>
                  <span className={
                    c.action_required === 'BLOCK'
                      ? 'recommendation-BLOCK'
                      : 'recommendation-HOLD'
                  }>
                    {c.action_required}
                  </span>
                </td>
                <td style={{ color: '#EF4444', fontSize: 12, fontWeight: 600 }}>
                  {c.sla_hours}h SLA
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────
function App() {
  const [activeTab, setActiveTab]       = useState('feed');
  const [transactions, setTransactions] = useState([]);
  const [stats, setStats]               = useState(null);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState(null);
  const [lastUpdated, setLastUpdated]   = useState(null);

  const fetchData = async () => {
    try {
      setError(null);
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

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const tierCounts = transactions.reduce((acc, txn) => {
    const tier = txn.risk_tier || 'LOW';
    acc[tier] = (acc[tier] || 0) + 1;
    return acc;
  }, {});

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
        {error && <div className="error">⚠️ {error}</div>}

        {/* KPI Cards */}
        <div className="kpi-grid">
          <KPICard label="Total Transactions"
            value={stats?.total_transactions || transactions.length}
            sub="All time" color="#3B82F6" />
          <KPICard label="🟢 Low Risk"
            value={tierCounts.LOW || 0}
            sub="Auto approved" color="#22C55E" />
          <KPICard label="🟡 Medium Risk"
            value={tierCounts.MEDIUM || 0}
            sub="Review needed" color="#EAB308" />
          <KPICard label="🟠 High Risk"
            value={tierCounts.HIGH || 0}
            sub="Hold transaction" color="#F97316" />
          <KPICard label="🔴 Critical"
            value={tierCounts.CRITICAL || 0}
            sub="Block immediately" color="#EF4444" />
          <KPICard label="ML Model"
            value="XGBoost" sub="v1.0 — Active" color="#8B5CF6" />
        </div>

        {/* Tabs */}
        <div className="tabs">
          {[
            { id: 'feed',   label: '📊 Live Feed' },
            { id: 'cases',  label: '🚨 Cases' },
            { id: 'submit', label: '➕ Submit Transaction' },
          ].map(tab => (
            <button key={tab.id}
              className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'feed' && (
          <div className="section">
            <div className="section-header">
              <h2>Recent Transactions</h2>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                <span className="count">{transactions.length} transactions</span>
                <button className="refresh-btn" onClick={fetchData}>
                  🔄 Refresh
                </button>
              </div>
            </div>

            {loading ? (
              <div className="loading">Loading...</div>
            ) : transactions.length === 0 ? (
              <div className="empty">No transactions yet!</div>
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
                  {transactions.map((txn, i) => (
                    <tr key={txn.transaction_id || i}>
                      <td className="txn-id">
                        {txn.transaction_id?.substring(0, 16)}...
                      </td>
                      <td>
                        <span style={{
                          background: '#1E3A5F', color: '#60A5FA',
                          padding: '2px 8px', borderRadius: 6, fontSize: 12,
                        }}>
                          {txn.transaction_type}
                        </span>
                      </td>
                      <td className="amount">
                        {parseFloat(txn.amount||0).toLocaleString('en-IN')}
                      </td>
                      <td style={{ fontFamily: 'monospace', fontSize: 12 }}>
                        {txn.sender?.substring(0, 15)}
                      </td>
                      <td>{txn.city || '—'}</td>
                      <td><RiskBadge tier={txn.risk_tier || 'LOW'} /></td>
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
        )}

        {activeTab === 'cases' && <CasesTab />}

        {activeTab === 'submit' && (
          <SubmitForm onSuccess={fetchData} />
        )}

      </div>
    </div>
  );
}

export default App;