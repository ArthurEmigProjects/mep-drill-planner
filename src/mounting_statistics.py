"""Statistics for the mounting-element database and the duplex inventory.

The report is computed from ``data/mounting_elements/products.json`` and
``data/inventory/zenodo_duplex_mountable.json``. Coverage is recalculated
with ``feasible_mountings`` so the figures follow the mapper, including the
rule that concrete anchors are companions only when the substrate is concrete.

Writes the same tables to Markdown, plain text, Word, PDF and Excel:

    python -m src.mounting_statistics

Word, PDF and Excel need ``python-docx``, ``reportlab`` and ``openpyxl``.
They are report writers only and are not part of ``requirements.txt``.
"""

from __future__ import annotations

import json
import statistics
import textwrap
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from itertools import combinations
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from src.mounting import (
    INVENTORY_PATH,
    RANGE_TOLERANCE_MM,
    coverage_report,
    feasible_mountings,
    load_database,
)

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "mounting_elements" / "statistics"
TYPE_ORDER = (
    "pipe",
    "duct_round",
    "duct_rectangular",
    "duct_flex",
    "radiator",
    "threaded_rod",
    "channel",
    "ceiling_anchor",
)
DESC_HEADERS = (
    "series",
    "n",
    "sum",
    "min",
    "max",
    "range",
    "mean",
    "median",
    "sample stdev",
    "q1",
    "q3",
)


@dataclass
class Block:
    kind: str
    text: str = ""
    headers: list = field(default_factory=list)
    rows: list = field(default_factory=list)


@dataclass
class Report:
    blocks: list[Block] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def h1(self, text: str) -> None:
        self.blocks.append(Block("h1", text))

    def h2(self, text: str) -> None:
        self.blocks.append(Block("h2", text))

    def p(self, text: str) -> None:
        self.blocks.append(Block("p", text))

    def table(self, headers: tuple | list, rows: list) -> None:
        self.blocks.append(Block("table", headers=list(headers), rows=rows))


def fmt(value) -> str:
    """Short stable rendering for a table cell."""
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        text = f"{value:.3f}".rstrip("0").rstrip(".")
        return text if text not in {"-0", ""} else "0"
    return str(value)


def pct(part: float, whole: float) -> str:
    if not whole:
        return ""
    return f"{100.0 * part / whole:.1f}%"


def describe(values: list[float]) -> dict | None:
    """Unweighted descriptive statistics. Quartiles need at least four values."""
    nums = [float(item) for item in values if item is not None]
    if not nums:
        return None
    ordered = sorted(nums)
    n = len(ordered)
    total = sum(ordered)
    q1 = q3 = None
    if n >= 4:
        q1, _, q3 = statistics.quantiles(ordered, n=4, method="inclusive")
    return {
        "n": n,
        "sum": total,
        "min": ordered[0],
        "max": ordered[-1],
        "range": ordered[-1] - ordered[0],
        "mean": total / n,
        "median": statistics.median(ordered),
        "stdev": statistics.stdev(ordered) if n >= 2 else None,
        "q1": q1,
        "q3": q3,
    }


def desc_row(name: str, values: list[float]) -> list:
    stats = describe(values)
    if stats is None:
        return [name, 0, "", "", "", "", "", "", "", "", ""]
    return [
        name,
        stats["n"],
        stats["sum"],
        stats["min"],
        stats["max"],
        stats["range"],
        stats["mean"],
        stats["median"],
        "" if stats["stdev"] is None else stats["stdev"],
        "" if stats["q1"] is None else stats["q1"],
        "" if stats["q3"] is None else stats["q3"],
    ]


def weighted_mean(pairs: list[tuple[float, float]]) -> float | None:
    used = [(value, weight) for value, weight in pairs if weight]
    total = sum(weight for _, weight in used)
    if not total:
        return None
    return sum(value * weight for value, weight in used) / total


def weighted_median(pairs: list[tuple[float, float]]) -> float | None:
    used = sorted((value, weight) for value, weight in pairs if weight > 0)
    total = sum(weight for _, weight in used)
    if not total:
        return None
    running = 0.0
    for value, weight in used:
        running += weight
        if running >= total / 2:
            return value
    return used[-1][0]


def load_kn(product: dict) -> float | None:
    rating = product.get("load_rating")
    if not rating or rating.get("value") is None:
        return None
    unit = rating.get("unit")
    if unit == "kN":
        return float(rating["value"])
    if unit == "N":
        return float(rating["value"]) / 1000.0
    return None


def blank(value) -> str:
    if value is None or value == "":
        return "(none)"
    return str(value)


def frequency(pairs: list[tuple[object, float]], label: str) -> list[list]:
    totals: Counter = Counter()
    for key, weight in pairs:
        totals[blank(key)] += weight
    grand = sum(totals.values())
    rows = []
    running = 0.0
    for key, count in totals.most_common():
        running += count
        rows.append([key, count, pct(count, grand), pct(running, grand)])
    if not rows:
        rows.append([f"(no {label})", 0, "", ""])
    return rows


def merged_windows(windows: list[tuple[float, float]]) -> list[list[float]]:
    merged: list[list[float]] = []
    for lo, hi in sorted(windows):
        if not merged or lo > merged[-1][1] + RANGE_TOLERANCE_MM:
            merged.append([lo, hi])
        else:
            merged[-1][1] = max(merged[-1][1], hi)
    return merged


def _groups(inventory: dict):
    for model_name, model in inventory["models"].items():
        for group in model["groups"]:
            yield model_name, model, group


