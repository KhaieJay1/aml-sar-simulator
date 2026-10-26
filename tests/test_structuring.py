import pytest
from datetime import datetime, timedelta
from src.models import (
    Transaction,
    TransactionDirection,
    TransactionChannel,
    TypologyType
)
from src.detectors.structuring import StructuringDetector

def test_structuring_detected():
    detector = StructuringDetector(threshold_upper=10000.0, threshold_lower_ratio=0.70, window_days=7)
    base_time = datetime(2026, 10, 10, 10, 0, 0)
    
    # 3 deposits of £9,500 over 3 days (smurfing below £10,000)
    txs = [
        Transaction(
            transaction_id=f"TX-{i}",
            account_id="ACC-01",
            customer_id="CUST-01",
            timestamp=(base_time + timedelta(days=i)).isoformat(),
            amount=9500.0,
            direction=TransactionDirection.INBOUND,
            channel=TransactionChannel.CASH_DEPOSIT
        ) for i in range(3)
    ]

    alerts = detector.analyze(txs)
    assert len(alerts) >= 1
    assert alerts[0].typology == TypologyType.STRUCTURING
    assert alerts[0].risk_score >= 80.0
    assert alerts[0].details["transactions_count"] == 3
    assert alerts[0].details["aggregate_amount"] == 28500.0

def test_normal_transactions_no_structuring():
    detector = StructuringDetector(threshold_upper=10000.0, threshold_lower_ratio=0.70, window_days=7)
    base_time = datetime(2026, 10, 10, 10, 0, 0)
    
    # Normal everyday transactions (£50, £120, £300)
    txs = [
        Transaction(
            transaction_id=f"TX-{i}",
            account_id="ACC-02",
            customer_id="CUST-02",
            timestamp=(base_time + timedelta(days=i)).isoformat(),
            amount=float(50 + (i * 70)),
            direction=TransactionDirection.OUTBOUND,
            channel=TransactionChannel.CARD_PURCHASE
        ) for i in range(5)
    ]

    alerts = detector.analyze(txs)
    assert len(alerts) == 0

def test_single_large_transaction_not_flagged_as_structuring():
    # A single large £25,000 transaction is NOT structuring (it is above threshold and reported directly via standard CTR)
    detector = StructuringDetector(threshold_upper=10000.0, threshold_lower_ratio=0.70, window_days=7)
    tx = Transaction(
        transaction_id="TX-LARGE-01",
        account_id="ACC-03",
        customer_id="CUST-03",
        timestamp="2026-10-10T12:00:00",
        amount=25000.0,
        direction=TransactionDirection.INBOUND,
        channel=TransactionChannel.CHAPS
    )
    alerts = detector.analyze([tx])
    assert len(alerts) == 0
