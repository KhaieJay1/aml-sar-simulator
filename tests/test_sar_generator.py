import pytest
from src.sar_generator import SARNarrativeGenerator
from src.models import TypologyType

def test_sar_generation_offline(seeded_db):
    generator = SARNarrativeGenerator(db_path=seeded_db, force_offline=True)
    
    # Generate SAR for structuring subject
    sar = generator.generate_sar(
        customer_id="CUST-ANOM-STR-01",
        filing_type="UK_NCA_SAR",
        mlro_notes="Customer failed to provide commercial receipts upon branch inquiry."
    )

    assert sar.sar_id.startswith("SAR-")
    assert sar.subject_name == "Arthur Pendelton"
    assert sar.total_suspicious_amount == 38400.0
    assert TypologyType.STRUCTURING in sar.typologies_detected
    
    # Verify 5Ws are present and not empty
    assert "WHO" in sar.narrative_5ws and len(sar.narrative_5ws["WHO"]) > 10
    assert "WHAT" in sar.narrative_5ws and len(sar.narrative_5ws["WHAT"]) > 10
    assert "WHERE" in sar.narrative_5ws and len(sar.narrative_5ws["WHERE"]) > 10
    assert "WHEN" in sar.narrative_5ws and len(sar.narrative_5ws["WHEN"]) > 10
    assert "WHY" in sar.narrative_5ws and "failed to provide commercial receipts" in sar.narrative_5ws["WHY"]
    assert "HOW" in sar.narrative_5ws

    assert "CONFIDENTIAL // SUSPICIOUS ACTIVITY REPORT" in sar.full_narrative_text

def test_sar_generation_invalid_customer(seeded_db):
    generator = SARNarrativeGenerator(db_path=seeded_db, force_offline=True)
    with pytest.raises(ValueError):
        generator.generate_sar("CUST-DOES-NOT-EXIST")