def build_report(
    database: dict | None = None,
    inventory: dict | None = None,
    generated_at: datetime | None = None,
) -> Report:
    """Build every table the catalogue, inventory and mapper can support."""
    database = database if database is not None else load_database()
    if inventory is None:
        inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    products = database["products"]
    guidance = database["guidance"]
    coverage = coverage_report(inventory, database)
    when = generated_at or datetime.now(ZoneInfo("Europe/Berlin"))
    stamp = when.strftime("%d %B %Y, %H:%M %Z")
    report = Report()
    by_id = {product["id"]: product for product in products}

    paired = []
    for model_name, model in inventory["models"].items():
        cov_groups = coverage["models"][model_name]["groups"]
        for group, covered in zip(model["groups"], cov_groups):
            paired.append((model_name, group, covered))

    element_total = sum(group["count"] for _, group, _ in paired)
    group_total = len(paired)
    status_elements: Counter = Counter()
    status_groups: Counter = Counter()
    for _, group, covered in paired:
        status_elements[covered["status"]] += group["count"]
        status_groups[covered["status"]] += 1

    pipe_segments = [
        (model_name, group)
        for model_name, group, _ in paired
        if group["kind"] == "pipe_segment"
    ]
    duct_segments = [
        (model_name, group)
        for model_name, group, _ in paired
        if group["kind"] == "duct_segment"
    ]
    pipe_length = sum(group["total_length_m"] or 0 for _, group in pipe_segments)
    duct_length = sum(group["total_length_m"] or 0 for _, group in duct_segments)

    report.summary = {
        "product_count": len(products),
        "guidance_count": len(guidance),
        "primary_products": sum(1 for product in products if product["role"] == "primary"),
        "companion_products": sum(1 for product in products if product["role"] == "companion"),
        "manufacturers": len({product["manufacturer"] for product in products}),
        "element_count": element_total,
        "group_count": group_total,
        "matched_elements": status_elements["matched"],
        "assumption_elements": status_elements["matched_with_assumption"],
        "unmatched_elements": status_elements["unmatched"],
        "pipe_segment_length_m": round(pipe_length, 3),
        "duct_segment_length_m": round(duct_length, 3),
    }

    dataset = inventory.get("dataset") or {}
    report.h1("Mounting-element statistics")
    report.p(
        f"Generated {stamp} from data/mounting_elements/products.json "
        f"(schema version {database.get('schema_version')}) and "
        "data/inventory/zenodo_duplex_mountable.json. "
        f"Dataset: {dataset.get('title', '')} "
        f"({dataset.get('creators', '')}, {dataset.get('year', '')}), "
        f"DOI {dataset.get('doi', '')}, {dataset.get('license', '')}."
    )
    report.p(
        "Figures are counts, shares and descriptive statistics of fields that "
        "are actually stored. A null load, spacing or material stays empty. "
        "An element can match more than one clamp, so product-hit totals are "
        "not a partition of the element count. A system assignment total can "
        "exceed the element count when one element sits in more than one system. "
        "Coverage below uses substrate none, so concrete anchors are not counted "
        "as matches. The architecture ceilings are gypsum under timber joists."
    )

    report.h2("Headline figures")
    report.table(
        ("measure", "value"),
        [
            ["products", len(products)],
            ["guidance records", len(guidance)],
            ["manufacturers", report.summary["manufacturers"]],
            ["primary products", report.summary["primary_products"]],
            ["companion products", report.summary["companion_products"]],
            ["inventory size groups", group_total],
            ["inventory elements", element_total],
            ["elements matched on a published size", status_elements["matched"]],
            ["elements matched with an assumption", status_elements["matched_with_assumption"]],
            ["elements unmatched", status_elements["unmatched"]],
            ["share matched on a published size", pct(status_elements["matched"], element_total)],
            ["share matched with an assumption", pct(status_elements["matched_with_assumption"], element_total)],
            ["share unmatched", pct(status_elements["unmatched"], element_total)],
            ["pipe segment length, m", round(pipe_length, 3)],
            ["duct segment length, m", round(duct_length, 3)],
            ["models", len(inventory["models"])],
        ],
    )

    report.h2("Products by manufacturer")
    report.p("Each product counts once. Share is the share of the catalogue, not of the building.")
    manufacturer_rows = []
    manufacturers = sorted({product["manufacturer"] for product in products})
    for name in manufacturers:
        owned = [product for product in products if product["manufacturer"] == name]
        manufacturer_rows.append(
            [
                name,
                len(owned),
                pct(len(owned), len(products)),
                sum(1 for product in owned if product["role"] == "primary"),
                sum(1 for product in owned if product["role"] == "companion"),
                sum(1 for product in owned if product["load_rating"] is not None),
                sum(1 for product in owned if product["load_rating"] is None),
                ", ".join(sorted({item for product in owned for item in product["element_types"]})),
            ]
        )
    report.table(
        (
            "manufacturer",
            "products",
            "share",
            "primary",
            "companion",
            "with load",
            "load empty",
            "element types",
        ),
        manufacturer_rows,
    )

    report.h2("Products by product line")
    line_rows = []
    for product in products:
        line_rows.append(
            (
                product["product_line"],
                product["manufacturer"],
                product["role"],
                ", ".join(product["element_types"]),
            )
        )
    report.table(
        ("product line", "manufacturer", "products", "share", "roles", "element types"),
        _collapse_lines(line_rows, len(products)),
    )

    report.h2("Products by element type")
    report.p(
        "duct_flex is listed even when the count is zero: the catalogue has no flex-duct hanger. "
        "A product with several element types would be counted in each column of the cross table "
        "and once in this table per type."
    )
    type_rows = []
    for element_type in TYPE_ORDER:
        owned = [product for product in products if element_type in product["element_types"]]
        type_rows.append(
            [
                element_type,
                len(owned),
                pct(len(owned), len(products)),
                sum(1 for product in owned if product["role"] == "primary"),
                sum(1 for product in owned if product["role"] == "companion"),
                sum(1 for product in owned if product["outer_diameter_mm"] is not None),
                sum(1 for product in owned if product["nominal_diameter_mm"] is not None),
                sum(1 for product in owned if product["load_rating"] is not None),
            ]
        )
    report.table(
        (
            "element type",
            "products",
            "share of catalogue",
            "primary",
            "companion",
            "with OD window",
            "with nominal diameter",
            "with load",
        ),
        type_rows,
    )

    report.h2("Manufacturer by element type")
    header = ["manufacturer", *TYPE_ORDER, "products"]
    cross_rows = []
    for name in manufacturers:
        owned = [product for product in products if product["manufacturer"] == name]
        counts = [
            sum(1 for product in owned if element_type in product["element_types"])
            for element_type in TYPE_ORDER
        ]
        cross_rows.append([name, *counts, len(owned)])
    totals = ["all", *([sum(row[index] for row in cross_rows) for index in range(1, len(TYPE_ORDER) + 1)]), len(products)]
    cross_rows.append(totals)
    report.table(header, cross_rows)

    report.h2("Products by role")
    report.table(
        ("role", "products", "share", "cumulative share"),
        frequency([(product["role"], 1) for product in products], "role"),
    )

    report.h2("Field completeness")
    report.p(
        "Filled means the JSON value is not null and, for a list, not empty. "
        "max_support_spacing is null on every product: published spacing lives in guidance."
    )
    fields = (
        ("product_line", lambda product: product["product_line"]),
        ("article_number", lambda product: product["article_number"]),
        ("outer_diameter_mm", lambda product: product["outer_diameter_mm"]),
        ("nominal_diameter_mm", lambda product: product["nominal_diameter_mm"]),
        ("connection_threads", lambda product: product["connection_threads"]),
        ("load_rating", lambda product: product["load_rating"]),
        ("max_support_spacing", lambda product: product["max_support_spacing"]),
        ("anchor", lambda product: product["anchor"]),
        ("assumptions", lambda product: product["assumptions"]),
        ("notes", lambda product: product["notes"]),
        ("sources", lambda product: product["sources"]),
    )
    complete_rows = []
    for name, getter in fields:
        filled = sum(1 for product in products if _filled(getter(product)))
        complete_rows.append(
            [name, filled, len(products) - filled, pct(filled, len(products))]
        )
    report.table(("field", "filled", "empty", "filled share"), complete_rows)
    articles = [product["article_number"] for product in products]
    report.p(
        f"Article numbers: {len(articles)} stored, {len(set(articles))} distinct. "
        f"Product ids: {len(products)} stored, {len({product['id'] for product in products})} distinct."
    )

    report.h2("Connection threads")
    report.p(
        "A clamp with M8/M10 is counted under both threads. The share is the share of "
        "catalogue products that include the thread, so the column can sum to more than 100%."
    )
    thread_counts: Counter = Counter(
        thread for product in products for thread in product["connection_threads"]
    )
    report.table(
        ("thread", "products", "share of catalogue"),
        [
            [thread, count, pct(count, len(products))]
            for thread, count in thread_counts.most_common()
        ],
    )
    bare_threads = sum(1 for product in products if not product["connection_threads"])
    report.p(f"Products with an empty connection_threads list: {bare_threads} of {len(products)}.")
    combo_counter: Counter = Counter()
    for product in products:
        combo = "+".join(product["connection_threads"]) if product["connection_threads"] else "(none)"
        combo_counter[(combo, product["role"])] += 1
    report.table(
        ("thread combination", "role", "products", "share of catalogue"),
        [
            [combo, role, count, pct(count, len(products))]
            for (combo, role), count in sorted(combo_counter.items())
        ],
    )

    pipe_clamps = [
        product
        for product in products
        if product["role"] == "primary"
        and "pipe" in product["element_types"]
        and product["outer_diameter_mm"] is not None
    ]
    report.h2("Pipe-clamp windows")
    window_rows = []
    for product in sorted(pipe_clamps, key=lambda item: (item["outer_diameter_mm"]["min"], item["id"])):
        window = product["outer_diameter_mm"]
        window_rows.append(
            [
                product["id"],
                product["manufacturer"],
                product["article_number"],
                window["min"],
                window["max"],
                window["max"] - window["min"],
                ", ".join(product["connection_threads"]),
                "" if load_kn(product) is None else load_kn(product),
            ]
        )
    report.table(
        ("id", "manufacturer", "article", "min mm", "max mm", "span mm", "threads", "load kN"),
        window_rows,
    )
    report.p(
        "Span is max minus min of the published window. Load kN converts N by dividing by 1000 "
        "and leaves a cell empty when the source published no load. The definitions still differ "
        "by product and are not one allowable-load population."
    )
    report.h2("Descriptive statistics of pipe-clamp windows")
    report.table(
        DESC_HEADERS,
        [
            desc_row("window min, mm", [row[3] for row in window_rows]),
            desc_row("window max, mm", [row[4] for row in window_rows]),
            desc_row("window span, mm", [row[5] for row in window_rows]),
            desc_row(
                "published load of these clamps, kN",
                [row[7] for row in window_rows if row[7] != ""],
            ),
        ],
    )

    report.h2("Overlapping pipe-clamp windows")
    report.p(
        "Two windows overlap when their intervals meet within "
        f"{RANGE_TOLERANCE_MM:g} mm, the same tolerance the mapper uses. "
        "A zero-width overlap is a shared boundary, so an outside diameter equal "
        "to that boundary matches both clamps."
    )
    overlap_rows = []
    for left, right in combinations(pipe_clamps, 2):
        left_window = left["outer_diameter_mm"]
        right_window = right["outer_diameter_mm"]
        if left_window["min"] > right_window["max"] + RANGE_TOLERANCE_MM:
            continue
        if right_window["min"] > left_window["max"] + RANGE_TOLERANCE_MM:
            continue
        overlap_lo = max(left_window["min"], right_window["min"])
        overlap_hi = min(left_window["max"], right_window["max"])
        overlap_rows.append(
            [
                left["article_number"],
                right["article_number"],
                overlap_lo,
                overlap_hi,
                max(0.0, overlap_hi - overlap_lo),
            ]
        )
    overlap_rows.sort(key=lambda row: (row[2], row[0], row[1]))
    report.table(
        ("article A", "article B", "overlap min mm", "overlap max mm", "overlap width mm"),
        overlap_rows,
    )
    report.p(f"Overlapping or boundary-touching pairs: {len(overlap_rows)}.")

    report.h2("Merged clamp coverage and holes")
    windows = [
        (product["outer_diameter_mm"]["min"], product["outer_diameter_mm"]["max"])
        for product in pipe_clamps
    ]
    merged = merged_windows(windows)
    report.table(
        ("covered from mm", "covered to mm", "width mm"),
        [[lo, hi, hi - lo] for lo, hi in merged],
    )
    hole_rows = []
    for (left_lo, left_hi), (right_lo, right_hi) in zip(merged, merged[1:]):
        hole_rows.append([left_hi, right_lo, right_lo - left_hi])
    report.table(("hole after mm", "hole before mm", "width mm"), hole_rows)
    if windows:
        start = int(min(lo for lo, _ in windows))
        stop = int(max(hi for _, hi in windows))
    else:
        start, stop = 0, -1
    depth_rows = []
    for millimetre in range(start, stop + 1):
        result = feasible_mountings(
            {
                "kind": "pipe_segment",
                "shape": "round",
                "outer_diameter_mm": float(millimetre),
                "outer_diameters_mm": [float(millimetre)],
            },
            database,
        )
        matched_ids = [item["id"] for item in result["matches"]]
        depth_rows.append([millimetre, len(matched_ids), ", ".join(matched_ids)])
    report.p(
        "Depth is how many primary pipe clamps the mapper returns for each integer "
        "millimetre from the lowest published minimum to the highest published maximum."
    )
    report.h2("Descriptive statistics of integer clamp depth")
    report.table(DESC_HEADERS, [desc_row("clamps covering each integer mm", [row[1] for row in depth_rows])])
    depth_hist = frequency([(row[1], 1) for row in depth_rows], "depth")
    report.table(("clamps at that mm", "integer mm count", "share of the scanned mm", "cumulative share"), depth_hist)
    uncovered = _runs([row[0] for row in depth_rows if row[1] == 0])
    report.table(
        ("uncovered integers from mm", "uncovered integers to mm", "count of integers"),
        uncovered or [["(none)", "", 0]],
    )
    report.h2("Clamp depth at each integer millimetre")
    report.table(("mm", "matching clamps", "product ids"), depth_rows)

    report.h2("Published loads")
    report.p(
        "kN is the stored value when the unit is already kN, and the stored value divided by "
        "1000 when the unit is N. Empty load cells are excluded from the descriptive rows. "
        "Kinds are kept apart because a recommended static load, a Nutzlast and an anchor Fzul "
        "are not interchangeable."
    )
    load_rows = []
    for product in products:
        rating = product["load_rating"]
        if rating is None:
            continue
        load_rows.append(
            [
                product["id"],
                product["manufacturer"],
                ", ".join(product["element_types"]),
                rating["value"],
                rating["unit"],
                load_kn(product) if load_kn(product) is not None else "",
                rating["kind"],
            ]
        )
    report.table(
        ("id", "manufacturer", "element type", "value", "unit", "kN", "kind"),
        load_rows,
    )
    kind_groups: dict[str, list[float]] = {}
    for row in load_rows:
        kind_groups.setdefault(row[6], []).append(row[5])
    desc_rows = [
        desc_row("all published loads converted to kN", [row[5] for row in load_rows if row[5] != ""])
    ]
    for kind, values in sorted(kind_groups.items()):
        desc_rows.append(desc_row(kind, values))
    report.table(DESC_HEADERS, desc_rows)
    missing_load = [product for product in products if product["load_rating"] is None]
    report.table(
        ("id", "manufacturer", "element type", "article"),
        [
            [product["id"], product["manufacturer"], ", ".join(product["element_types"]), product["article_number"]]
            for product in missing_load
        ],
    )
    report.p(f"Products with no published load in the database: {len(missing_load)} of {len(products)}.")

    report.h2("Anchors stored on products")
    anchor_rows = []
    for product in products:
        anchor = product["anchor"]
        if not anchor:
            continue
        anchor_rows.append(
            [
                product["id"],
                product["manufacturer"],
                anchor.get("type"),
                anchor.get("thread"),
                anchor.get("substrate"),
                anchor.get("included_fixings"),
                "" if load_kn(product) is None else load_kn(product),
            ]
        )
    report.table(
        ("id", "manufacturer", "anchor type", "thread", "substrate", "included fixings", "load kN"),
        anchor_rows,
    )
    report.table(
        ("substrate", "products", "share of anchored products", "cumulative share"),
        frequency([(row[4], 1) for row in anchor_rows], "substrate"),
    )

    report.h2("Guidance records")
    guidance_rows = []
    for item in guidance:
        table_rows = [row for row in item["rows"] if isinstance(row, dict) and row.get("table_row") is True]
        guidance_rows.append(
            [
                item["id"],
                ", ".join(item["applies_to"]),
                len(item["rows"]),
                len(table_rows) if any(isinstance(row, dict) and "table_row" in row for row in item["rows"]) else "",
                len(item["sources"]),
                len(item.get("notes") or ""),
            ]
        )
    report.table(
        ("id", "applies to", "rows", "rows flagged table_row", "sources", "note characters"),
        guidance_rows,
    )

    for item in guidance:
        report.h2(f"Guidance rows: {item['id']}")
        report.p(item.get("notes") or "")
        if not item["rows"]:
            report.p("This record has no numeric rows.")
            continue
        columns = list(dict.fromkeys(key for row in item["rows"] for key in row.keys()))
        report.table(
            columns,
            [[row.get(column, "") for column in columns] for row in item["rows"]],
        )
        horizontal = [
            row["horizontal_m"]
            for row in item["rows"]
            if row.get("horizontal_m") is not None and row.get("table_row") is not False
        ]
        if horizontal:
            label = "horizontal spacing, m"
            if any("table_row" in row for row in item["rows"]):
                label = "horizontal spacing of table_row true, m"
            report.table(DESC_HEADERS, [desc_row(label, horizontal)])
        diameters = [
            row["outer_diameter_mm"]
            for row in item["rows"]
            if row.get("outer_diameter_mm") is not None
        ]
        if diameters:
            report.table(DESC_HEADERS, [desc_row("table outside diameter, mm", diameters)])

    report.h2("Inventory by model")
    model_rows = []
    for model_name, model in inventory["models"].items():
        summary = coverage["models"][model_name]["summary"]
        elements = summary["elements"]
        groups = summary["groups"]
        length = sum(
            group["total_length_m"] or 0
            for name, group, _ in paired
            if name == model_name
        )
        model_rows.append(
            [
                model_name,
                model["file"],
                model["schema"],
                model["element_count"],
                pct(model["element_count"], element_total),
                len(model["groups"]),
                round(length, 3),
                elements["matched"],
                elements["matched_with_assumption"],
                elements["unmatched"],
                pct(elements["matched"], model["element_count"]),
                pct(elements["unmatched"], model["element_count"]),
                groups["matched"],
                groups["matched_with_assumption"],
                groups["unmatched"],
            ]
        )
    report.table(
        (
            "model",
            "file",
            "schema",
            "elements",
            "share of elements",
            "groups",
            "recorded length m",
            "elements matched",
            "elements with assumption",
            "elements unmatched",
            "element matched share",
            "element unmatched share",
            "groups matched",
            "groups with assumption",
            "groups unmatched",
        ),
        model_rows,
    )

    report.h2("Elements by kind")
    report.table(
        ("kind", "elements", "share of elements", "cumulative share"),
        frequency([(group["kind"], group["count"]) for _, group, _ in paired], "kind"),
    )
    report.h2("Size groups by kind")
    report.table(
        ("kind", "groups", "share of groups", "cumulative share"),
        frequency([(group["kind"], 1) for _, group, _ in paired], "kind"),
    )
    kind_names = sorted({group["kind"] for _, group, _ in paired})
    kind_model_rows = []
    for kind in kind_names:
        row = [kind]
        for model_name in inventory["models"]:
            count = sum(
                group["count"]
                for name, group, _ in paired
                if name == model_name and group["kind"] == kind
            )
            row.append(count)
        row.append(sum(row[1:]))
        kind_model_rows.append(row)
    report.table(["kind", *inventory["models"].keys(), "elements"], kind_model_rows)

    report.h2("Elements by IFC class")
    report.table(
        ("IFC class", "elements", "share of elements", "cumulative share"),
        frequency([(group["ifc_class"], group["count"]) for _, group, _ in paired], "class"),
    )
    report.h2("Elements by size method")
    report.table(
        ("size method", "elements", "share of elements", "cumulative share"),
        frequency([(group["size_method"], group["count"]) for _, group, _ in paired], "method"),
    )
    report.h2("Elements by family")
    report.table(
        ("family", "elements", "share of elements", "cumulative share"),
        frequency([(group["family"], group["count"]) for _, group, _ in paired], "family"),
    )
    report.h2("Elements by cross-section shape")
    report.table(
        ("shape", "elements", "share of elements", "cumulative share"),
        frequency([(group["shape"], group["count"]) for _, group, _ in paired], "shape"),
    )

    report.h2("Missing material, insulation and predefined type")
    report.p("Counts are size groups. The inventory found no material name and no insulation on these models.")
    missing_rows = []
    for model_name, model in inventory["models"].items():
        groups = model["groups"]
        missing_rows.append(
            [
                model_name,
                len(groups),
                sum(1 for group in groups if not group.get("material")),
                sum(1 for group in groups if group.get("insulation") is None),
                sum(1 for group in groups if not group.get("predefined_type")),
                sum(group["count"] for group in groups if not group.get("material")),
            ]
        )
    report.table(
        (
            "model",
            "groups",
            "groups with no material",
            "groups with no insulation",
            "groups with no predefined type",
            "elements with no material",
        ),
        missing_rows,
    )
    nominal_groups = [
        (model_name, group)
        for model_name, group, _ in paired
        if any(str(item).startswith("NominalDiameter") for item in group.get("assumptions") or [])
    ]
    multi_groups = [
        (model_name, group)
        for model_name, group, _ in paired
        if len(group.get("outer_diameters_mm") or []) > 1
    ]
    report.p(
        f"Size groups whose NominalDiameter property disagrees with the connected profile: "
        f"{len(nominal_groups)} groups, {sum(group['count'] for _, group in nominal_groups)} elements. "
        f"Size groups with more than one outside diameter (reducers and similar): "
        f"{len(multi_groups)} groups, {sum(group['count'] for _, group in multi_groups)} elements."
    )

    report.h2("System assignments")
    report.p(
        "The count is the sum of system memberships stored on each size group. "
        "It can exceed the element count."
    )
    system_rows = []
    for model_name, model in inventory["models"].items():
        totals: Counter = Counter()
        for group in model["groups"]:
            for system in group["systems"]:
                totals[system.get("object_type") or system["name"]] += system["count"]
        assigned = sum(totals.values())
        for name, count in totals.most_common():
            system_rows.append(
                [
                    model_name,
                    name,
                    count,
                    pct(count, assigned),
                    model["element_count"],
                    assigned - model["element_count"],
                ]
            )
    report.table(
        (
            "model",
            "system object type",
            "assignments",
            "share of that model's assignments",
            "elements in the model",
            "assignments minus elements",
        ),
        system_rows,
    )

    report.h2("Pipe segments by outside diameter")
    pipe_rows = []
    ordered_pipes = sorted(
        pipe_segments,
        key=lambda item: (-(item[1]["total_length_m"] or 0), item[0], item[1]["outer_diameter_mm"] or 0),
    )
    running_length = 0.0
    for model_name, group in ordered_pipes:
        length = group["total_length_m"] or 0
        running_length += length
        result = feasible_mountings(group, database)
        pipe_rows.append(
            [
                model_name,
                group["outer_diameter_mm"],
                group["count"],
                pct(group["count"], sum(item["count"] for _, item in pipe_segments)),
                round(length, 3),
                pct(length, pipe_length),
                pct(running_length, pipe_length),
                round(length / group["count"], 3) if group["count"] else "",
                result["status"],
                len(result["matches"]),
                ", ".join(item["article_number"] or item["id"] for item in result["matches"]),
            ]
        )
    report.table(
        (
            "model",
            "OD mm",
            "segments",
            "share of segments",
            "length m",
            "share of pipe length",
            "cumulative length share",
            "mean length per segment m",
            "match status",
            "clamps",
            "articles",
        ),
        pipe_rows,
    )
    report.h2("Pipe-segment diameter statistics")
    diameter_rows = []
    for model_name in inventory["models"]:
        owned = [(name, group) for name, group in pipe_segments if name == model_name]
        if not owned:
            continue
        length_pairs = [
            (group["outer_diameter_mm"], group["total_length_m"] or 0) for _, group in owned
        ]
        expanded = []
        for _, group in owned:
            expanded.extend([group["outer_diameter_mm"]] * group["count"])
        stats = describe(expanded)
        total_count = sum(group["count"] for _, group in owned)
        total_length = sum(group["total_length_m"] or 0 for _, group in owned)
        diameter_rows.append(
            [
                model_name,
                total_count,
                round(total_length, 3),
                round(total_length / total_count, 3) if total_count else "",
                stats["min"] if stats else "",
                stats["max"] if stats else "",
                stats["mean"] if stats else "",
                stats["median"] if stats else "",
                "" if not stats or stats["stdev"] is None else stats["stdev"],
                weighted_mean(length_pairs),
                weighted_median(length_pairs),
            ]
        )
    all_expanded = []
    all_length_pairs = []
    for _, group in pipe_segments:
        all_expanded.extend([group["outer_diameter_mm"]] * group["count"])
        all_length_pairs.append((group["outer_diameter_mm"], group["total_length_m"] or 0))
    all_stats = describe(all_expanded)
    all_count = sum(group["count"] for _, group in pipe_segments)
    diameter_rows.append(
        [
            "all pipe segments",
            all_count,
            round(pipe_length, 3),
            round(pipe_length / all_count, 3) if all_count else "",
            all_stats["min"] if all_stats else "",
            all_stats["max"] if all_stats else "",
            all_stats["mean"] if all_stats else "",
            all_stats["median"] if all_stats else "",
            "" if not all_stats or all_stats["stdev"] is None else all_stats["stdev"],
            weighted_mean(all_length_pairs),
            weighted_median(all_length_pairs),
        ]
    )
    report.p(
        "Min, max, mean, median and sample stdev treat one segment as one observation, "
        "so a common small diameter pulls the mean down. The length-weighted columns "
        "weight each size by its recorded centreline length."
    )
    report.table(
        (
            "model",
            "segments",
            "length m",
            "mean length per segment m",
            "min OD mm",
            "max OD mm",
            "count-weighted mean OD mm",
            "count-weighted median OD mm",
            "count-weighted sample stdev mm",
            "length-weighted mean OD mm",
            "length-weighted median OD mm",
        ),
        diameter_rows,
    )
    distinct = [group["outer_diameter_mm"] for _, group in pipe_segments]
    report.table(
        DESC_HEADERS,
        [desc_row("distinct pipe-segment OD values, one row per size group, mm", distinct)],
    )

    report.h2("Duct segments by cross-section")
    duct_rows = []
    running_length = 0.0
    ordered_ducts = sorted(
        duct_segments,
        key=lambda item: (-(item[1]["total_length_m"] or 0), item[1]["size_label"]),
    )
    for model_name, group in ordered_ducts:
        length = group["total_length_m"] or 0
        running_length += length
        result = feasible_mountings(group, database)
        area = ""
        if group.get("width_mm") and group.get("height_mm"):
            area = group["width_mm"] * group["height_mm"]
        duct_rows.append(
            [
                model_name,
                group.get("shape"),
                group["size_label"],
                group.get("width_mm"),
                group.get("height_mm"),
                group.get("outer_diameter_mm"),
                area,
                group["count"],
                round(length, 3),
                pct(length, duct_length),
                pct(running_length, duct_length),
                round(length / group["count"], 3) if group["count"] else "",
                result["status"],
                len(result["matches"]),
            ]
        )
    report.table(
        (
            "model",
            "shape",
            "size",
            "width mm",
            "height mm",
            "OD mm",
            "section area mm2",
            "segments",
            "length m",
            "share of duct length",
            "cumulative length share",
            "mean length per segment m",
            "match status",
            "primary products",
        ),
        duct_rows,
    )
    rect = [group for _, group in duct_segments if group.get("shape") == "rectangular"]
    report.table(
        DESC_HEADERS,
        [
            desc_row("rectangular duct width, one size group, mm", [group["width_mm"] for group in rect]),
            desc_row("rectangular duct height, one size group, mm", [group["height_mm"] for group in rect]),
            desc_row(
                "rectangular section area, one size group, mm2",
                [group["width_mm"] * group["height_mm"] for group in rect],
            ),
            desc_row(
                "duct segment length, one size group, m",
                [group["total_length_m"] for _, group in duct_segments],
            ),
        ],
    )
    if rect:
        report.p(
            "Length-weighted mean rectangular width is "
            f"{fmt(weighted_mean([(group['width_mm'], group['total_length_m'] or 0) for group in rect]))} mm; "
            "height "
            f"{fmt(weighted_mean([(group['height_mm'], group['total_length_m'] or 0) for group in rect]))} mm; "
            "section area "
            f"{fmt(weighted_mean([(group['width_mm'] * group['height_mm'], group['total_length_m'] or 0) for group in rect]))} mm2."
        )

    report.h2("Devices and other bounding boxes")
    device_kinds = {
        "sanitary_fixture",
        "water_heater",
        "air_handling_unit",
        "air_terminal",
        "radiator",
        "stove",
    }
    device_rows = []
    for model_name, group, covered in paired:
        if group["kind"] not in device_kinds and group.get("size_method") != "world_bbox":
            continue
        bbox = group.get("bbox_mm") or []
        device_rows.append(
            [
                model_name,
                group["kind"],
                group["ifc_class"],
                group["size_label"],
                group["count"],
                pct(group["count"], element_total),
                bbox[0] if len(bbox) == 3 else "",
                bbox[1] if len(bbox) == 3 else "",
                bbox[2] if len(bbox) == 3 else "",
                covered["status"],
                covered["gap"] or "",
            ]
        )
    report.table(
        (
            "model",
            "kind",
            "IFC class",
            "size",
            "elements",
            "share of all elements",
            "bbox axis 1 mm",
            "bbox axis 2 mm",
            "bbox axis 3 mm",
            "status",
            "gap",
        ),
        device_rows,
    )

    report.h2("Coverage by kind")
    kind_status_rows = []
    for kind in kind_names:
        owned = [(group, covered) for _, group, covered in paired if group["kind"] == kind]
        elements = sum(group["count"] for group, _ in owned)
        row = [kind, len(owned), elements]
        for status in ("matched", "matched_with_assumption", "unmatched"):
            count = sum(group["count"] for group, covered in owned if covered["status"] == status)
            row.extend([count, pct(count, elements)])
        kind_status_rows.append(row)
    report.table(
        (
            "kind",
            "groups",
            "elements",
            "matched elements",
            "matched share",
            "assumption elements",
            "assumption share",
            "unmatched elements",
            "unmatched share",
        ),
        kind_status_rows,
    )

    report.h2("Unmatched size groups")
    gap_rows = []
    for gap in coverage["gaps"]:
        model_elements = inventory["models"][gap["model"]]["element_count"]
        gap_rows.append(
            [
                gap["model"],
                gap["kind"],
                gap["size_label"],
                gap["count"],
                pct(gap["count"], model_elements),
                pct(gap["count"], element_total),
                gap["gap"],
            ]
        )
    report.table(
        (
            "model",
            "kind",
            "size",
            "elements",
            "share of that model",
            "share of all elements",
            "gap",
        ),
        gap_rows,
    )
    report.p(
        f"Unmatched groups: {len(coverage['gaps'])}. "
        f"Unmatched elements: {status_elements['unmatched']} "
        f"({pct(status_elements['unmatched'], element_total)} of {element_total})."
    )

    report.h2("Primary-product utilisation")
    report.p(
        "Element hits sum the size groups for which the product is a primary match. "
        "A reducer that matches two clamps, and a diameter that matches three clamps, "
        "are counted once for each product. The shares can therefore sum to more than 100%."
    )
    use_elements: Counter = Counter()
    use_groups: Counter = Counter()
    for _, group, covered in paired:
        for product_id in covered["product_ids"]:
            use_elements[product_id] += group["count"]
            use_groups[product_id] += 1
    use_rows = []
    for product in products:
        if product["role"] != "primary":
            continue
        hits = use_elements[product["id"]]
        use_rows.append(
            [
                product["id"],
                product["manufacturer"],
                product["article_number"],
                ", ".join(product["element_types"]),
                use_groups[product["id"]],
                hits,
                pct(hits, element_total),
            ]
        )
    use_rows.sort(key=lambda row: (-row[5], row[0]))
    report.table(
        ("id", "manufacturer", "article", "element type", "groups", "element hits", "share of all elements"),
        use_rows,
    )
    unused_primary = [row[0] for row in use_rows if row[5] == 0]
    report.p(
        "Primary products with no hit in this inventory: "
        + (", ".join(unused_primary) if unused_primary else "none")
        + f". Primary products with at least one hit: {sum(1 for row in use_rows if row[5])} "
        f"of {len(use_rows)}."
    )
    report.table(
        DESC_HEADERS,
        [desc_row("element hits per primary product", [row[5] for row in use_rows])],
    )

    report.h2("Companion products under two substrates")
    report.p(
        "Companions are rods, channel and anchors returned with a primary match. "
        "substrate none is the duplex default. substrate concrete is the German "
        "commercial ceiling the anchor articles were recorded for. Each element is "
        "counted once per companion: a rod is attached when the matched clamps use "
        "that thread, and it is not multiplied by the number of clamps."
    )
    companion_none: Counter = Counter()
    companion_concrete: Counter = Counter()
    groups_none: Counter = Counter()
    groups_concrete: Counter = Counter()
    for _, group, _ in paired:
        plain = feasible_mountings(group, database)
        concrete = feasible_mountings(group, database, substrate="concrete")
        for bucket, grouped, result in (
            (companion_none, groups_none, plain),
            (companion_concrete, groups_concrete, concrete),
        ):
            for companion in result["companions"]:
                bucket[companion["id"]] += group["count"]
                grouped[companion["id"]] += 1
    companion_rows = []
    for product in products:
        if product["role"] != "companion":
            continue
        companion_rows.append(
            [
                product["id"],
                ", ".join(product["element_types"]),
                ", ".join(product["connection_threads"]),
                groups_none[product["id"]],
                companion_none[product["id"]],
                groups_concrete[product["id"]],
                companion_concrete[product["id"]],
            ]
        )
    report.table(
        (
            "id",
            "element type",
            "threads",
            "groups, substrate none",
            "elements, substrate none",
            "groups, substrate concrete",
            "elements, substrate concrete",
        ),
        companion_rows,
    )

    report.h2("Size-group census")
    census = []
    for model_name, group, covered in paired:
        census.append(
            [
                model_name,
                group["kind"],
                blank(group.get("family")),
                group["ifc_class"],
                group["size_label"],
                group["count"],
                "" if group.get("total_length_m") is None else round(group["total_length_m"], 3),
                group["size_method"],
                blank(group.get("shape")),
                covered["status"],
                len(covered["product_ids"]),
                len(group.get("assumptions") or []),
            ]
        )
    report.table(
        (
            "model",
            "kind",
            "family",
            "IFC class",
            "size",
            "elements",
            "length m",
            "size method",
            "shape",
            "status",
            "primary products",
            "assumption notes",
        ),
        census,
    )

    architecture = inventory.get("architecture") or {}
    report.h2("Architecture storeys")
    storeys = architecture.get("storeys") or []
    report.table(
        ("name", "elevation m"),
        [[storey["name"], storey["elevation_m"]] for storey in storeys],
    )
    report.table(DESC_HEADERS, [desc_row("storey elevation, m", [storey["elevation_m"] for storey in storeys])])

    for collection, title in (
        ("slabs", "Architecture slabs and roofs"),
        ("ceilings", "Architecture ceilings"),
        ("beams", "Architecture beams"),
    ):
        rows_src = architecture.get(collection) or []
        report.h2(title)
        report.table(
            ("type", "predefined type", "thickness mm", "z min m", "z max m", "count"),
            [
                [
                    item["type_name"],
                    blank(item.get("predefined_type")),
                    item["thickness_mm"],
                    item["z_min_m"],
                    item["z_max_m"],
                    item["count"],
                ]
                for item in rows_src
            ],
        )
        expanded = []
        for item in rows_src:
            expanded.extend([item["thickness_mm"]] * item["count"])
        report.table(
            DESC_HEADERS,
            [
                desc_row(f"{collection} thickness, one type row, mm", [item["thickness_mm"] for item in rows_src]),
                desc_row(f"{collection} thickness, one instance, mm", expanded),
            ],
        )

    gaps = architecture.get("ceiling_to_structure_gaps") or []
    report.h2("Ceiling to structure gaps")
    report.table(
        ("ceiling z max m", "ceiling thickness mm", "overhead", "overhead z min m", "gap mm", "ceilings"),
        [
            [
                item["ceiling_z_max_m"],
                item["ceiling_thickness_mm"],
                item["overhead_name"],
                item["overhead_z_min_m"],
                item["gap_mm"],
                item["count"],
            ]
            for item in gaps
        ],
    )
    expanded_gaps = []
    for item in gaps:
        expanded_gaps.extend([item["gap_mm"]] * item["count"])
    report.table(
        DESC_HEADERS,
        [
            desc_row("clear gap, one ceiling instance, mm", expanded_gaps),
            desc_row("ceiling thickness in the gap table, one instance, mm", [
                item["ceiling_thickness_mm"] for item in gaps for _ in range(item["count"])
            ]),
        ],
    )
    for observation in architecture.get("observations") or []:
        report.p(observation)

    report.h2("Sources")
    source_counter: Counter = Counter()
    accessed: Counter = Counter()
    per_product = []
    for product in products:
        per_product.append(len(product["sources"]))
        for source in product["sources"]:
            source_counter[(source["title"], source["url"])] += 1
            accessed[source.get("accessed") or "(none)"] += 1
    for item in guidance:
        for source in item["sources"]:
            source_counter[(source["title"], source["url"])] += 1
            accessed[source.get("accessed") or "(none)"] += 1
    report.table(DESC_HEADERS, [desc_row("sources cited by one product", per_product)])
    report.table(
        ("accessed", "citations", "share of citations", "cumulative share"),
        frequency(list(accessed.items()), "date"),
    )
    domains: Counter = Counter()
    for (_, url), count in source_counter.items():
        domains[urlparse(url).netloc] += count
    report.table(
        ("source host", "citations", "share of citations", "cumulative share"),
        frequency(list(domains.items()), "host"),
    )
    report.table(
        ("title", "url", "citations", "host"),
        [
            [title, url, count, urlparse(url).netloc]
            for (title, url), count in sorted(source_counter.items(), key=lambda item: (-item[1], item[0][1]))
        ],
    )
    report.p(
        f"Distinct source URLs: {len(source_counter)}. "
        f"Citations counting a reused URL once per product or guidance record: {sum(source_counter.values())}."
    )

    report.h2("Assumptions stored on products")
    assumption_rows = [
        [product["id"], assumption]
        for product in products
        for assumption in product["assumptions"]
    ]
    report.table(("id", "assumption"), assumption_rows or [["(none)", ""]])
    report.p(f"Product assumption strings: {len(assumption_rows)} on {sum(1 for product in products if product['assumptions'])} products.")

    for note in inventory.get("notes") or []:
        report.p(note)
    return report


