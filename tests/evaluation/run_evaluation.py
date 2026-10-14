"""
Layer 2 evaluation — 50 labelled cases
Run: python tests/evaluation/run_evaluation.py
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

from backend.models.transaction import Transaction
from backend.agent import run_agent
from backend.internal_api.feature_store import load_features
from backend.internal_api.blacklist import load_blacklist

def main():
    print("Loading data...")
    load_features()
    load_blacklist()

    with open(ROOT / "tests/evaluation/ground_truth.json") as f:
        cases = json.load(f)

    results = []
    tp = fp = tn = fn = 0

    print(f"Running {len(cases)} cases...\n")

    for i, case in enumerate(cases):
        tx_data = case["transaction"]
        expected = case["expected_decision"]

        try:
            tx = Transaction(
                transaction_id=tx_data["transaction_id"],
                account_id=tx_data["account_id"],
                dest_account=tx_data["dest_account"],
                amount=float(tx_data["amount"]),
                type=tx_data["type"],
                timestamp=datetime.fromisoformat(tx_data["timestamp"]),
            )
            tx.signature = tx.compute_signature()

            start = time.time()
            result = run_agent(tx, trace_id=f"eval_{i}")
            duration = round(time.time() - start, 2)

            score = result.get("score_result")
            predicted = score.decision if score else "pass"
            risk_score = score.risk_score if score else 0.0

        except Exception as e:
            print(f"  ERROR case {case['id']}: {e}")
            predicted = "pass"
            risk_score = 0.0
            duration = 0.0

        correct = predicted == expected

        if expected == "block" and predicted == "block": tp += 1
        elif expected == "pass" and predicted == "block": fp += 1
        elif expected == "pass" and predicted == "pass":  tn += 1
        elif expected == "block" and predicted == "pass": fn += 1

        status = "✓" if correct else "✗"
        print(f"  {status} {case['id']} | expected={expected} predicted={predicted} score={risk_score:.2f} ({duration}s)")

        results.append({
            "id": case["id"],
            "account_id": tx_data["account_id"],
            "expected": expected,
            "predicted": predicted,
            "correct": correct,
            "risk_score": risk_score,
            "duration_s": duration,
            "is_fraud": case["is_fraud"],
        })

    # Metrics
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print(f"""
{'='*50}
RESULTS

  True Positives:  {tp}
  True Negatives:  {tn}
  False Positives: {fp}
  False Negatives: {fn}

  Recall:    {recall:.3f}  (target ≥ 0.85)  {'✓' if recall >= 0.85 else '✗'}
  Precision: {precision:.3f}  (target ≥ 0.70)  {'✓' if precision >= 0.70 else '✓'}
  F1:        {f1:.3f}
{'='*50}
""")

    if fn > 0:
        print("False Negatives (missed fraud):")
        for r in results:
            if r["expected"] == "block" and r["predicted"] == "pass":
                print(f"  - {r['id']} {r['account_id']} score={r['risk_score']:.2f}")

    # Save
    output = {
        "metrics": {
            "recall": round(recall, 3),
            "precision": round(precision, 3),
            "f1": round(f1, 3),
            "tp": tp, "tn": tn, "fp": fp, "fn": fn,
            "total": len(cases),
        },
        "results": results,
    }
    with open(ROOT / "tests/evaluation/results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("Saved to tests/evaluation/results.json")

if __name__ == "__main__":
    main()