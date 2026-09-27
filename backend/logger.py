import structlog
import logging
import uuid
from datetime import datetime

logging.basicConfig(
    format="%(message)s",
    level=logging.INFO,
)

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

def generate_trace_id(account_id: str) -> str:
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    rand = uuid.uuid4().hex[:4]
    return f"{account_id}-{ts}-{rand}"

def get_logger(trace_id: str = None):
    if trace_id:
        return logger.bind(trace_id=trace_id)
    return logger