def _filled(value) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, dict, str)) and len(value) == 0:
        return False
    return True


def _collapse_lines(rows: list[tuple], product_count: int) -> list[list]:
    grouped: dict[tuple, dict] = {}
    for line, manufacturer, role, element_type in rows:
        key = (line, manufacturer)
        bucket = grouped.setdefault(key, {"n": 0, "roles": set(), "types": set()})
        bucket["n"] += 1
        bucket["roles"].add(role)
        bucket["types"].add(element_type)
    collapsed = []
    for (line, manufacturer), bucket in sorted(grouped.items(), key=lambda item: (-item[1]["n"], item[0][0] or "")):
        collapsed.append(
            [
                line,
                manufacturer,
                bucket["n"],
                pct(bucket["n"], product_count),
                ", ".join(sorted(bucket["roles"])),
                ", ".join(sorted(bucket["types"])),
            ]
        )
    return collapsed


def _runs(values: list[int]) -> list[list]:
    if not values:
        return []
    ordered = sorted(values)
    start = previous = ordered[0]
    rows = []
    for value in ordered[1:]:
        if value == previous + 1:
            previous = value
            continue
        rows.append([start, previous, previous - start + 1])
        start = previous = value
    rows.append([start, previous, previous - start + 1])
    return rows


def render_markdown(report: Report) -> str:
    lines = []
    for block in report.blocks:
        if block.kind == "h1":
            lines.extend(["", f"# {block.text}", ""])
        elif block.kind == "h2":
            lines.extend(["", f"## {block.text}", ""])
        elif block.kind == "p":
            lines.extend([block.text, ""])
        elif block.kind == "table":
            headers = [str(header) for header in block.headers]
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join("---" for _ in headers) + " |")
            for row in block.rows:
                cells = [_md_cell(value) for value in row]
                while len(cells) < len(headers):
                    cells.append("")
                lines.append("| " + " | ".join(cells[: len(headers)]) + " |")
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def _md_cell(value) -> str:
    return fmt(value).replace("|", "\\|").replace("\n", " ")


