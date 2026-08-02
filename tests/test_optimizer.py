import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import AppHandler
from optimizer import optimize


class OptimizerTests(unittest.TestCase):
    def test_plan_respects_dairy_exclusion_and_budget(self):
        result = optimize({"age": 16, "sex": "female", "activity": "medium", "budget": 13000, "exclusions": ["dairy"]})
        self.assertTrue(result["constraints"]["알레르기·제외 식품"])
        self.assertLessEqual(result["totals"]["cost"], 13000)
        self.assertNotIn("우유", sum(result["meals"].values(), []))
        self.assertNotIn("플레인요거트", sum(result["meals"].values(), []))

    def test_invalid_age_is_rejected(self):
        with self.assertRaises(ValueError):
            optimize({"age": 12, "budget": 12000})


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_health_and_optimize(self):
        conn = HTTPConnection("127.0.0.1", self.server.server_port)
        conn.request("GET", "/api/health")
        health_response = conn.getresponse()
        self.assertEqual(health_response.status, 200)
        health = json.loads(health_response.read())
        self.assertEqual(health["mode"], "deterministic_demo")
        self.assertEqual(health["data"], "synthetic_estimates")
        conn.request("POST", "/api/optimize", json.dumps({"age": 16, "budget": 12000}), {"Content-Type": "application/json"})
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        self.assertIn("meals", json.loads(response.read()))

    def test_home_is_served(self):
        conn = HTTPConnection("127.0.0.1", self.server.server_port)
        conn.request("GET", "/")
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        self.assertIn("Meal Constraint Lab", response.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
