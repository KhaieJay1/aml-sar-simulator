import json
from typing import Dict, Any
from tabulate import tabulate
from .models import SARFiling, TypologyAlert

class AMLReporter:
    """Formats alerts and SAR filings into Markdown, JSON, and terminal tables."""

    @staticmethod
    def alert_table(alerts: list[TypologyAlert]) -> str:
        rows = []
        for a in alerts:
            rows.append([
                a.alert_id,
                a.severity.value,
                a.typology.value,
                a.customer_id,
                f"{a.risk_score:.1f}",
                a.description[:65] + ("..." if len(a.description) > 65 else "")
            ])
        return tabulate(
            rows,
            headers=["Alert ID", "Severity", "Typology", "Customer ID", "Risk Score", "Description"],
            tablefmt="grid"
        )

    @staticmethod
    def sar_to_markdown(sar: SARFiling) -> str:
        typos = ", ".join(t.value for t in sar.typologies_detected)
        lines = [
            f"# {sar.filing_type} Suspicious Activity Report",
            f"**Filing ID:** `{sar.sar_id}` | **Date:** `{sar.filing_date}` | **Status:** `{sar.status}`",
            f"**Drafting Engine:** `{sar.drafting_engine}`",
            "",
            "## Executive Summary",
            f"| Field | Detail |",
            f"|---|---|",
            f"| **Subject Name** | {sar.subject_name} |",
            f"| **Subject ID** | `{sar.subject_id}` |",
            f"| **Entity Type** | {sar.subject_type} |",
            f"| **Suspicious Amount** | **£{sar.total_suspicious_amount:,.2f} {sar.currency}** |",
            f"| **Observed Timeframe** | {sar.activity_timeframe} |",
            f"| **Typologies Detected** | {typos} |",
            "",
            "---",
            "",
            "## 5Ws Regulatory Narrative Breakdown",
            "",
            f"### 1. WHO (Subject Identity & KYC Profile)",
            f"{sar.narrative_5ws.get('WHO', 'N/A')}",
            "",
            f"### 2. WHAT (Suspicious Modus Operandi & Typology Details)",
            f"{sar.narrative_5ws.get('WHAT', 'N/A')}",
            "",
            f"### 3. WHERE (Delivery Channels & Jurisdictions)",
            f"{sar.narrative_5ws.get('WHERE', 'N/A')}",
            "",
            f"### 4. WHEN (Chronology & Transaction Velocity)",
            f"{sar.narrative_5ws.get('WHEN', 'N/A')}",
            "",
            f"### 5. WHY (Grounds for Suspicion & Commercial Inconsistency)",
            f"{sar.narrative_5ws.get('WHY', 'N/A')}",
            "",
            f"### 6. HOW / DISPOSITION (Mitigating Action & Asset Restraint)",
            f"{sar.narrative_5ws.get('HOW', 'N/A')}",
            "",
            "---",
            "*Report compiled under strict financial crime compliance standards. Confidential regulatory disclosure.*"
        ]
        return "\n".join(lines)

    @staticmethod
    def sar_to_json(sar: SARFiling) -> str:
        return json.dumps(sar.model_dump(), indent=2)
