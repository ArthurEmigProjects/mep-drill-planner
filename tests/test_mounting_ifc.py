"""Hanger rods written as their own IFC, with status and trade."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.element

from src.mounting_ifc import (
    ROD_STUB_M,
    annotate_mountings,
    status_for_point,
    trade_for_file,
    trade_from_systems,
    write_mounting_ifc,
)
from src.mounting_points import plan_mounting_points

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "HeatingAndCooling.ifc"


def _point(point_id, x, y, z, reason, clear, status, trade, anchor=None, direction=None):
    return {
        "id": point_id,
        "run_id": "R-0001",
        "x": x,
        "y": y,
        "z": z,
        "reason": reason,
        "clear": clear,
        "status": status,
        "trade": trade,
        "mount_direction": direction if direction is not None else [0.0, 0.0, 1.0],
        "anchor": anchor,
    }


def _plan(points, source="mixed.ifc"):
    return {
        "source": source,
        "runs": [{"id": "R-0001", "kind": "pipe_segment", "system_names": ["Domestic Cold Water"]}],
        "points": points,
    }


class TradeAndStatusTests(unittest.TestCase):
    def test_reasons_map_onto_the_three_classes(self):
        self.assertEqual(status_for_point({"reason": "regular_70", "clear": True}), "clear")
        self.assertEqual(status_for_point({"reason": "shifted_under_95", "clear": True}), "moved")
        self.assertEqual(status_for_point({"reason": "shifted_into_90_95", "clear": True}), "moved")
        self.assertEqual(status_for_point({"reason": "respaced_90_95", "clear": True}), "moved")
        self.assertEqual(status_for_point({"reason": "unresolved_clash", "clear": False}), "clash")
        self.assertEqual(status_for_point({"reason": "regular_70", "clear": False}), "clash")

    def test_duplex_file_names_choose_the_trade(self):
        self.assertEqual(trade_for_file("zenodo-duplex-piping.ifc"), "sanitary")
        self.assertEqual(trade_for_file(r"examples\HeatingAndCooling.ifc"), "heating_cooling")
        self.assertEqual(trade_for_file("zenodo-duplex-ventilation.ifc"), "ventilation")
        self.assertIsNone(trade_for_file("buildingsmart-duplex-mep.ifc"))

    def test_system_names_choose_the_trade_for_a_mixed_file(self):
        self.assertEqual(trade_from_systems(["Domestic Hot Water 1"]), "sanitary")
        self.assertEqual(trade_from_systems(["Sewage1"]), "sanitary")
        self.assertEqual(trade_from_systems(["Hydronic Supply"]), "heating_cooling")
        self.assertEqual(trade_from_systems(["SupplyAir1.1"]), "ventilation")
        self.assertEqual(trade_from_systems([], "duct_segment"), "ventilation")
        self.assertEqual(trade_from_systems([], "pipe_segment"), "unknown")

    def test_a_known_file_overrides_the_system_name(self):
        plan = annotate_mountings(
            {
                "source": "HeatingAndCooling.ifc",
                "runs": [{"id": "R-0001", "kind": "pipe_segment", "system_names": ("Hydronic Supply",)}],
                "points": [{"id": "M-0001", "run_id": "R-0001", "reason": "regular_70", "clear": True, "kind": "pipe_segment"}],
            }
        )
        self.assertEqual(plan["points"][0]["trade"], "heating_cooling")
        self.assertEqual(plan["points"][0]["status"], "clear")
        self.assertEqual(plan["points"][0]["system_names"], ["Hydronic Supply"])

    def test_placement_records_status_and_trade(self):
        segment = {
            "global_id": "pipe-1",
            "kind": "pipe_segment",
            "system_names": ("Domestic Cold Water",),
            "start": (0.0, 0.0, 1.0),
            "end": (4.2, 0.0, 1.0),
            "outer_diameter_mm": 22.225,
            "width_mm": None,
            "height_mm": None,
            "adjacent_ids": [],
            "fitting_ids": [],
        }
        plan = plan_mounting_points([segment], [], source="custom.ifc")
        self.assertTrue(plan["points"])
        self.assertTrue(all(point["status"] == "clear" for point in plan["points"]))
        self.assertTrue(all(point["trade"] == "sanitary" for point in plan["points"]))


class MountingIfcTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "hangers.ifc"

    def tearDown(self):
        self._tmp.cleanup()

    def test_rods_carry_status_trade_colour_and_storey(self):
        points = [
            _point("M-0001", 1.0, 2.0, 1.2, "regular_70", True, "clear", "sanitary"),
            _point("M-0002", 3.0, 2.0, 4.5, "shifted_under_95", True, "moved", "heating_cooling"),
            _point(
                "M-0003",
                5.0,
                2.0,
                1.5,
                "unresolved_clash",
                False,
                "clash",
                "ventilation",
                anchor=[5.4, 2.0, 1.5],
                direction=[1.0, 0.0, 0.0],
            ),
        ]
        write_mounting_ifc(_plan(points), self.path, source=None)
        model = ifcopenshell.open(str(self.path))
        proxies = model.by_type("IfcBuildingElementProxy")
        self.assertEqual(len(proxies), 3)
        by_name = {element.Name: element for element in proxies}
        self.assertEqual(by_name["M-0001"].ObjectType, "clear")
        self.assertEqual(by_name["M-0001"].Tag, "sanitary")
        self.assertEqual(by_name["M-0001"].Description, "Mountings")
        self.assertEqual(ifcopenshell.util.element.get_psets(by_name["M-0001"])["Pset_DrillMount"]["Storey"], "Mountings")
        self.assertEqual(ifcopenshell.util.element.get_psets(by_name["M-0002"])["Pset_DrillMount"]["Status"], "moved")
        self.assertEqual(ifcopenshell.util.element.get_psets(by_name["M-0003"])["Pset_DrillMount"]["Trade"], "ventilation")

        stub = by_name["M-0001"].Representation.Representations[0].Items[0]
        self.assertAlmostEqual(stub.Depth, ROD_STUB_M)
        self.assertEqual(tuple(stub.Position.Location.Coordinates), (1.0, 2.0, 1.2))
        wall = by_name["M-0003"].Representation.Representations[0].Items[0]
        self.assertAlmostEqual(wall.Depth, 0.4)

        colours = {}
        for styled in model.by_type("IfcStyledItem"):
            rendering = styled.Styles[0].Styles[0]
            colours[styled.Item] = (
                rendering.SurfaceColour.Red,
                rendering.SurfaceColour.Green,
                rendering.SurfaceColour.Blue,
            )
        self.assertGreater(colours[stub][1], colours[stub][0])
        self.assertGreater(colours[wall][0], colours[wall][1])

        storey = ifcopenshell.util.element.get_container(by_name["M-0001"])
        self.assertEqual(storey.Name, "Mountings")
        self.assertEqual(storey.is_a(), "IfcBuildingStorey")

    @unittest.skipUnless(SAMPLE.is_file(), "sample IFC is not in examples/")
    def test_storey_names_follow_the_source_model(self):
        from src.ifc_drawings import read_storeys

        storeys = read_storeys([SAMPLE])
        self.assertGreaterEqual(len(storeys), 1)
        low = storeys[0]["elevation_m"]
        high = storeys[-1]["elevation_m"]
        points = [
            _point("M-LOW", 0.0, 0.0, low + 0.2, "regular_70", True, "clear", "heating_cooling"),
            _point("M-HIGH", 0.0, 0.0, high + 1.0, "regular_70", True, "clear", "heating_cooling"),
        ]
        write_mounting_ifc(_plan(points, SAMPLE.name), self.path, source=SAMPLE)
        model = ifcopenshell.open(str(self.path))
        names = {storey.Name for storey in model.by_type("IfcBuildingStorey")}
        self.assertEqual(names, {row["name"] for row in storeys})
        by_name = {element.Name: element for element in model.by_type("IfcBuildingElementProxy")}
        self.assertEqual(ifcopenshell.util.element.get_container(by_name["M-LOW"]).Name, storeys[0]["name"])
        self.assertEqual(ifcopenshell.util.element.get_container(by_name["M-HIGH"]).Name, storeys[-1]["name"])
        self.assertEqual(
            ifcopenshell.util.element.get_psets(by_name["M-LOW"])["Pset_DrillMount"]["Storey"],
            storeys[0]["name"],
        )


if __name__ == "__main__":
    unittest.main()
