"""Runs every test script in this folder and prints a summary. Usage: python tests/run_all.py"""
import subprocess, sys
from pathlib import Path

here = Path(__file__).resolve().parent
results = []
for t in sorted(here.glob("test_*.py")):
    print("\n=== %s ===" % t.name)
    r = subprocess.run([sys.executable, str(t)])
    results.append((t.name, r.returncode))
print("\n--- summary ---")
for n, c in results:
    print(("ok    " if c == 0 else "FAIL  ") + n)
sys.exit(1 if any(c for _, c in results) else 0)
