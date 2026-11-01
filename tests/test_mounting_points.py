"""Run detection, regular hanger spacing, and the vertical clash correction."""

from __future__ import annotations

import unittest

from src.mounting_points import (
    ADJUSTED_SPACING_MAX_RATIO,
    ADJUSTED_SPACING_MIN_RATIO,
    INITIAL_SPACING_RATIO,
    detect_runs,
    even_stations,
    max_support_spacing_m,
    plan_mounting_points,
    plan_stations,
    rod_hits_obstacle,
)


def _pipe(global_id, start, end, diameter=22.225, adjacent=(), fittings=(), systems=()):
    return {
        "global_id": global_id,
        "kind": "pipe_segment",
        "system_names": tuple(systems),
        "start": start,
        "end": end,
        "outer_diameter_mm": diameter,
        "width_mm": None,
        "height_mm": None,
        "adjacent_ids": list(adjacent),
        "fitting_ids": list(fittings),
    }


def _gaps(stations):
    return [stations[i + 1] - stations[i] for i in range(len(stations) - 1)]


class EvenStationTests(unittest.TestCase):
    def test_exact_multiple_keeps_one_gap_per_cap(self):
        stations = even_stations(1.4, 1.4)
        self.assertEqual(len(stations), 2)
        self.assertAlmostEqual(stations[0], 0.0)
        self.assertAlmostEqual(stations[-1], 1.4)

    def test_longer_run_splits_so_the_gap_stays_under_the_cap(self):
        stations = even_stations(10.0, 1.4)
        gaps = _gaps(stations)
        self.assertTrue(all(gap <= 1.4 + 1e-9 for gap in gaps))
        self.assertAlmostEqual(stations[0], 0.0)
        self.assertAlmostEqual(stations[-1], 10.0)
        self.assertEqual(len(set(round(gap, 6) for gap in gaps)), 1)

    def test_short_run_is_still_held_at_both_ends(self):
        stations = even_stations(0.5, 1.4)
        self.assertEqual(len(stations), 2)
        self.assertAlmostEqual(_gaps(stations)[0], 0.5)


class SpacingLookupTests(unittest.TestCase):
    def test_cited_rows(self):
        spacing, guidance = max_support_spacing_m(
            {"kind": "pipe_segment", "outer_diameter_mm": 15.0, "outer_diameters_mm": [15.0]}
        )
        self.assertEqual(spacing, 1.25)
        self.assertEqual(guidance, "copper-tube-spacing-din1988-2-as-cited")

        spacing, _guidance = max_support_spacing_m(
            {"kind": "pipe_segment", "outer_diameter_mm": 22.225, "outer_diameters_mm": [22.225]}
        )
        self.assertEqual(spacing, 2.0)

    def test_sizes_without_a_row_have_no_limit(self):
        spacing, guidance = max_support_spacing_m(
            {"kind": "pipe_segment", "outer_diameter_mm": 9.52, "outer_diameters_mm": [9.52]}
        )
        self.assertIsNone(spacing)
        self.assertIsNone(guidance)
        spacing, _guidance = max_support_spacing_m(
            {
                "kind": "duct_segment",
                "shape": "rectangular",
                "width_mm": 150.0,
                "height_mm": 150.0,
            }
        )
        self.assertIsNone(spacing)

    def test_duct_rows(self):
        spacing, guidance = max_support_spacing_m(
            {
                "kind": "duct_segment",
                "shape": "rectangular",
                "width_mm": 200.0,
                "height_mm": 150.0,
            }
        )
        self.assertEqual(spacing, 2.4)
        self.assertEqual(guidance, "lindab-duct-suspension-spacing")
        spacing, _guidance = max_support_spacing_m(
            {
                "kind": "duct_segment",
                "shape": "round",
                "outer_diameter_mm": 150.0,
                "outer_diameters_mm": [150.0],
            }
        )
        self.assertEqual(spacing, 3.0)


