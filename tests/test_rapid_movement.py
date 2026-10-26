import pytest
from datetime import datetime, timedelta
from src.models import (
    Transaction,
    TransactionDirection,
    TransactionChannel,
    TypologyType
)
from src.detectors.rapid_movement import RapidMovementDetector

def test_rapid_passthrough_mule_layering_detected():
    detector = RapidMovementDetector(min_inbound_amount=5000.0, flow_through_ratio_threshold=0.80, velocity_window_hours=6)
    base_time = datetime(2026, 10, 12, 9, 0, 0)

    # Inbound £40,000 at 09:00
    tx_in = Transaction(
        transaction_id="TX-IN-01",
        account_id="ACC-MULE-01",
        customer_id="CUST-MULE-01",
        timestamp=base_time.isoformat(),
        amount=40000.0,
        direction=TransactionDirection.INBOUND,
        channel=TransactionChannel.FASTER_PAYMENTS,
        counterparty_name="Unknown Wire Source"
    )

    # 4 Outbound payments of £9,000 each within 2 hours (£36,000 out / £40,000 in = 90% flow-through)
    outbound_txs = [
        Transaction(
            transaction_id=f"TX-OUT-{i}",
            account_id="ACC-MULE-01",
            customer_id="CUST-MULE-01",
            timestamp=(base_time + timedelta(minutes=25 * (i + 1))).isoformat(),
            amount=9000.0,
            direction=TransactionDirection.OUTBOUND,
            channel=TransactionChannel.FASTER_PAYMENTS,
            counterparty_name=f"Recipient #{i+1}"
        ) for i in range(4)
    ]

    alerts = detector.analyze([tx_in] + outbound_txs)
    assert len(alerts) >= 1
    assert alerts[0].typology == TypologyType.RAPID_MOVEMENT
    assert alerts[0].risk_score >= 85.0
    assert alerts[0].details["flow_through_ratio"] >= 0.85

def test_slow_retention_not_flagged():
    # Inbound £20,000 salary/dividend retained in account (only 10% spent over 12 hours)
    detector = RapidMovementDetector(min_inbound_amount=5000.0, flow_through_ratio_threshold=0.80, velocity_window_hours=6)
    base_time = datetime(2026, 10, 12, 9, 0, 0)

    tx_in = Transaction(
        transaction_id="TX-IN-02",
        account_id="ACC-CLEAN-01",
        customer_id="CUST-CLEAN-01",
        timestamp=base_time.isoformat(),
        amount=20000.0,
        direction=TransactionDirection.INBOUND,
        channel=TransactionChannel.FASTER_PAYMENTS
    )

    tx_out = Transaction(
        transaction_id="TX-OUT-02",
        account_id="ACC-CLEAN-01",
        customer_id="CUST-CLEAN-01",
        timestamp=(base_time + timedelta(hours=2)).isoformat(),
        amount=500.0,
        direction=TransactionDirection.OUTBOUND,
        channel=TransactionChannel.CARD_PURCHASE
    )

    alerts = detector.analyze([tx_in, tx_out])
    assert len(alerts) == 0
