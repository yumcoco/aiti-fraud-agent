"""
Experiment 1: Lower PageRank trigger threshold 0.7 → 0.5
Control: all other parameters unchanged
"""
import json, sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent.parent.parent
load_dotenv(ROOT / ".env")
sys.path.append(str(ROOT))

from backend.models.transaction import Transaction
from backend.internal_api.feature_store import load_features
from backend.internal_api.blacklist import load_blacklist
from backend.tools.graph_tool import investigate_transaction_network
from backend.tools.profile_tool import get_risk_profile
from backend.models.tool_outputs import GraphResult, ProfileResult

BLOCK_THRESHOLD = 0.55
WEIGHTS = {
    "shared_device_2plus": 0.25,
    "pagerank_above_05": 0.15,   # threshold changed to 0.5
    "community_detected": 0.10,
    "account_age_under_30": 0.15,
    "amount_deviation_10x": 0.12,
    "night_ratio_above_50": 0.08,
    "amount_above_10k": 0.10,
    "type_transfer": 0.05,
}

def score(tx, graph, profile):
    total = 0.0
    triggered = []
    if graph.success:
        if graph.shared_device_count >= 2:
            total += WEIGHTS["shared_device_2plus"]
            triggered.append("shared_device >= 2")
        if graph.pagerank > 0.5:          # ← changed from 0.7
            total += WEIGHTS["pagerank_above_05"]
            triggered.append("pagerank > 0.5")
        if graph.community_id is not None:
            total += WEIGHTS["community_detected"]
            triggered.append("community_detected")
    if profile.success:
        if profile.days_since_open < 30:
            total += WEIGHTS["account_age_under_30"]
            triggered.append("account_age < 30")
        if profile.amount_deviation_ratio > 10:
            total += WEIGHTS["amount_deviation_10x"]
            triggered.append("amount_deviation > 10x")
        if profile.night_transaction_ratio > 0.5:
            total += WEIGHTS["night_ratio_above_50"]
            triggered.append("night_ratio > 50%")
    if tx.amount > 10000:
        total += WEIGHTS["amount_above_10k"]
        triggered.append("amount > 10000")
    if tx.type == "TRANSFER":
        total += WEIGHTS["type_transfer"]
        triggered.append("type = TRANSFER")
    decision = "block" if total >= BLOCK_THRESHOLD else "pass"
    return round(min(total, 1.0), 4), decision, triggered

def main():
    load_features()
    load_blacklist()

    with open(ROOT / "tests/evaluation/ground_truth.json") as f:
        cases = json.load(f)

    results = []
    tp = fp = tn = fn = 0

    for case in cases:
        tx_data = case["transaction"]
        expected = case["expected_decision"]
        tx = Transaction(
            transaction_id=tx_data["transaction_id"],
            account_id=tx_data["account_id"],
            dest_account=tx_data["dest_account"],
            amount=float(tx_data["amount"]),
            type=tx_data["type"],
            timestamp=datetime.fromisoformat(tx_data["timestamp"]),
        )
        tx.signature = tx.compute_signature()
        graph = investigate_transaction_network(tx_data["account_id"], trace_id="exp1")
        profile = get_risk_profile(tx_data["account_id"], trace_id="exp1")
        risk_score, predicted, triggered = score(tx, graph, profile)

        if expected == "block" and predicted == "block": tp += 1
        elif expected == "pass" and predicted == "block": fp += 1
        elif expected == "pass" and predicted == "pass":  tn += 1
        elif expected == "block" and predicted == "pass": fn += 1

        results.append({
            "id": case["id"],
            "expected": expected,
            "predicted": predicted,
            "correct": predicted == expected,
            "risk_score": risk_score,
            "triggered": triggered,
        })

    recall    = tp/(tp+fn) if (tp+fn) > 0 else 0
    precision = tp/(tp+fp) if (tp+fp) > 0 else 0
    f1        = 2*precision*recall/(precision+recall) if (precision+recall) > 0 else 0

    print(f"""
Experiment 1: PageRank threshold 0.7 → 0.5
{'='*50}
  TP={tp} TN={tn} FP={fp} FN={fn}
  Recall:    {recall:.3f}
  Precision: {precision:.3f}
  F1:        {f1:.3f}
{'='*50}
""")

    output = {
        "experiment": "exp1_pagerank_threshold_05",
        "change": "pagerank threshold 0.7 → 0.5",
        "metrics": {"recall": round(recall,3), "precision": round(precision,3), "f1": round(f1,3),
                    "tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "results": results,
    }
    with open(ROOT / "tests/evaluation/experiments/exp1_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("Saved to tests/evaluation/experiments/exp1_results.json")

if __name__ == "__main__":
    main()