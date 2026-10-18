"""Loader and size-mapping tests for the mounting-element database."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.mounting import (
    SCHEMA_PATH,
    DatabaseError,
    coverage_report,
    feasible_mountings,
    load_database,
)

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "data" / "inventory" / "zenodo_duplex_mountable.json"


def _pipe(diameter: float, kind: str = "pipe_segment") -> dict:
    return {
        "kind": kind,
        "shape": "round",
        "outer_diameter_mm": diameter,
        "outer_diameters_mm": [diameter],
    }


class LoadDatabaseTests(unittest.TestCase):
    def test_shipped_database_loads(self):
        database = load_database()
        ids = [product["id"] for product in database["products"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(database["products"]), 20)
        self.assertGreaterEqual(len(database["guidance"]), 3)

    def test_every_product_stays_inside_the_schema_keys(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        database = load_database()
        product_keys = set(schema["$defs"]["product"]["properties"])
        guidance_keys = set(schema["$defs"]["guidance"]["properties"])
        for product in database["products"]:
            self.assertEqual(set(product) - product_keys, set())
            self.assertTrue(product["sources"])
            for source in product["sources"]:
                self.assertTrue(source["url"].startswith("http"))
            # Spacing is a separate guidance list. Nothing in the product
            # pages we cited publishes a spacing, so the field stays empty.
            self.assertIsNone(product["max_support_spacing"])
        for item in database["guidance"]:
            self.assertEqual(set(item) - guidance_keys, set())

    def test_missing_file_raises(self):
        with self.assertRaises(DatabaseError):
            load_database(Path("/tmp/does-not-exist-mounting.json"))

    def test_duplicate_id_raises(self):
        database = load_database()
        database["products"].append(dict(database["products"][0]))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "products.json"
            path.write_text(json.dumps(database), encoding="utf-8")
            with self.assertRaises(DatabaseError):
                load_database(path)

    def test_reversed_diameter_window_raises(self):
        database = load_database()
        database["products"][0]["outer_diameter_mm"] = {"min": 30, "max": 10}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "products.json"
            path.write_text(json.dumps(database), encoding="utf-8")
            with self.assertRaises(DatabaseError):
                load_database(path)


class MappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database = load_database()

    def _ids(self, element, **kwargs):
        result = feasible_mountings(element, self.database, **kwargs)
        return result, [item["id"] for item in result["matches"]]

    def test_half_inch_copper_od_uses_fischer_15_19_not_muepro_13_15(self):
        result, ids = self._ids(_pipe(15.875))
        self.assertEqual(result["status"], "matched")
        self.assertIn("fischer-frs-plus-079441", ids)
        self.assertIn("hilti-mp-mi-20843", ids)
        self.assertNotIn("muepro-optimal-119866", ids)
        self.assertNotIn("fischer-frs-plus-079440", ids)

    def test_metric_15_mm_hits_the_13_15_clamp_and_the_spacing_row(self):
        result, ids = self._ids(_pipe(15.0))
        self.assertEqual(result["status"], "matched")
        self.assertIn("muepro-optimal-119866", ids)
        self.assertIn("fischer-frs-plus-079440", ids)
        spacing = [
            item
            for item in result["guidance"]
            if item["guidance_id"] == "copper-tube-spacing-din1988-2-as-cited"
        ]
        self.assertEqual(spacing[0]["horizontal_m"], 1.25)
        self.assertTrue(any("unnamed" in note for note in result["assumptions"]))

    def test_small_heating_od_uses_the_8_11_clamp_only(self):
        result, ids = self._ids(_pipe(9.52))
        self.assertEqual(result["status"], "matched")
        self.assertEqual(ids, ["fischer-frs-l-539443"])
        self.assertEqual(
            [item for item in result["guidance"] if "spacing" in item["guidance_id"] and "copper" in item["guidance_id"]],
            [],
        )

    def test_three_quarter_inch_od_and_nearest_spacing_row(self):
        result, ids = self._ids(_pipe(22.225))
        self.assertIn("muepro-optimal-119862", ids)
        self.assertIn("fischer-frs-plus-079442", ids)
        self.assertIn("hilti-mp-mi-20845", ids)
        copper = next(
            item
            for item in result["guidance"]
            if item["guidance_id"] == "copper-tube-spacing-din1988-2-as-cited"
        )
        self.assertEqual(copper["table_outer_diameter_mm"], 22)
        self.assertEqual(copper["horizontal_m"], 2.0)

    def test_nineteen_mm_is_inside_19_24_and_outside_15_19(self):
        _result, ids = self._ids(_pipe(19.05))
        self.assertIn("muepro-optimal-119862", ids)
        self.assertNotIn("fischer-frs-plus-079441", ids)
        self.assertNotIn("hilti-mp-mi-20845", ids)

    def test_four_inch_copper_od_is_between_the_dn100_steps(self):
        result, ids = self._ids(_pipe(104.775))
        self.assertEqual(result["status"], "matched")
        self.assertIn("walraven-bismat-ksb2-3396105", ids)
        self.assertIn("walraven-bismat-2000-3403105", ids)
        self.assertIn("fischer-frs-a2-064697", ids)
        self.assertNotIn("muepro-optimal-119858", ids)

    def test_one_and_a_half_inch_od(self):
        _result, ids = self._ids(_pipe(41.275))
        self.assertIn("muepro-optimal-119858", ids)
        self.assertIn("fischer-frs-plus-079445", ids)
        self.assertIn("hilti-mp-mi-20851", ids)

    def test_reducer_needs_a_clamp_for_every_end(self):
        covered, ids = self._ids(
            {
                "kind": "pipe_fitting",
                "outer_diameters_mm": [15.875, 22.225],
            }
        )
        self.assertEqual(covered["status"], "matched")
        self.assertIn("fischer-frs-plus-079441", ids)
        self.assertIn("fischer-frs-plus-079442", ids)
        uncovered, _ids = self._ids(
            {"kind": "pipe_fitting", "outer_diameters_mm": [15.875, 7.0]}
        )
        self.assertEqual(uncovered["status"], "unmatched")
        self.assertTrue(uncovered["gap"])
        self.assertEqual(uncovered["matches"], [])

    def test_rectangular_duct_returns_luw_and_lindab_spacing(self):
        result, ids = self._ids(
            {
                "kind": "duct_segment",
                "shape": "rectangular",
                "width_mm": 200.0,
                "height_mm": 150.0,
            }
        )
        self.assertEqual(result["status"], "matched_with_assumption")
        self.assertIn("sikla-luw-sl-189893", ids)
        self.assertIn("sikla-luw-sz-189902", ids)
        self.assertIn("hilti-mq-41-3-369596", [item["id"] for item in result["companions"]])
        lindab = [
            item
            for item in result["guidance"]
            if item["guidance_id"] == "lindab-duct-suspension-spacing" and item.get("horizontal_m")
        ]
        self.assertEqual(lindab[0]["horizontal_m"], 2.4)

    def test_square_150_has_no_lindab_size_row(self):
        result, _ids = self._ids(
            {
                "kind": "duct_segment",
                "shape": "rectangular",
                "width_mm": 150.0,
                "height_mm": 150.0,
            }
        )
        self.assertEqual(result["status"], "matched_with_assumption")
        self.assertFalse(
            any(item.get("size") == "150×150 mm" for item in result["guidance"])
        )
        self.assertTrue(any("150" in note and "Lindab" in note for note in result["assumptions"]))

    def test_round_duct_150_matches_plu_and_three_metre_spacing(self):
        result, ids = self._ids(
            {
                "kind": "duct_segment",
                "shape": "round",
                "outer_diameter_mm": 150.0,
                "outer_diameters_mm": [150.0],
            }
        )
        self.assertEqual(result["status"], "matched")
        self.assertEqual(ids, ["sikla-plu-2g-199893"])
        self.assertTrue(
            any(item.get("horizontal_m") == 3.0 for item in result["guidance"])
        )

    def test_flex_mesh_is_a_gap(self):
        result, ids = self._ids(
            {"kind": "duct_flex", "shape": "round", "mesh_minor_axis_mm": 151.6}
        )
        self.assertEqual(result["status"], "unmatched")
        self.assertEqual(ids, [])
        self.assertIn("151.6", result["gap"])
        self.assertIn("not applied", result["gap"])

    def test_radiator_is_kind_only(self):
        result, ids = self._ids(
            {"kind": "radiator", "bbox_mm": [100.0, 350.0, 1000.0]}
        )
        self.assertEqual(result["status"], "matched_with_assumption")
        self.assertEqual(ids, ["kermi-console-zb02870003"])
        self.assertIn("Kermi", " ".join(result["assumptions"]))
        self.assertEqual(result["matches"][0]["anchor"]["substrate"], "wall")

    def test_air_terminal_sanitary_and_appliances_are_gaps(self):
        for kind in ("air_terminal", "sanitary_fixture", "water_heater", "stove", "air_handling_unit"):
            result, ids = self._ids({"kind": kind, "bbox_mm": [100, 200, 300]})
            self.assertEqual(result["status"], "unmatched", kind)
            self.assertEqual(ids, [])
            self.assertTrue(result["gap"], kind)

    def test_concrete_substrate_adds_the_matching_anchor_only(self):
        concrete, _ids = self._ids(_pipe(22.225), substrate="concrete")
        companion_ids = [item["id"] for item in concrete["companions"]]
        # Müpro/Fischer clamps on this OD take M8/M10; Hilti MP-MI takes M10/M12.
        self.assertIn("hilti-rod-am8-339793", companion_ids)
        self.assertIn("hilti-rod-am10-339795", companion_ids)
        self.assertIn("fischer-ea-ii-m8-532231", companion_ids)
        self.assertIn("fischer-ea-ii-m10-532232", companion_ids)
        timber, _ids = self._ids(_pipe(22.225), substrate="timber")
        timber_ids = [item["id"] for item in timber["companions"]]
        self.assertNotIn("fischer-ea-ii-m10-532232", timber_ids)
        self.assertTrue(any("timber" in note for note in timber["assumptions"]))

    def test_m8_clamp_brings_the_m8_rod_and_anchor(self):
        result, _ids = self._ids(_pipe(12.7), substrate="concrete")
        companion_ids = [item["id"] for item in result["companions"]]
        self.assertIn("hilti-rod-am8-339793", companion_ids)
        self.assertIn("fischer-ea-ii-m8-532231", companion_ids)

    def test_shipped_inventory_covers_every_pipe_and_rigid_duct_size(self):
        inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
        report = coverage_report(inventory, self.database)
        unmatched = {
            (gap["model"], gap["kind"], gap["size_label"]) for gap in report["gaps"]
        }
        for model in inventory["models"].values():
            for group in model["groups"]:
                key = (model["file"], group["kind"], group["size_label"])
                if group["kind"] in {"pipe_segment", "duct_segment"}:
                    self.assertNotIn(
                        ( _model_key(inventory, model["file"]), group["kind"], group["size_label"]),
                        unmatched,
                        key,
                    )
        flex = [gap for gap in report["gaps"] if gap["kind"] == "duct_flex"]
        self.assertGreaterEqual(sum(gap["count"] for gap in flex), 36)


def _model_key(inventory: dict, filename: str) -> str:
    for key, model in inventory["models"].items():
        if model["file"] == filename:
            return key
    raise KeyError(filename)


class InventoryGeometryTests(unittest.TestCase):
    def test_port_axis_picks_height_and_width(self):
        import numpy as np

        from src.inventory_elements import rectangular_cross_section

        axes = {
            "px": (np.array([1.0, 0.0, 0.0]), 2.4),
            "py": (np.array([0.0, 1.0, 0.0]), 0.2),
            "ex": (np.array([0.0, 0.0, 1.0]), 0.15),
        }
        section = rectangular_cross_section(axes, np.array([1.0, 0.0, 0.0]))
        self.assertEqual(section["width_mm"], 200.0)
        self.assertEqual(section["height_mm"], 150.0)
        self.assertEqual(section["length_m"], 2.4)

    def test_polish_pipe_names_are_not_ducts(self):
        from src.inventory_elements import classify

        self.assertEqual(
            classify("M_Kolano - ogólne:Standardowy:1", "Pipe Fittings", "IfcFlowFitting"),
            "pipe_fitting",
        )
        self.assertEqual(
            classify("M_Kolano prostokątne - promień:1 W:1", "Duct Fittings", "IfcFlowFitting"),
            "duct_fitting",
        )
        self.assertEqual(
            classify("Flex Duct Round:x:1", "Flex Ducts", "IfcFlowSegment"),
            "duct_flex",
        )
        self.assertEqual(
            classify("Radiator:Radiator:1", "Mechanical Equipment", "IfcFlowTerminal"),
            "radiator",
        )


if __name__ == "__main__":
    unittest.main()
