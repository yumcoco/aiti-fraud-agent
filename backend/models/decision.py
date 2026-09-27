from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DecisionLog(BaseModel):
    transaction_id: str
    account_id: str
    dest_account: str
    amount: float
    transaction_type: str
    decision: str                          # block / pass
    risk_score: Optional[float] = None
    triggered_rules: List[str] = []
    graph_result: Optional[dict] = None    # raw GraphResult
    profile_result: Optional[dict] = None  # raw ProfileResult
    sar_report: Optional[str] = None
    report_status: str = "n/a"            # verified / requires_review / pending_manual_review / n/a
    model_version: str = "champion"
    trace_id: str = ""
    graph_available: bool = True
    created_at: datetime = None

    def model_post_init(self, __context):
        if self.created_at is None:
            self.created_at = datetime.utcnow()