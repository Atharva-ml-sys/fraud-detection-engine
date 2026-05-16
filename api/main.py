# api/main.py
import sys
import os
import asyncio
import json
from datetime import datetime
from typing import Optional
from prometheus_fastapi_instrumentator import Instrumentator

# ── Paths set karo — SABSE PEHLE ─────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "database"))
sys.path.insert(0, os.path.join(BASE_DIR, "redis_layer"))
sys.path.insert(0, os.path.join(BASE_DIR, "ml_engine"))
sys.path.insert(0, os.path.join(BASE_DIR, "simulator"))
sys.path.insert(0, os.path.join(BASE_DIR, "gnn_engine"))

# ── Imports ───────────────────────────────────────────────────────
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from db_setup    import create_tables, insert_transaction, get_all_transactions
from redis_setup import track_transaction, get_velocity, check_duplicate
from inference   import load_model, score_transaction, explain_transaction

# GNN temporarily disabled — blocking issue fix karna hai
GNN_AVAILABLE = False

# ── App ───────────────────────────────────────────────────────────
app = FastAPI(
    title="Fraud Detection Engine API",
    description="Real-Time Financial Fraud Detection & Risk Scoring",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── WebSocket Connection Manager ──────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ WebSocket connected! Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"❌ WebSocket disconnected! Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

manager = ConnectionManager()
ml_model = None

@app.on_event("startup")
async def startup_event():
    global ml_model
    create_tables()
    ml_model = load_model()
    print("✅ API ready! ML model loaded.")

Instrumentator().instrument(app).expose(app)

# ── Schemas ───────────────────────────────────────────────────────
class TransactionRequest(BaseModel):
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
    transaction_id: str
    risk_score:     float
    risk_tier:      str
    recommendation: str
    fraud_prob:     float
    processing_ms:  int
    message:        str
    explanation:    Optional[dict] = None
    graph_info:     Optional[dict] = None

class FeedbackRequest(BaseModel):
    transaction_id: str
    analyst_id:     str
    verdict:        str
    notes:          Optional[str] = None

# ── Endpoints ─────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "message": "Fraud Detection Engine API",
        "version": "1.0.0",
        "docs":    "http://localhost:8000/docs",
        "status":  "running"
    }

@app.get("/api/v1/health")
async def health_check():
    return {
        "status":    "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api":            "up",
            "ml_model":       "loaded" if ml_model else "not loaded",
            "database":       "connected",
            "websocket_clients": len(manager.active_connections),
        }
    }

@app.post("/api/v1/score", response_model=ScoreResponse)
async def score_transaction_endpoint(request: TransactionRequest):
    import time
    import uuid
    start_time = time.time()

    txn_id = request.transaction_id or f"TXN_{uuid.uuid4().hex[:8].upper()}"

    if check_duplicate(txn_id):
        raise HTTPException(status_code=409, detail=f"Duplicate: {txn_id}")

    track_transaction(request.sender_account, request.amount)
    velocity = get_velocity(request.sender_account)

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

    final_score = ml_result["risk_score"]
    final_tier  = ml_result["risk_tier"]
    graph_info  = None

    # SHAP — HIGH/CRITICAL ke liye
    explanation = None
    if final_tier in ["HIGH", "CRITICAL"]:
        try:
            explanation = explain_transaction(
                ml_model, txn_for_ml, velocity_for_ml
            )
        except Exception:
            explanation = None

    tier = final_tier
    recommendations = {
        "LOW":      "APPROVE",
        "MEDIUM":   "REVIEW",
        "HIGH":     "HOLD",
        "CRITICAL": "BLOCK",
    }

    txn_data = {
        "id":         txn_id,
        "type":       request.transaction_type,
        "amount":     request.amount,
        "sender":     request.sender_account,
        "receiver":   request.receiver_account,
        "city":       request.city,
        "risk_score": final_score,
        "risk_tier":  final_tier,
    }
    insert_transaction(txn_data)

    processing_ms = int((time.time() - start_time) * 1000)

    # WebSocket broadcast
    await manager.broadcast({
        "type":           "new_transaction",
        "transaction_id": txn_id,
        "risk_score":     final_score,
        "risk_tier":      final_tier,
        "amount":         request.amount,
        "sender":         request.sender_account,
        "city":           request.city or "Unknown",
        "timestamp":      datetime.utcnow().isoformat(),
    })

    return ScoreResponse(
        transaction_id = txn_id,
        risk_score     = final_score,
        risk_tier      = tier,
        recommendation = recommendations[tier],
        fraud_prob     = ml_result["fraud_prob"],
        processing_ms  = processing_ms,
        message        = f"Transaction {recommendations[tier]} — {tier} risk",
        explanation    = explanation,
        graph_info     = graph_info,
    )

@app.get("/api/v1/transactions")
async def list_transactions(limit: int = 20):
    rows = get_all_transactions()
    transactions = []
    for row in rows[:limit]:
        transactions.append({
            "transaction_id":   row[0],
            "transaction_type": row[1],
            "amount":           float(row[2]),
            "sender":           row[3],
            "city":             row[4],
            "risk_score":       float(row[5]) if row[5] else 0,
            "risk_tier":        row[6] or "LOW",
            "created_at":       str(row[7]),
        })
    return {"total": len(transactions), "transactions": transactions}

@app.get("/api/v1/stats")
async def get_stats():
    rows  = get_all_transactions()
    total = len(rows)
    return {
        "total_transactions": total,
        "message":            f"{total} transactions processed so far!",
        "api_status":         "running",
        "ml_model":           "XGBoost v1.0",
        "websocket_clients":  len(manager.active_connections),
    }

@app.post("/api/v1/feedback")
async def submit_feedback(request: FeedbackRequest):
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
            "success":        True,
            "message":        f"Feedback recorded: {request.verdict}",
            "transaction_id": request.transaction_id,
            "analyst_id":     request.analyst_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/cases")
async def list_cases():
    from db_setup import get_connection
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            SELECT transaction_id, transaction_type, amount,
                   sender_account, city, risk_score, risk_tier, created_at
            FROM transactions
            WHERE risk_tier IN ('HIGH', 'CRITICAL')
            ORDER BY created_at DESC
            LIMIT 50
        """)
        rows  = cur.fetchall()
        cases = []
        for row in rows:
            tier = row[6]
            cases.append({
                "transaction_id":   row[0],
                "transaction_type": row[1],
                "amount":           float(row[2]),
                "sender":           row[3],
                "city":             row[4],
                "risk_score":       float(row[5]) if row[5] else 0,
                "risk_tier":        tier,
                "created_at":       str(row[7]),
                "sla_hours":        0.5 if tier == "CRITICAL" else 4,
                "action_required":  "BLOCK" if tier == "CRITICAL" else "HOLD",
            })
        cur.close()
        conn.close()
        return {"total_cases": len(cases), "cases": cases}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/transaction/{transaction_id}")
async def get_transaction(transaction_id: str):
    from db_setup import get_connection
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("""
            SELECT transaction_id, transaction_type, amount,
                   sender_account, receiver_account, city,
                   risk_score, risk_tier, created_at
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
            "LOW": "APPROVE", "MEDIUM": "REVIEW",
            "HIGH": "HOLD",   "CRITICAL": "BLOCK",
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

# ── WebSocket Endpoint ────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)