import argparse
import sys
import os
from tabulate import tabulate
from .db import (
    DEFAULT_DB_PATH,
    get_database_stats,
    get_all_sanctions
)
from .engine import TransactionMonitoringEngine
from .detectors import SanctionsScreeningEngine
from .sar_generator import SARNarrativeGenerator
from .reporter import AMLReporter

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AML Transaction Monitoring & SAR Simulator - CLI Intelligence Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: scan
    scan_p = subparsers.add_parser("scan", help="Run automated AML transaction monitoring scan over the ledger")
    scan_p.add_argument("--save-alerts", action="store_true", default=True, help="Save generated alerts to the database")

    # Command: screen
    screen_p = subparsers.add_parser("screen", help="Screen a person or entity name against Sanctions & PEP watchlist")
    screen_p.add_argument("name", help="Full name or entity string to screen (e.g. 'Victor Butt', 'Al-Nour Hawala')")
    screen_p.add_argument("--threshold", "-t", type=float, default=0.75, help="Fuzzy match threshold (0.0 - 1.0)")

    # Command: sar
    sar_p = subparsers.add_parser("sar", help="Draft a formal regulatory Suspicious Activity Report (SAR)")
    sar_p.add_argument("customer_id", help="Subject Customer ID (e.g. CUST-ANOM-STR-01, CUST-ANOM-RPM-02)")
    sar_p.add_argument("--type", choices=["UK_NCA_SAR", "US_FINCEN_SAR"], default="UK_NCA_SAR", help="Jurisdiction standard")
    sar_p.add_argument("--output", "-o", choices=["markdown", "json", "terminal"], default="terminal", help="Output format")
    sar_p.add_argument("--save", "-s", help="Path to save output report file")
    sar_p.add_argument("--offline", action="store_true", help="Force fast deterministic SAR drafting without calling Ollama")
    sar_p.add_argument("--notes", "-n", help="Optional MLRO investigation notes to include in grounds for suspicion")

    # Command: stats
    subparsers.add_parser("stats", help="Display AML surveillance and database metrics")

    return parser

def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "scan":
        print("\nExecuting comprehensive AML Transaction Monitoring & Surveillance scan...")
        engine = TransactionMonitoringEngine()
        alerts = engine.run_full_scan(persist_alerts=args.save_alerts)
        print(f"\n[+] Scan completed. {len(alerts)} suspicious activity alerts triggered:\n")
        print(AMLReporter.alert_table(alerts))

    elif args.command == "screen":
        print(f"\nScreening name '{args.name}' against synthetic Sanctions & PEP Watchlist (Threshold: {args.threshold})...")
        sanctions_entries = get_all_sanctions()
        screener = SanctionsScreeningEngine(sanctions_entries, match_threshold=args.threshold)
        matches = screener.screen_name(args.name)
        if not matches:
            print("[+] Zero watchlist hits found. Name appears clean at current threshold.")
        else:
            print(f"[!] {len(matches)} Watchlist Hits Detected:\n")
            rows = []
            for entry, score, matched_name in matches:
                rows.append([
                    entry.entry_id,
                    entry.sanctions_program,
                    f"{score*100:.1f}%",
                    matched_name,
                    entry.primary_name,
                    entry.listing_reason[:60] + "..."
                ])
            print(tabulate(rows, headers=["Entry ID", "Program", "Match Score", "Matched On", "Primary Name", "Listing Reason"], tablefmt="grid"))

    elif args.command == "sar":
        mode_str = "offline deterministic engine" if args.offline else "local Ollama LLM / deterministic fallback"
        print(f"\nDrafting {args.type} for subject '{args.customer_id}' using {mode_str}...")
        generator = SARNarrativeGenerator(force_offline=args.offline)
        try:
            sar = generator.generate_sar(
                customer_id=args.customer_id,
                filing_type=args.type,
                mlro_notes=args.notes
            )
        except Exception as e:
            print(f"Error generating SAR: {e}")
            sys.exit(1)

        if args.output == "markdown":
            formatted = AMLReporter.sar_to_markdown(sar)
        elif args.output == "json":
            formatted = AMLReporter.sar_to_json(sar)
        else: # terminal
            formatted = AMLReporter.sar_to_markdown(sar)

        if args.save:
            with open(args.save, "w", encoding="utf-8") as f:
                f.write(formatted)
            print(f"[+] SAR filing successfully saved to: {args.save}")
        else:
            print("\n" + formatted)

    elif args.command == "stats":
        stats = get_database_stats()
        print("\n=== AML SURVEILLANCE & TRANSACTION MONITORING METRICS ===")
        print(f"Total Customers:            {stats['customers']}")
        print(f"Total Accounts:             {stats['accounts']}")
        print(f"Total Ledger Transactions:  {stats['transactions']}")
        print(f"Synthetic Ground Anomalies: {stats['synthetic_anomalies']}")
        print(f"Watchlist Sanctions:        {stats['sanctions_entries']}")
        print(f"Active Alerts in DB:        {stats['alerts_generated']}")
        print(f"Filed SAR Records:          {stats['sar_filings']}")

if __name__ == "__main__":
    main()
