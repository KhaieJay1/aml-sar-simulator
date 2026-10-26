from typing import List, Dict, Any
from datetime import datetime, timedelta
from ..models import (
    Transaction,
    TypologyAlert,
    TypologyType,
    AlertSeverity,
    TransactionChannel
)

class StructuringDetector:
    """
    Detects Structuring / Smurfing typologies:
    Deliberately breaking cash or fast transfers into amounts just below statutory
    currency reporting thresholds (e.g. £10,000 in UK / $10,000 in US) within rolling timeframes.
    """
    def __init__(
        self,
        threshold_upper: float = 10000.0,
        threshold_lower_ratio: float = 0.70, # Flags transactions between 70% and 99.9% of threshold
        window_days: int = 7,
        min_transactions: int = 2
    ):
        self.threshold_upper = threshold_upper
        self.threshold_lower = threshold_upper * threshold_lower_ratio
        self.window_days = timedelta(days=window_days)
        self.min_transactions = min_transactions

    def analyze(self, transactions: List[Transaction]) -> List[TypologyAlert]:
        alerts: List[TypologyAlert] = []
        if not transactions:
            return alerts

        # Sort transactions chronologically
        sorted_txs = sorted(transactions, key=lambda t: t.timestamp)
        
        # Group by customer
        by_customer: Dict[str, List[Transaction]] = {}
        for tx in sorted_txs:
            by_customer.setdefault(tx.customer_id, []).append(tx)

        for cust_id, cust_txs in by_customer.items():
            # Sliding window over transactions
            n = len(cust_txs)
            flagged_tx_ids = set()

            for i in range(n):
                t_start = datetime.fromisoformat(cust_txs[i].timestamp)
                window_txs = []
                
                for j in range(i, n):
                    t_curr = datetime.fromisoformat(cust_txs[j].timestamp)
                    if t_curr - t_start <= self.window_days:
                        window_txs.append(cust_txs[j])
                    else:
                        break

                # Check for individual transactions near threshold (£7,000 - £9,999)
                near_threshold_txs = [
                    t for t in window_txs 
                    if self.threshold_lower <= t.amount < self.threshold_upper
                ]

                # Check for multiple cash deposits or faster payments summing > threshold
                cash_or_instant_txs = [
                    t for t in window_txs 
                    if t.channel in (TransactionChannel.CASH_DEPOSIT, TransactionChannel.FASTER_PAYMENTS)
                ]
                sum_cash_instant = sum(t.amount for t in cash_or_instant_txs)

                is_alert = False
                alert_txs = []
                severity = AlertSeverity.MEDIUM
                risk_score = 65.0
                desc = ""

                # Pattern A: Multiple transactions just below threshold (£7k - £9.99k)
                if len(near_threshold_txs) >= self.min_transactions:
                    unflagged = [t for t in near_threshold_txs if t.transaction_id not in flagged_tx_ids]
                    if len(unflagged) >= self.min_transactions:
                        is_alert = True
                        alert_txs = near_threshold_txs
                        total_amt = sum(t.amount for t in near_threshold_txs)
                        risk_score = min(95.0, 75.0 + (len(near_threshold_txs) * 5.0))
                        severity = AlertSeverity.HIGH if risk_score >= 85 else AlertSeverity.MEDIUM
                        desc = (
                            f"Structuring pattern detected: {len(near_threshold_txs)} transactions just below "
                            f"the £{self.threshold_upper:,.0f} statutory reporting threshold "
                            f"(total: £{total_amt:,.2f}) within {self.window_days.days} days."
                        )

                # Pattern B: Multiple cash deposits summing to well above threshold
                elif len(cash_or_instant_txs) >= 3 and sum_cash_instant >= self.threshold_upper:
                    unflagged = [t for t in cash_or_instant_txs if t.transaction_id not in flagged_tx_ids]
                    if len(unflagged) >= 2:
                        is_alert = True
                        alert_txs = cash_or_instant_txs
                        risk_score = 80.0
                        severity = AlertSeverity.HIGH
                        desc = (
                            f"Smurfing / Structured deposits detected: {len(cash_or_instant_txs)} deposits "
                            f"aggregating to £{sum_cash_instant:,.2f} exceeding reporting threshold "
                            f"within {self.window_days.days} days."
                        )

                if is_alert:
                    tx_ids = [t.transaction_id for t in alert_txs]
                    for tid in tx_ids:
                        flagged_tx_ids.add(tid)

                    alerts.append(TypologyAlert(
                        alert_id=f"ALT-STR-{cust_id[:6]}-{datetime.now().strftime('%H%M%S%f')[:8]}",
                        typology=TypologyType.STRUCTURING,
                        customer_id=cust_id,
                        account_id=alert_txs[0].account_id if alert_txs else None,
                        risk_score=risk_score,
                        severity=severity,
                        description=desc,
                        evidence_transactions=tx_ids,
                        details={
                            "transactions_count": len(alert_txs),
                            "aggregate_amount": sum(t.amount for t in alert_txs),
                            "window_days": self.window_days.days,
                            "threshold_upper": self.threshold_upper,
                            "channels": list(set(t.channel.value for t in alert_txs))
                        },
                        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))
                    break # Avoid duplicate overlapping alerts for the same window

        return alerts
