"""The statistics report is computed from the shipped catalogue and inventory."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.mounting_statistics import build_report, render_markdown, write_reports


class StatisticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_headline_counts(self):
        summary = self.report.summary
        self.assertEqual(summary["product_count"], 23)
        self.assertEqual(summary["guidance_count"], 3)
        self.assertEqual(summary["primary_products"], 18)
        self.assertEqual(summary["companion_products"], 5)
        self.assertEqual(summary["manufacturers"], 6)
        self.assertEqual(summary["element_count"], 1163)
        self.assertEqual(summary["group_count"], 98)
        self.assertEqual(
            summary["matched_elements"]
            + summary["assumption_elements"]
            + summary["unmatched_elements"],
            1163,
        )
        self.assertEqual(summary["unmatched_elements"], 96)
        self.assertAlmostEqual(summary["pipe_segment_length_m"], 303.832, places=3)
        self.assertAlmostEqual(summary["duct_segment_length_m"], 118.376, places=3)

    def test_markdown_contains_the_main_sections(self):
        text = render_markdown(self.report)
        for heading in (
            "Field completeness",
            "Pipe-clamp windows",
            "Unmatched size groups",
            "Companion products under two substrates",
            "Ceiling to structure gaps",
        ):
            self.assertIn(heading, text)
        self.assertIn("1163", text)

    def test_writers_emit_all_five_formats(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = write_reports(self.report, Path(directory))
            self.assertEqual(set(paths), {"md", "txt", "docx", "pdf", "xlsx"})
            for path in paths.values():
                self.assertGreater(path.stat().st_size, 1000, path)
            self.assertTrue(paths["pdf"].read_bytes().startswith(b"%PDF"))
            self.assertEqual(paths["docx"].read_bytes()[:2], b"PK")
            self.assertEqual(paths["xlsx"].read_bytes()[:2], b"PK")


if __name__ == "__main__":
    unittest.main()
