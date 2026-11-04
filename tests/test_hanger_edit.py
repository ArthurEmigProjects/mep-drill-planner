"""Hangers can be moved, deleted, and put back."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from src.hanger_edit import HangerEditError, edit_hangers
from src.ui import OUT_DIR, WEB, AppHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "HeatingAndCooling.ifc"


def _plan() -> dict:
    return {
        "source": "HeatingAndCooling.ifc",
        "units": "m",
        "clash_models": ["HeatingAndCooling.ifc"],
        "runs": [
            {
                "id": "R-0001",
                "kind": "pipe",
                "size_label": "22 mm",
                "system_names": ["Hydronic Supply"],
                "length_m": 4.0,
                "max_spacing_m": 2.0,
                "direction": [1.0, 0.0, 0.0],
                "origin": [0.0, 0.0, 3.0],
                "point_ids": ["M-0001", "M-0002"],
                "status": "placed_initial",
            }
        ],
        "points": [
            {
                "id": "M-0001",
                "run_id": "R-0001",
                "x": 1.0,
                "y": 0.2,
                "z": 3.0,
                "station_m": 1.0,
                "max_spacing_m": 2.0,
                "reason": "regular_70",
                "clear": True,
                "kind": "pipe",
                "mount": "wall",
            },
            {
                "id": "M-0002",
                "run_id": "R-0001",
                "x": 3.0,
                "y": 0.2,
                "z": 3.0,
                "station_m": 3.0,
                "max_spacing_m": 2.0,
                "reason": "regular_70",
                "clear": True,
                "kind": "pipe",
                "mount": "wall",
            },
        ],
    }


class HangerEditTests(unittest.TestCase):
    def test_station_move_keeps_the_wall_offset_and_updates_the_gap(self):
        plan = _plan()
        revised = edit_hangers(plan, {"op": "move", "hanger_id": "M-0001", "station_m": 1.5})
        moved = revised["points"][0]
        self.assertEqual(plan["points"][0]["x"], 1.0)
        self.assertEqual(moved["x"], 1.5)
        self.assertEqual(moved["y"], 0.2)
        self.assertEqual(moved["station_m"], 1.5)
        self.assertEqual(moved["reason"], "user_moved")
        self.assertEqual(moved["status"], "moved")
        self.assertEqual(moved["trade"], "heating_cooling")
        self.assertEqual(moved["spacing_to_next_m"], 1.5)
        self.assertAlmostEqual(moved["spacing_ratio"], 0.75)
        self.assertEqual(revised["runs"][0]["status"], "placed_adjusted")
        self.assertEqual(revised["runs"][0]["cantilever_start_m"], 1.5)
        self.assertEqual(revised["runs"][0]["point_ids"], ["M-0001", "M-0002"])

    def test_coordinates_move_without_changing_the_station(self):
        revised = edit_hangers(
            _plan(),
            {"op": "move", "hanger_id": "M-0002", "x": 3.2, "y": 0.4, "z": 3.1},
        )
        moved = next(point for point in revised["points"] if point["id"] == "M-0002")
        self.assertEqual(moved["station_m"], 3.0)
        self.assertEqual([moved["x"], moved["y"], moved["z"]], [3.2, 0.4, 3.1])
        self.assertEqual(moved["reason"], "user_moved")

    def test_a_clashing_hanger_stays_clashing_when_it_is_moved(self):
        plan = _plan()
        plan["points"][0]["clear"] = False
        plan["points"][0]["reason"] = "unresolved_clash"
        revised = edit_hangers(plan, {"op": "move", "hanger_id": "M-0001", "station_m": 1.2})
        moved = revised["points"][0]
        self.assertFalse(moved["clear"])
        self.assertEqual(moved["reason"], "user_moved")
        self.assertEqual(moved["status"], "clash")

    def test_delete_closes_the_gap_and_replace_puts_the_hanger_back(self):
        plan = _plan()
        deleted = edit_hangers(plan, {"op": "delete", "hanger_id": "M-0001"})
        self.assertEqual([point["id"] for point in deleted["points"]], ["M-0002"])
        self.assertIsNone(deleted["points"][0]["spacing_to_previous_m"])
        self.assertEqual(deleted["runs"][0]["point_ids"], ["M-0002"])
        restored = edit_hangers(deleted, {"op": "replace", "points": plan["points"]})
        self.assertEqual([point["id"] for point in restored["points"]], ["M-0001", "M-0002"])
        self.assertEqual(restored["points"][0]["reason"], "regular_70")
        self.assertEqual(restored["points"][0]["x"], 1.0)

    def test_station_outside_the_run_is_rejected(self):
        with self.assertRaises(HangerEditError):
            edit_hangers(_plan(), {"op": "move", "hanger_id": "M-0001", "station_m": 4.2})

    def test_page_lists_hangers_and_offers_undo(self):
        page = (WEB / "index.html").read_text(encoding="utf-8")
        script = (WEB / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="hanger-objects"', page)
        self.assertIn('id="undo"', page)
        self.assertIn('id="redo"', page)
        self.assertIn('id="hanger-delete"', page)
        self.assertIn("/api/mounting-edits", script)
        self.assertIn("user_moved", script)


class HangerEditHttpTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._previous = OUT_DIR
        self._module = __import__("src.ui", fromlist=["OUT_DIR"])
        self._module.OUT_DIR = Path(self._tmp.name)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base = f"http://{host}:{port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self._module.OUT_DIR = self._previous
        self._tmp.cleanup()

    def _saved(self) -> Path:
        path = Path(self._tmp.name) / "HeatingAndCooling-mounting-points.json"
        path.write_text(json.dumps(_plan()), encoding="utf-8")
        return path

    def _post(self, payload: dict) -> tuple[int, dict]:
        request = urllib.request.Request(
            f"{self.base}/api/mounting-edits",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.loads(exc.read().decode("utf-8"))
            finally:
                exc.close()

    @unittest.skipUnless(SAMPLE.is_file(), "sample IFC is not in examples/")
    def test_edit_rewrites_the_saved_list_and_the_hanger_model(self):
        saved = self._saved()
        status, body = self._post(
            {
                "id": "sample:HeatingAndCooling.ifc",
                "op": "move",
                "hanger_id": "M-0001",
                "station_m": 1.5,
            }
        )
        self.assertEqual(status, 200, body)
        self.assertEqual(body["points"][0]["x"], 1.5)
        self.assertEqual(body["adjusted_count"], 1)
        self.assertTrue(str(body["mounting_out"]).endswith("HeatingAndCooling-mountings.ifc"))
        on_disk = json.loads(saved.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["points"][0]["reason"], "user_moved")
        ifc_path = Path(self._tmp.name) / "HeatingAndCooling-mountings.ifc"
        self.assertTrue(ifc_path.is_file())
        self.assertIn(b"ISO-10303-21", ifc_path.read_bytes()[:64])

    @unittest.skipUnless(SAMPLE.is_file(), "sample IFC is not in examples/")
    def test_a_bad_station_does_not_change_the_file(self):
        saved = self._saved()
        before = saved.read_text(encoding="utf-8")
        status, body = self._post(
            {
                "id": "sample:HeatingAndCooling.ifc",
                "op": "move",
                "hanger_id": "M-0001",
                "station_m": 9,
            }
        )
        self.assertEqual(status, 400)
        self.assertIn("Station", body["error"])
        self.assertEqual(saved.read_text(encoding="utf-8"), before)

    def test_edit_before_placement_is_refused(self):
        status, body = self._post(
            {"id": "sample:HeatingAndCooling.ifc", "op": "delete", "hanger_id": "M-0001"}
        )
        self.assertEqual(status, 400)
        self.assertIn("Place mounting points", body["error"])


if __name__ == "__main__":
    unittest.main()
