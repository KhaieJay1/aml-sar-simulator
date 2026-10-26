from typing import List, Dict, Any, Optional
from datetime import datetime
from .models import (
    Customer,
    Transaction,
    TypologyAlert,
    TypologyType,
    AlertSeverity
)
from .db import (
    DEFAULT_DB_PATH,
    get_all_customers,
    get_all_transactions,
    get_all_sanctions,
    save_alert,
    get_customer,
    get_customer_transactions
)
from .detectors import (
    StructuringDetector,
    RapidMovementDetector,
    SanctionsScreeningEngine,
    HighRiskCorridorDetector
)

class TransactionMonitoringEngine:
    """
    Core AML Transaction Monitoring & Surveillance Orchestrator.
    Executes multiple specialized detection engines across customer transaction ledgers,
    aggregates alert dossiers, and prepares suspicious activity evidence for SAR filing.
    """
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.structuring_detector = StructuringDetector()
        self.rapid_movement_detector = RapidMovementDetector()
        self.high_risk_detector = HighRiskCorridorDetector()
        
        # Load sanctions list from DB
        sanctions_entries = get_all_sanctions(db_path)
        self.sanctions_engine = SanctionsScreeningEngine(sanctions_entries)

    def run_full_scan(self, persist_alerts: bool = True) -> List[TypologyAlert]:
        """Runs all detection engines across the complete transaction ledger and customer base."""
        all_txs = get_all_transactions(self.db_path)
        all_customers = get_all_customers(self.db_path)

        all_alerts: List[TypologyAlert] = []

        # 1. Structuring Detection
        struct_alerts = self.structuring_detector.analyze(all_txs)
        all_alerts.extend(struct_alerts)

        # 2. Rapid Passthrough / Mule Layering Detection
        rpm_alerts = self.rapid_movement_detector.analyze(all_txs)
        all_alerts.extend(rpm_alerts)

        # 3. Sanctions & PEP Customer Screening
        cust_snc_alerts = self.sanctions_engine.screen_customers(all_customers)
        all_alerts.extend(cust_snc_alerts)

        # 4. Sanctions Counterparty Screening
        tx_snc_alerts = self.sanctions_engine.screen_transactions(all_txs)
        all_alerts.extend(tx_snc_alerts)

        # 5. High-Risk Corridor Detection
        hrc_alerts = self.high_risk_detector.analyze(all_txs)
        all_alerts.extend(hrc_alerts)

        # Sort by risk score descending
        all_alerts.sort(key=lambda a: a.risk_score, reverse=True)

        if persist_alerts:
            for alert in all_alerts:
                save_alert(alert, self.db_path)

        return all_alerts

    def get_subject_dossier(self, customer_id: str) -> Dict[str, Any]:
        """
        Retrieves full KYC and transactional evidence profile for a customer
        to support SAR narrative drafting.
        """
        cust = get_customer(customer_id, self.db_path)
        if not cust:
            raise ValueError(f"Customer '{customer_id}' not found.")

        txs = get_customer_transactions(customer_id, self.db_path)
        
        # Run targeted detections for this customer
        struct_alerts = self.structuring_detector.analyze(txs)
        rpm_alerts = self.rapid_movement_detector.analyze(txs)
        cust_snc = self.sanctions_engine.screen_customers([cust])
        tx_snc = self.sanctions_engine.screen_transactions(txs)
        hrc_alerts = self.high_risk_detector.analyze(txs)

        subject_alerts = struct_alerts + rpm_alerts + cust_snc + tx_snc + hrc_alerts
        subject_alerts.sort(key=lambda a: a.risk_score, reverse=True)

        total_volume = sum(t.amount for t in txs)
        anomalies = [t for t in txs if t.is_synthetic_anomaly]
        suspicious_volume = sum(t.amount for t in anomalies) if anomalies else sum(t.amount for t in txs)

        timeframe_start = txs[0].timestamp[:10] if txs else "N/A"
        timeframe_end = txs[-1].timestamp[:10] if txs else "N/A"

        return {
            "customer": cust,
            "transactions": txs,
            "alerts": subject_alerts,
            "total_transactions": len(txs),
            "total_volume": total_volume,
            "suspicious_volume": suspicious_volume,
            "timeframe": f"{timeframe_start} to {timeframe_end}",
            "anomaly_count": len(anomalies)
        }
