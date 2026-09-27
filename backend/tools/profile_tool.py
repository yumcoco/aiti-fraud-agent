import time
from backend.internal_api.feature_store import get_account_features
from backend.models.tool_outputs import ProfileResult
from backend.logger import get_logger


def get_risk_profile(account_id: str, trace_id: str) -> ProfileResult:
    log_ctx = get_logger(trace_id)
    start = time.time()

    try:
        raw = get_account_features(account_id)

        if raw is None:
            log_ctx.warning("profile_tool", status="fallback", account_id=account_id)
            return ProfileResult(success=False, error="Account not found in feature store")

        duration_ms = round((time.time() - start) * 1000)
        log_ctx.info("profile_tool",
                     status="success",
                     account_id=account_id,
                     days_since_open=raw["days_since_open"],
                     amount_deviation=raw["amount_deviation_ratio"],
                     duration_ms=duration_ms)

        return ProfileResult(
            success=True,
            days_since_open=raw["days_since_open"],
            avg_transaction_amount=raw["avg_transaction_amount"],
            amount_deviation_ratio=raw["amount_deviation_ratio"],
            night_transaction_ratio=raw["night_transaction_ratio"],
            cross_account_transfer_ratio=raw["cross_account_transfer_ratio"],
            transaction_frequency_7d=raw["transaction_frequency_7d"]
        )

    except Exception as e:
        duration_ms = round((time.time() - start) * 1000)
        log_ctx.error("profile_tool",
                      status="failed",
                      account_id=account_id,
                      error=str(e),
                      duration_ms=duration_ms)
        return ProfileResult(success=False, error=str(e))