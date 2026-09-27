import time
from backend.models.tool_outputs import GraphResult, ProfileResult, ScoreResult
from backend.models.transaction import Transaction
from backend.config import score as score_config
from backend.logger import get_logger


def score_transaction(
    tx: Transaction,
    graph: GraphResult,
    profile: ProfileResult,
    trace_id: str
) -> ScoreResult:
    log_ctx = get_logger(trace_id)
    start = time.time()

    weights = score_config["weights"]
    threshold = score_config["block_threshold"]

    total = 0.0
    triggered = []

    # 图谱维度
    if graph.success:
        if graph.shared_device_count >= 2:
            total += weights["shared_device_2plus"]
            triggered.append("shared_device_count >= 2")

        if graph.pagerank > 0.7:
            total += weights["pagerank_above_07"]
            triggered.append("pagerank > 0.7")

        if graph.community_id is not None:
            total += weights["community_detected"]
            triggered.append("community_detected")

    # 画像维度
    if profile.success:
        if profile.days_since_open < 30:
            total += weights["account_age_under_30"]
            triggered.append("account_age < 30 days")

        if profile.amount_deviation_ratio > 10:
            total += weights["amount_deviation_10x"]
            triggered.append("amount_deviation > 10x")

        if profile.night_transaction_ratio > 0.5:
            total += weights["night_ratio_above_50"]
            triggered.append("night_ratio > 50%")

    # 交易维度
    if tx.amount > 10000:
        total += weights["amount_above_10k"]
        triggered.append("amount > 10000")

    if tx.type == "TRANSFER":
        total += weights["type_transfer"]
        triggered.append("type = TRANSFER")

    risk_score = round(min(total, 1.0), 4)
    decision = "block" if risk_score >= threshold else "pass"

    duration_ms = round((time.time() - start) * 1000)
    log_ctx.info("scoring_tool",
                 status="success",
                 risk_score=risk_score,
                 decision=decision,
                 triggered_count=len(triggered),
                 duration_ms=duration_ms)

    return ScoreResult(
        success=True,
        risk_score=risk_score,
        decision=decision,
        triggered_rules=triggered
    )