class PlanStationTests(unittest.TestCase):
    def test_clear_run_stays_on_the_seventy_percent_pitch(self):
        # 70% of 2.0 m is 1.4 m, and 4.2 divides into three equal gaps.
        planned = plan_stations(4.2, 2.0, [])
        stations = [item["station_m"] for item in planned]
        self.assertEqual([item["reason"] for item in planned], ["regular_70"] * 4)
        self.assertEqual(len(stations), 4)
        for gap in _gaps(stations):
            self.assertLessEqual(gap, INITIAL_SPACING_RATIO * 2.0 + 1e-9)
            self.assertAlmostEqual(gap, 1.4)
        self.assertAlmostEqual(stations[0], 0.0)
        self.assertAlmostEqual(stations[-1], 4.2)

    def test_a_clash_respaces_the_run_into_the_ninety_percent_band(self):
        planned = plan_stations(4.2, 2.0, [(1.3, 1.5)])
        stations = [item["station_m"] for item in planned]
        self.assertTrue(all(item["reason"] == "respaced_90_95" for item in planned))
        self.assertGreaterEqual(len(stations), 2)
        for gap in _gaps(stations):
            ratio = gap / 2.0
            self.assertGreaterEqual(ratio, ADJUSTED_SPACING_MIN_RATIO - 1e-6)
            self.assertLessEqual(ratio, ADJUSTED_SPACING_MAX_RATIO + 1e-6)
        for station in stations:
            self.assertFalse(1.3 <= station <= 1.5)
        self.assertLessEqual(stations[0], ADJUSTED_SPACING_MAX_RATIO * 2.0)
        self.assertLessEqual(4.2 - stations[-1], ADJUSTED_SPACING_MAX_RATIO * 2.0)

    def test_shift_lands_in_the_band_when_no_even_pitch_is_clear(self):
        # Clear only at the original supports and in the 1.8–1.9 m band, so a
        # regular 90–95% pitch cannot cover the run and one hanger must move.
        blocked = [(0.05, 1.8), (1.9, 2.75), (2.85, 4.15)]
        planned = plan_stations(4.2, 2.0, blocked)
        self.assertEqual(planned[1]["reason"], "shifted_into_90_95")
        self.assertAlmostEqual(planned[0]["station_m"], 0.0, places=3)
        self.assertAlmostEqual(planned[1]["station_m"], 1.801, places=3)
        self.assertAlmostEqual(planned[2]["station_m"], 2.8, places=3)
        self.assertAlmostEqual(planned[3]["station_m"], 4.2, places=3)
        opened = planned[1]["station_m"] - planned[0]["station_m"]
        self.assertGreaterEqual(opened / 2.0, ADJUSTED_SPACING_MIN_RATIO - 1e-6)
        self.assertLessEqual(opened / 2.0, ADJUSTED_SPACING_MAX_RATIO + 1e-6)
        for gap in _gaps([item["station_m"] for item in planned]):
            self.assertLessEqual(gap, ADJUSTED_SPACING_MAX_RATIO * 2.0 + 1e-6)

    def test_small_slide_when_the_band_itself_is_blocked(self):
        blocked = [(0.2, 1.5), (1.7, 2.6), (3.0, 4.0)]
        planned = plan_stations(4.2, 2.0, blocked)
        self.assertEqual(planned[1]["reason"], "shifted_under_95")
        self.assertAlmostEqual(planned[1]["station_m"], 1.501, places=3)
        self.assertAlmostEqual(planned[0]["station_m"], 0.0, places=3)
        self.assertAlmostEqual(planned[2]["station_m"], 2.8, places=3)
        for gap in _gaps([item["station_m"] for item in planned]):
            self.assertLessEqual(gap, ADJUSTED_SPACING_MAX_RATIO * 2.0 + 1e-6)

    def test_a_fully_blocked_run_keeps_the_stations_and_marks_them(self):
        planned = plan_stations(4.2, 2.0, [(0.0, 4.2)])
        self.assertTrue(all(item["reason"] == "unresolved_clash" for item in planned))
        self.assertAlmostEqual(planned[1]["station_m"], 1.4)


