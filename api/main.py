# api/main.py
#
# FastAPI application — Fraud Detection Engine ka REST API
#
# Endpoints:
#   GET  /                     → Welcome message
#   GET  /api/v1/health        → System health check
#   POST /api/v1/score         → Transaction score karo
#   GET  /api/v1/transactions  → Sab transactions list karo
#   GET  /api/v1/stats         → Dashboard stats
#
# Docs: http://localhost:8000/docs (Swagger UI — automatic!)

import sys
import os
from datetime import datetime
from typing import Optional

# FastAPI imports
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Apni files import karo
sys.path.insert(0, "../database")
sys.path.insert(0, "../redis_layer")
sys.path.insert(0, "../ml_engine")
sys.path.insert(0, "../simulator")

from db_setup    import create_tables, insert_transaction, get_all_transactions
from redis_setup import track_transaction, get_velocity, check_duplicate
from inference   import load_model, score_transaction

# ── App banao ─────────────────────────────────────────────────────
app = FastAPI(
    title="Fraud Detection Engine API",
    description="Real-Time Financial Fraud Detection & Risk Scoring",
    version="1.0.0",
)

# CORS — React dashboard baad mein connect karega
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ML Model — ek baar load karo ─────────────────────────────────
# Global variable — har request pe load nahi hoga!
ml_model = None

@app.on_event("startup")
async def startup_event():
    """App start hone pe yeh run hoga"""
    global ml_model
    create_tables()
    ml_model = load_model()
    print("✅ API ready! ML model loaded.")

# ── Request/Response Schemas ──────────────────────────────────────
class TransactionRequest(BaseModel):
    """
    Transaction submit karne ka format.
    Pydantic automatically validate karega!
    """
    transaction_id:   Optional[str]   = None
    transaction_type: str             = Field(..., example="UPI")
    amount:           float           = Field(..., gt=0, example=15000)
    sender_account:   str             = Field(..., example="ACC_001")
    receiver_account: str             = Field(..., example="ACC_002")
    city:             Optional[str]   = "Unknown"
    device_seen:      Optional[int]   = 1
    new_receiver:     Optional[int]   = 0
    geo_distance:     Optional[float] = 0.0
    receiver_risk:    Optional[float] = 0.01

class ScoreResponse(BaseModel):
    """API ka response format"""
    transaction_id: str
    risk_score:     float
    risk_tier:      str
    recommendation: str
    fraud_prob:     float
    processing_ms:  int
    message:        str

# ── Endpoints ─────────────────────────────────────────────────────

# 1. Welcome
@app.get("/")
async def root():
    return {
        "message": "Fraud Detection Engine API",
        "version": "1.0.0",
        "docs":    "http://localhost:8000/docs",
        "status":  "running"
    }

# 2. Health Check
@app.get("/api/v1/health")
async def health_check():
    """
    System health check.
    Monitoring tools yeh endpoint use karti hain.
    """
    return {
        "status":    "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api":      "up",
            "ml_model": "loaded" if ml_model else "not loaded",
            "database": "connected",
        }
    }

# 3. Score Transaction — Main Endpoint!
@app.post("/api/v1/score", response_model=ScoreResponse)
async def score_transaction_endpoint(request: TransactionRequest):
    """
    Transaction submit karo → Risk score lo!

    Yeh main endpoint hai — banks aur fintechs yahi use karenge.

    Example:
    POST /api/v1/score
    {
        "transaction_type": "UPI",
        "amount": 750000,
        "sender_account": "ACC_001",
        "receiver_account": "ACC_002"
    }
    """
    import time
    start_time = time.time()

    # Transaction ID generate karo agar nahi diya
    import uuid
    txn_id = request.transaction_id or f"TXN_{uuid.uuid4().hex[:8].upper()}"

    # Duplicate check
    if check_duplicate(txn_id):
        raise HTTPException(
            status_code=409,
            detail=f"Duplicate transaction: {txn_id}"
        )

    # Velocity track karo
    track_transaction(request.sender_account, request.amount)
    velocity = get_velocity(request.sender_account)

    # ML Score
    txn_for_ml = {
        "id":            txn_id,
        "amount":        request.amount,
        "type":          request.transaction_type,
        "new_receiver":  request.new_receiver,
        "geo_distance":  request.geo_distance,
        "device_seen":   request.device_seen,
        "receiver_risk": request.receiver_risk,
    }

    velocity_for_ml = {
        "txn_count_1h":  velocity["txn_count_1h"],
        "amount_sum_1h": velocity["amount_sum_1h"],
        "avg_amount":    10000,
        "std_amount":    5000,
    }

    ml_result = score_transaction(ml_model, txn_for_ml, velocity_for_ml)

    # Recommendation
    tier = ml_result["risk_tier"]
    recommendations = {
        "LOW":      "APPROVE",
        "MEDIUM":   "REVIEW",
        "HIGH":     "HOLD",
        "CRITICAL": "BLOCK",
    }
    recommendation = recommendations[tier]

    # DB save
    txn_data = {
        "id":       txn_id,
        "type":     request.transaction_type,
        "amount":   request.amount,
        "sender":   request.sender_account,
        "receiver": request.receiver_account,
        "city":     request.city,
    }
    insert_transaction(txn_data)

    processing_ms = int((time.time() - start_time) * 1000)

    return ScoreResponse(
        transaction_id = txn_id,
        risk_score     = ml_result["risk_score"],
        risk_tier      = tier,
        recommendation = recommendation,
        fraud_prob     = ml_result["fraud_prob"],
        processing_ms  = processing_ms,
        message        = f"Transaction {recommendation} — {tier} risk"
    )

