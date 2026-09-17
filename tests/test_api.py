"""
Integration Tests for Foresight AI Local REST API.
Python Standard Library only (urllib, threading, http.server).
"""

import unittest
import threading
import json
import urllib.request
import urllib.error
from http.server import HTTPServer
from app import ForesightHTTPHandler, app_state, sec_db, session_mgr
from src.security.auth import hash_password


class TestAPIEndpoints(unittest.TestCase):
    server = None
    server_thread = None
    port = 8899
    base_url = f"http://127.0.0.1:{port}"
    session_cookie = None

    @classmethod
    def setUpClass(cls):
        # Ensure test admin exists and session created
        p_hash, p_salt = hash_password("ApiTestAdminPassword2026!")
        user = sec_db.get_user_by_username_or_email("api_tester")
        if not user:
            uid = sec_db.create_user("api_tester", "api@foresight.ai", p_hash, p_salt, "ADMIN")
        else:
            uid = user["id"]
        sess = session_mgr.create_session(uid)
        cls.session_cookie = f"foresight_session={sess['session_id']}"

        cls.server = HTTPServer(("127.0.0.1", cls.port), ForesightHTTPHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        if cls.server:
            cls.server.shutdown()
            cls.server.server_close()

    def _get(self, endpoint, with_auth=True):
        req = urllib.request.Request(f"{self.base_url}{endpoint}")
        if with_auth and self.session_cookie:
            req.add_header("Cookie", self.session_cookie)
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, response.read()

    def test_public_api_direct_access(self):
        # All endpoints now support direct public access without authentication gating
        req = urllib.request.Request(f"{self.base_url}/api/overview")
        with urllib.request.urlopen(req, timeout=5) as response:
            self.assertEqual(response.status, 200)
            data = json.loads(response.read().decode("utf-8"))
            self.assertIn("kpis", data)

    def test_health_endpoint(self):
        # Health endpoint is public
        status, body = self._get("/api/health", with_auth=False)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["skus"], 50)

    def test_overview_endpoint(self):
        status, body = self._get("/api/overview")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("kpis", data)

        self.assertEqual(data["kpis"]["total_products"], 50)
        self.assertIn("monthly_sales", data)
        self.assertIn("insights", data)

    def test_products_endpoint(self):
        status, body = self._get("/api/products")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(len(data), 50)

        # Test SKU filter
        status, body = self._get("/api/products?sku=SKU001")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["sku"], "SKU001")

    def test_inventory_endpoint(self):
        status, body = self._get("/api/inventory")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("summary", data)
        self.assertIn("matrix", data)
        self.assertEqual(len(data["matrix"]), 50)

    def test_forecast_endpoint(self):
        status, body = self._get("/api/forecast?sku=SKU001&horizon=14")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["sku"], "SKU001")
        self.assertIn("forecast", data)
        self.assertEqual(len(data["forecast"]["points"]), 14)

    def test_stockout_endpoint(self):
        status, body = self._get("/api/stockout")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("summary", data)
        self.assertIn("risks", data)
        self.assertEqual(len(data["risks"]), 50)

    def test_reorder_endpoint(self):
        status, body = self._get("/api/reorder")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("summary", data)
        self.assertIn("recommendations", data)
        self.assertEqual(len(data["recommendations"]), 50)

    def test_csv_export_endpoint(self):
        status, body = self._get("/api/export/products")
        self.assertEqual(status, 200)
        content = body.decode("utf-8")
        self.assertTrue(content.startswith("SKU,Product_Name"))
        self.assertGreater(len(content.splitlines()), 50)


if __name__ == "__main__":
    unittest.main()
