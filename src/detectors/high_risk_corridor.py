from typing import List, Dict, Any, Set
from datetime import datetime
from ..models import (
    Transaction,
    TypologyAlert,
    TypologyType,
    AlertSeverity
)

# Standard FATF high-risk jurisdictions / non-cooperative corridors
DEFAULT_HIGH_RISK_JURISDICTIONS: Set[str] = {
    "KP", # North Korea
    "IR", # Iran
    "MM", # Myanmar
    "SY", # Syria
    "CU", # Cuba
    "RU", # Russia (Sanctioned / High Risk)
    "BY", # Belarus
    "YE", # Yemen
}

class HighRiskCorridorDetector:
    """
    Detects cross-border transactions routed to or from FATF-identified
    high-risk or non-cooperative jurisdictions.
    """
    def __init__(self, high_risk_countries: Set[str] = DEFAULT_HIGH_RISK_JURISDICTIONS, min_amount: float = 1000.0):
        self.high_risk_countries = high_risk_countries
        self.min_amount = min_amount

    def analyze(self, transactions: List[Transaction]) -> List[TypologyAlert]:
        alerts = []
        for tx in transactions:
            country = (tx.counterparty_country or "").upper().strip()
            if country in self.high_risk_countries and tx.amount >= self.min_amount:
                risk_score = 90.0 if country in {"KP", "IR", "SY"} else 80.0
                severity = AlertSeverity.CRITICAL if risk_score >= 90.0 else AlertSeverity.HIGH

                desc = (
                    f"High-Risk Corridor Transfer: Payment of £{tx.amount:,.2f} ({tx.direction.value}) "
                    f"involving high-risk / FATF sanctioned jurisdiction code '{country}'. "
                    f"Counterparty: '{tx.counterparty_name or 'Unknown'}'."
                )

                alerts.append(TypologyAlert(
                    alert_id=f"ALT-HRC-{tx.customer_id[:6]}-{datetime.now().strftime('%H%M%S%f')[:8]}",
                    typology=TypologyType.HIGH_RISK_CORRIDOR,
                    customer_id=tx.customer_id,
                    account_id=tx.account_id,
                    risk_score=risk_score,
                    severity=severity,
                    description=desc,
                    evidence_transactions=[tx.transaction_id],
                    details={
                        "country": country,
                        "amount": tx.amount,
                        "counterparty": tx.counterparty_name,
                        "direction": tx.direction.value,
                        "channel": tx.channel.value
                    },
                    created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))

        return alerts