class RunDetectionTests(unittest.TestCase):
    def test_collinear_chain_becomes_one_run(self):
        segments = [
            _pipe("a", (0, 0, 1), (1, 0, 1), adjacent=["b"]),
            _pipe("b", (1, 0, 1), (2, 0, 1), adjacent=["a", "c"]),
            _pipe("c", (2.05, 0, 1), (3, 0, 1), adjacent=["b"]),
        ]
        runs = detect_runs(segments)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["element_ids"], ["a", "b", "c"])
        self.assertAlmostEqual(runs[0]["length_m"], 3.0, places=4)
        self.assertAlmostEqual(runs[0]["origin"][0], 0.0, places=4)
        self.assertAlmostEqual(runs[0]["direction"][0], 1.0, places=4)

    def test_elbow_and_reducer_split_the_run(self):
        elbow = [
            _pipe("a", (0, 0, 1), (1, 0, 1), adjacent=["b"]),
            _pipe("b", (1, 0, 1), (1, 1, 1), adjacent=["a"]),
        ]
        self.assertEqual(len(detect_runs(elbow)), 2)
        reducer = [
            _pipe("a", (0, 0, 1), (1, 0, 1), diameter=15.0, adjacent=["b"]),
            _pipe("b", (1, 0, 1), (2, 0, 1), diameter=22.225, adjacent=["a"]),
        ]
        runs = detect_runs(reducer)
        self.assertEqual(len(runs), 2)
        self.assertEqual({run["outer_diameter_mm"] for run in runs}, {15.0, 22.225})

    def test_parallel_pipes_that_are_not_connected_stay_apart(self):
        segments = [
            _pipe("a", (0, 0, 1), (2, 0, 1)),
            _pipe("b", (0, 0.5, 1), (2, 0.5, 1)),
        ]
        self.assertEqual(len(detect_runs(segments)), 2)

    def test_offset_above_the_tolerance_does_not_join(self):
        segments = [
            _pipe("a", (0, 0, 1), (1, 0, 1), adjacent=["b"]),
            _pipe("b", (1, 0.05, 1), (2, 0.05, 1), adjacent=["a"]),
        ]
        self.assertEqual(len(detect_runs(segments)), 2)


class RodClashTests(unittest.TestCase):
    def test_box_above_hits_and_box_below_or_beside_does_not(self):
        above = {"shape": "box", "min": (0.4, -0.2, 1.2), "max": (0.6, 0.2, 2.0)}
        below = {"shape": "box", "min": (0.4, -0.2, 0.0), "max": (0.6, 0.2, 0.5)}
        beside = {"shape": "box", "min": (0.4, 0.5, 1.2), "max": (0.6, 0.8, 2.0)}
        self.assertTrue(rod_hits_obstacle(0.5, 0.0, 1.0, above))
        self.assertFalse(rod_hits_obstacle(0.5, 0.0, 1.0, below))
        self.assertFalse(rod_hits_obstacle(0.5, 0.0, 1.0, beside))

    def test_crossing_cylinder_hits_and_a_parallel_one_does_not(self):
        crossing = {
            "shape": "cylinder",
            "start": (0.5, -1.0, 1.5),
            "end": (0.5, 1.0, 1.5),
            "radius_m": 0.05,
        }
        parallel = {
            "shape": "cylinder",
            "start": (0.0, 0.5, 1.0),
            "end": (2.0, 0.5, 1.0),
            "radius_m": 0.02,
        }
        self.assertTrue(rod_hits_obstacle(0.5, 0.0, 1.0, crossing))
        self.assertFalse(rod_hits_obstacle(0.5, 0.0, 1.0, parallel))

    def test_segment_distance_for_a_rod_above_a_horizontal_pipe(self):
        # The rod starts 2 mm above z_top. A pipe whose top is that z_top
        # is 2 mm clear of the rod axis, so only the rod radius can still hit.
        pipe = {
            "shape": "cylinder",
            "start": (0.0, 0.0, 1.0),
            "end": (2.0, 0.0, 1.0),
            "radius_m": 0.01,
        }
        self.assertFalse(rod_hits_obstacle(1.0, 0.0, 1.01, pipe, rod_radius_m=0.0))
        self.assertTrue(rod_hits_obstacle(1.0, 0.0, 1.01, pipe, rod_radius_m=0.01))


