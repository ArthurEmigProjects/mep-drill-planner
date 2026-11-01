"""The local page can hand an IFC to the browser viewer."""

from __future__ import annotations

import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from src.mounting_ifc import write_mounting_ifc
from src.ui import OUT_DIR, WEB, AppHandler, ThreadingHTTPServer

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
            self.assertIn(b"view-mounting", body)
            self.assertIn(b"Pset_DrillMount", body)
            self.assertIn(b"mounting", body)
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

    def test_mounting_ifc_is_served_and_kept_out_of_the_sample_list(self):
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUT_DIR / "viewer-mountings.ifc"
        write_mounting_ifc(
            {
                "source": "viewer.ifc",
                "runs": [],
                "points": [
                    {
                        "id": "M-0001",
                        "x": 0.0,
                        "y": 0.0,
                        "z": 1.0,
                        "reason": "regular_70",
                        "clear": True,
                        "status": "clear",
                        "trade": "sanitary",
                        "mount_direction": [0.0, 0.0, 1.0],
                        "anchor": None,
                    }
                ],
            },
            path,
        )
        try:
            url = f"{self.base}/api/ifc?id=out:viewer-mountings.ifc"
            with urllib.request.urlopen(url, timeout=10) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(b"ISO-10303-21", response.read(64))
            with urllib.request.urlopen(f"{self.base}/api/files", timeout=5) as response:
                files = __import__("json").loads(response.read())["files"]
            self.assertFalse(any(item["name"] == "viewer-mountings.ifc" for item in files))
            window = f"{self.base}/viewer?id=sample:HeatingAndCooling.ifc&mounting=out:viewer-mountings.ifc"
            with urllib.request.urlopen(window, timeout=5) as response:
                self.assertIn("viewer.js", response.read().decode("utf-8"))
        finally:
            path.unlink(missing_ok=True)

    def test_unknown_ifc_is_rejected(self):
        url = f"{self.base}/api/ifc?id=sample:missing.ifc"
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(url, timeout=5)
        self.assertEqual(caught.exception.code, 400)
        caught.exception.close()


if __name__ == "__main__":
    unittest.main()