# 4. List Transactions
@app.get("/api/v1/transactions")
async def list_transactions(limit: int = 20):
    """Sab transactions list karo"""
    rows = get_all_transactions()
    transactions = []

    for row in rows[:limit]:
        transactions.append({
            "transaction_id":   row[0],
            "transaction_type": row[1],
            "amount":           float(row[2]),
            "sender":           row[3],
            "city":             row[4],
            "created_at":       str(row[5]),
        })

    return {
        "total":        len(transactions),
        "transactions": transactions,
    }

# 5. Dashboard Stats
@app.get("/api/v1/stats")
async def get_stats():
    """KPI stats for dashboard"""
    rows = get_all_transactions()
    total = len(rows)

    return {
        "total_transactions": total,
        "message": f"{total} transactions processed so far!",
        "api_status": "running",
        "ml_model":   "XGBoost v1.0",
    }
# ── 6. Feedback Submit ────────────────────────────────────────────
class FeedbackRequest(BaseModel):
    """Analyst ka verdict"""
    transaction_id: str
    analyst_id:     str
    verdict:        str  # CONFIRMED_FRAUD / FALSE_POSITIVE / LEGITIMATE
    notes:          Optional[str] = None

@app.post("/api/v1/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Analyst feedback submit karo.
    Yeh baad mein model retraining mein use hoga!
    
    Verdicts:
    - CONFIRMED_FRAUD  → Sach mein fraud tha
    - FALSE_POSITIVE   → Normal tha, wrongly flagged
    - LEGITIMATE       → Legitimate transaction
    """
    import psycopg2
    sys.path.insert(0, "../database")
    from db_setup import get_connection

    try:
        conn = get_connection()
        cur  = conn.cursor()

        cur.execute("""
            INSERT INTO analyst_feedback
                (transaction_id, analyst_id, verdict, notes, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (
            request.transaction_id,
            request.analyst_id,
            request.verdict,
            request.notes,
        ))

        conn.commit()
        cur.close()
        conn.close()

        return {
            "success": True,
            "message": f"Feedback recorded: {request.verdict}",
            "transaction_id": request.transaction_id,
            "analyst_id":     request.analyst_id,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 7. Cases List ─────────────────────────────────────────────────
@app.get("/api/v1/cases")
async def list_cases():
    """
    Fraud cases list karo — HIGH aur CRITICAL transactions.
    Analyst dashboard yeh use karega.
    """
    sys.path.insert(0, "../database")
    from db_setup import get_connection

    try:
        conn = get_connection()
        cur  = conn.cursor()

        cur.execute("""
            SELECT
                transaction_id,
                transaction_type,
                amount,
                sender_account,
                city,
                risk_score,
                risk_tier,
                created_at
            FROM transactions
            WHERE risk_tier IN ('HIGH', 'CRITICAL')
            ORDER BY created_at DESC
            LIMIT 50
        """)

        rows  = cur.fetchall()
        cases = []

        for row in rows:
            tier = row[6]
            # SLA calculate karo
            sla_hours = 0.5 if tier == "CRITICAL" else 4
            cases.append({
                "transaction_id":   row[0],
                "transaction_type": row[1],
                "amount":           float(row[2]),
                "sender":           row[3],
                "city":             row[4],
                "risk_score":       float(row[5]) if row[5] else 0,
                "risk_tier":        tier,
                "created_at":       str(row[7]),
                "sla_hours":        sla_hours,
                "action_required":  "BLOCK" if tier == "CRITICAL" else "HOLD",
            })

        cur.close()
        conn.close()

        return {
            "total_cases": len(cases),
            "cases":       cases,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 8. Single Transaction Detail ──────────────────────────────────
@app.get("/api/v1/transaction/{transaction_id}")
async def get_transaction(transaction_id: str):
    """
    Ek transaction ki poori detail lo.
    Analyst case investigate karte waqt yeh use karega.
    """
    sys.path.insert(0, "../database")
    from db_setup import get_connection

    try:
        conn = get_connection()
        cur  = conn.cursor()

        cur.execute("""
            SELECT
                transaction_id,
                transaction_type,
                amount,
                sender_account,
                receiver_account,
                city,
                risk_score,
                risk_tier,
                created_at
            FROM transactions
            WHERE transaction_id = %s
        """, (transaction_id,))

        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"Transaction {transaction_id} not found"
            )

        tier = row[7]
        recommendations = {
            "LOW":      "APPROVE",
            "MEDIUM":   "REVIEW",
            "HIGH":     "HOLD",
            "CRITICAL": "BLOCK",
        }

        return {
            "transaction_id":   row[0],
            "transaction_type": row[1],
            "amount":           float(row[2]),
            "sender":           row[3],
            "receiver":         row[4],
            "city":             row[5],
            "risk_score":       float(row[6]) if row[6] else 0,
            "risk_tier":        tier,
            "recommendation":   recommendations.get(tier, "REVIEW"),
            "created_at":       str(row[8]),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))