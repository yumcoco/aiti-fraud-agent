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

STRICT GROUNDING RULES:
- Every sentence must reference a specific field from the evidence data below
- Do NOT use phrases like 'consistent with patterns', 'typically associated with', 'often indicates', 'atypical of standard behaviour'
- Do NOT add industry context, general knowledge, or inferences beyond the data
- Do NOT interpret what signals mean beyond what the data explicitly states
- If a field is unavailable, write "data unavailable"
- Every numerical claim must come directly from the evidence data
- Describe WHAT the data shows, not WHAT it implies
- For the Recommended action: be specific and actionable based on the risk signals found in the data (e.g. freeze account, escalate to compliance, expand investigation to related accounts)

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
[2-3 sentences describing ONLY what the data shows, no inferences]

Evidence chain:
1. [evidence from graph data with specific values]
2. [evidence from graph data with specific values]
3. [evidence from profile data with specific values]
4. [evidence from profile data with specific values]
5. [evidence from score with specific values]

Risk level: HIGH
Recommended action: [2-3 specific actions: account freeze, investigation scope, regulatory filing if applicable]
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