def render_text(report: Report) -> str:
    chunks = []
    for block in report.blocks:
        if block.kind == "h1":
            chunks.append("")
            chunks.append(block.text)
            chunks.append("=" * len(block.text))
        elif block.kind == "h2":
            chunks.append("")
            chunks.append(block.text)
            chunks.append("-" * len(block.text))
        elif block.kind == "p":
            chunks.append(textwrap.fill(block.text, width=100))
        elif block.kind == "table":
            chunks.append(_text_table(block.headers, block.rows))
    return "\n".join(chunks).strip() + "\n"


def _text_table(headers: list, rows: list) -> str:
    rendered = [[fmt(value) for value in row] for row in rows]
    titles = [str(header) for header in headers]
    widths = []
    for index, title in enumerate(titles):
        longest = len(title)
        for row in rendered:
            if index < len(row):
                longest = max(longest, min(42, len(row[index])))
        widths.append(max(4, min(42, longest)))
    rule = "  ".join("-" * width for width in widths)

    def paint(cells: list[str]) -> list[str]:
        wrapped = []
        height = 1
        for index, width in enumerate(widths):
            text = cells[index] if index < len(cells) else ""
            lines = textwrap.wrap(text, width) or [""]
            wrapped.append(lines)
            height = max(height, len(lines))
        painted = []
        for line_index in range(height):
            pieces = []
            for index, width in enumerate(widths):
                piece = wrapped[index][line_index] if line_index < len(wrapped[index]) else ""
                pieces.append(piece.ljust(width))
            painted.append("  ".join(pieces).rstrip())
        return painted

    lines = paint(titles)
    lines.append(rule)
    for row in rendered:
        lines.extend(paint(row))
    return "\n".join(lines)


