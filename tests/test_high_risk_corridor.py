import pytest
from src.models import (
    Transaction,
    TransactionDirection,
    TransactionChannel,
    TypologyType,
    AlertSeverity
)
from src.detectors.high_risk_corridor import HighRiskCorridorDetector

def test_high_risk_corridor_flagged():
    detector = HighRiskCorridorDetector()
    tx = Transaction(
        transaction_id="TX-HRC-TEST-01",
        account_id="ACC-01",
        customer_id="CUST-01",
        timestamp="2026-10-15T10:00:00",
        amount=15000.0,
        direction=TransactionDirection.INBOUND,
        channel=TransactionChannel.SWIFT,
        counterparty_name="Damascus Foreign Trade Bank",
        counterparty_country="SY" # Syria
    )

    alerts = detector.analyze([tx])
    assert len(alerts) == 1
    assert alerts[0].typology == TypologyType.HIGH_RISK_CORRIDOR
    assert alerts[0].risk_score >= 90.0
    assert alerts[0].severity == AlertSeverity.CRITICAL

def test_standard_corridor_not_flagged():
    detector = HighRiskCorridorDetector()
    tx = Transaction(
        transaction_id="TX-STD-TEST-01",
        account_id="ACC-02",
        customer_id="CUST-02",
        timestamp="2026-10-15T11:00:00",
        amount=25000.0,
        direction=TransactionDirection.OUTBOUND,
        channel=TransactionChannel.SWIFT,
        counterparty_name="Deutsche Bank AG",
        counterparty_country="DE" # Germany (Low risk)
    )

    alerts = detector.analyze([tx])
    assert len(alerts) == 0
