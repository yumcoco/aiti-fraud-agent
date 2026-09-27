from datetime import datetime
from backend.config import rules
from backend.models.transaction import Transaction
from backend.logger import get_logger

log = get_logger()


def is_business_hours(timestamp: datetime) -> bool:
    hour = timestamp.hour
    return rules["business_hours_start"] <= hour < rules["business_hours_end"]


def evaluate(tx: Transaction, account_age_days: int, blacklist: set) -> str:
    log_ctx = log.bind(
        transaction_id=tx.transaction_id,
        account_id=tx.account_id,
        amount=tx.amount
    )

    # 黑名单检查 — 最快路径
    if tx.account_id in blacklist:
        log_ctx.info("rules_engine", result="investigate", reason="blacklist")
        return "investigate"

    # 金额阈值
    if tx.amount < rules["min_amount_threshold"]:
        log_ctx.info("rules_engine", result="pass", reason="amount_below_threshold")
        return "pass"

    # 账户年龄
    if account_age_days > rules["max_account_age_days"]:
        log_ctx.info("rules_engine", result="pass", reason="account_age_ok")
        return "pass"

    # 交易时间
    if is_business_hours(tx.timestamp):
        log_ctx.info("rules_engine", result="pass", reason="business_hours")
        return "pass"

    log_ctx.info("rules_engine", result="investigate", reason="all_rules_triggered")
    return "investigate"