def render_docx(report: Report, path: Path) -> None:
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.shared import Mm, Pt

    document = Document()
    section = document.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Mm(297)
    section.page_height = Mm(210)
    section.left_margin = Mm(12)
    section.right_margin = Mm(12)
    section.top_margin = Mm(12)
    section.bottom_margin = Mm(14)
    footer = section.footer.paragraphs[0]
    footer.text = "mep-drill-planner mounting-element statistics  "
    _add_page_field(footer)

    for block in report.blocks:
        if block.kind == "h1":
            document.add_heading(block.text, level=1)
        elif block.kind == "h2":
            document.add_heading(block.text, level=2)
        elif block.kind == "p":
            document.add_paragraph(block.text)
        elif block.kind == "table":
            _docx_table(document, block.headers, block.rows, Pt)

    document.save(path)


def _add_page_field(paragraph) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instruction)
    run._r.append(end)


def _docx_table(document, headers: list, rows: list, pt) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    table = document.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    for index, header in enumerate(headers):
        _set_docx_cell(table.rows[0].cells[index], str(header), pt, bold=True)
    header_row = table.rows[0]._tr
    properties = header_row.get_or_add_trPr()
    marker = OxmlElement("w:tblHeader")
    marker.set(qn("w:val"), "true")
    properties.append(marker)
    for row_index, row in enumerate(rows):
        for col_index in range(len(headers)):
            value = row[col_index] if col_index < len(row) else ""
            _set_docx_cell(table.rows[row_index + 1].cells[col_index], fmt(value), pt, bold=False)
    document.add_paragraph("")


