import json
import subprocess
import sys
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from app.main import Handler
from reliability.release_gate import evaluate


class ReleaseGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls.thread.join)
        cls.addClassCleanup(cls.server.server_close)
        cls.addClassCleanup(cls.server.shutdown)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    def run_gate(self, path, *flags):
        script = Path(__file__).resolve().parents[1] / "reliability" / "release_gate.py"
        return subprocess.run(
            [sys.executable, str(script), self.base + path, "--samples", "3",
             "--max-p95-ms", "10000", *flags],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_healthy_endpoint_promotes(self):
        result = self.run_gate("/health")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["decision"], "promote")
        self.assertEqual(report["successful_probes"], 3)
        self.assertEqual(report["probe_failures"], [])

    def test_http_error_holds(self):
        result = self.run_gate("/missing")
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["decision"], "hold")
        self.assertIsNone(report["p95_ms"])
        self.assertEqual(
            [failure["reason"] for failure in report["probe_failures"]],
            ["HTTP 404"] * 3,
        )

    def test_200_with_wrong_health_payload_holds(self):
        result = self.run_gate("/")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["successful_probes"], 0)

    def test_nonfinite_threshold_is_rejected(self):
        result = self.run_gate("/health", "--max-p95-ms", "nan")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")

    def test_p95_uses_nearest_rank_and_holds_when_over_limit(self):
        samples = [(20, None)] * 18 + [(300, None), (900, None)]
        with patch("reliability.release_gate.probe", side_effect=samples):
            report = evaluate(self.base + "/health", 20, 250, 2)

        self.assertEqual(report["decision"], "hold")
        self.assertEqual(report["p95_ms"], 300)
        self.assertEqual(report["probe_failures"], [])
