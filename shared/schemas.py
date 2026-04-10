# shared/schemas.py
#
# Yeh file define karti hai — ek transaction mein
# kya kya hona chahiye aur kaunsi type ka
#
# Pydantic = automatic validation
# Galat data aaya → automatic error

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

# Enum = fixed values ka set
# Sirf yeh transaction types allowed hain
class TransactionType(str, Enum):
    UPI         = "UPI"
    IMPS        = "IMPS"
    NEFT        = "NEFT"
    CARD_CREDIT = "CARD_CREDIT"
    CARD_DEBIT  = "CARD_DEBIT"

# Risk tiers — ML model yeh assign karega
class RiskTier(str, Enum):
    LOW      = "LOW"       # Score 0-29
    MEDIUM   = "MEDIUM"    # Score 30-59
    HIGH     = "HIGH"      # Score 60-85
    CRITICAL = "CRITICAL"  # Score 86-100

# Transaction ka schema — yeh main model hai
class Transaction(BaseModel):
    transaction_id:   str
    timestamp:        datetime
    transaction_type: TransactionType
    amount:           float = Field(gt=0, le=10_000_000)
    sender_account:   str
    receiver_account: str
    city:             Optional[str] = None

    # Risk score — baad mein ML engine fill karega
    risk_score: Optional[float] = None
    risk_tier:  Optional[RiskTier] = None