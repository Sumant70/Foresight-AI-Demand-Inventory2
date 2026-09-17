"""
Server-Side Session Management for Foresight AI.
Python Standard Library (secrets, datetime) only.
Provides secure random tokens, idle timeout, max lifetime, and cookie formatting.
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

DEFAULT_SESSION_HOURS = 8
REMEMBER_ME_DAYS = 7
IDLE_TIMEOUT_MINUTES = 30
COOKIE_NAME = "foresight_session"


class SessionManager:
    """Handles server-side session persistence in SQLite with idle and max expiry."""

    def __init__(self, db):
        self.db = db
        # Configurable via environment variables
        self.session_hours = int(os.environ.get("FORESIGHT_SESSION_HOURS", DEFAULT_SESSION_HOURS))
        self.idle_minutes = int(os.environ.get("FORESIGHT_IDLE_MINUTES", IDLE_TIMEOUT_MINUTES))
        self.secure_cookie = os.environ.get("FORESIGHT_SECURE_COOKIE", "false").lower() in ("true", "1", "yes")

    def create_session(self, user_id: int, remember_me: bool = False, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Dict[str, Any]:
        """Creates and stores a new cryptographically secure session and CSRF token."""
        session_id = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)

        lifetime_delta = timedelta(days=REMEMBER_ME_DAYS) if remember_me else timedelta(hours=self.session_hours)
        expires_at = (datetime.now() + lifetime_delta).isoformat()

        self.db.create_session(
            session_id=session_id,
            user_id=user_id,
            csrf_token=csrf_token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return {
            "session_id": session_id,
            "csrf_token": csrf_token,
            "expires_at": expires_at,
            "max_age_seconds": int(lifetime_delta.total_seconds()),
        }

    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Validates session existence, account active status, absolute expiry,
        and idle timeout. Updates last activity if valid.
        """
        if not session_id:
            return None

        session = self.db.get_session(session_id)
        if not session:
            return None

        # Verify user is active
        if not session["is_active"]:
            self.db.delete_session(session_id)
            return None

        now = datetime.now()

        # Check absolute expiration
        try:
            expires_dt = datetime.fromisoformat(session["expires_at"])
            if now > expires_dt:
                self.db.delete_session(session_id)
                return None
        except ValueError:
            self.db.delete_session(session_id)
            return None

        # Check idle timeout
        try:
            last_activity_dt = datetime.fromisoformat(session["last_activity"])
            if (now - last_activity_dt).total_seconds() > (self.idle_minutes * 60):
                self.db.delete_session(session_id)
                return None
        except ValueError:
            pass

        # Valid session -> Update last activity
        self.db.update_session_activity(session_id, now.isoformat())
        return session

    def destroy_session(self, session_id: str):
        """Invalidates a single session on logout."""
        if session_id:
            self.db.delete_session(session_id)

    def extract_session_id_from_headers(self, headers) -> Optional[str]:
        """Parses the session ID from HTTP Cookie headers."""
        cookie_header = headers.get("Cookie", "")
        if not cookie_header:
            return None

        cookies = [c.strip() for c in cookie_header.split(";")]
        for c in cookies:
            if "=" in c:
                name, val = c.split("=", 1)
                if name.strip() == COOKIE_NAME:
                    return val.strip()
        return None

    def build_set_cookie_header(self, session_id: str, max_age_seconds: int) -> str:
        """Constructs secure Set-Cookie header string."""
        parts = [
            f"{COOKIE_NAME}={session_id}",
            "Path=/",
            f"Max-Age={max_age_seconds}",
            "HttpOnly",
            "SameSite=Lax",
        ]
        if self.secure_cookie:
            parts.append("Secure")
        return "; ".join(parts)

    def build_clear_cookie_header(self) -> str:
        """Constructs cookie expiration header to clear client cookie on logout."""
        parts = [
            f"{COOKIE_NAME}=",
            "Path=/",
            "Expires=Thu, 01 Jan 1970 00:00:00 GMT",
            "Max-Age=0",
            "HttpOnly",
            "SameSite=Lax",
        ]
        if self.secure_cookie:
            parts.append("Secure")
        return "; ".join(parts)
