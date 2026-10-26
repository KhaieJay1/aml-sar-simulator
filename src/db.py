import sqlite3
import os
import json
from typing import List, Optional, Dict, Any, Tuple
from .models import (
    Customer,
    Account,
    Transaction,
    SanctionsEntry,
    TypologyAlert,
    SARFiling,
    CustomerType,
    RiskRating,
    TransactionDirection,
    TransactionChannel,
    TypologyType,
    AlertSeverity
)

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "aml_monitoring.db")

def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id TEXT PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        full_name TEXT NOT NULL,
        date_of_birth TEXT,
        nationality TEXT,
        country_of_residence TEXT,
        customer_type TEXT,
        occupation TEXT,
        is_pep INTEGER DEFAULT 0,
        risk_rating TEXT,
        created_at TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        account_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        account_type TEXT,
        currency TEXT DEFAULT 'GBP',
        balance REAL DEFAULT 0.0,
        opened_date TEXT,
        status TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id TEXT PRIMARY KEY,
        account_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        amount REAL NOT NULL,
        currency TEXT DEFAULT 'GBP',
        direction TEXT NOT NULL,
        channel TEXT NOT NULL,
        counterparty_name TEXT,
        counterparty_account TEXT,
        counterparty_country TEXT,
        narrative_reference TEXT,
        is_synthetic_anomaly INTEGER DEFAULT 0,
        anomaly_typology TEXT,
        FOREIGN KEY (account_id) REFERENCES accounts (account_id),
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sanctions_list (
        entry_id TEXT PRIMARY KEY,
        entity_type TEXT NOT NULL,
        primary_name TEXT NOT NULL,
        aliases_json TEXT,
        sanctions_program TEXT NOT NULL,
        nationality_or_country TEXT,
        listing_reason TEXT,
        listed_date TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        alert_id TEXT PRIMARY KEY,
        typology TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        account_id TEXT,
        risk_score REAL NOT NULL,
        severity TEXT NOT NULL,
        description TEXT NOT NULL,
        evidence_transactions_json TEXT,
        details_json TEXT,
        created_at TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sar_filings (
        sar_id TEXT PRIMARY KEY,
        filing_type TEXT NOT NULL,
        filing_date TEXT NOT NULL,
        subject_id TEXT NOT NULL,
        subject_name TEXT NOT NULL,
        subject_type TEXT NOT NULL,
        total_suspicious_amount REAL NOT NULL,
        currency TEXT DEFAULT 'GBP',
        activity_timeframe TEXT NOT NULL,
        typologies_json TEXT NOT NULL,
        narrative_5ws_json TEXT NOT NULL,
        full_narrative_text TEXT NOT NULL,
        drafting_engine TEXT NOT NULL,
        status TEXT DEFAULT 'DRAFT'
    );
    """)

    # Performance indexes for transaction monitoring window queries
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_customer ON transactions (customer_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions (account_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_timestamp ON transactions (timestamp);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_channel ON transactions (channel);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_amount ON transactions (amount);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_customer ON alerts (customer_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_typology ON alerts (typology);")

    conn.commit()
    conn.close()

def save_customer(cust: Customer, db_path: str = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO customers (
        customer_id, first_name, last_name, full_name, date_of_birth,
        nationality, country_of_residence, customer_type, occupation,
        is_pep, risk_rating, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        cust.customer_id, cust.first_name, cust.last_name, cust.full_name,
        cust.date_of_birth, cust.nationality, cust.country_of_residence,
        cust.customer_type.value, cust.occupation, 1 if cust.is_pep else 0,
        cust.risk_rating.value, cust.created_at
    ))
    conn.commit()
    conn.close()

def save_account(acc: Account, db_path: str = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO accounts (
        account_id, customer_id, account_type, currency, balance, opened_date, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        acc.account_id, acc.customer_id, acc.account_type,
        acc.currency, acc.balance, acc.opened_date, acc.status
    ))
    conn.commit()
    conn.close()

def save_transaction(tx: Transaction, db_path: str = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO transactions (
        transaction_id, account_id, customer_id, timestamp, amount,
        currency, direction, channel, counterparty_name, counterparty_account,
        counterparty_country, narrative_reference, is_synthetic_anomaly, anomaly_typology
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        tx.transaction_id, tx.account_id, tx.customer_id, tx.timestamp,
        tx.amount, tx.currency, tx.direction.value, tx.channel.value,
        tx.counterparty_name, tx.counterparty_account, tx.counterparty_country,
        tx.narrative_reference, 1 if tx.is_synthetic_anomaly else 0,
        tx.anomaly_typology
    ))
    conn.commit()
    conn.close()

def save_sanctions_entry(se: SanctionsEntry, db_path: str = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO sanctions_list (
        entry_id, entity_type, primary_name, aliases_json, sanctions_program,
        nationality_or_country, listing_reason, listed_date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        se.entry_id, se.entity_type, se.primary_name, json.dumps(se.aliases),
        se.sanctions_program, se.nationality_or_country, se.listing_reason, se.listed_date
    ))
    conn.commit()
    conn.close()

def save_alert(alert: TypologyAlert, db_path: str = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO alerts (
        alert_id, typology, customer_id, account_id, risk_score, severity,
        description, evidence_transactions_json, details_json, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        alert.alert_id, alert.typology.value, alert.customer_id, alert.account_id,
        alert.risk_score, alert.severity.value, alert.description,
        json.dumps(alert.evidence_transactions), json.dumps(alert.details),
        alert.created_at
    ))
    conn.commit()
    conn.close()

def save_sar(sar: SARFiling, db_path: str = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO sar_filings (
        sar_id, filing_type, filing_date, subject_id, subject_name,
        subject_type, total_suspicious_amount, currency, activity_timeframe,
        typologies_json, narrative_5ws_json, full_narrative_text,
        drafting_engine, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sar.sar_id, sar.filing_type, sar.filing_date, sar.subject_id,
        sar.subject_name, sar.subject_type, sar.total_suspicious_amount,
        sar.currency, sar.activity_timeframe,
        json.dumps([t.value for t in sar.typologies_detected]),
        json.dumps(sar.narrative_5ws), sar.full_narrative_text,
        sar.drafting_engine, sar.status
    ))
    conn.commit()
    conn.close()

def get_customer(customer_id: str, db_path: str = DEFAULT_DB_PATH) -> Optional[Customer]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return Customer(
        customer_id=row["customer_id"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        full_name=row["full_name"],
        date_of_birth=row["date_of_birth"],
        nationality=row["nationality"],
        country_of_residence=row["country_of_residence"],
        customer_type=CustomerType(row["customer_type"]),
        occupation=row["occupation"],
        is_pep=bool(row["is_pep"]),
        risk_rating=RiskRating(row["risk_rating"]),
        created_at=row["created_at"]
    )

def get_customer_transactions(customer_id: str, db_path: str = DEFAULT_DB_PATH) -> List[Transaction]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM transactions WHERE customer_id = ? ORDER BY timestamp ASC", (customer_id,))
    rows = cur.fetchall()
    conn.close()
    return [_row_to_transaction(r) for r in rows]

def get_all_transactions(db_path: str = DEFAULT_DB_PATH) -> List[Transaction]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM transactions ORDER BY timestamp ASC")
    rows = cur.fetchall()
    conn.close()
    return [_row_to_transaction(r) for r in rows]

def get_all_customers(db_path: str = DEFAULT_DB_PATH) -> List[Customer]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers ORDER BY customer_id ASC")
    rows = cur.fetchall()
    conn.close()
    return [
        Customer(
            customer_id=r["customer_id"],
            first_name=r["first_name"],
            last_name=r["last_name"],
            full_name=r["full_name"],
            date_of_birth=r["date_of_birth"],
            nationality=r["nationality"],
            country_of_residence=r["country_of_residence"],
            customer_type=CustomerType(r["customer_type"]),
            occupation=r["occupation"],
            is_pep=bool(r["is_pep"]),
            risk_rating=RiskRating(r["risk_rating"]),
            created_at=r["created_at"]
        ) for r in rows
    ]

def get_all_sanctions(db_path: str = DEFAULT_DB_PATH) -> List[SanctionsEntry]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM sanctions_list ORDER BY entry_id ASC")
    rows = cur.fetchall()
    conn.close()
    entries = []
    for r in rows:
        aliases = json.loads(r["aliases_json"]) if r["aliases_json"] else []
        entries.append(SanctionsEntry(
            entry_id=r["entry_id"],
            entity_type=r["entity_type"],
            primary_name=r["primary_name"],
            aliases=aliases,
            sanctions_program=r["sanctions_program"],
            nationality_or_country=r["nationality_or_country"],
            listing_reason=r["listing_reason"],
            listed_date=r["listed_date"]
        ))
    return entries

def get_alerts(db_path: str = DEFAULT_DB_PATH) -> List[TypologyAlert]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM alerts ORDER BY risk_score DESC, created_at DESC")
    rows = cur.fetchall()
    conn.close()
    alerts = []
    for r in rows:
        tx_ids = json.loads(r["evidence_transactions_json"]) if r["evidence_transactions_json"] else []
        details = json.loads(r["details_json"]) if r["details_json"] else {}
        alerts.append(TypologyAlert(
            alert_id=r["alert_id"],
            typology=TypologyType(r["typology"]),
            customer_id=r["customer_id"],
            account_id=r["account_id"],
            risk_score=r["risk_score"],
            severity=AlertSeverity(r["severity"]),
            description=r["description"],
            evidence_transactions=tx_ids,
            details=details,
            created_at=r["created_at"]
        ))
    return alerts

def get_database_stats(db_path: str = DEFAULT_DB_PATH) -> Dict[str, Any]:
    conn = get_connection(db_path)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM customers")
    cust_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM accounts")
    acc_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM transactions")
    tx_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM transactions WHERE is_synthetic_anomaly = 1")
    anomaly_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM sanctions_list")
    sanctions_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM alerts")
    alert_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM sar_filings")
    sar_count = cur.fetchone()[0]

    conn.close()
    return {
        "customers": cust_count,
        "accounts": acc_count,
        "transactions": tx_count,
        "synthetic_anomalies": anomaly_count,
        "sanctions_entries": sanctions_count,
        "alerts_generated": alert_count,
        "sar_filings": sar_count
    }

def _row_to_transaction(r: sqlite3.Row) -> Transaction:
    return Transaction(
        transaction_id=r["transaction_id"],
        account_id=r["account_id"],
        customer_id=r["customer_id"],
        timestamp=r["timestamp"],
        amount=float(r["amount"]),
        currency=r["currency"],
        direction=TransactionDirection(r["direction"]),
        channel=TransactionChannel(r["channel"]),
        counterparty_name=r["counterparty_name"],
        counterparty_account=r["counterparty_account"],
        counterparty_country=r["counterparty_country"],
        narrative_reference=r["narrative_reference"],
        is_synthetic_anomaly=bool(r["is_synthetic_anomaly"]),
        anomaly_typology=r["anomaly_typology"]
    )
