"""Floor plans, sections and 3D sheets for the hanger clash check."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.ifc_drawings import (
    axon_primitives,
    build_scene,
    clip_to_range,
    drawable_from_obstacle,
    host_wall_drawables,
    pages_for_scene,
    plan_primitives,
    plane_for_hanger,
    render_scene,
    scene_bounds,
    section_primitives,
)

ROOT = Path(__file__).resolve().parents[1]
PIPING = ROOT / "examples" / "zenodo-duplex-piping.ifc"


def scene_with_clash() -> dict:
    return {
        "models": ["piping.ifc", "Architecture.ifc"],
        "storeys": [
            {"name": "Level 1", "elevation_m": 0.0},
            {"name": "Level 2", "elevation_m": 3.0},
        ],
        "drawables": [
            {
                "kind": "segment",
                "category": "pipe",
                "element_id": "pipe-1",
                "source": None,
                "start": (0.0, 0.0, 1.0),
                "end": (4.0, 0.0, 1.0),
                "radius_m": 0.02,
            },
            {
                "kind": "box",
                "category": "structure",
                "element_id": "beam-1",
                "source": "Architecture.ifc",
                "min": (2.0, -0.1, 1.2),
                "max": (2.2, 0.1, 2.5),
            },
            {
                "kind": "segment",
                "category": "duct",
                "element_id": "duct-2",
                "source": None,
                "start": (0.0, 1.0, 4.0),
                "end": (3.0, 1.0, 4.0),
                "radius_m": 0.15,
            },
        ],
        "hangers": [
            {
                "id": "M-0001",
                "x": 2.1,
                "y": 0.0,
                "z": 1.02,
                "clear": False,
                "reason": "unresolved_clash",
                "clashing_element_ids": ["Architecture.ifc · beam-1"],
                "run_id": "R-0001",
            },
            {
                "id": "M-0002",
                "x": 0.5,
                "y": 0.0,
                "z": 1.02,
                "clear": True,
                "reason": "regular_70",
                "clashing_element_ids": [],
                "run_id": "R-0001",
            },
        ],
        "runs": {"R-0001": {"id": "R-0001", "direction": (1.0, 0.0, 0.0)}},
        "clash_count": 1,
        "hanger_count": 2,
        "rod_length_m": 2.0,
    }


class SheetListTests(unittest.TestCase):
    def test_sheets_cover_plans_sections_and_3d(self):
        titles = [page["title"] for page in pages_for_scene(scene_with_clash())]
        self.assertEqual(titles[0], "Clash drawings")
        self.assertIn("Level 1 · floor plan", titles)
        self.assertIn("Level 2 · floor plan", titles)
        self.assertTrue(any(title.startswith("Long section") for title in titles))
        self.assertTrue(any(title.startswith("Cross section") for title in titles))
        self.assertIn("M-0001 · section", titles)
        self.assertIn("3D views", titles)
        self.assertIn("Clashes · 3D", titles)

    def test_a_clear_model_has_no_clash_sheet(self):
        scene = scene_with_clash()
        scene["hangers"] = [hanger for hanger in scene["hangers"] if hanger["clear"]]
        scene["clash_count"] = 0
        titles = [page["title"] for page in pages_for_scene(scene)]
        self.assertFalse(any(title.endswith("· section") for title in titles))
        self.assertNotIn("Clashes · 3D", titles)
        self.assertIn("3D views", titles)


class GeometryTests(unittest.TestCase):
    def test_clip_keeps_the_slice_inside_the_range(self):
        start = (0.0, 0.0, 0.0)
        end = (4.0, 0.0, 0.0)
        clipped = clip_to_range(start, end, -1.0, 1.0, 0.0, 0.5)
        self.assertIsNotNone(clipped)
        self.assertAlmostEqual(clipped[0][0], 2.0)
        self.assertAlmostEqual(clipped[1][0], 3.0)

    def test_cylinder_keeps_its_category(self):
        item = drawable_from_obstacle(
            {
                "shape": "cylinder",
                "category": "duct",
                "element_id": "d1",
                "start": (0, 0, 0),
                "end": (1, 0, 0),
                "radius_m": 0.08,
            }
        )
        self.assertEqual(item["kind"], "segment")
        self.assertEqual(item["category"], "duct")

    def test_plan_draws_another_ifc_dashed(self):
        scene = scene_with_clash()
        band = {"name": "Level 1", "z0": 0.0, "z1": 3.0, "first": True, "last": False}
        primitives = plan_primitives(scene, band)
        beam = next(item for item in primitives if item["op"] == "rect")
        self.assertTrue(beam["dashed"])
        self.assertEqual(beam["color"], "structure")
        self.assertFalse(any(item.get("color") == "duct" for item in primitives))

    def test_clash_section_shows_the_pipe_the_beam_and_the_rod(self):
        scene = scene_with_clash()
        scene["bounds"] = scene_bounds(scene)
        hanger = scene["hangers"][0]
        plane = plane_for_hanger(scene, hanger)
        self.assertAlmostEqual(
            (hanger["x"] - plane["origin"][0]) * plane["normal"][0]
            + (hanger["y"] - plane["origin"][1]) * plane["normal"][1],
            0.0,
        )
        window = (-1.6, 1.6, hanger["z"] - 0.7, hanger["z"] + 1.6)
        primitives = section_primitives(
            scene,
            plane,
            depth=plane["depth"],
            thickness=0.16,
            symmetric=True,
            window=window,
        )
        markers = [item for item in primitives if item["op"] == "marker"]
        self.assertEqual(len(markers), 1)
        self.assertTrue(markers[0]["label"].startswith("M-0001"))
        self.assertTrue(any(item["op"] == "circle" and item["color"] == "pipe" for item in primitives))
        self.assertTrue(any(item["op"] == "line" and item["color"] == "clash" for item in primitives))
        self.assertTrue(any(item.get("color") == "structure" for item in primitives))

    def test_a_wall_bracket_is_drawn_sideways_on_the_plan(self):
        scene = scene_with_clash()
        scene["hangers"].append(
            {
                "id": "M-0003",
                "x": 0.02,
                "y": 1.0,
                "z": 4.0,
                "clear": True,
                "reason": "regular_70",
                "clashing_element_ids": [],
                "run_id": "R-0002",
                "mount": "wall",
                "mount_direction": [0.0, 1.0, 0.0],
                "anchor": [0.02, 1.25, 4.0],
            }
        )
        band = {"name": "Level 2", "z0": 3.0, "z1": 5.0, "first": False, "last": True}
        primitives = plan_primitives(scene, band)
        lines = [
            item
            for item in primitives
            if item["op"] == "line" and item["color"] == "clear"
        ]
        self.assertEqual(len(lines), 1)
        self.assertAlmostEqual(lines[0]["v1"] - lines[0]["v0"], 0.25, places=3)
        self.assertAlmostEqual(lines[0]["u0"], 0.02, places=3)

    def test_only_the_wall_beside_the_riser_is_drawn(self):
        wall = {
            "element_id": "shaft",
            "category": "wall",
            "shape": "box",
            "min": (0.2, -20.0, 0.0),
            "max": (0.4, 20.0, 12.0),
        }
        other = {
            "element_id": "elsewhere",
            "category": "wall",
            "shape": "box",
            "min": (30.0, 0.0, 0.0),
            "max": (30.2, 8.0, 3.0),
        }
        runs = [
            {
                "wall_element_id": "shaft",
                "wall_source": None,
                "origin": [0.0, 1.0, 0.0],
                "end": [0.0, 1.0, 3.0],
            }
        ]
        drawn = host_wall_drawables([wall, other], runs)
        self.assertEqual(len(drawn), 1)
        self.assertEqual(drawn[0]["element_id"], "shaft")
        self.assertGreater(drawn[0]["min"][1], -2.0)
        self.assertLess(drawn[0]["max"][1], 4.0)
        self.assertLess(drawn[0]["max"][2], 5.0)

    def test_axonometric_draws_farther_edges_first(self):
        scene = scene_with_clash()
        primitives = axon_primitives(scene, flip=False)
        depths = [item["depth"] for item in primitives]
        self.assertEqual(depths, sorted(depths))
        self.assertTrue(any(item["op"] == "marker" and item["marker"] == "clash" for item in primitives))


class PdfTests(unittest.TestCase):
    def test_synthetic_scene_writes_a_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "views.pdf"
            titles = render_scene(scene_with_clash(), path)
            data = path.read_bytes()
            size = path.stat().st_size
        self.assertTrue(data.startswith(b"%PDF"))
        self.assertGreater(size, 2000)
        self.assertIn("Level 1 · floor plan", titles)
        self.assertIn("M-0001 · section", titles)
        self.assertIn("3D views", titles)
        self.assertIn(b"Clash drawings", data)
        self.assertIn(b"floor plan", data)
        self.assertIn(b"Long section", data)
        self.assertIn(b"3D views", data)
        self.assertIn(b"M-0001", data)


class IfcSceneTests(unittest.TestCase):
    @unittest.skipUnless(PIPING.is_file(), "sample IFC is not in examples/")
    def test_piping_model_gets_a_clash_section(self):
        scene = build_scene(PIPING)
        self.assertEqual(scene["models"], ["zenodo-duplex-piping.ifc"])
        self.assertGreater(scene["clash_count"], 0)
        self.assertTrue(any(item["category"] == "pipe" for item in scene["drawables"]))
        titles = [page["title"] for page in pages_for_scene(scene)]
        self.assertTrue(any("floor plan" in title for title in titles))
        self.assertTrue(any(title.startswith("Long section") for title in titles))
        self.assertTrue(any(title.startswith("Cross section") for title in titles))
        self.assertTrue(any(title.endswith("· section") for title in titles))
        self.assertIn("3D views", titles)
        self.assertIn("Clashes · 3D", titles)


if __name__ == "__main__":
    unittest.main()
