"""
Seed the FBE POC database with contract metadata, fee schedules, and
simulated transactions — including some deliberate fee violations so
the Analysis agent has something interesting to find.

Usage (from project root):
    python database/setup/seed_contracts_db.py

Reads DB credentials from .env (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD).
"""

import os
import random
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_FILE = PROJECT_ROOT / "database" / "schemas" / "contracts_schema.sql"

load_dotenv(PROJECT_ROOT / ".env")


# ---------------------------------------------------------------------
# Contract metadata + fee schedules extracted from data/contracts/*.txt
# ---------------------------------------------------------------------

CONTRACTS = [
    {
        "contract_id": "BOA-VISA-2025-001",
        "participant": "BANK OF AMERICA",
        "service_provider": "VISA",
        "contract_type": "First Amendment to Addendum to Participation Agreement",
        "effective_date": "2025-03-18",
        "term_months": 24,
        "source_file": "Bank_of_America_VISA_Contract_2025.txt",
        "fees": [
            ("processing_fee_monthly", 50.0, None, "per_month", "Monthly processing fee"),
            ("network_access_fee_monthly", 25.0, None, "per_month", "Monthly network access fee"),
            ("standard_transaction_discount", 0.001, None, "per_transaction", "Discount applied to standard transactions"),
            ("us_issuer_atm_discount", 0.01, None, "per_transaction", "Discount on US Issuer ATM fee"),
        ],
    },
    {
        "contract_id": "DBS-VISA-2020-001",
        "participant": "DBS BANK",
        "service_provider": "VISA",
        "contract_type": "Addendum to Participation Agreement",
        "effective_date": "2020-09-13",
        "term_months": 24,
        "source_file": "DBS_VISA_Participation_Agreement_2020.txt",
        "fees": [
            ("standard_transaction_discount", 0.005, None, "per_transaction", "Discount on standard transactions"),
            ("fixed_fee_discount", 0.025, None, "per_transaction", "Discount on fixed fee component"),
            ("us_issuer_atm_discount", 0.15, None, "per_transaction", "Discount on US Issuer ATM fee"),
            ("network_security_fee", 200.0, None, "per_month", "Monthly network security fee"),
            ("acquirer_atm_fee", 0.005, None, "per_transaction", "Acquirer ATM fee"),
            ("cross_border_processing", 1.50, None, "per_transaction", "Cross-border transaction processing"),
            ("currency_conversion", None, 0.012, "percentage", "1.2% currency conversion"),
            ("international_atm_access", 0.50, None, "per_transaction", "International ATM access fee"),
            ("debit_interchange_fixed", 0.10, 0.012, "per_transaction", "Debit: 1.2% + $0.10"),
            ("credit_interchange_fixed", 0.20, 0.022, "per_transaction", "Credit: 2.2% + $0.20"),
            ("premium_interchange_fixed", 0.30, 0.031, "per_transaction", "Premium: 3.1% + $0.30"),
        ],
    },
    {
        "contract_id": "DBS-MC-2021-001",
        "participant": "DBS BANK",
        "service_provider": "MASTERCARD",
        "contract_type": "Acquiring and Processing Agreement",
        "effective_date": "2021-01-15",
        "term_months": 36,
        "source_file": "DBS_MasterCard_Service_Agreement_2021.txt",
        "fees": [
            ("atm_withdrawal", 0.008, None, "per_transaction", "ATM withdrawal processing"),
            ("pos", 0.140, None, "per_transaction", "Point-of-sale processing"),
            ("online_cnp", 0.160, None, "per_transaction", "Online / card-not-present"),
            ("contactless", 0.120, None, "per_transaction", "Contactless payments"),
            ("debit_interchange_fixed", 0.08, 0.011, "per_transaction", "Debit: 1.1% + $0.08"),
            ("credit_interchange_fixed", 0.18, 0.021, "per_transaction", "Credit: 2.1% + $0.18"),
            ("premium_credit_interchange", 0.25, 0.032, "per_transaction", "Premium credit: 3.2% + $0.25"),
            ("corporate_interchange", 0.20, 0.028, "per_transaction", "Corporate: 2.8% + $0.20"),
            ("account_maintenance_monthly", 150.0, None, "per_month", "Account maintenance"),
            ("fraud_monitoring_monthly", 75.0, None, "per_month", "Fraud monitoring"),
            ("compliance_reporting_monthly", 50.0, None, "per_month", "Compliance reporting"),
            ("chargeback_admin", 10.0, None, "per_case", "Chargeback administrative fee"),
            ("international_processing", 1.25, None, "per_transaction", "Cross-border processing"),
            ("currency_conversion", None, 0.010, "percentage", "Currency conversion 1.0%"),
        ],
    },
    {
        "contract_id": "PULSE-DBS-2020-ADD",
        "participant": "DBS BANK",
        "service_provider": "PULSE",
        "contract_type": "Network Access Addendum",
        "effective_date": "2020-09-13",
        "term_months": None,
        "source_file": "PULSE_Network_Access_Addendum_2020.txt",
        "fees": [
            ("network_access", 0.050, None, "per_transaction", "Network access fee"),
            ("switch_processing", 0.020, None, "per_transaction", "Switch processing"),
            ("international_atm", 0.150, None, "per_transaction", "International ATM fee"),
            ("balance_inquiry", 0.010, None, "per_transaction", "Balance inquiry"),
            ("network_participation_monthly", 500.0, None, "per_month", "Network participation"),
            ("enhanced_routing_monthly", 200.0, None, "per_month", "Enhanced routing"),
            ("international_access_monthly", 300.0, None, "per_month", "International access"),
            ("premium_services_monthly", 150.0, None, "per_month", "Premium services"),
            ("domestic_settlement", 0.005, None, "per_transaction", "Domestic settlement"),
            ("international_settlement", 0.025, None, "per_transaction", "International settlement"),
            ("currency_conversion", None, 0.005, "percentage", "Currency conversion 0.5%"),
            ("failed_transaction", 1.00, None, "per_transaction", "Failed transaction fee"),
        ],
    },
    {
        "contract_id": "SCB-VISA-2023-002",
        "participant": "SC BANK",
        "service_provider": "VISA",
        "contract_type": "Second Amendment to Participation Agreement",
        "effective_date": "2023-08-29",
        "term_months": 120,
        "source_file": "SC_Bank_VISA_Contract_2023.txt",
        "fees": [
            ("transaction_processing", 0.05, None, "per_transaction", "Transaction processing"),
            ("interchange", None, 0.0175, "percentage", "Interchange 1.75%"),
            ("service_monthly", 500.0, None, "per_month", "Monthly service charge"),
            ("optional_programs_annual", 1000.0, None, "per_year", "Optional program fees"),
        ],
    },
]


