from pydantic import BaseModel
from typing import Optional, List


class SharedDevice(BaseModel):
    device_id: str
    accounts_sharing: List[str]
    share_count: int


class RelatedAccount(BaseModel):
    id: str
    community_id: Optional[int] = None
    centrality: float = 0.0


class GraphResult(BaseModel):
    success: bool
    community_id: Optional[int] = None
    pagerank: float = 0.0
    network_size: int = 0
    shared_device_count: int = 0
    shared_devices: List[SharedDevice] = []
    high_centrality_neighbors: int = 0
    related_accounts: List[RelatedAccount] = []
    error: Optional[str] = None


class ProfileResult(BaseModel):
    success: bool
    days_since_open: int = 0
    avg_transaction_amount: float = 0.0
    amount_deviation_ratio: float = 0.0
    night_transaction_ratio: float = 0.0
    cross_account_transfer_ratio: float = 0.0
    transaction_frequency_7d: int = 0
    error: Optional[str] = None


class ScoreResult(BaseModel):
    success: bool
    risk_score: float = 0.0
    decision: str = "pass"
    triggered_rules: List[str] = []
    error: Optional[str] = None


class SARReport(BaseModel):
    success: bool
    report_text: Optional[str] = None
    report_status: str = "verified"
    error: Optional[str] = None