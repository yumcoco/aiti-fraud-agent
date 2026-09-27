"""
Transaction producer — replays PaySim CSV into Redis Streams.
Simulates CDC event stream from core banking system.
Run: python producer/transaction_producer.py
"""
import sys
import time
import hashlib
import json
import pandas as pd
from pathlib import Path
from redis import Redis
from neo4j import GraphDatabase
from backend.models.transaction import Transaction
from datetime import datetime, timedelta

ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))

from backend.config import redis as redis_config, neo4j as neo4j_config, demo

PAYSIM_PATH = ROOT / "data" / "paysim" / "PS_20174392719_1491204439457_log.csv"
INTERVAL = demo["producer_interval_seconds"]

redis_client = Redis(host="localhost", port=6379, decode_responses=True)
neo4j_driver = GraphDatabase.driver(
    neo4j_config["uri"],
    auth=(neo4j_config["user"], neo4j_config["password"])
)


def make_transaction(row, sent: int) -> dict:
    tx_time = datetime(2024, 1, 1) + timedelta(hours=int(row["step"]))

    tx = Transaction(
        transaction_id=f"TXN_{row['nameOrig']}_{sent}",
        account_id=row["nameOrig"],
        dest_account=row["nameDest"],
        amount=float(row["amount"]),
        type=row["type"],
        timestamp=tx_time,
    )
    tx.signature = tx.compute_signature()

    # 转成 Redis 可存的字符串格式
    return {
        "transaction_id": tx.transaction_id,
        "account_id": tx.account_id,
        "dest_account": tx.dest_account,
        "amount": str(tx.amount),
        "type": tx.type,
        "timestamp": tx.timestamp.isoformat(),
        "is_fraud": str(row["isFraud"]),
        "signature": tx.signature,
    }


def update_neo4j(tx: dict):
    """Simulate CDC: add new transfer edge to graph in real time."""
    try:
        with neo4j_driver.session() as s:
            s.run("""
                MERGE (a:Account {id: $src})
                MERGE (b:Account {id: $dst})
                MERGE (a)-[:TRANSFERS_TO {amount: $amt}]->(b)
            """, src=tx["account_id"], dst=tx["dest_account"],
                  amt=float(tx["amount"]))
    except Exception as e:
        print(f"  Neo4j update failed: {e}")


def main():
    print(f"Loading PaySim from {PAYSIM_PATH}...")
    df = pd.read_csv(PAYSIM_PATH,
                     usecols=["step", "type", "nameOrig",
                               "nameDest", "amount", "isFraud"])

    df = df[
        df["type"].isin(["TRANSFER", "CASH_OUT"]) &
        df["nameOrig"].str.startswith("C")
    ].reset_index(drop=True)

    print(f"Transactions to replay: {len(df):,}")
    print(f"Fraud transactions: {df['isFraud'].sum():,}")
    print(f"Interval: {INTERVAL}s per transaction")
    print("Starting replay... (Ctrl+C to stop)\n")

    stream = redis_config["stream_name"]
    sent = 0
    fraud_sent = 0

    for step, group in df.groupby("step"):
        for _, row in group.iterrows():
            tx_data = make_transaction(row, sent)

            redis_client.xadd(stream, tx_data)
            update_neo4j(tx_data)

            sent += 1
            if row["isFraud"] == 1:
                fraud_sent += 1

            if sent % 100 == 0:
                print(f"Sent: {sent:,} | Fraud: {fraud_sent} | Step: {step}")

            time.sleep(INTERVAL)

    print(f"\nDone. Total sent: {sent:,}, Fraud: {fraud_sent}")
if __name__ == "__main__":
    main()