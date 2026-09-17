"""
First-Time Administrator Setup Utility for Foresight AI.
Python Standard Library (getpass, argparse, sys) only.
Securely initializes the primary ADMIN account in users.db without printing credentials.
"""

import sys
import getpass
import argparse
from pathlib import Path

from src.security.database import SecurityDatabase
from src.security.auth import hash_password, validate_password_policy


def create_admin_interactive(username=None, email=None, password=None):
    print("=" * 60)
    print("  FORESIGHT AI — Administrator Account Initialization")
    print("=" * 60)

    db = SecurityDatabase()

    if not username:
        username = input("Enter Admin Username: ").strip()
    if not email:
        email = input("Enter Admin Email: ").strip()

    if not username or not email:
        print("[Error] Username and Email are required.")
        sys.exit(1)

    # Check if user already exists
    existing = db.get_user_by_username_or_email(username)
    if existing:
        if password:
            is_valid, msg = validate_password_policy(password)
            if not is_valid:
                print(f"[Error] {msg}")
                sys.exit(1)
            p_hash, p_salt = hash_password(password)
            db.update_user_password(existing["id"], p_hash, p_salt)
            db.update_user_role(existing["id"], "ADMIN")
            db.update_user_status(existing["id"], True)
            db.unlock_user(existing["id"])
            db.delete_all_user_sessions(existing["id"])
            db.log_audit_event("PASSWORD_RESET_CLI", existing["id"], "127.0.0.1", f"Admin '{username}' password reset via CLI")
            print(f"[Success] User '{username}' password successfully updated and account unlocked.")
            return
        else:
            print(f"[Notice] User '{username}' already exists. Updating role to ADMIN and unlocking account.")
            db.update_user_role(existing["id"], "ADMIN")
            db.update_user_status(existing["id"], True)
            db.unlock_user(existing["id"])
            print("[Success] User is now an active ADMIN.")
            return

    # Password input & confirmation
    if not password:
        while True:
            password = getpass.getpass("Enter Admin Password (min 12 chars, upper, lower, digit, symbol): ")
            confirm = getpass.getpass("Confirm Admin Password: ")

            if password != confirm:
                print("[Error] Passwords do not match. Please try again.\n")
                continue

            is_valid, msg = validate_password_policy(password)
            if not is_valid:
                print(f"[Error] {msg}\n")
                continue
            break
    else:
        is_valid, msg = validate_password_policy(password)
        if not is_valid:
            print(f"[Error] {msg}")
            sys.exit(1)

    # Hash and store securely
    p_hash, p_salt = hash_password(password)
    user_id = db.create_user(
        username=username,
        email=email,
        password_hash=p_hash,
        password_salt=p_salt,
        role="ADMIN"
    )

    db.log_audit_event("USER_CREATED", user_id, "127.0.0.1", f"Initial admin '{username}' initialized via CLI")

    print(f"\n[Success] Administrator '{username}' successfully initialized (ID: {user_id}).")
    print("[Security Notice] Password has been hashed with PBKDF2-HMAC-SHA256 and stored in users.db.")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Foresight AI Initial Administrator Account")
    parser.add_argument("--username", help="Admin username")
    parser.add_argument("--email", help="Admin email")
    parser.add_argument("--password", help="Admin password (non-interactive)")
    parser.add_argument("--reset", action="store_true", help="Reset existing admin credentials")

    args = parser.parse_args()
    create_admin_interactive(args.username, args.email, args.password)

