import os
import sys
import random
from datetime import datetime, timedelta

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import (
    Customer,
    Account,
    Transaction,
    SanctionsEntry,
    CustomerType,
    RiskRating,
    TransactionDirection,
    TransactionChannel
)
from src.db import (
    DEFAULT_DB_PATH,
    init_db,
    save_customer,
    save_account,
    save_transaction,
    save_sanctions_entry,
    get_connection
)

SYNTHETIC_SANCTIONS_DATA = [
    {
        "entry_id": "UK-OFSI-001",
        "entity_type": "INDIVIDUAL",
        "primary_name": "Viktor Anatolyevich Bout",
        "aliases": ["Victor Bout", "Viktor Butt", "Vadim Aminov"],
        "sanctions_program": "UK_OFSI",
        "nationality_or_country": "RU",
        "listing_reason": "Illicit arms trafficking and weapons proliferation.",
        "listed_date": "2008-04-12"
    },
    {
        "entry_id": "OFAC-SDN-002",
        "entity_type": "INDIVIDUAL",
        "primary_name": "Sergei Sergeyevich Ivanov",
        "aliases": ["Sergey Ivanov", "Sergei S. Ivanov"],
        "sanctions_program": "OFAC_SDN",
        "nationality_or_country": "RU",
        "listing_reason": "Senior official in designated Russian financial and industrial state entities.",
        "listed_date": "2022-02-24"
    },
    {
        "entry_id": "UK-OFSI-003",
        "entity_type": "INDIVIDUAL",
        "primary_name": "Mikhail Maratovich Fridman",
        "aliases": ["Michael Fridman", "Mikhail Friedman"],
        "sanctions_program": "UK_OFSI",
        "nationality_or_country": "RU",
        "listing_reason": "Prominent Russian oligarch involved in economic sectors providing substantial revenue.",
        "listed_date": "2022-03-15"
    },
    {
        "entry_id": "OFAC-SDN-004",
        "entity_type": "ENTITY",
        "primary_name": "Al-Nour Financial Exchange LLC",
        "aliases": ["Al Nour Hawala", "Al-Noor Currency Services"],
        "sanctions_program": "OFAC_SDN",
        "nationality_or_country": "SY",
        "listing_reason": "Operated illicit money remittance network for designated regional militant groups.",
        "listed_date": "2019-11-18"
    },
    {
        "entry_id": "UN-SC-005",
        "entity_type": "ENTITY",
        "primary_name": "Korea Ryonbong General Corp",
        "aliases": ["Ryonbong Trading", "Korea General Machinery"],
        "sanctions_program": "UN_SECURITY_COUNCIL",
        "nationality_or_country": "KP",
        "listing_reason": "Procurement of specialized materials and equipment for ballistic and nuclear programs.",
        "listed_date": "2006-10-14"
    },
    {
        "entry_id": "UK-OFSI-006",
        "entity_type": "INDIVIDUAL",
        "primary_name": "Bashar Hafez Al-Assad",
        "aliases": ["Bashar Al Assad", "Bashar Asad"],
        "sanctions_program": "UK_OFSI",
        "nationality_or_country": "SY",
        "listing_reason": "Head of Syrian state regime responsible for violent repression of civilian population.",
        "listed_date": "2011-05-23"
    },
    {
        "entry_id": "OFAC-SDN-007",
        "entity_type": "ENTITY",
        "primary_name": "Kashgar Petrochemical Trading",
        "aliases": ["Kashgar Petrochem", "KPC Global Supply"],
        "sanctions_program": "OFAC_SDN",
        "nationality_or_country": "IR",
        "listing_reason": "Facilitated illicit export and revenue generation for Iranian petroleum sector.",
        "listed_date": "2021-09-03"
    }
]

FIRST_NAMES = ["Oliver", "George", "Arthur", "Noah", "Muhammad", "Leo", "Oscar", "Harry", "Jack", "Henry",
               "Olivia", "Amelia", "Isla", "Ava", "Mia", "Ivy", "Lily", "Freya", "Florence", "Emily"]
LAST_NAMES = ["Smith", "Jones", "Taylor", "Brown", "Williams", "Wilson", "Johnson", "Davies", "Patel", "Robinson",
              "Wright", "Thompson", "Evans", "Walker", "White", "Roberts", "Green", "Hall", "Thomas", "Clarke"]

OCCUPATIONS = [
    "Software Engineer", "Consultant", "Accountant", "Medical Doctor", "Solicitor",
    "Civil Servant", "Architect", "University Lecturer", "Operations Director", "Retail Manager"
]