# ---------------------------------------------------------------------
# Transaction generator
# ---------------------------------------------------------------------

# For each (contract_id, transaction_type), we pick the expected fee from the
# fee schedule. Some transactions are deliberately planted with incorrect fees
# so the agent has something to flag.

TXN_TYPES_BY_CONTRACT = {
    "BOA-VISA-2025-001": ["standard_transaction_discount", "us_issuer_atm_discount"],
    "DBS-VISA-2020-001": ["debit_interchange_fixed", "credit_interchange_fixed", "cross_border_processing",
                          "international_atm_access", "acquirer_atm_fee"],
    "DBS-MC-2021-001": ["atm_withdrawal", "pos", "online_cnp", "contactless",
                         "debit_interchange_fixed", "credit_interchange_fixed"],
    "PULSE-DBS-2020-ADD": ["network_access", "switch_processing", "international_atm",
                            "balance_inquiry", "domestic_settlement"],
    "SCB-VISA-2023-002": ["transaction_processing"],
}

MERCHANTS = [
    "Amazon", "Walmart", "Target", "Starbucks", "Uber", "Shell",
    "McDonalds", "Apple Store", "Costco", "Netflix", "Delta Airlines",
    "Marriott Hotels", "Home Depot", "Best Buy", "Whole Foods",
]


def compute_fee(fee_row, amount):
    """Compute expected fee from a fee_schedule row + transaction amount."""
    fixed = Decimal(str(fee_row["fee_amount"])) if fee_row["fee_amount"] is not None else Decimal("0")
    pct = Decimal(str(fee_row["fee_percentage"])) if fee_row["fee_percentage"] is not None else Decimal("0")
    return fixed + (Decimal(str(amount)) * pct)