def _set_docx_cell(cell, text: str, pt, bold: bool) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    run = paragraph.add_run(text)
    run.bold = bold
    run.font.size = pt(8)
    run.font.name = "Arial"


def render_pdf(report: Report, path: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    pdfmetrics.registerFont(TTFont("DejaVu", regular))
    pdfmetrics.registerFont(TTFont("DejaVuBold", bold))
    body = ParagraphStyle(
        "body",
        fontName="DejaVu",
        fontSize=9,
        leading=12,
        alignment=TA_LEFT,
        spaceAfter=4,
    )
    heading = ParagraphStyle(
        "heading",
        fontName="DejaVuBold",
        fontSize=13,
        leading=16,
        spaceBefore=8,
        spaceAfter=4,
        textColor=colors.HexColor("#1F4E79"),
    )
    title = ParagraphStyle(
        "title",
        fontName="DejaVuBold",
        fontSize=16,
        leading=20,
        spaceAfter=6,
        textColor=colors.HexColor("#1F4E79"),
    )
    cell_style = ParagraphStyle("cell", fontName="DejaVu", fontSize=7, leading=9)
    head_style = ParagraphStyle("head", fontName="DejaVuBold", fontSize=7, leading=9, textColor=colors.white)

    story = []
    for block in report.blocks:
        if block.kind == "h1":
            story.append(Paragraph(_xml(block.text), title))
        elif block.kind == "h2":
            story.append(Paragraph(_xml(block.text), heading))
        elif block.kind == "p":
            story.append(Paragraph(_xml(block.text), body))
        elif block.kind == "table":
            story.append(_pdf_table(block.headers, block.rows, cell_style, head_style, colors))
            story.append(Spacer(1, 3 * mm))

    def footer(canvas, doc):
        canvas.saveState()
        width, _height = canvas._pagesize
        canvas.setFont("DejaVu", 8)
        canvas.drawString(12 * mm, 8 * mm, "mep-drill-planner mounting-element statistics")
        canvas.drawRightString(width - 12 * mm, 8 * mm, str(doc.page))
        canvas.restoreState()

    document = SimpleDocTemplate(
        str(path),
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=14 * mm,
        title="Mounting-element statistics",
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)


def _xml(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def _pdf_table(headers, rows, cell_style, head_style, colors):
    from reportlab.platypus import Paragraph, Table, TableStyle

    usable = 273 * 1  # millimetres converted below by the caller via points
    # landscape A4 content width: 297 - 24 mm = 273 mm = 773 points approximately
    usable_points = 273 * 72 / 25.4
    titles = [str(header) for header in headers]
    rendered = [[fmt(value) for value in row] for row in rows]
    weights = []
    for index, title in enumerate(titles):
        samples = [min(48, len(title))]
        for row in rendered[:6]:
            if index < len(row):
                samples.append(min(48, len(row[index])))
        weights.append(max(6, max(samples)))
    scale = usable_points / sum(weights)
    widths = [weight * scale for weight in weights]
    data = [[Paragraph(_xml(title), head_style) for title in titles]]
    for row in rendered:
        cells = []
        for index in range(len(titles)):
            text = row[index] if index < len(row) else ""
            cells.append(Paragraph(_xml(text), cell_style))
        data.append(cells)
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.2, colors.HexColor("#B0B8C1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FB")]),
            ]
        )
    )
    return table


