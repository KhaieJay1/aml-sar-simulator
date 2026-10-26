import subprocess
import sys
import os

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_cli(*args):
    cmd = [sys.executable, "-m", "src.cli"] + list(args)
    res = subprocess.run(
        cmd,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )
    return res

def test_cli_stats():
    res = run_cli("stats")
    assert res.returncode == 0
    assert "Total Customers:" in res.stdout
    assert "Total Ledger Transactions:" in res.stdout

def test_cli_scan():
    res = run_cli("scan")
    assert res.returncode == 0
    assert "Scan completed" in res.stdout
    assert "SANCTIONS_PEP_MATCH" in res.stdout or "STRUCTURING" in res.stdout

def test_cli_screen_hit():
    res = run_cli("screen", "Victor Butt")
    assert res.returncode == 0
    assert "Watchlist Hits Detected" in res.stdout
    assert "UK_OFSI" in res.stdout

def test_cli_screen_clean():
    res = run_cli("screen", "Alice Clean Customer")
    assert res.returncode == 0
    assert "Zero watchlist hits found" in res.stdout

def test_cli_sar_offline():
    res = run_cli("sar", "CUST-ANOM-STR-01", "--offline", "--output", "markdown")
    assert res.returncode == 0
    assert "UK_NCA_SAR Suspicious Activity Report" in res.stdout
    assert "Arthur Pendelton" in res.stdout
    assert "5Ws Regulatory Narrative Breakdown" in res.stdout
