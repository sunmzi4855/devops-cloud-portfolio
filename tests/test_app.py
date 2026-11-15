import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen
from app.main import Handler


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_health(self):
        with urlopen(self.base + "/health") as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.load(response)["status"], "healthy")

    def test_metrics(self):
        with urlopen(self.base + "/health"):
            pass
        with urlopen(self.base + "/metrics") as response:
            self.assertEqual(response.status, 200)
            text = response.read().decode()
            self.assertIn("devops_http_requests_total", text)
            self.assertIn('path="/health"', text)

    def test_not_found(self):
        with self.assertRaises(HTTPError) as e:
            urlopen(self.base + "/missing")
        self.assertEqual(e.exception.code, 404)
