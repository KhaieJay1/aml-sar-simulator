from typing import List, Dict, Any
from datetime import datetime, timedelta
from ..models import (
    Transaction,
    TypologyAlert,
    TypologyType,
    AlertSeverity,
    TransactionDirection
)

class RapidMovementDetector:
    """
    Detects Rapid Movement of Funds / Passthrough Layering:
    Substantial inbound funds immediately dispersed (>80% within a short timeframe)
    to external counterparties, characteristic of money mule accounts and layering.
    """
    def __init__(
        self,
        min_inbound_amount: float = 5000.0,
        flow_through_ratio_threshold: float = 0.80,
        velocity_window_hours: int = 12
    ):
        self.min_inbound_amount = min_inbound_amount
        self.ratio_threshold = flow_through_ratio_threshold
        self.window_hours = timedelta(hours=velocity_window_hours)

    def analyze(self, transactions: List[Transaction]) -> List[TypologyAlert]:
        alerts: List[TypologyAlert] = []
        if not transactions:
            return alerts

        sorted_txs = sorted(transactions, key=lambda t: t.timestamp)
        by_customer: Dict[str, List[Transaction]] = {}
        for tx in sorted_txs:
            by_customer.setdefault(tx.customer_id, []).append(tx)

        for cust_id, cust_txs in by_customer.items():
            inbound_txs = [
                t for t in cust_txs 
                if t.direction == TransactionDirection.INBOUND and t.amount >= self.min_inbound_amount
            ]

            for in_tx in inbound_txs:
                t_in = datetime.fromisoformat(in_tx.timestamp)
                
                # Look for subsequent outbound transactions within window
                subsequent_out = [
                    t for t in cust_txs
                    if t.direction == TransactionDirection.OUTBOUND
                    and datetime.fromisoformat(t.timestamp) >= t_in
                    and datetime.fromisoformat(t.timestamp) - t_in <= self.window_hours
                ]

                if not subsequent_out:
                    continue

                total_outbound = sum(t.amount for t in subsequent_out)
                ratio = total_outbound / in_tx.amount

                if ratio >= self.ratio_threshold:
                    earliest_out = min(datetime.fromisoformat(t.timestamp) for t in subsequent_out)
                    time_diff_hours = max(0.1, (earliest_out - t_in).total_seconds() / 3600.0)

                    # Velocity factor: faster dispersion gives higher risk score
                    velocity_multiplier = 1.0 if time_diff_hours > 4 else 1.2
                    risk_score = min(98.0, round((75.0 + (ratio * 15.0)) * min(1.15, velocity_multiplier), 1))
                    
                    severity = AlertSeverity.CRITICAL if risk_score >= 90.0 else AlertSeverity.HIGH

                    desc = (
                        f"Rapid Passthrough / Mule Layering: Inbound £{in_tx.amount:,.2f} received and "
                        f"{ratio*100:.1f}% (£{total_outbound:,.2f}) dispersed across {len(subsequent_out)} "
                        f"outbound transfers within {time_diff_hours:.1f} hours."
                    )

                    evidence_ids = [in_tx.transaction_id] + [t.transaction_id for t in subsequent_out]

                    alerts.append(TypologyAlert(
                        alert_id=f"ALT-RPM-{cust_id[:6]}-{datetime.now().strftime('%H%M%S%f')[:8]}",
                        typology=TypologyType.RAPID_MOVEMENT,
                        customer_id=cust_id,
                        account_id=in_tx.account_id,
                        risk_score=risk_score,
                        severity=severity,
                        description=desc,
                        evidence_transactions=evidence_ids,
                        details={
                            "inbound_amount": in_tx.amount,
                            "outbound_amount": total_outbound,
                            "flow_through_ratio": round(ratio, 3),
                            "hours_elapsed": round(time_diff_hours, 2),
                            "outbound_transfer_count": len(subsequent_out),
                            "counterparties": [t.counterparty_name for t in subsequent_out if t.counterparty_name]
                        },
                        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))

        return alerts
