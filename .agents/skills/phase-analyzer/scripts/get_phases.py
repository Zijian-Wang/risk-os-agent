#!/usr/bin/env python3
"""
Compute phases for multiple tickers. Calls get_phase logic per ticker.
Usage: get_phases.py TICKER1 TICKER2 ...
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
GET_PHASE = SCRIPT_DIR / "get_phase.py"


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: get_phases.py TICKER1 TICKER2 ..."}))
        sys.exit(1)

    tickers = [t.upper() for t in sys.argv[1:]]
    results = []

    for ticker in tickers:
        try:
            out = subprocess.run(
                [sys.executable, str(GET_PHASE), ticker],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if out.returncode == 0:
                results.append(json.loads(out.stdout))
            else:
                results.append({"ticker": ticker, "error": out.stderr or out.stdout or "Unknown error"})
        except Exception as e:
            results.append({"ticker": ticker, "error": str(e)})

    print(json.dumps({"phases": results}))


if __name__ == "__main__":
    main()
