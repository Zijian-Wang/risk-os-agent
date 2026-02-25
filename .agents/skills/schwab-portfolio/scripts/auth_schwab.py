#!/usr/bin/env python3
"""
One-time OAuth flow for Schwab API. Opens browser to sign in.
Run once to create token.json. Token is refreshed automatically by get_positions.py.
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE = REPO_ROOT / "workspace" / "portfolio"
WORKSPACE.mkdir(parents=True, exist_ok=True)

TOKEN_PATH = Path(os.environ.get("SCHWAB_TOKEN_PATH", str(WORKSPACE / "token.json")))

api_key = os.environ.get("SCHWAB_API_KEY")
app_secret = os.environ.get("SCHWAB_APP_SECRET")
callback = os.environ.get("SCHWAB_CALLBACK_URL", "https://127.0.0.1")

if not api_key or not app_secret:
    print("Set SCHWAB_API_KEY and SCHWAB_APP_SECRET. Get keys from https://developer.schwab.com/")
    sys.exit(1)

try:
    from schwab.auth import easy_client
except ImportError:
    print("pip install schwab-py")
    sys.exit(1)

print(f"Token will be saved to {TOKEN_PATH}")
print("A browser will open for Schwab sign-in...")

c = easy_client(
    api_key=api_key,
    app_secret=app_secret,
    callback_url=callback,
    token_path=str(TOKEN_PATH),
)

# Test
r = c.get_account_numbers()
if r.status_code == 200:
    print("Auth successful. Run get_positions.py to fetch portfolio.")
else:
    print(f"Auth may have failed: {r.status_code} {r.text}")
    sys.exit(1)
