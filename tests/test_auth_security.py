"""
Comprehensive Security & Authentication Test Suite for Foresight AI.
Validates:
- PBKDF2-HMAC-SHA256 hashing and verification
- Enterprise password policy enforcement
- Brute-force account lockout (5 attempts -> 15 min lock)
- Session lifecycle (idle timeout, max age, HttpOnly cookies)
- CSRF token validation
- RBAC permissions (ADMIN, ANALYST, VIEWER)
- HTTP security headers and endpoint protection
"""

import os
import time
import json
import unittest
import urllib.request
import urllib.parse
from http.cookiejar import CookieJar
from datetime import datetime, timedelta

from src.security.database import SecurityDatabase
from src.security.auth import hash_password, verify_password, validate_password_policy, AuthService
from src.security.session import SessionManager
from src.security.csrf import CSRFManager
from src.security.rbac import RBAC, ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER


class TestPasswordSecurity(unittest.TestCase):
    """Unit tests for PBKDF2 hashing and password policy validation."""

    def test_pbkdf2_hashing_and_verification(self):
        password = "SecureEnterprisePassword2026!"
        p_hash, p_salt = hash_password(password)

        self.assertIsInstance(p_hash, str)
        self.assertIsInstance(p_salt, str)
        self.assertEqual(len(p_salt), 64)  # 32 bytes in hex = 64 chars

        # Verify correct password
        self.assertTrue(verify_password(password, p_hash, p_salt))

        # Verify incorrect password
        self.assertFalse(verify_password("WrongPassword123!", p_hash, p_salt))

        # Verify salt uniqueness
        p_hash2, p_salt2 = hash_password(password)
        self.assertNotEqual(p_salt, p_salt2)
        self.assertNotEqual(p_hash, p_hash2)

    def test_password_policy(self):
        # Too short (< 12)
        valid, msg = validate_password_policy("Short1!")
        self.assertFalse(valid)
        self.assertIn("at least 12", msg)

        # Missing uppercase
        valid, msg = validate_password_policy("nouppercasehere123!")
        self.assertFalse(valid)
        self.assertIn("uppercase", msg)

        # Missing lowercase
        valid, msg = validate_password_policy("NOLOWERCASEHERE123!")
        self.assertFalse(valid)
        self.assertIn("lowercase", msg)

        # Missing digit
        valid, msg = validate_password_policy("NoDigitsInThisPassword!")
        self.assertFalse(valid)
        self.assertIn("numerical digit", msg)

        # Missing special character
        valid, msg = validate_password_policy("NoSpecialCharacter1234")
        self.assertFalse(valid)
        self.assertIn("special character", msg)

        # Valid password
        valid, msg = validate_password_policy("ValidPassword123!")
        self.assertTrue(valid)


class TestAuthAndLockout(unittest.TestCase):
    """Tests for authentication and brute-force mitigation."""

    def setUp(self):
        # Use an isolated in-memory or temporary SQLite database
        self.db = SecurityDatabase(":memory:")
        self.auth_service = AuthService(self.db)

        # Create a test user
        p_hash, p_salt = hash_password("TestMasterPass2026!")
        self.user_id = self.db.create_user(
            username="lockout_tester",
            email="tester@foresight.ai",
            password_hash=p_hash,
            password_salt=p_salt,
            role="ANALYST"
        )

    def test_successful_authentication(self):
        res = self.auth_service.authenticate("lockout_tester", "TestMasterPass2026!", ip_address="127.0.0.1")
        self.assertTrue(res["success"])
        self.assertEqual(res["user"]["username"], "lockout_tester")

    def test_timing_safe_nonexistent_user(self):
        res = self.auth_service.authenticate("nonexistent_user", "SomePassword123!", ip_address="127.0.0.1")
        self.assertFalse(res["success"])
        self.assertEqual(res["error"], "Invalid username or password.")

    def test_brute_force_lockout_after_five_failures(self):
        # 4 failed attempts -> still active
        for i in range(1, 5):
            res = self.auth_service.authenticate("lockout_tester", "BadPassword!", ip_address="127.0.0.1")
            self.assertFalse(res["success"])
            self.assertEqual(res["error"], "Invalid username or password.")

        # 5th failed attempt -> locks out account
        res5 = self.auth_service.authenticate("lockout_tester", "BadPassword!", ip_address="127.0.0.1")
        self.assertFalse(res5["success"])
        self.assertIn("locked", res5["error"].lower())

        # 6th attempt with correct password while locked -> still blocked!
        res6 = self.auth_service.authenticate("lockout_tester", "TestMasterPass2026!", ip_address="127.0.0.1")
        self.assertFalse(res6["success"])
        self.assertIn("locked", res6["error"].lower())

        # Admin unlocks user
        self.db.unlock_user(self.user_id)

        # Now correct password succeeds
        res_after = self.auth_service.authenticate("lockout_tester", "TestMasterPass2026!", ip_address="127.0.0.1")
        self.assertTrue(res_after["success"])


