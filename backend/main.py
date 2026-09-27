from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json

from backend.auth import verify_credentials, create_token, get_current_user
from backend.config import pg
from backend.internal_api.feature_store import load_features
from backend.internal_api.blacklist import load_blacklist
from backend.internal_api.graph_service import get_driver
from backend.logger import get_logger

log = get_logger()

app = FastAPI(title="Anti-Fraud AI Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup ───────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    log.info("startup", status="loading_data")
    load_features()
    load_blacklist()
    get_driver()  # warm up Neo4j connection
    log.info("startup", status="ready")


# ── Auth ──────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/auth/login")
async def login(req: LoginRequest):
    user = verify_credentials(req.username, req.password)
    token = create_token(user["username"], user["role"])
    return {"access_token": token, "token_type": "bearer"}


# ── Health ────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Decisions feed (Dashboard) ────────────────────────────────────
@app.get("/api/v1/decisions/recent")
async def get_recent_decisions(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    import psycopg2
    conn = psycopg2.connect(
        host=pg["host"], port=pg["port"],
        dbname=pg["db"], user=pg["user"], password=pg["password"]
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT transaction_id, account_id, dest_account, amount,
               transaction_type, decision, risk_score, triggered_rules,
               report_status, model_version, trace_id, created_at
        FROM decisions
        ORDER BY created_at DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "transaction_id": r[0],
            "account_id": r[1],
            "dest_account": r[2],
            "amount": r[3],
            "type": r[4],
            "decision": r[5],
            "risk_score": r[6],
            "triggered_rules": r[7],
            "report_status": r[8],
            "model_version": r[9],
            "trace_id": r[10],
            "created_at": r[11].isoformat() if r[11] else None
        }
        for r in rows
    ]


# ── Single decision + SAR ─────────────────────────────────────────
@app.get("/api/v1/decision/{transaction_id}")
async def get_decision(
    transaction_id: str,
    current_user: dict = Depends(get_current_user)
):
    import psycopg2
    conn = psycopg2.connect(
        host=pg["host"], port=pg["port"],
        dbname=pg["db"], user=pg["user"], password=pg["password"]
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT transaction_id, account_id, dest_account, amount,
               transaction_type, decision, risk_score, triggered_rules,
               sar_report, report_status, trace_id, created_at
        FROM decisions WHERE transaction_id = %s
    """, (transaction_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {
        "transaction_id": row[0],
        "account_id": row[1],
        "dest_account": row[2],
        "amount": row[3],
        "type": row[4],
        "decision": row[5],
        "risk_score": row[6],
        "triggered_rules": row[7],
        "sar_report": row[8],
        "report_status": row[9],
        "trace_id": row[10],
        "created_at": row[11].isoformat() if row[11] else None
    }


# ── Chat endpoint ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str
    message: str
    account_context: Optional[str] = None


@app.post("/api/v1/chat")
async def chat(
    req: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    from backend.chat import handle_chat_stream
    return StreamingResponse(
        handle_chat_stream(req.session_id, req.message, req.account_context),
        media_type="text/event-stream"
    )


# ── FIU submission simulation ─────────────────────────────────────
@app.post("/api/v1/report/fiu/{transaction_id}")
async def submit_fiu(
    transaction_id: str,
    current_user: dict = Depends(get_current_user)
):
    import uuid
    ref = f"FIU-{uuid.uuid4().hex[:8].upper()}"
    log.info("fiu_submission",
             transaction_id=transaction_id,
             reference=ref,
             submitted_by=current_user["username"])
    return {
        "status": "submitted",
        "reference_number": ref,
        "transaction_id": transaction_id
    }