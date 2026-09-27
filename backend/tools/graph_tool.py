import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from backend.internal_api.graph_service import query_account_network
from backend.models.tool_outputs import GraphResult, SharedDevice, RelatedAccount
from backend.config import graph
from backend.logger import get_logger

log = get_logger()


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(min=1, max=4),
    retry=retry_if_exception_type(Exception),
    reraise=False
)
def _query_with_retry(account_id: str, hop_depth: int) -> dict | None:
    return query_account_network(account_id, hop_depth)


def investigate_transaction_network(
    account_id: str,
    trace_id: str,
    hop_depth: int = None
) -> GraphResult:
    if hop_depth is None:
        hop_depth = graph["hop_depth"]

    log_ctx = get_logger(trace_id)
    start = time.time()

    try:
        raw = _query_with_retry(account_id, hop_depth)

        if raw is None:
            log_ctx.warning("graph_tool", status="fallback", account_id=account_id)
            return GraphResult(success=False, error="Graph query returned no data")

        duration_ms = round((time.time() - start) * 1000)
        log_ctx.info("graph_tool",
                     status="success",
                     account_id=account_id,
                     community_id=raw.get("community_id"),
                     duration_ms=duration_ms)

        return GraphResult(
            success=True,
            community_id=raw.get("community_id"),
            pagerank=raw.get("pagerank", 0.0),
            network_size=raw.get("network_size", 0),
            shared_device_count=raw.get("shared_device_count", 0),
            shared_devices=[
                SharedDevice(**d) for d in raw.get("shared_devices", [])
            ],
            high_centrality_neighbors=raw.get("high_centrality_neighbors", 0),
            related_accounts=[
                RelatedAccount(**r) for r in raw.get("related_accounts", [])
            ]
        )

    except Exception as e:
        duration_ms = round((time.time() - start) * 1000)
        log_ctx.error("graph_tool",
                      status="failed",
                      account_id=account_id,
                      error=str(e),
                      duration_ms=duration_ms)
        return GraphResult(success=False, error=str(e))