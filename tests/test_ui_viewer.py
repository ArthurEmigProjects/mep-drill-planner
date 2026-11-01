"""The local page can hand an IFC to the browser viewer."""

from __future__ import annotations

import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from src.ui import WEB, AppHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "HeatingAndCooling.ifc"


class ViewerHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address
        cls.base = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_page_loads_that_open_viewer(self):
        page = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("@thatopen/components", page)
        self.assertIn('id="viewer-canvas"', page)
        script = (WEB / "viewer.js").read_text(encoding="utf-8")
        self.assertIn("FragmentsManager", script)
        with urllib.request.urlopen(f"{self.base}/assets/viewer.js", timeout=5) as response:
            self.assertEqual(response.status, 200)
            body = response.read()
            self.assertIn(b"MepViewer", body)
            self.assertIn(b"filesFromQuery", body)
            self.assertIn(b"Clipper", body)
            self.assertIn(b"Section height", body)
            self.assertIn(b"getCategories", body)
        index = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="view-window"', index)

    def test_viewer_window_page_is_served(self):
        url = f"{self.base}/viewer?id=sample:HeatingAndCooling.ifc&clash=sample:Architecture.ifc"
        with urllib.request.urlopen(url, timeout=5) as response:
            self.assertEqual(response.status, 200)
            page = response.read().decode("utf-8")
        self.assertIn('data-page="viewer"', page)
        self.assertIn('id="viewer-canvas"', page)
        self.assertIn("/assets/viewer.js", page)

    @unittest.skipUnless(SAMPLE.is_file(), "sample IFC is not in examples/")
    def test_ifc_bytes_are_served_for_the_viewer(self):
        url = f"{self.base}/api/ifc?id=sample:HeatingAndCooling.ifc"
        with urllib.request.urlopen(url, timeout=10) as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"ISO-10303-21", response.read(64))

    def test_unknown_ifc_is_rejected(self):
        url = f"{self.base}/api/ifc?id=sample:missing.ifc"
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(url, timeout=5)
        self.assertEqual(caught.exception.code, 400)
        caught.exception.close()


if __name__ == "__main__":
    unittest.main()
