# @Versin:1.0
# @Author:Sha Li
# @Date:2026/9/27
# @Description:
"""
Initialize PostgreSQL database schema.
Run once: python scripts/init_db.py
"""
import psycopg2
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from backend.config import pg


def main():
    conn = psycopg2.connect(
        host=pg["host"],
        port=pg["port"],
        dbname=pg["db"],
        user=pg["user"],
        password=pg["password"]
    )
    cur = conn.cursor()

    print("Creating decisions table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            transaction_id   TEXT PRIMARY KEY,
            account_id       TEXT NOT NULL,
            dest_account     TEXT,
            amount           REAL,
            transaction_type TEXT,
            decision         TEXT NOT NULL,
            risk_score       REAL,
            triggered_rules  JSONB DEFAULT '[]',
            graph_result     JSONB,
            profile_result   JSONB,
            sar_report       TEXT,
            report_status    TEXT DEFAULT 'n/a',
            model_version    TEXT DEFAULT 'champion',
            trace_id         TEXT,
            graph_available  BOOLEAN DEFAULT TRUE,
            created_at       TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    print("Creating indexes...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_decisions_account_id
        ON decisions(account_id)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_decisions_decision
        ON decisions(decision)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_decisions_created_at
        ON decisions(created_at DESC)
    """)

    print("Creating chat_sessions table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id   TEXT PRIMARY KEY,
            username     TEXT NOT NULL,
            title        TEXT,
            created_at   TIMESTAMPTZ DEFAULT NOW(),
            updated_at   TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    print("Creating chat_messages table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id           SERIAL PRIMARY KEY,
            session_id   TEXT REFERENCES chat_sessions(session_id),
            role         TEXT NOT NULL,
            content      TEXT NOT NULL,
            created_at   TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    conn.commit()
    conn.close()
    print("Done — database schema initialized")


if __name__ == "__main__":
    main()