from pathlib import Path
from typing import Optional
import pandas as pd
from backend.logger import get_logger

log = get_logger()

ROOT = Path(__file__).parent.parent.parent
PARQUET_PATH = ROOT / "data" / "processed" / "features.parquet"

_df: Optional[pd.DataFrame] = None


def load_features() -> None:
    global _df
    if not PARQUET_PATH.exists():
        log.warning("feature_store", status="file_not_found", path=str(PARQUET_PATH))
        _df = None
        return

    _df = pd.read_parquet(PARQUET_PATH)
    log.info("feature_store", status="loaded", rows=len(_df))


def get_account_features(account_id: str) -> Optional[dict]:
    if _df is None:
        log.warning("feature_store", status="not_loaded", account_id=account_id)
        return None

    rows = _df[_df["account_id"] == account_id]
    if rows.empty:
        log.warning("feature_store", status="account_not_found", account_id=account_id)
        return None

    row = rows.iloc[0]
    return {
        "days_since_open":              int(row.get("days_since_open", 0)),
        "avg_transaction_amount":       float(row.get("avg_amount", 0.0)),
        "amount_deviation_ratio":       float(row.get("amount_deviation", 0.0)),
        "night_transaction_ratio":      float(row.get("night_ratio", 0.0)),
        "cross_account_transfer_ratio": float(row.get("cross_ratio", 0.0)),
        "transaction_frequency_7d":     int(row.get("freq_7d", 0)),
    }