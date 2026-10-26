import os
import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional, List
from .models import (
    Customer,
    Transaction,
    TypologyAlert,
    SARFiling,
    TypologyType,
    AlertSeverity
)
from .db import (
    DEFAULT_DB_PATH,
    get_customer,
    get_customer_transactions,
    save_sar
)
from .engine import TransactionMonitoringEngine

OLLAMA_API_URL = "http://localhost:11434/api/generate"
DEFAULT_OLLAMA_MODEL = "llama3.2"

class SARNarrativeGenerator:
    """
    Generates regulatory-compliant Suspicious Activity Reports (SAR)
    adhering strictly to UK NCA (National Crime Agency) and US FinCEN filing standards.
    Supports local Ollama LLM synthesis with deterministic fallback.
    """
    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        ollama_url: str = OLLAMA_API_URL,
        model: str = DEFAULT_OLLAMA_MODEL,
        force_offline: bool = False
    ):
        self.db_path = db_path
        self.ollama_url = ollama_url
        self.model = model
        self.force_offline = force_offline
        self.engine = TransactionMonitoringEngine(db_path)

    def is_ollama_available(self) -> bool:
        if self.force_offline or os.environ.get("AML_OFFLINE_MODE") == "1":
            return False
        try:
            res = requests.get("http://localhost:11434/api/tags", timeout=2)
            return res.status_code == 200
        except Exception:
            return False

    def generate_sar(
        self,
        customer_id: str,
        filing_type: str = "UK_NCA_SAR",
        mlro_notes: Optional[str] = None
    ) -> SARFiling:
        dossier = self.engine.get_subject_dossier(customer_id)
        cust: Customer = dossier["customer"]
        txs: List[Transaction] = dossier["transactions"]
        alerts: List[TypologyAlert] = dossier["alerts"]

        if not alerts:
            raise ValueError(f"No suspicious activity alerts found for customer '{customer_id}'.")

        # Collect detected typologies
        detected_typos = list(set(a.typology for a in alerts))
        suspicious_amt = dossier["suspicious_volume"]
        timeframe = dossier["timeframe"]

        sar_id = f"SAR-{datetime.now().strftime('%Y%m%d')}-{customer_id[-6:]}"

        ollama_online = self.is_ollama_available()
        drafting_engine = f"Local Ollama ({self.model})" if ollama_online else "Deterministic SAR Narrative Engine"

        if ollama_online:
            narrative_5ws, full_text = self._draft_with_ollama(dossier, filing_type, mlro_notes)
        else:
            narrative_5ws, full_text = self._draft_deterministically(dossier, filing_type, mlro_notes)

        sar_record = SARFiling(
            sar_id=sar_id,
            filing_type=filing_type,
            filing_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            subject_id=cust.customer_id,
            subject_name=cust.full_name,
            subject_type=cust.customer_type.value,
            total_suspicious_amount=suspicious_amt,
            currency="GBP",
            activity_timeframe=timeframe,
            typologies_detected=detected_typos,
            narrative_5ws=narrative_5ws,
            full_narrative_text=full_text,
            drafting_engine=drafting_engine,
            status="DRAFT"
        )

        save_sar(sar_record, self.db_path)
        return sar_record

    def _draft_deterministically(
        self,
        dossier: Dict[str, Any],
        filing_type: str,
        mlro_notes: Optional[str]
    ) -> (Dict[str, str], str):
        cust: Customer = dossier["customer"]
        txs: List[Transaction] = dossier["transactions"]
        alerts: List[TypologyAlert] = dossier["alerts"]

        # 5Ws structure
        who = (
            f"Subject: {cust.full_name}, DOB: {cust.date_of_birth or 'Unknown'}, "
            f"Nationality: {cust.nationality}, Resident: {cust.country_of_residence}. "
            f"Occupation: {cust.occupation or 'Unstated'}. "
            f"Customer ID: {cust.customer_id}. KYC Risk Rating: {cust.risk_rating.value}."
            + (" (Identified Politically Exposed Person / PEP)." if cust.is_pep else "")
        )

        what_items = []
        for a in alerts:
            what_items.append(f"- [{a.typology.value}] {a.description}")
        what = "\n".join(what_items)

        accounts_involved = list(set(t.account_id for t in txs if t.is_synthetic_anomaly))
        where = (
            f"Accounts Involved: {', '.join(accounts_involved) if accounts_involved else 'Primary Checking'}. "
            f"Reporting Institution Jurisdiction: United Kingdom (GB). "
            f"Counterparty Jurisdictions: {', '.join(set(t.counterparty_country or 'GB' for t in txs))}."
        )

        when = f"Activity observed between {dossier['timeframe']} across {len(txs)} transactions."

        why_grounds = []
        for a in alerts:
            if a.typology == TypologyType.STRUCTURING:
                why_grounds.append("Repetitive high-value deposits just below mandatory threshold indicating deliberate structuring.")
            elif a.typology == TypologyType.RAPID_MOVEMENT:
                why_grounds.append("Immediate pass-through velocity with funds dispersed within hours to unrelated counterparties, consistent with money mule operations.")
            elif a.typology == TypologyType.SANCTIONS_PEP_MATCH:
                why_grounds.append(f"Name match against statutory watchlist: {a.description}")
            elif a.typology == TypologyType.HIGH_RISK_CORRIDOR:
                why_grounds.append(f"Cross-border transfer involving FATF high-risk jurisdiction.")
        
        why = " ".join(why_grounds)
        if mlro_notes:
            why += f" Additional MLRO Observation: {mlro_notes}"

        how = "Internal automated transaction monitoring rules engine flagged atypical velocity and threshold deviations."

        narrative_5ws = {
            "WHO": who,
            "WHAT": what,
            "WHERE": where,
            "WHEN": when,
            "WHY": why,
            "HOW": how
        }

        full_text = f"""### CONFIDENTIAL // SUSPICIOUS ACTIVITY REPORT ({filing_type})
**Filing Reference:** SAR-{cust.customer_id[-6:]}  
**Subject:** {cust.full_name} ({cust.customer_id})  
**Total Suspicious Amount:** £{dossier['suspicious_volume']:,.2f} GBP  
**Activity Period:** {dossier['timeframe']}

---

#### 1. WHO (Subject Details & KYC Profile)
{who}

#### 2. WHAT (Suspicious Activity & Typology Breakdown)
{what}

#### 3. WHERE (Accounts & Jurisdictions)
{where}

#### 4. WHEN (Chronological Activity Window)
{when}

#### 5. WHY (Grounds for Suspicion & Rationale)
{why}

#### 6. HOW / DISPOSITION (Action Taken)
{how}
- Account placed on operational hold pending Law Enforcement / MLRO consent.
- Complete audit trail and counterparty identifiers preserved.
"""
        return narrative_5ws, full_text

    def _draft_with_ollama(
        self,
        dossier: Dict[str, Any],
        filing_type: str,
        mlro_notes: Optional[str]
    ) -> (Dict[str, str], str):
        cust: Customer = dossier["customer"]
        alerts: List[TypologyAlert] = dossier["alerts"]
        txs: List[Transaction] = dossier["transactions"]

        evidence_summary = []
        for a in alerts:
            evidence_summary.append(f"- {a.typology.value} (Risk {a.risk_score}/100): {a.description}")

        tx_summary = []
        for t in txs[:10]:
            tx_summary.append(f"- {t.timestamp}: {t.direction.value} £{t.amount:,.2f} via {t.channel.value} (Counterparty: {t.counterparty_name or 'N/A'}, Country: {t.counterparty_country})")

        prompt = f"""You are a Senior Money Laundering Reporting Officer (MLRO) and Chartered Compliance Specialist.
Draft a formal, objective, legally rigorous Suspicious Activity Report (SAR) narrative adhering to {filing_type} standards.

SUBJECT KYC:
- Name: {cust.full_name}
- Customer ID: {cust.customer_id}
- Nationality: {cust.nationality}, Resident: {cust.country_of_residence}
- Occupation: {cust.occupation}
- PEP Status: {cust.is_pep}

SUSPICIOUS ALERTS FLAGGED:
{chr(10).join(evidence_summary)}

TRANSACTIONAL TIMELINE:
{chr(10).join(tx_summary)}

TOTAL SUSPICIOUS AMOUNT: £{dossier['suspicious_volume']:,.2f} GBP
TIMEFRAME: {dossier['timeframe']}
MLRO NOTES: {mlro_notes or 'Standard compliance review triggered.'}

Structure the narrative strictly following the 5Ws Framework:
1. WHO (Subject identity and KYC context)
2. WHAT (Specific suspicious mechanism and financial flows)
3. WHERE (Accounts, delivery channels, and cross-border corridors)
4. WHEN (Chronology and transaction velocity)
5. WHY (Grounds for suspicion and lack of commercial rationale)
6. DISPOSITION (Recommended regulatory referral and account restraint)

Return ONLY a valid JSON object with keys:
{{
  "WHO": "...",
  "WHAT": "...",
  "WHERE": "...",
  "WHEN": "...",
  "WHY": "...",
  "HOW": "...",
  "full_narrative_text": "Complete formatted Markdown SAR narrative"
}}
"""
        try:
            resp = requests.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.2}
                },
                timeout=45
            )
            if resp.status_code == 200:
                body = resp.json().get("response", "{}")
                data = json.loads(body)
                narrative_5ws = {
                    "WHO": data.get("WHO", ""),
                    "WHAT": data.get("WHAT", ""),
                    "WHERE": data.get("WHERE", ""),
                    "WHEN": data.get("WHEN", ""),
                    "WHY": data.get("WHY", ""),
                    "HOW": data.get("HOW", "")
                }
                full_text = data.get("full_narrative_text", "")
                if not full_text:
                    _, full_text = self._draft_deterministically(dossier, filing_type, mlro_notes)
                return narrative_5ws, full_text
        except Exception as e:
            print(f"Warning: Ollama SAR drafting encountered error ({e}). Falling back to deterministic engine.")

        return self._draft_deterministically(dossier, filing_type, mlro_notes)
