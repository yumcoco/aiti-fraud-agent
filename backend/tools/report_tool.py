import time
import re
from anthropic import Anthropic
from backend.models.tool_outputs import GraphResult, ProfileResult, ScoreResult, SARReport
from backend.models.transaction import Transaction
from backend.config import llm
from backend.logger import get_logger

client = Anthropic()


def generate_sar_report(
    tx: Transaction,
    graph: GraphResult,
    profile: ProfileResult,
    score: ScoreResult,
    trace_id: str
) -> SARReport:
    log_ctx = get_logger(trace_id)
    start = time.time()

    import uuid, datetime
    case_id = f"SAR-{datetime.date.today().strftime('%Y')}-{uuid.uuid4().hex[:4].upper()}"

    prompt = f"""You are a bank compliance officer. Generate a SAR report using ONLY the data provided below.
Do NOT invent or add any information not present in the data.
If a field is unavailable, write "data unavailable".

TRANSACTION DATA:
- Transaction ID: {tx.transaction_id}
- Account: {tx.account_id}
- Destination: {tx.dest_account}
- Amount: €{tx.amount:,.2f}
- Type: {tx.type}
- Timestamp: {tx.timestamp}

GRAPH ANALYSIS:
- Community ID: {graph.community_id}
- PageRank: {graph.pagerank}
- Network size: {graph.network_size}
- Shared device count: {graph.shared_device_count}
- Shared devices: {[d.device_id for d in graph.shared_devices]}

RISK PROFILE:
- Account age (days): {profile.days_since_open}
- Amount deviation: {profile.amount_deviation_ratio}x historical average
- Night transaction ratio: {profile.night_transaction_ratio:.0%}

SCORE:
- Risk score: {score.risk_score}
- Triggered rules: {', '.join(score.triggered_rules)}

Generate the report in this exact format:
Case ID: {case_id}
Involved account: [account]
Destination account: [account]
Amount: [amount]
Timestamp: [timestamp]

Suspicious behaviour:
[2-3 sentences describing the suspicious behaviour based on the data]

Evidence chain:
1. [evidence from graph data]
2. [evidence from graph data]
3. [evidence from profile data]
4. [evidence from profile data]
5. [evidence from score]

Risk level: HIGH
Recommended action: [specific action based on evidence]
"""

    for attempt in range(llm["max_retries"]):
        try:
            response = client.messages.create(
                model=llm["report_model"],
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            report_text = response.content[0].text

            # Grounding check
            score_in_report = _extract_score(report_text, score.risk_score)
            status = "verified" if score_in_report else "requires_review"

            duration_ms = round((time.time() - start) * 1000)
            log_ctx.info("report_tool",
                         status=status,
                         case_id=case_id,
                         duration_ms=duration_ms)

            return SARReport(
                success=True,
                report_text=report_text,
                report_status=status
            )

        except Exception as e:
            log_ctx.warning("report_tool",
                            status=f"attempt_{attempt+1}_failed",
                            error=str(e))

    log_ctx.error("report_tool", status="all_retries_failed")
    return SARReport(
        success=False,
        report_status="pending_manual_review",
        error="LLM unavailable after retries"
    )


def _extract_score(report_text: str, expected: float) -> bool:
    matches = re.findall(r'\b0\.\d+\b', report_text)
    for m in matches:
        if abs(float(m) - expected) < 0.05:
            return True
    return False