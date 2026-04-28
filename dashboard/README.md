# 🛡️ Real-Time Financial Fraud Detection & Risk Scoring Engine

> End-to-end ML-powered fraud detection system — built from scratch, solo developer.

![Dashboard](docs/dashboard.png)

## 🚀 What This Project Does

This system detects financial fraud in **real-time** — processing transactions in under 500ms using machine learning, event streaming, and a live analyst dashboard.

**Key Achievement:** When a suspicious transaction arrives (new device + impossible travel + high amount), the system flags it as CRITICAL and recommends BLOCK — all in ~26ms.

---

## 🏗️ Architecture
Bank/App → Kafka → Validator → Feature Engine → XGBoost ML → FastAPI → React Dashboard
↓                              ↓
Redis                       PostgreSQL
---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Event Streaming | Apache Kafka | Real-time transaction pipeline |
| ML Model | XGBoost + scikit-learn | Fraud scoring (AUC: 0.97+) |
| Explainability | SHAP (Phase 2) | Why was this flagged? |
| Backend API | FastAPI + Python | REST API, <500ms response |
| Frontend | React.js | Live analyst dashboard |
| Database | PostgreSQL | Transaction storage |
| Cache | Redis | Velocity features, dedup |
| Containers | Docker Compose | One-command deployment |

---

## 📊 ML Model Performance

- **Algorithm:** XGBoost (Gradient Boosting)
- **AUC-ROC:** 0.97+
- **False Negatives:** 0 (no fraud missed!)
- **Inference time:** ~26ms per transaction
- **Features:** 12 engineered features (velocity, geo, device, amount patterns)

---

## 🔍 Fraud Patterns Detected

| Pattern | Signal | Action |
|---------|--------|--------|
| High velocity | 15+ transactions/hour | CRITICAL |
| Impossible travel | 1400km in 4 minutes | CRITICAL |
| Large unusual amount | 4.7x above average | HIGH |
| New device + new receiver | First-time combination | HIGH |
| Suspicious receiver | 78% fraud history | CRITICAL |

---

## 🚀 Quick Start

```bash
# 1. Clone repo
git clone https://github.com/Atharva-ml-sys/fraud-detection-engine
cd fraud-detection-engine

# 2. Start all services
docker-compose up --build

# 3. API Docs
open http://localhost:8000/docs

# 4. Dashboard
open http://localhost:3000
```

---

## 📁 Project Structure
fraud-detection-engine/
├── simulator/          Transaction generator (5 fraud patterns)
├── validator/          Schema validation (VAL-001 to VAL-008)
├── feature_engine/     42-feature engineering
├── kafka_layer/        Kafka producer, consumer, full pipeline
├── ml_engine/          XGBoost training + inference
├── api/                FastAPI REST API (8 endpoints)
├── database/           PostgreSQL setup
├── redis_layer/        Velocity tracking
└── dashboard/          React analyst dashboard
---

## 🎯 API Endpoints
POST /api/v1/score              Score a transaction (ML)
GET  /api/v1/transactions       List all transactions
GET  /api/v1/cases              HIGH/CRITICAL fraud cases
POST /api/v1/feedback           Analyst verdict submission
GET  /api/v1/transaction/{id}   Single transaction detail
GET  /api/v1/stats              KPI metrics
GET  /api/v1/health             System health check
---

## 📈 Risk Tiers

| Tier | Score | Action | SLA |
|------|-------|--------|-----|
| 🟢 LOW | 0-29 | Auto Approve | — |
| 🟡 MEDIUM | 30-59 | Review | 24h |
| 🟠 HIGH | 60-85 | Hold | 4h |
| 🔴 CRITICAL | 86-100 | Block | 30min |

---

## 🗺️ Roadmap

- [x] Phase 1 — Foundation (Weeks 1-8)
  - [x] Kafka event pipeline
  - [x] XGBoost ML engine
  - [x] FastAPI REST API
  - [x] React dashboard
- [ ] Phase 2 — Intelligence
  - [ ] Graph Neural Network (GNN)
  - [ ] SHAP explainability
  - [ ] Model drift detection
- [ ] Phase 3 — Production
  - [ ] Kubernetes deployment
  - [ ] Grafana monitoring
  - [ ] Load testing

---

*Built as a portfolio project — End-to-End ML + Full-Stack Engineering*