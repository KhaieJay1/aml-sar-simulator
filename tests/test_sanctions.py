import pytest
from src.models import SanctionsEntry, Customer, RiskRating, CustomerType
from src.detectors.sanctions_screening import (
    SanctionsScreeningEngine,
    compute_composite_match_score,
    levenshtein_ratio,
    jaro_winkler_similarity,
    token_sort_similarity
)

@pytest.fixture
def mock_sanctions():
    return [
        SanctionsEntry(
            entry_id="TEST-001",
            entity_type="INDIVIDUAL",
            primary_name="Viktor Anatolyevich Bout",
            aliases=["Victor Bout", "Viktor Butt"],
            sanctions_program="UK_OFSI",
            listing_reason="Arms trafficking",
            listed_date="2008-01-01"
        ),
        SanctionsEntry(
            entry_id="TEST-002",
            entity_type="ENTITY",
            primary_name="Al-Nour Financial Exchange LLC",
            aliases=["Al Nour Hawala"],
            sanctions_program="OFAC_SDN",
            listing_reason="Illicit hawala network",
            listed_date="2019-01-01"
        )
    ]

def test_exact_match(mock_sanctions):
    screener = SanctionsScreeningEngine(mock_sanctions, match_threshold=0.85)
    matches = screener.screen_name("Viktor Anatolyevich Bout")
    assert len(matches) == 1
    assert matches[0][1] >= 0.98

def test_fuzzy_alias_match(mock_sanctions):
    screener = SanctionsScreeningEngine(mock_sanctions, match_threshold=0.85)
    matches = screener.screen_name("Victor Butt")
    assert len(matches) == 1
    assert matches[0][0].entry_id == "TEST-001"
    assert matches[0][1] >= 0.90

def test_transposed_name_matching(mock_sanctions):
    # Testing token sort invariance: "Bout Viktor"
    screener = SanctionsScreeningEngine(mock_sanctions, match_threshold=0.80)
    matches = screener.screen_name("Bout Victor")
    assert len(matches) >= 1
    assert matches[0][0].entry_id == "TEST-001"

def test_clean_name_not_matched(mock_sanctions):
    screener = SanctionsScreeningEngine(mock_sanctions, match_threshold=0.80)
    matches = screener.screen_name("Oliver Christopher Smith")
    assert len(matches) == 0

def test_screen_customer_records(mock_sanctions):
    screener = SanctionsScreeningEngine(mock_sanctions, match_threshold=0.85)
    cust_flagged = Customer(
        customer_id="C-TEST-01",
        first_name="Victor",
        last_name="Butt",
        full_name="Victor Butt",
        nationality="GB",
        country_of_residence="GB",
        customer_type=CustomerType.INDIVIDUAL,
        created_at="2026-01-01 00:00:00"
    )
    cust_clean = Customer(
        customer_id="C-TEST-02",
        first_name="Emily",
        last_name="Davis",
        full_name="Emily Davis",
        nationality="GB",
        country_of_residence="GB",
        customer_type=CustomerType.INDIVIDUAL,
        created_at="2026-01-01 00:00:00"
    )

    alerts = screener.screen_customers([cust_flagged, cust_clean])
    assert len(alerts) == 1
    assert alerts[0].customer_id == "C-TEST-01"
    assert alerts[0].risk_score >= 90.0
