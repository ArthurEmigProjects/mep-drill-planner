"""The page payload includes the hanger reason from the clash adjustment."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.ui import build_mounting_plan

ROOT = Path(__file__).resolve().parents[1]
PIPING = ROOT / "examples" / "zenodo-duplex-piping.ifc"


class MountingPlanPayloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = build_mounting_plan(PIPING)

    def test_piping_reports_moved_and_unresolved_hangers(self):
        counts = self.plan["reason_counts"]
        self.assertGreater(counts.get("shifted_under_95", 0), 0)
        self.assertGreater(counts.get("respaced_90_95", 0), 0)
        self.assertGreater(counts.get("unresolved_clash", 0), 0)
        self.assertEqual(
            self.plan["adjusted_count"],
            sum(count for reason, count in counts.items() if reason != "regular_70"),
        )
        self.assertEqual(self.plan["clash_count"], counts["unresolved_clash"])
        self.assertTrue(all("reason" in point for point in self.plan["points"]))
        self.assertEqual(self.plan["clash_models"], ["zenodo-duplex-piping.ifc"])


if __name__ == "__main__":
    unittest.main()
