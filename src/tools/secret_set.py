"""
secret_set.py — CLI for managing MC secrets in Windows Credential Manager.

Usage:
    python -m src.tools.secret_set MC_GH_PAT
    python -m src.tools.secret_set MC_TG_BOT_TOKEN
    python -m src.tools.secret_set MC_GCAL_TOKEN
    python -m src.tools.secret_set --list
    python -m src.tools.secret_set --delete MC_GH_PAT

Secrets are stored via keyring → Windows Credential Manager (DPAPI).
Never stored in .env or any plaintext file (ADR-005).
"""

import argparse
import getpass
import sys

try:
    import keyring
except ImportError:
    print("[ERROR] keyring not installed: pip install keyring pywin32", file=sys.stderr)
    sys.exit(1)

KNOWN_KEYS = ("MC_GH_PAT", "MC_TG_BOT_TOKEN", "MC_GCAL_TOKEN")
_KEYRING_USER = "iet03"


def cmd_set(key: str) -> None:
    if key not in KNOWN_KEYS:
        print(f"[WARN] '{key}' is not in known keys: {KNOWN_KEYS}", file=sys.stderr)
    value = getpass.getpass(f"Value for {key}: ")
    if not value.strip():
        print("[ERROR] Empty value — aborting.", file=sys.stderr)
        sys.exit(1)
    keyring.set_password(key, _KEYRING_USER, value.strip())
    print(f"[OK] Stored {key} in Windows Credential Manager.")


def cmd_list() -> None:
    print("MC secrets in Windows Credential Manager:")
    for key in KNOWN_KEYS:
        val = keyring.get_password(key, _KEYRING_USER)
        status = "✓ set" if val else "✗ not set"
        print(f"  {key:30s} {status}")


def cmd_delete(key: str) -> None:
    try:
        keyring.delete_password(key, _KEYRING_USER)
        print(f"[OK] Deleted {key}")
    except keyring.errors.PasswordDeleteError:
        print(f"[WARN] {key} was not set.")


def main() -> None:
    parser = argparse.ArgumentParser(description="MC secret manager (Windows Credential Manager)")
    parser.add_argument("key", nargs="?", help="Secret key to set")
    parser.add_argument("--list", action="store_true", help="List all secrets")
    parser.add_argument("--delete", metavar="KEY", help="Delete a secret")
    args = parser.parse_args()

    if args.list:
        cmd_list()
    elif args.delete:
        cmd_delete(args.delete)
    elif args.key:
        cmd_set(args.key)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
