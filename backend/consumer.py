import json
import asyncio
import psycopg2
from datetime import datetime
from redis import Redis
from backend.config import redis as redis_config, pg
from backend.models.transaction import Transaction
from backend.rules_engine import evaluate
from backend.agent import run_agent
from backend.router import route_to_model
from backend.internal_api.blacklist import get_blacklist, is_blacklisted
from backend.internal_api.feature_store import get_account_features
from backend.logger import get_logger, generate_trace_id
from backend.internal_api.feature_store import load_features, get_account_features
from backend.internal_api.blacklist import load_blacklist, get_blacklist, is_blacklisted
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
# 在模块级别加载
load_features()
load_blacklist()

log = get_logger()

redis_client = Redis(host="localhost", port=6379, decode_responses=True)


def get_account_age(account_id: str) -> int:
    features = get_account_features(account_id)
    if features:
        return features.get("days_since_open", 365)
    return 365


def save_decision(decision_data: dict):
    conn = psycopg2.connect(
        host=pg["host"], port=pg["port"],
        dbname=pg["db"], user=pg["user"], password=pg["password"]
    )
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO decisions (
            transaction_id, account_id, dest_account, amount,
            transaction_type, decision, risk_score, triggered_rules,
            graph_result, profile_result, sar_report, report_status,
            model_version, trace_id, graph_available
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (transaction_id) DO UPDATE SET
            sar_report = EXCLUDED.sar_report,
            report_status = EXCLUDED.report_status,
            decision = EXCLUDED.decision,
            risk_score = EXCLUDED.risk_score,
            triggered_rules = EXCLUDED.triggered_rules
    """, (
        decision_data["transaction_id"],
        decision_data["account_id"],
        decision_data["dest_account"],
        decision_data["amount"],
        decision_data["transaction_type"],
        decision_data["decision"],
        decision_data.get("risk_score"),
        json.dumps(decision_data.get("triggered_rules", [])),
        json.dumps(decision_data.get("graph_result")),
        json.dumps(decision_data.get("profile_result")),
        decision_data.get("sar_report"),
        decision_data.get("report_status", "n/a"),
        decision_data.get("model_version", "champion"),
        decision_data.get("trace_id"),
        decision_data.get("graph_available", True),
    ))
    conn.commit()
    conn.close()


def process_transaction(tx_data: dict):
    trace_id = generate_trace_id(tx_data.get("account_id", "unknown"))

    try:
        tx = Transaction(
            transaction_id=tx_data["transaction_id"],
            account_id=tx_data["account_id"],
            dest_account=tx_data["dest_account"],
            amount=float(tx_data["amount"]),
            type=tx_data["type"],
            timestamp=datetime.fromisoformat(tx_data["timestamp"]),
            signature=tx_data.get("signature")
        )
    except Exception as e:
        log.error("consumer", status="parse_failed",
                  error=str(e), trace_id=trace_id)
        return

    # Signature check
    if not tx.verify_signature():
        log.warning("consumer", status="invalid_signature",
                    transaction_id=tx.transaction_id, trace_id=trace_id)
        return

    # Champion-Challenger routing
    model_version = route_to_model(tx.transaction_id)

    # Rules engine
    account_age = get_account_age(tx.account_id)
    blacklist = get_blacklist()
    rule_result = evaluate(tx, account_age, blacklist)

    if rule_result == "pass":
        save_decision({
            "transaction_id": tx.transaction_id,
            "account_id": tx.account_id,
            "dest_account": tx.dest_account,
            "amount": tx.amount,
            "transaction_type": tx.type,
            "decision": "pass",
            "model_version": model_version,
            "trace_id": trace_id,
        })
        return

    # Agent
    result = run_agent(tx, trace_id)
    score = result.get("score_result")
    graph = result.get("graph_result")
    profile = result.get("profile_result")
    sar = result.get("sar_report")

    save_decision({
        "transaction_id": tx.transaction_id,
        "account_id": tx.account_id,
        "dest_account": tx.dest_account,
        "amount": tx.amount,
        "transaction_type": tx.type,
        "decision": score.decision if score else "unknown",
        "risk_score": score.risk_score if score else None,
        "triggered_rules": score.triggered_rules if score else [],
        "graph_result": graph.model_dump() if graph else None,
        "profile_result": profile.model_dump() if profile else None,
        "sar_report": sar.report_text if sar else None,
        "report_status": sar.report_status if sar else "n/a",
        "model_version": model_version,
        "trace_id": trace_id,
        "graph_available": graph.success if graph else False,
    })


def run_consumer():
    stream = redis_config["stream_name"]
    group = redis_config["consumer_group"]
    consumer = redis_config["consumer_name"]

    # Create consumer group
    try:
        redis_client.xgroup_create(stream, group, id="0", mkstream=True)
        log.info("consumer", status="group_created", group=group)
    except Exception:
        log.info("consumer", status="group_exists", group=group)

    log.info("consumer", status="listening", stream=stream)

    while True:
        try:
            messages = redis_client.xreadgroup(
                group, consumer, {stream: ">"}, count=1, block=1000
            )
            if not messages:
                continue

            for stream_name, entries in messages:
                for entry_id, data in entries:
                    try:
                        process_transaction(data)
                        redis_client.xack(stream, group, entry_id)
                    except Exception as e:
                        log.error("consumer",
                                  status="processing_failed",
                                  error=str(e),
                                  entry_id=entry_id)
                        redis_client.xack(stream, group, entry_id)

        except KeyboardInterrupt:
            log.info("consumer", status="stopped")
            break
        except Exception as e:
            log.error("consumer", status="error", error=str(e))
            import time
            time.sleep(1)


if __name__ == "__main__":
    run_consumer()