import json
import asyncio
from typing import Optional, AsyncGenerator
from anthropic import Anthropic
from backend.config import llm, pg
from backend.internal_api.graph_service import query_account_network
from backend.internal_api.feature_store import get_account_features
from backend.logger import get_logger, generate_trace_id
import psycopg2

client = Anthropic()
log = get_logger()

SYSTEM_PROMPT = """You are a fraud investigation assistant for a bank FEC team.
You help investigators analyze accounts, understand fraud patterns, and generate compliance reports.

You can answer questions about:
- Account risk profiles and transaction patterns
- Fraud ring membership and graph connections
- SAR report details
- Block rate trends and statistics
- Specific transaction decisions

When asked about block rates, statistics, or recent activity, use the Global statistics provided in the context.
When referencing data, always cite the source (graph analysis, risk profile, or decision log).
Keep answers concise and evidence-based.

You ONLY answer questions related to fraud investigation and compliance.
For unrelated questions, politely redirect: "I'm a fraud investigation assistant. I can only help with account risk analysis and fraud investigation."
"""


def get_db_conn():
    return psycopg2.connect(
        host=pg["host"], port=pg["port"],
        dbname=pg["db"], user=pg["user"], password=pg["password"]
    )


def get_session_history(session_id: str) -> list:
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT role, content FROM chat_messages
            WHERE session_id = %s
            ORDER BY created_at ASC
            LIMIT 20
        """, (session_id,))
        rows = cur.fetchall()
        conn.close()
        return [{"role": r[0], "content": r[1]} for r in rows]
    except Exception:
        return []


def save_message(session_id: str, role: str, content: str, username: str):
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO chat_sessions (session_id, username, title)
            VALUES (%s, %s, %s)
            ON CONFLICT (session_id) DO UPDATE SET updated_at = NOW()
        """, (session_id, username, content[:50]))
        cur.execute("""
            INSERT INTO chat_messages (session_id, role, content)
            VALUES (%s, %s, %s)
        """, (session_id, role, content))
        conn.commit()
        conn.close()
    except Exception as e:
        log.error("chat", status="save_failed", error=str(e))


def gather_context(message: str, account_context: Optional[str]) -> str:
    context_parts = []

    try:
        conn = get_db_conn()
        cur = conn.cursor()

        # Global statistics
        cur.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN decision='block' THEN 1 ELSE 0 END) as blocked,
                AVG(risk_score) as avg_score
            FROM decisions
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """)
        stats = cur.fetchone()
        if stats and stats[0] > 0:
            block_rate = round((stats[1] or 0) / stats[0] * 100, 2)
            context_parts.append(f"""
Global statistics (last 24h):
- Total transactions: {stats[0]}
- Blocked: {stats[1] or 0}
- Block rate: {block_rate}%
- Avg risk score: {round(float(stats[2] or 0), 3)}
""")

        # Recent blocks
        cur.execute("""
            SELECT account_id, risk_score, triggered_rules, created_at
            FROM decisions
            WHERE decision = 'block'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        blocks = cur.fetchall()
        if blocks:
            block_text = "\n".join([
                f"  - {b[0]} score={b[1]} at {b[3]}"
                for b in blocks
            ])
            context_parts.append(f"Recent blocked accounts:\n{block_text}")

        conn.close()
    except Exception as e:
        log.error("chat", status="db_context_failed", error=str(e))

    # Account-specific context
    import re
    account_ids = re.findall(r'C\d{7,10}', message)
    if account_context:
        account_ids = [account_context] + account_ids

    for account_id in account_ids[:2]:
        # Graph data
        graph = query_account_network(account_id, hop_depth=2)
        if graph:
            context_parts.append(f"""
Graph analysis for {account_id}:
- Community ID: {graph.get('community_id')}
- PageRank: {graph.get('pagerank', 0):.3f}
- Network size: {graph.get('network_size')}
- Shared devices: {graph.get('shared_device_count')}
""")

        # Profile data
        profile = get_account_features(account_id)
        if profile:
            context_parts.append(f"""
Risk profile for {account_id}:
- Account age: {profile.get('days_since_open')} days
- Avg amount: €{profile.get('avg_transaction_amount', 0):,.2f}
- Night ratio: {profile.get('night_transaction_ratio', 0):.0%}
- Cross-account ratio: {profile.get('cross_account_transfer_ratio', 0):.0%}
""")

        # Recent decisions for this account
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            cur.execute("""
                SELECT decision, risk_score, triggered_rules, created_at
                FROM decisions WHERE account_id = %s
                ORDER BY created_at DESC LIMIT 10
            """, (account_id,))
            decisions = cur.fetchall()
            conn.close()
            if decisions:
                dec_text = "\n".join([
                    f"  - {d[0]} (score: {d[1]}) at {d[3]}"
                    for d in decisions
                ])
                context_parts.append(f"Recent decisions for {account_id}:\n{dec_text}")
        except Exception:
            pass

    return "\n".join(context_parts)


async def handle_chat_stream(
    session_id: str,
    message: str,
    account_context: Optional[str] = None,
    username: str = "investigator"
) -> AsyncGenerator[str, None]:

    trace_id = generate_trace_id(session_id)
    log.info("chat", status="start", session_id=session_id, trace_id=trace_id)

    save_message(session_id, "user", message, username)
    history = get_session_history(session_id)

    yield f"data: {json.dumps({'type': 'status', 'content': 'Gathering context...'})}\n\n"
    await asyncio.sleep(0)

    context = gather_context(message, account_context)

    messages = history[:-1] if history else []
    user_content = message
    if context:
        user_content = f"{message}\n\nRelevant data:\n{context}"

    messages.append({"role": "user", "content": user_content})

    full_response = ""
    yield f"data: {json.dumps({'type': 'status', 'content': 'Analyzing...'})}\n\n"
    await asyncio.sleep(0)

    try:
        with client.messages.stream(
            model=llm["decision_model"],
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                yield f"data: {json.dumps({'type': 'token', 'content': text})}\n\n"
                await asyncio.sleep(0)

    except Exception as e:
        log.error("chat", status="stream_failed", error=str(e), trace_id=trace_id)
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        return

    save_message(session_id, "assistant", full_response, username)
    yield f"data: {json.dumps({'type': 'done'})}\n\n"
    log.info("chat", status="complete", session_id=session_id, trace_id=trace_id)