def render_xlsx(report: Report, path: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    workbook = Workbook()
    contents = workbook.active
    contents.title = "Contents"
    narrative = workbook.create_sheet("Narrative")
    header_fill = PatternFill("solid", fgColor="1F4E79")
    header_font = Font(bold=True, color="FFFFFF", name="Calibri")
    title_font = Font(bold=True, size=16, color="1F4E79", name="Calibri")
    section_font = Font(bold=True, size=13, color="1F4E79", name="Calibri")
    wrap = Alignment(wrap_text=True, vertical="top")
    used = {"Contents", "Narrative"}
    for column, title in enumerate(("sheet", "section", "columns", "rows"), start=1):
        cell = contents.cell(1, column, title)
        cell.fill = header_fill
        cell.font = header_font
    contents_row = 2
    row_index = 1
    pending_title = "Table"
    table_number = 0
    for block in report.blocks:
        if block.kind == "h1":
            narrative.cell(row_index, 1, block.text).font = title_font
            row_index += 2
        elif block.kind == "h2":
            narrative.cell(row_index, 1, block.text).font = section_font
            pending_title = block.text
            row_index += 1
        elif block.kind == "p":
            cell = narrative.cell(row_index, 1, block.text)
            cell.alignment = wrap
            row_index += 2
        elif block.kind == "table":
            table_number += 1
            sheet_title = _sheet_name(f"{table_number:02d} {pending_title}", used)
            sheet = workbook.create_sheet(sheet_title)
            _write_sheet(sheet, pending_title, block.headers, block.rows, header_fill, header_font, wrap)
            contents.cell(contents_row, 1, sheet_title)
            contents.cell(contents_row, 2, pending_title)
            contents.cell(contents_row, 3, ", ".join(str(header) for header in block.headers))
            contents.cell(contents_row, 4, len(block.rows))
            contents_row += 1
            row_index += 1
    narrative.column_dimensions["A"].width = 120
    for column, width in enumerate((36, 48, 80, 12), start=1):
        contents.column_dimensions[get_column_letter(column)].width = width
    contents.freeze_panes = "A2"
    contents.auto_filter.ref = f"A1:D{max(1, contents_row - 1)}"
    workbook.save(path)


def _sheet_name(title: str, used: set[str]) -> str:
    cleaned = "".join(character for character in title if character not in "[]:*?/\\")
    cleaned = cleaned.strip() or "Table"
    base = cleaned[:31]
    name = base
    suffix = 2
    while name in used:
        tail = f" {suffix}"
        name = base[: 31 - len(tail)] + tail
        suffix += 1
    used.add(name)
    return name


def _write_sheet(sheet, title, headers, rows, header_fill, header_font, wrap) -> None:
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    sheet["A1"] = title
    sheet["A1"].font = Font(bold=True, size=14, color="1F4E79", name="Calibri")
    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(1, len(headers)))
    for index, header in enumerate(headers, start=1):
        cell = sheet.cell(3, index, str(header))
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = wrap
    for row_index, row in enumerate(rows, start=4):
        for col_index in range(1, len(headers) + 1):
            value = row[col_index - 1] if col_index - 1 < len(row) else ""
            cell = sheet.cell(row_index, col_index)
            if isinstance(value, bool) or value == "":
                cell.value = fmt(value) if value != "" else None
            elif isinstance(value, (int, float)):
                cell.value = value
                if isinstance(value, float):
                    cell.number_format = "0.###"
            else:
                cell.value = str(value)
            cell.alignment = wrap
    sheet.auto_filter.ref = f"A3:{get_column_letter(max(1, len(headers)))}{max(3, 3 + len(rows))}"
    sheet.freeze_panes = "A4"
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToPage = True
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    for index in range(1, len(headers) + 1):
        longest = len(str(headers[index - 1]))
        for row in rows[:40]:
            if index - 1 < len(row):
                longest = max(longest, min(48, len(fmt(row[index - 1]))))
        sheet.column_dimensions[get_column_letter(index)].width = longest + 2
    sheet.row_dimensions[1].height = 22