class PlanMountingPointsTests(unittest.TestCase):
    def _run_of_22_mm(self, obstacles, fittings=()):
        segment = _pipe(
            "pipe-1",
            (0.0, 0.0, 1.0),
            (4.2, 0.0, 1.0),
            fittings=fittings,
        )
        # The pipe's own body is an obstacle, as it would be from an IFC load.
        own = {
            "element_id": "pipe-1",
            "shape": "cylinder",
            "start": segment["start"],
            "end": segment["end"],
            "radius_m": 22.225 / 2000.0,
        }
        return plan_mounting_points([segment], [own, *obstacles])

    def test_clear_pipe_is_placed_at_seventy_percent(self):
        plan = self._run_of_22_mm([])
        self.assertEqual(len(plan["runs"]), 1)
        self.assertEqual(plan["runs"][0]["status"], "placed_initial")
        self.assertEqual(plan["runs"][0]["max_spacing_m"], 2.0)
        stations = [point["station_m"] for point in plan["points"]]
        self.assertEqual(len(stations), 4)
        for gap in _gaps(stations):
            self.assertAlmostEqual(gap, 1.4)
        self.assertTrue(all(point["clear"] for point in plan["points"]))
        # z is the top of the pipe, not the centre-line.
        self.assertAlmostEqual(plan["points"][0]["z"], 1.0 + 22.225 / 2000.0, places=4)
        self.assertAlmostEqual(plan["points"][0]["x"], 0.0, places=4)
        self.assertEqual(plan["points"][0]["element_id"], "pipe-1")

    def test_box_above_one_hanger_respaces_the_run(self):
        box = {
            "element_id": "duct-above",
            "shape": "box",
            "min": (1.3, -0.2, 1.2),
            "max": (1.5, 0.2, 2.0),
        }
        plan = self._run_of_22_mm([box])
        self.assertEqual(plan["runs"][0]["status"], "placed_respaced")
        for point in plan["points"]:
            self.assertTrue(point["clear"], point)
            self.assertFalse(1.3 <= point["x"] <= 1.5)
        for gap_name in ("spacing_to_previous_m", "spacing_to_next_m"):
            for point in plan["points"]:
                gap = point[gap_name]
                if gap is None:
                    continue
                self.assertGreaterEqual(gap / 2.0, ADJUSTED_SPACING_MIN_RATIO - 1e-6)
                self.assertLessEqual(gap / 2.0, ADJUSTED_SPACING_MAX_RATIO + 1e-6)

    def test_a_connected_fitting_does_not_count_as_a_clash(self):
        fitting = {
            "element_id": "elbow-1",
            "shape": "box",
            "min": (-0.05, -0.05, 1.0),
            "max": (0.05, 0.05, 1.4),
        }
        plan = self._run_of_22_mm([fitting], fittings=["elbow-1"])
        self.assertEqual(plan["runs"][0]["status"], "placed_initial")

    def test_vertical_run_is_detected_and_not_hung_with_the_horizontal_table(self):
        segment = _pipe("riser", (0, 0, 0), (0, 0, 3))
        plan = plan_mounting_points([segment], [])
        self.assertEqual(plan["runs"][0]["status"], "skipped_not_horizontal")
        self.assertEqual(plan["points"], [])

    def test_size_without_a_spacing_row_is_reported(self):
        segment = _pipe("small", (0, 0, 1), (3, 0, 1), diameter=9.52)
        plan = plan_mounting_points([segment], [])
        self.assertEqual(plan["runs"][0]["status"], "no_spacing_guidance")
        self.assertIsNone(plan["runs"][0]["max_spacing_m"])
        self.assertEqual(plan["points"], [])


if __name__ == "__main__":
    unittest.main()
