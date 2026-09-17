"""
CSRF Protection Middleware for Foresight AI.
Python Standard Library (hmac) only.
Validates session-bound CSRF tokens on state-changing HTTP methods.
"""

import hmac
from typing import Dict, Any, Optional

EXEMPT_PATHS = {
    "/api/auth/login",
    "/api/auth/forgot-password",
}


class CSRFProtection:
    """Validates session-bound CSRF tokens."""

    def __init__(self, db=None):
        self.db = db

    @staticmethod
    def is_exempt(path: str) -> bool:
        clean_path = path.split("?")[0]
        return clean_path in EXEMPT_PATHS

    @staticmethod
    def validate(request_method: str, path: str, session: Optional[Dict[str, Any]], provided_token: Optional[str]) -> bool:
        """
        Validates CSRF token for mutating requests (POST, PUT, DELETE).
        Returns True if exempt or valid; False otherwise.
        """
        if request_method.upper() in ("GET", "HEAD", "OPTIONS"):
            return True

        if CSRFProtection.is_exempt(path):
            return True

        if not session or not session.get("csrf_token"):
            return False

        if not provided_token:
            return False

        expected_token = session["csrf_token"]
        return hmac.compare_digest(provided_token.strip(), expected_token.strip())

    def validate_token(self, session_id_or_dict, provided_token: Optional[str]) -> bool:
        """Validates provided token against session token or session ID lookup."""
        if not provided_token:
            return False
        if isinstance(session_id_or_dict, dict):
            expected = session_id_or_dict.get("csrf_token")
        elif self.db and isinstance(session_id_or_dict, str):
            sess = self.db.get_session(session_id_or_dict)
            expected = sess.get("csrf_token") if sess else None
        else:
            expected = None

        if not expected:
            return False
        return hmac.compare_digest(str(provided_token).strip(), str(expected).strip())


CSRFManager = CSRFProtection