def write_reports(report: Report, out_dir: Path | None = None) -> dict[str, Path]:
    """Write md, txt, docx, pdf and xlsx. Returns the paths."""
    destination = out_dir or OUT_DIR
    destination.mkdir(parents=True, exist_ok=True)
    stem = destination / "mounting_elements_statistics"
    paths = {
        "md": stem.with_suffix(".md"),
        "txt": stem.with_suffix(".txt"),
        "docx": stem.with_suffix(".docx"),
        "pdf": stem.with_suffix(".pdf"),
        "xlsx": stem.with_suffix(".xlsx"),
    }
    paths["md"].write_text(render_markdown(report), encoding="utf-8")
    paths["txt"].write_text(render_text(report), encoding="utf-8")
    render_docx(report, paths["docx"])
    render_pdf(report, paths["pdf"])
    render_xlsx(report, paths["xlsx"])
    return paths


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT_DIR, help="Directory for the five report files")
    args = parser.parse_args(argv)
    report = build_report()
    paths = write_reports(report, args.out)
    summary = report.summary
    print(
        "products {product_count}, elements {element_count}, "
        "matched {matched_elements}, assumption {assumption_elements}, "
        "unmatched {unmatched_elements}".format(**summary)
    )
    for kind, path in paths.items():
        print(f"{kind}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
