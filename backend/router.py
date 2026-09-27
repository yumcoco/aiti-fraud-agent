import hashlib
from backend.config import cc
from backend.logger import get_logger

log = get_logger()


def route_to_model(transaction_id: str) -> str:
    """
    Champion-Challenger routing.
    Currently 100% champion. Challenger ratio controlled via config.yaml.
    """
    ratio = cc["challenger_traffic_ratio"]

    if ratio == 0.0:
        return "champion"

    # 用 transaction_id hash 做确定性分流
    # 同一笔交易永远路由到同一个模型
    hash_val = int(hashlib.md5(transaction_id.encode()).hexdigest(), 16)
    if (hash_val % 100) < (ratio * 100):
        log.info("router", model="challenger", transaction_id=transaction_id)
        return "challenger"

    return "champion"