def generate_synthetic_data(db_path: str = DEFAULT_DB_PATH, num_customers: int = 35):
    print(f"Initializing synthetic AML dataset at: {db_path}")
    init_db(db_path)

    # 1. Insert Sanctions Watchlist
    print(f"Seeding {len(SYNTHETIC_SANCTIONS_DATA)} synthetic Sanctions & PEP Watchlist entries...")
    for s_data in SYNTHETIC_SANCTIONS_DATA:
        entry = SanctionsEntry(**s_data)
        save_sanctions_entry(entry, db_path)

    now = datetime(2026, 10, 15, 12, 0, 0)
    customers = []
    accounts = []
    transactions = []

    # 2. Generate Standard Clean Customers
    print(f"Generating {num_customers} baseline retail & corporate customers...")
    for i in range(1, num_customers + 1):
        cid = f"CUST-GB-{1000 + i}"
        fn = random.choice(FIRST_NAMES)
        ln = random.choice(LAST_NAMES)
        full_name = f"{fn} {ln}"
        dob = (now - timedelta(days=random.randint(22*365, 65*365))).strftime("%Y-%m-%d")
        
        cust = Customer(
            customer_id=cid,
            first_name=fn,
            last_name=ln,
            full_name=full_name,
            date_of_birth=dob,
            nationality="GB",
            country_of_residence="GB",
            customer_type=CustomerType.INDIVIDUAL,
            occupation=random.choice(OCCUPATIONS),
            is_pep=False,
            risk_rating=RiskRating.LOW,
            created_at=(now - timedelta(days=random.randint(180, 720))).strftime("%Y-%m-%d %H:%M:%S")
        )
        save_customer(cust, db_path)
        customers.append(cust)

        # Account for customer
        aid = f"ACC-GB-CHK-{2000 + i}"
        acc = Account(
            account_id=aid,
            customer_id=cid,
            account_type="PERSONAL_CHECKING",
            currency="GBP",
            balance=round(random.uniform(1200.0, 15000.0), 2),
            opened_date=cust.created_at[:10],
            status="ACTIVE"
        )
        save_account(acc, db_path)
        accounts.append(acc)

        # Generate 4-8 normal transactions for clean customers
        tx_count = random.randint(4, 8)
        base_time = now - timedelta(days=45)
        for t_idx in range(tx_count):
            tx_time = base_time + timedelta(days=t_idx * 5, hours=random.randint(1, 12))
            is_salary = (t_idx == 0)
            if is_salary:
                tx = Transaction(
                    transaction_id=f"TXN-CLEAN-{cid[-4:]}-{t_idx+1:03d}",
                    account_id=aid,
                    customer_id=cid,
                    timestamp=tx_time.strftime("%Y-%m-%d %H:%M:%S"),
                    amount=round(random.uniform(2800.0, 5500.0), 2),
                    currency="GBP",
                    direction=TransactionDirection.INBOUND,
                    channel=TransactionChannel.FASTER_PAYMENTS,
                    counterparty_name="Acme Global UK Payroll",
                    counterparty_account="GB29ACME0012345678",
                    counterparty_country="GB",
                    narrative_reference="Monthly Salary & Allowances",
                    is_synthetic_anomaly=False
                )
            else:
                amt = round(random.uniform(15.0, 350.0), 2)
                merchants = ["Sainsburys Supermarkets", "TFL Travel", "Amazon UK", "British Gas", "PureGym Ltd", "Costa Coffee"]
                tx = Transaction(
                    transaction_id=f"TXN-CLEAN-{cid[-4:]}-{t_idx+1:03d}",
                    account_id=aid,
                    customer_id=cid,
                    timestamp=tx_time.strftime("%Y-%m-%d %H:%M:%S"),
                    amount=amt,
                    currency="GBP",
                    direction=TransactionDirection.OUTBOUND,
                    channel=TransactionChannel.CARD_PURCHASE,
                    counterparty_name=random.choice(merchants),
                    counterparty_account=None,
                    counterparty_country="GB",
                    narrative_reference="Point of Sale Purchase",
                    is_synthetic_anomaly=False
                )
            save_transaction(tx, db_path)
            transactions.append(tx)

    # 3. Inject Explicit Ground-Truth Typology Test Cases:
    print("Injecting ground-truth financial crime typologies...")

    # TYPOLOGY 1: STRUCTURING / SMURFING
    # Subject: Arthur Pendelton
    # Pattern: 4 cash deposits just below £10,000 threshold within 4 days (£9,500, £9,800, £9,200, £9,900)
    c_str = Customer(
        customer_id="CUST-ANOM-STR-01",
        first_name="Arthur",
        last_name="Pendelton",
        full_name="Arthur Pendelton",
        date_of_birth="1984-06-12",
        nationality="GB",
        country_of_residence="GB",
        customer_type=CustomerType.INDIVIDUAL,
        occupation="Sole Trader Antiques",
        is_pep=False,
        risk_rating=RiskRating.HIGH,
        created_at=(now - timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S")
    )
    save_customer(c_str, db_path)
    a_str = Account(
        account_id="ACC-ANOM-STR-01",
        customer_id=c_str.customer_id,
        account_type="BUSINESS_OPERATING",
        currency="GBP",
        balance=38400.0,
        opened_date=c_str.created_at[:10],
        status="ACTIVE"
    )
    save_account(a_str, db_path)

    struct_amounts = [9500.0, 9800.0, 9200.0, 9900.0]
    struct_start = now - timedelta(days=6)
    for s_i, s_amt in enumerate(struct_amounts):
        s_time = struct_start + timedelta(days=s_i, hours=2 * s_i)
        tx_str = Transaction(
            transaction_id=f"TXN-STR-ANOM-{s_i+1:03d}",
            account_id=a_str.account_id,
            customer_id=c_str.customer_id,
            timestamp=s_time.strftime("%Y-%m-%d %H:%M:%S"),
            amount=s_amt,
            currency="GBP",
            direction=TransactionDirection.INBOUND,
            channel=TransactionChannel.CASH_DEPOSIT,
            counterparty_name="Branch ATM Deposit #402",
            counterparty_account=None,
            counterparty_country="GB",
            narrative_reference="Cash sales proceeds antique stock",
            is_synthetic_anomaly=True,
            anomaly_typology="STRUCTURING"
        )
        save_transaction(tx_str, db_path)

    # TYPOLOGY 2: RAPID MOVEMENT OF FUNDS / MULE PASSTHROUGH LAYERING
    # Subject: Elena Rostova
    # Pattern: £54,000 inbound Faster Payment at 10:00 AM, followed by 5 rapid outbound transfers of £10,000 within 2.5 hours
    c_rpm = Customer(
        customer_id="CUST-ANOM-RPM-02",
        first_name="Elena",
        last_name="Rostova",
        full_name="Elena Rostova",
        date_of_birth="1996-03-22",
        nationality="GB",
        country_of_residence="GB",
        customer_type=CustomerType.INDIVIDUAL,
        occupation="Freelance Designer",
        is_pep=False,
        risk_rating=RiskRating.HIGH,
        created_at=(now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    )
    save_customer(c_rpm, db_path)
    a_rpm = Account(
        account_id="ACC-ANOM-RPM-02",
        customer_id=c_rpm.customer_id,
        account_type="PERSONAL_CHECKING",
        currency="GBP",
        balance=1200.0,
        opened_date=c_rpm.created_at[:10],
        status="ACTIVE"
    )
    save_account(a_rpm, db_path)

    rpm_base = now - timedelta(days=3, hours=14)
    # Inbound wire £54,000
    tx_in = Transaction(
        transaction_id="TXN-RPM-IN-001",
        account_id=a_rpm.account_id,
        customer_id=c_rpm.customer_id,
        timestamp=rpm_base.strftime("%Y-%m-%d %H:%M:%S"),
        amount=54000.0,
        currency="GBP",
        direction=TransactionDirection.INBOUND,
        channel=TransactionChannel.FASTER_PAYMENTS,
        counterparty_name="Meridian Consulting Partners Ltd",
        counterparty_account="GB12MERI9988776655",
        counterparty_country="GB",
        narrative_reference="Consulting contract fee disbursement",
        is_synthetic_anomaly=True,
        anomaly_typology="RAPID_MOVEMENT"
    )
    save_transaction(tx_in, db_path)

    # 5 outbound transfers of £10,000 to different recipients within 2.5 hours
    rpm_destinations = [
        ("Apex Digital Asset Exchange", "GB88CRYP11223344"),
        ("Kavkaz Overseas Trading", "GB99KAVK55667788"),
        ("Global Remit Express", "GB33REMT99001122"),
        ("Sovereign Escrow Services", "GB44SOVR33445566"),
        ("Prestige Private Wealth", "GB77PRES22334455")
    ]
    for o_idx, (cp_name, cp_acc) in enumerate(rpm_destinations):
        out_time = rpm_base + timedelta(minutes=25 * (o_idx + 1))
        tx_out = Transaction(
            transaction_id=f"TXN-RPM-OUT-{o_idx+1:03d}",
            account_id=a_rpm.account_id,
            customer_id=c_rpm.customer_id,
            timestamp=out_time.strftime("%Y-%m-%d %H:%M:%S"),
            amount=10000.0,
            currency="GBP",
            direction=TransactionDirection.OUTBOUND,
            channel=TransactionChannel.FASTER_PAYMENTS,
            counterparty_name=cp_name,
            counterparty_account=cp_acc,
            counterparty_country="GB",
            narrative_reference="Immediate investment tranche allocation",
            is_synthetic_anomaly=True,
            anomaly_typology="RAPID_MOVEMENT"
        )
        save_transaction(tx_out, db_path)

    # TYPOLOGY 3: FUZZY SANCTIONS & PEP MATCH ON CUSTOMER
    # Subject: Victor Butt (Fuzzy match to Viktor Anatolyevich Bout, UK OFSI entry)
    c_snc = Customer(
        customer_id="CUST-ANOM-SNC-03",
        first_name="Victor",
        last_name="Butt",
        full_name="Victor Butt",
        date_of_birth="1967-01-13",
        nationality="RU",
        country_of_residence="AE",
        customer_type=CustomerType.INDIVIDUAL,
        occupation="Aviation Consultant",
        is_pep=True,
        risk_rating=RiskRating.HIGH,
        created_at=(now - timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S")
    )
    save_customer(c_snc, db_path)
    a_snc = Account(
        account_id="ACC-ANOM-SNC-03",
        customer_id=c_snc.customer_id,
        account_type="BUSINESS_OPERATING",
        currency="GBP",
        balance=95000.0,
        opened_date=c_snc.created_at[:10],
        status="ACTIVE"
    )
    save_account(a_snc, db_path)

    # TYPOLOGY 4: SANCTIONED COUNTERPARTY MATCH IN TRANSACTION
    # Clean customer receiving transfer from "Al-Nour Financial Exchange LLC" (OFAC SDN)
    c_cp = Customer(
        customer_id="CUST-ANOM-CPSNC-04",
        first_name="Marcus",
        last_name="Vance",
        full_name="Marcus Vance",
        date_of_birth="1978-11-04",
        nationality="GB",
        country_of_residence="GB",
        customer_type=CustomerType.INDIVIDUAL,
        occupation="Import Export Merchant",
        is_pep=False,
        risk_rating=RiskRating.HIGH,
        created_at=(now - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")
    )
    save_customer(c_cp, db_path)
    a_cp = Account(
        account_id="ACC-ANOM-CPSNC-04",
        customer_id=c_cp.customer_id,
        account_type="BUSINESS_OPERATING",
        currency="GBP",
        balance=22000.0,
        opened_date=c_cp.created_at[:10],
        status="ACTIVE"
    )
    save_account(a_cp, db_path)

    tx_cpsnc = Transaction(
        transaction_id="TXN-CPSNC-001",
        account_id=a_cp.account_id,
        customer_id=c_cp.customer_id,
        timestamp=(now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
        amount=14500.0,
        currency="GBP",
        direction=TransactionDirection.INBOUND,
        channel=TransactionChannel.SWIFT,
        counterparty_name="Al Nour Hawala", # Matches alias of Al-Nour Financial Exchange LLC
        counterparty_account="SY99NOUR11223344",
        counterparty_country="SY",
        narrative_reference="Commercial invoice settlement goods",
        is_synthetic_anomaly=True,
        anomaly_typology="SANCTIONS_PEP_MATCH"
    )
    save_transaction(tx_cpsnc, db_path)

    # TYPOLOGY 5: HIGH-RISK JURISDICTION CORRIDOR
    # Wire transfer from Myanmar (MM) FATF Blacklist
    tx_hrc = Transaction(
        transaction_id="TXN-HRC-001",
        account_id=a_cp.account_id,
        customer_id=c_cp.customer_id,
        timestamp=(now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        amount=32000.0,
        currency="GBP",
        direction=TransactionDirection.INBOUND,
        channel=TransactionChannel.SWIFT,
        counterparty_name="Yangon Precious Metals Trading",
        counterparty_account="MM55YANG99887766",
        counterparty_country="MM", # Myanmar
        narrative_reference="Timber & minerals consignment settlement",
        is_synthetic_anomaly=True,
        anomaly_typology="HIGH_RISK_CORRIDOR"
    )
    save_transaction(tx_hrc, db_path)

    print("Synthetic AML dataset successfully generated and committed to SQLite.")

if __name__ == "__main__":
    generate_synthetic_data()
