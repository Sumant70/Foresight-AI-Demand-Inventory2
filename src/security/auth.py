"""
Password Hashing and Policy Validation for Foresight AI.
Python Standard Library (hashlib, hmac, secrets, re) only.
Implements PBKDF2-HMAC-SHA256 with 32-byte salt, constant-time verification,
and enterprise password strength policy enforcement.
"""

import re
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any, Optional

ITERATIONS = 100_000
SALT_BYTES = 32
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[str, str]:
    """
    Hashes password using PBKDF2-HMAC-SHA256 with 100,000 iterations.
    Returns (hash_hex, salt_hex).
    """
    if salt is None:
        salt = secrets.token_bytes(SALT_BYTES)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return derived.hex(), salt.hex()


def verify_password(password: str, hash_hex: str, salt_hex: str) -> bool:
    """Constant-time verification of password against stored hash and salt."""
    try:
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        calculated_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
        return hmac.compare_digest(calculated_hash, expected_hash)
    except Exception:
        return False


def validate_password_policy(password: str) -> Tuple[bool, str]:
    """
    Enforces password complexity:
    - Min 12 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    - At least 1 special character
    """
    if len(password) < 12:
        return False, "Password must be at least 12 characters in length."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one numerical digit."
    if not re.search(r"[!@#$%^&*()_\-+=\[\]{}|;:,.<>?/~`]", password):
        return False, "Password must contain at least one special character."
    return True, "Password meets all enterprise security criteria."


class AuthService:
    """Manages authentication, brute-force mitigation, and account lockout."""

    def __init__(self, db):
        self.db = db

    def authenticate(self, identifier: str, password: str, ip_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Authenticates user with timing-safe checks and brute-force mitigation.
        Never reveals whether the user or email exists.
        """
        user = self.db.get_user_by_username_or_email(identifier)
        now = datetime.now()

        # Dummy computation for constant time if user does not exist
        if not user:
            dummy_salt = secrets.token_bytes(SALT_BYTES)
            hash_password(password, dummy_salt)
            self.db.log_audit_event("LOGIN_FAILURE", None, ip_address, f"Identifier not found: {identifier[:3]}***")
            return {"success": False, "error": "Invalid username or password."}

        # Check account activation
        if not user["is_active"]:
            self.db.log_audit_event("LOGIN_INACTIVE_BLOCK", user["id"], ip_address, "Account deactivated")
            return {"success": False, "error": "Invalid username or password."}

        # Check temporary lockout
        locked_until_str = user["locked_until"]
        if locked_until_str:
            try:
                locked_until_dt = datetime.fromisoformat(locked_until_str)
                if now < locked_until_dt:
                    diff_mins = int((locked_until_dt - now).total_seconds() / 60) + 1
                    self.db.log_audit_event("LOGIN_LOCKED_BLOCK", user["id"], ip_address, f"Locked for {diff_mins}m")
                    return {
                        "success": False,
                        "error": f"Account temporarily locked due to excessive failed attempts. Please try again in {diff_mins} minutes or contact your administrator."
                    }
                else:
                    # Lockout expired, reset attempts
                    self.db.unlock_user(user["id"])
            except ValueError:
                pass

        # Verify password
        is_valid = verify_password(password, user["password_hash"], user["password_salt"])

        if is_valid:
            self.db.record_login_success(user["id"])
            self.db.log_audit_event("LOGIN_SUCCESS", user["id"], ip_address, f"User {user['username']} logged in")
            return {"success": True, "user": user}
        else:
            # Handle failure and check if lockout threshold reached
            failed_count = user["failed_login_attempts"] + 1
            if failed_count >= MAX_FAILED_ATTEMPTS:
                lock_dt = now + timedelta(minutes=LOCKOUT_MINUTES)
                self.db.record_login_failure(user["id"], lock_until=lock_dt.isoformat())
                self.db.log_audit_event("ACCOUNT_LOCKOUT", user["id"], ip_address, f"Exceeded {MAX_FAILED_ATTEMPTS} attempts. Locked for {LOCKOUT_MINUTES}m")
                return {
                    "success": False,
                    "error": f"Account temporarily locked due to excessive failed attempts. Please try again in {LOCKOUT_MINUTES} minutes."
                }
            else:
                self.db.record_login_failure(user["id"])
                self.db.log_audit_event("LOGIN_FAILURE", user["id"], ip_address, f"Bad password ({failed_count}/{MAX_FAILED_ATTEMPTS})")
                return {"success": False, "error": "Invalid username or password."}
