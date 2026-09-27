import hashlib
import json
from datetime import datetime
from pydantic import BaseModel, field_validator
from typing import Optional


class Transaction(BaseModel):
    transaction_id: str
    account_id: str
    dest_account: str
    amount: float
    type: str
    timestamp: datetime
    signature: Optional[str] = None

    def compute_signature(self) -> str:
        payload = {
            "transaction_id": self.transaction_id,
            "account_id": self.account_id,
            "dest_account": self.dest_account,
            "amount": self.amount,
            "type": self.type,
            "timestamp": self.timestamp.isoformat(),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()

    def verify_signature(self) -> bool:
        if not self.signature:
            return False
        return self.signature == self.compute_signature()

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v

    @field_validator("type")
    @classmethod
    def type_must_be_valid(cls, v):
        valid = {"TRANSFER", "CASH_OUT", "PAYMENT", "CASH_IN", "DEBIT"}
        if v not in valid:
            raise ValueError(f"Invalid transaction type: {v}")
        return v