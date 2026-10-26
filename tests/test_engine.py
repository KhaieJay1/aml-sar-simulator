import pytest
from src.engine import TransactionMonitoringEngine
from src.models import TypologyType

def test_monitoring_engine_full_scan(seeded_db):
    engine = TransactionMonitoringEngine(db_path=seeded_db)
    alerts = engine.run_full_scan(persist_alerts=False)

    assert len(alerts) >= 5
    
    # Check that major typologies are represented
    typologies = {a.typology for a in alerts}
    assert TypologyType.STRUCTURING in typologies
    assert TypologyType.RAPID_MOVEMENT in typologies
    assert TypologyType.SANCTIONS_PEP_MATCH in typologies
    assert TypologyType.HIGH_RISK_CORRIDOR in typologies

def test_subject_dossier_retrieval(seeded_db):
    engine = TransactionMonitoringEngine(db_path=seeded_db)
    dossier = engine.get_subject_dossier("CUST-ANOM-STR-01")

    assert dossier["customer"].customer_id == "CUST-ANOM-STR-01"
    assert dossier["total_transactions"] == 4
    assert dossier["suspicious_volume"] == 38400.0
    assert len(dossier["alerts"]) >= 1
