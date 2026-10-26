from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class CustomerType(str, Enum):
    INDIVIDUAL = "INDIVIDUAL"
    CORPORATE = "CORPORATE"

class RiskRating(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class TransactionDirection(str, Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"

class TransactionChannel(str, Enum):
    CASH_DEPOSIT = "CASH_DEPOSIT"
    FASTER_PAYMENTS = "FASTER_PAYMENTS"
    CHAPS = "CHAPS"
    SWIFT = "SWIFT"
    CARD_PURCHASE = "CARD_PURCHASE"
    ATM_WITHDRAWAL = "ATM_WITHDRAWAL"

class TypologyType(str, Enum):
    STRUCTURING = "STRUCTURING"
    RAPID_MOVEMENT = "RAPID_MOVEMENT"
    SANCTIONS_PEP_MATCH = "SANCTIONS_PEP_MATCH"
    HIGH_RISK_CORRIDOR = "HIGH_RISK_CORRIDOR"

class AlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class Customer(BaseModel):
    customer_id: str
    first_name: str
    last_name: str
    full_name: str
    date_of_birth: Optional[str] = None
    nationality: str = "GB"
    country_of_residence: str = "GB"
    customer_type: CustomerType = CustomerType.INDIVIDUAL
    occupation: Optional[str] = "Professional"
    is_pep: bool = False
    risk_rating: RiskRating = RiskRating.LOW
    created_at: str

class Account(BaseModel):
    account_id: str
    customer_id: str
    account_type: str = "PERSONAL_CHECKING"
    currency: str = "GBP"
    balance: float = 0.0
    opened_date: str
    status: str = "ACTIVE"

class Transaction(BaseModel):
    transaction_id: str
    account_id: str
    customer_id: str
    timestamp: str
    amount: float
    currency: str = "GBP"
    direction: TransactionDirection
    channel: TransactionChannel
    counterparty_name: Optional[str] = None
    counterparty_account: Optional[str] = None
    counterparty_country: Optional[str] = "GB"
    narrative_reference: Optional[str] = None
    is_synthetic_anomaly: bool = False
    anomaly_typology: Optional[str] = None

class SanctionsEntry(BaseModel):
    entry_id: str
    entity_type: str = "INDIVIDUAL"
    primary_name: str
    aliases: List[str] = Field(default_factory=list)
    sanctions_program: str = "UK_OFSI"
    nationality_or_country: str = "GB"
    listing_reason: str
    listed_date: str

class TypologyAlert(BaseModel):
    alert_id: str
    typology: TypologyType
    customer_id: str
    account_id: Optional[str] = None
    risk_score: float = Field(..., ge=0.0, le=100.0)
    severity: AlertSeverity
    description: str
    evidence_transactions: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: str

class SARFiling(BaseModel):
    sar_id: str
    filing_type: str = "UK_NCA_SAR"
    filing_date: str
    subject_id: str
    subject_name: str
    subject_type: str = "INDIVIDUAL"
    total_suspicious_amount: float
    currency: str = "GBP"
    activity_timeframe: str
    typologies_detected: List[TypologyType]
    narrative_5ws: Dict[str, str] = Field(default_factory=dict)
    full_narrative_text: str
    drafting_engine: str = "Deterministic SAR Engine"
    status: str = "DRAFT"