def generate_transactions(contracts_with_fees):
    """Yield simulated transaction dicts. Plants ~10% intentional violations."""
    random.seed(42)
    rng = random.Random(42)
    today = datetime.now()
    earliest = today - timedelta(days=90)

    violation_count = 0
    total_count = 0

    for contract in contracts_with_fees:
        cid = contract["contract_id"]
        fees_by_cat = {f["fee_category"]: f for f in contract["fees_inserted"]}
        categories = [c for c in TXN_TYPES_BY_CONTRACT.get(cid, []) if c in fees_by_cat]
        if not categories:
            continue

        # 20-40 transactions per contract
        n_txns = rng.randint(20, 40)
        for _ in range(n_txns):
            category = rng.choice(categories)
            fee_row = fees_by_cat[category]

            # Transaction amount: varies by category
            if "atm" in category or "withdrawal" in category:
                amount = Decimal(rng.choice([20, 40, 60, 100, 200, 300]))
            elif "cross_border" in category or "international" in category:
                amount = Decimal(rng.uniform(50, 2000)).quantize(Decimal("0.01"))
            else:
                amount = Decimal(rng.uniform(5, 500)).quantize(Decimal("0.01"))

            correct_fee = compute_fee(fee_row, amount)

            # 10% chance of planting a violation (fee charged incorrectly)
            if rng.random() < 0.10:
                # Overcharge by 20-100% or wrong fixed amount
                multiplier = Decimal(str(rng.uniform(1.2, 2.0)))
                fee_charged = (correct_fee * multiplier).quantize(Decimal("0.000001"))
                violation_count += 1
            else:
                fee_charged = correct_fee.quantize(Decimal("0.000001"))

            # Random timestamp in last 90 days
            ts = earliest + timedelta(
                seconds=rng.randint(0, int((today - earliest).total_seconds()))
            )

            yield {
                "contract_id": cid,
                "transaction_date": ts,
                "transaction_type": category,
                "transaction_amount": amount,
                "fee_charged": fee_charged,
                "currency": "USD",
                "merchant_name": rng.choice(MERCHANTS),
            }
            total_count += 1

    print(f"   Generated {total_count} transactions ({violation_count} deliberate violations)")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    conn_kwargs = dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "financial_services_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )
    print(f"🔌 Connecting to Postgres at {conn_kwargs['host']}:{conn_kwargs['port']}/{conn_kwargs['dbname']}")

    with psycopg2.connect(**conn_kwargs) as conn:
        with conn.cursor() as cur:
            print("📜 Applying schema...")
            cur.execute(SCHEMA_FILE.read_text())

            print("📝 Inserting contracts & fee schedules...")
            contracts_with_fees = []
            for c in CONTRACTS:
                cur.execute(
                    """INSERT INTO contracts (contract_id, participant, service_provider,
                                              contract_type, effective_date, term_months, source_file)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (c["contract_id"], c["participant"], c["service_provider"],
                     c["contract_type"], c["effective_date"], c["term_months"], c["source_file"]),
                )
                fees_inserted = []
                for (cat, amt, pct, unit, note) in c["fees"]:
                    cur.execute(
                        """INSERT INTO fee_schedules (contract_id, fee_category, fee_amount,
                                                      fee_percentage, fee_unit, notes)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (c["contract_id"], cat, amt, pct, unit, note),
                    )
                    fees_inserted.append({"fee_category": cat, "fee_amount": amt, "fee_percentage": pct})
                contracts_with_fees.append({**c, "fees_inserted": fees_inserted})

            print(f"   Inserted {len(CONTRACTS)} contracts")

            print("💳 Generating transactions...")
            rows = list(generate_transactions(contracts_with_fees))
            cur.executemany(
                """INSERT INTO transactions (contract_id, transaction_date, transaction_type,
                                             transaction_amount, fee_charged, currency, merchant_name)
                   VALUES (%(contract_id)s, %(transaction_date)s, %(transaction_type)s,
                           %(transaction_amount)s, %(fee_charged)s, %(currency)s, %(merchant_name)s)""",
                rows,
            )

            # Summary
            cur.execute("SELECT COUNT(*) FROM contracts")
            n_contracts = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM fee_schedules")
            n_fees = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM transactions")
            n_txns = cur.fetchone()[0]

        conn.commit()

    print("")
    print("✅ Done.")
    print(f"   • contracts:      {n_contracts}")
    print(f"   • fee_schedules:  {n_fees}")
    print(f"   • transactions:   {n_txns}")


if __name__ == "__main__":
    main()
