"""
Layer 3: LLM-as-Judge SAR quality evaluation
Run: python tests/evaluation/judge_scores.py
"""
import json
import sys
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent.parent
load_dotenv(ROOT / ".env")
sys.path.append(str(ROOT))

from anthropic import Anthropic
from backend.models.transaction import Transaction
from backend.agent import run_agent
from backend.internal_api.feature_store import load_features
from backend.internal_api.blacklist import load_blacklist

client = Anthropic()

JUDGE_PROMPT = """You are a DNB compliance reviewer evaluating a Suspicious Activity Report (SAR).

Score this SAR on 4 dimensions, each 1-5:

1. Evidence completeness: Are all triggered risk signals cited with source data?
2. Logical consistency: Does the recommended action match the risk level?
3. Required fields: Are all SAR fields present (case ID, accounts, behaviour, evidence, risk level, recommendation)?
4. Grounding accuracy: Does the report contain only facts from the provided evidence? No invented data?

Evidence provided to the system:
{evidence}

SAR Report:
{report}

Return JSON only, no explanation:
{{"evidence": N, "logic": N, "fields": N, "grounding": N}}"""


def main():
    print("Loading data...")
    load_features()
    load_blacklist()

    with open(ROOT / "tests/evaluation/ground_truth.json") as f:
        cases = json.load(f)

    # Only use fraud cases (block decisions generate SAR)
    fraud_cases = [c for c in cases if c["is_fraud"]][:10]
    print(f"Evaluating SAR quality for {len(fraud_cases)} blocked cases...\n")

    scores = []

    for i, case in enumerate(fraud_cases):
        tx_data = case["transaction"]
        print(f"  [{i+1}/10] {tx_data['account_id']}...", end=" ", flush=True)

        try:
            tx = Transaction(
                transaction_id=f"JUDGE_{tx_data['transaction_id']}",
                account_id=tx_data["account_id"],
                dest_account=tx_data["dest_account"],
                amount=float(tx_data["amount"]),
                type=tx_data["type"],
                timestamp=datetime.fromisoformat(tx_data["timestamp"]),
            )
            tx.signature = tx.compute_signature()

            result = run_agent(tx, trace_id=f"judge_{i}")
            sar = result.get("sar_report")
            graph = result.get("graph_result")
            profile = result.get("profile_result")
            score_result = result.get("score_result")

            if not sar or not sar.report_text:
                print("no SAR generated, skipping")
                continue

            # Build evidence summary
            evidence = f"""
Graph: community_id={graph.community_id if graph else None}, 
       pagerank={graph.pagerank if graph else 0},
       shared_devices={graph.shared_device_count if graph else 0}
Profile: days_since_open={profile.days_since_open if profile else None},
         amount_deviation={profile.amount_deviation_ratio if profile else None}
Score: risk_score={score_result.risk_score if score_result else None},
       triggered={score_result.triggered_rules if score_result else []}
"""

            # Judge call
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                messages=[{
                    "role": "user",
                    "content": JUDGE_PROMPT.format(
                        evidence=evidence,
                        report=sar.report_text
                    )
                }]
            )

            raw = response.content[0].text.strip()
            # del markdown
            if raw.startswith('```'):
                raw = raw.split('```')[1]
                if raw.startswith('json'):
                    raw = raw[4:]
                raw = raw.strip()
            judge_scores = json.loads(raw)
            avg = round(sum(judge_scores.values()) / len(judge_scores), 2)

            print(f"evidence={judge_scores['evidence']} logic={judge_scores['logic']} "
                  f"fields={judge_scores['fields']} grounding={judge_scores['grounding']} avg={avg}")

            scores.append({
                "case_id": case["id"],
                "account_id": tx_data["account_id"],
                "scores": judge_scores,
                "average": avg,
                "report_status": sar.report_status,
            })

        except Exception as e:
            print(f"ERROR: {e}")

        time.sleep(1)

    if not scores:
        print("No SAR reports generated.")
        return

    # Summary
    avg_evidence  = round(sum(s["scores"]["evidence"]  for s in scores) / len(scores), 2)
    avg_logic     = round(sum(s["scores"]["logic"]     for s in scores) / len(scores), 2)
    avg_fields    = round(sum(s["scores"]["fields"]    for s in scores) / len(scores), 2)
    avg_grounding = round(sum(s["scores"]["grounding"] for s in scores) / len(scores), 2)
    overall       = round(sum(s["average"] for s in scores) / len(scores), 2)

    print(f"""
{'='*50}
LLM-AS-JUDGE RESULTS ({len(scores)} SAR reports)

  Evidence completeness:  {avg_evidence} / 5.0
  Logical consistency:    {avg_logic} / 5.0
  Required fields:        {avg_fields} / 5.0
  Grounding accuracy:     {avg_grounding} / 5.0

  Overall average:        {overall} / 5.0  {'✓' if overall >= 4.0 else '✗'} (target ≥ 4.0)
{'='*50}
""")

    output = {
        "summary": {
            "total_reports": len(scores),
            "avg_evidence": avg_evidence,
            "avg_logic": avg_logic,
            "avg_fields": avg_fields,
            "avg_grounding": avg_grounding,
            "overall": overall,
            "target": 4.0,
            "passed": overall >= 4.0,
        },
        "details": scores,
    }

    with open(ROOT / "tests/evaluation/sar_scores.json", "w") as f:
        json.dump(output, f, indent=2)
    print("Saved to tests/evaluation/sar_scores.json")


if __name__ == "__main__":
    main()