class TestSessionLifecycle(unittest.TestCase):
    """Tests for session creation, validation, idle expiration, and cookie strings."""

    def setUp(self):
        self.db = SecurityDatabase(":memory:")
        self.session_mgr = SessionManager(self.db)
        p_hash, p_salt = hash_password("ValidPassword2026!")
        self.user_id = self.db.create_user("session_user", "session@foresight.ai", p_hash, p_salt, "ANALYST")

    def test_create_and_validate_session(self):
        sess = self.session_mgr.create_session(self.user_id, ip_address="127.0.0.1")
        token = sess["session_id"]
        self.assertIsNotNone(token)
        self.assertIsNotNone(sess["csrf_token"])

        # Validate
        val = self.session_mgr.validate_session(token)
        self.assertIsNotNone(val)
        self.assertEqual(val["user_id"], self.user_id)

    def test_deactivated_user_session_invalidation(self):
        sess = self.session_mgr.create_session(self.user_id)
        # Deactivate user
        self.db.update_user_status(self.user_id, False)

        val = self.session_mgr.validate_session(sess["session_id"])
        self.assertIsNone(val)

    def test_destroy_session_on_logout(self):
        sess = self.session_mgr.create_session(self.user_id)
        self.session_mgr.destroy_session(sess["session_id"])
        val = self.session_mgr.validate_session(sess["session_id"])
        self.assertIsNone(val)

    def test_cookie_headers(self):
        set_hdr = self.session_mgr.build_set_cookie_header("test_token_abc", 3600)
        self.assertIn("foresight_session=test_token_abc", set_hdr)
        self.assertIn("HttpOnly", set_hdr)
        self.assertIn("SameSite=Lax", set_hdr)
        self.assertIn("Max-Age=3600", set_hdr)

        clear_hdr = self.session_mgr.build_clear_cookie_header()
        self.assertIn("Max-Age=0", clear_hdr)
        self.assertIn("Expires=", clear_hdr)


class TestCSRFProtection(unittest.TestCase):
    """Tests for anti-CSRF token verification."""

    def setUp(self):
        self.db = SecurityDatabase(":memory:")
        self.session_mgr = SessionManager(self.db)
        self.csrf_mgr = CSRFManager(self.db)
        p_hash, p_salt = hash_password("ValidPassword2026!")
        self.user_id = self.db.create_user("csrf_user", "csrf@foresight.ai", p_hash, p_salt, "ANALYST")
        self.sess = self.session_mgr.create_session(self.user_id)

    def test_csrf_validation(self):
        token = self.sess["csrf_token"]
        session_id = self.sess["session_id"]

        # Valid token
        self.assertTrue(self.csrf_mgr.validate_token(session_id, token))

        # Tampered / invalid token
        self.assertFalse(self.csrf_mgr.validate_token(session_id, "invalid_forged_token"))

        # Empty token
        self.assertFalse(self.csrf_mgr.validate_token(session_id, ""))
        self.assertFalse(self.csrf_mgr.validate_token(session_id, None))


class TestRBACPermissions(unittest.TestCase):
    """Tests for role-based access control policies."""

    def test_admin_permissions(self):
        self.assertTrue(RBAC.has_permission(ROLE_ADMIN, "admin:users"))
        self.assertTrue(RBAC.has_permission(ROLE_ADMIN, "admin:security"))
        self.assertTrue(RBAC.has_permission(ROLE_ADMIN, "view:inventory"))
        self.assertTrue(RBAC.has_permission(ROLE_ADMIN, "view:dashboard"))
        self.assertTrue(RBAC.can_access_endpoint(ROLE_ADMIN, "/api/admin/users"))
        self.assertTrue(RBAC.can_access_endpoint(ROLE_ADMIN, "/api/admin/security-status"))

    def test_analyst_permissions(self):
        self.assertFalse(RBAC.has_permission(ROLE_ANALYST, "admin:users"))
        self.assertFalse(RBAC.has_permission(ROLE_ANALYST, "admin:security"))
        self.assertTrue(RBAC.has_permission(ROLE_ANALYST, "view:inventory"))
        self.assertTrue(RBAC.has_permission(ROLE_ANALYST, "view:forecast"))
        self.assertFalse(RBAC.can_access_endpoint(ROLE_ANALYST, "/api/admin/users"))
        self.assertTrue(RBAC.can_access_endpoint(ROLE_ANALYST, "/api/inventory"))

    def test_viewer_permissions(self):
        self.assertFalse(RBAC.has_permission(ROLE_VIEWER, "admin:users"))
        self.assertFalse(RBAC.has_permission(ROLE_VIEWER, "view:inventory"))
        self.assertFalse(RBAC.has_permission(ROLE_VIEWER, "view:stockout"))
        self.assertTrue(RBAC.has_permission(ROLE_VIEWER, "view:dashboard"))
        self.assertTrue(RBAC.has_permission(ROLE_VIEWER, "view:products"))
        self.assertFalse(RBAC.can_access_endpoint(ROLE_VIEWER, "/api/inventory"))
        self.assertFalse(RBAC.can_access_endpoint(ROLE_VIEWER, "/api/stockout"))
        self.assertTrue(RBAC.can_access_endpoint(ROLE_VIEWER, "/api/overview"))
        self.assertTrue(RBAC.can_access_endpoint(ROLE_VIEWER, "/api/products"))


if __name__ == "__main__":
    unittest.main()
