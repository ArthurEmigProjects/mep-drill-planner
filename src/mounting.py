"""Load the mounting-element database and match it to an MEP element.

An element is a plain dict with at least ``kind`` and a size. Inventory groups
written by ``src.inventory_elements`` are valid input. The mapper returns the
products whose published size window contains that size, plus rods and
concrete anchors that share the product's connection thread.

Spacing is not stored on the products. Where a cited table has a row within
0.5 mm of a pipe outside diameter, or an exact duct size, that guidance is
attached separately and always carries the material assumption.

Run a coverage report from the repo root:

    python -m src.mounting
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT / "data" / "mounting_elements" / "products.json"
SCHEMA_PATH = ROOT / "data" / "mounting_elements" / "schema.json"
INVENTORY_PATH = ROOT / "data" / "inventory" / "zenodo_duplex_mountable.json"

# Floats from inch fractions (22.225) still have to fall inside integer windows
# such as 20–24. Two hundredths of a millimetre only absorbs binary rounding.
RANGE_TOLERANCE_MM = 0.02
# Copper-spacing rows are metric outside diameters. 22.225 mm is 0.225 mm from
# the 22 mm row; 15.875 mm is 0.875 mm from 15 mm and is not attached.
SPACING_TOLERANCE_MM = 0.5
NOMINAL_DUCT_TOLERANCE_MM = 1.0

ELEMENT_TYPES = {
    "pipe",
    "duct_round",
    "duct_rectangular",
    "duct_flex",
    "radiator",
    "threaded_rod",
    "channel",
    "ceiling_anchor",
}
PIPE_KINDS = {"pipe_segment", "pipe_fitting", "pipe_accessory"}
SIZED_MATCHES = {"published_range", "nominal_type"}

_REQUIRED_PRODUCT = (
    "id",
    "manufacturer",
    "name",
    "article_number",
    "element_types",
    "role",
    "outer_diameter_mm",
    "nominal_diameter_mm",
    "connection_threads",
    "load_rating",
    "max_support_spacing",
    "anchor",
    "assumptions",
    "notes",
    "sources",
)


class DatabaseError(ValueError):
    """The mounting database file is missing a required field or contradicts itself."""


def load_database(path: Path | None = None) -> dict:
    """Read and check the product database. Raises DatabaseError on a bad file."""
    database_path = Path(path) if path is not None else DATABASE_PATH
    if not database_path.is_file():
        raise DatabaseError(f"Mounting database not found: {database_path}")
    try:
        data = json.loads(database_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatabaseError(f"Mounting database is not valid JSON: {exc}") from exc
    _validate(data)
    return data


def _validate(data: dict) -> None:
    if not isinstance(data, dict):
        raise DatabaseError("Database root must be an object.")
    for key in ("schema_version", "products", "guidance"):
        if key not in data:
            raise DatabaseError(f"Database is missing {key}.")
    if not isinstance(data["products"], list) or not data["products"]:
        raise DatabaseError("Database products must be a non-empty list.")
    seen = set()
    for product in data["products"]:
        if not isinstance(product, dict):
            raise DatabaseError("Each product must be an object.")
        missing = [key for key in _REQUIRED_PRODUCT if key not in product]
        if missing:
            raise DatabaseError(f"Product {product.get('id')!r} is missing {missing}.")
        identifier = product["id"]
        if not identifier or identifier in seen:
            raise DatabaseError(f"Duplicate or empty product id {identifier!r}.")
        seen.add(identifier)
        if product["role"] not in {"primary", "companion"}:
            raise DatabaseError(f"{identifier} has role {product['role']!r}.")
        types = product["element_types"]
        if not types or any(item not in ELEMENT_TYPES for item in types):
            raise DatabaseError(f"{identifier} has element_types {types!r}.")
        window = product["outer_diameter_mm"]
        if window is not None:
            if window["min"] > window["max"]:
                raise DatabaseError(f"{identifier} has a reversed diameter window.")
        _require_sources(identifier, product["sources"])
        load = product["load_rating"]
        if load is not None and (not load.get("unit") or load.get("value") is None):
            raise DatabaseError(f"{identifier} load_rating needs a value and a unit.")
    guidance_ids = set()
    for item in data["guidance"]:
        if item["id"] in guidance_ids:
            raise DatabaseError(f"Duplicate guidance id {item['id']!r}.")
        guidance_ids.add(item["id"])
        _require_sources(item["id"], item["sources"])


def _require_sources(identifier: str, sources: list) -> None:
    if not sources:
        raise DatabaseError(f"{identifier} has no sources.")
    for source in sources:
        url = source.get("url") or ""
        if not url.startswith("http"):
            raise DatabaseError(f"{identifier} source {url!r} is not an http URL.")


def sizes_of(element: dict) -> list[dict]:
    """Sizes that each need their own support product.

    Pipe fittings contribute every connected outside diameter. A reducer is
    covered only when each of those diameters has a clamp.
    """
    kind = element.get("kind")
    if kind in PIPE_KINDS:
        diameters = list(element.get("outer_diameters_mm") or [])
        if not diameters and element.get("outer_diameter_mm") is not None:
            diameters = [element["outer_diameter_mm"]]
        return [{"product_type": "pipe", "outer_diameter_mm": value} for value in diameters]
    if kind == "duct_segment" and element.get("shape") == "rectangular":
        return [
            {
                "product_type": "duct_rectangular",
                "width_mm": element.get("width_mm"),
                "height_mm": element.get("height_mm"),
            }
        ]
    if kind == "duct_segment" and element.get("outer_diameter_mm") is not None:
        return [
            {"product_type": "duct_round", "outer_diameter_mm": element["outer_diameter_mm"]}
        ]
    if kind == "duct_flex":
        return [
            {
                "product_type": "duct_flex",
                "mesh_minor_axis_mm": element.get("mesh_minor_axis_mm"),
            }
        ]
    if kind in {"duct_fitting", "duct_accessory"}:
        sizes = []
        for item in element.get("connected_duct_sizes") or []:
            if item.get("shape") == "round" and item.get("outer_diameter_mm") is not None:
                sizes.append(
                    {"product_type": "duct_round", "outer_diameter_mm": item["outer_diameter_mm"]}
                )
            elif item.get("width_mm") is not None and item.get("height_mm") is not None:
                sizes.append(
                    {
                        "product_type": "duct_rectangular",
                        "width_mm": item["width_mm"],
                        "height_mm": item["height_mm"],
                    }
                )
        return sizes
    if kind == "radiator":
        return [{"product_type": "radiator", "bbox_mm": element.get("bbox_mm")}]
    return []


def _in_range(value, window: dict | None) -> bool:
    if value is None or window is None:
        return False
    return window["min"] - RANGE_TOLERANCE_MM <= value <= window["max"] + RANGE_TOLERANCE_MM


def _match_quality(product: dict, size: dict) -> str | None:
    if product.get("role") != "primary":
        return None
    if size["product_type"] not in product["element_types"]:
        return None
    product_type = size["product_type"]
    if product_type in {"pipe", "duct_round"}:
        diameter = size.get("outer_diameter_mm")
        if _in_range(diameter, product.get("outer_diameter_mm")):
            return "published_range"
        nominal = product.get("nominal_diameter_mm")
        if (
            product_type == "duct_round"
            and diameter is not None
            and nominal is not None
            and abs(diameter - nominal) <= NOMINAL_DUCT_TOLERANCE_MM
        ):
            return "nominal_type"
        return None
    if product_type == "duct_flex":
        if _in_range(size.get("mesh_minor_axis_mm"), product.get("outer_diameter_mm")):
            return "published_range"
        return None
    if product_type in {"duct_rectangular", "radiator"}:
        # These products publish an application, not a dimension window.
        return "kind_only"
    return None


def _public_product(product: dict, quality: str, why: str) -> dict:
    return {
        "id": product["id"],
        "manufacturer": product["manufacturer"],
        "product_line": product["product_line"],
        "name": product["name"],
        "article_number": product["article_number"],
        "element_types": list(product["element_types"]),
        "connection_threads": list(product["connection_threads"]),
        "outer_diameter_mm": product["outer_diameter_mm"],
        "nominal_diameter_mm": product["nominal_diameter_mm"],
        "load_rating": product["load_rating"],
        "max_support_spacing": product["max_support_spacing"],
        "anchor": product["anchor"],
        "match_quality": quality,
        "why": why,
    }


def _why(product: dict, size: dict, quality: str) -> str:
    if quality == "published_range":
        window = product["outer_diameter_mm"]
        diameter = size.get("outer_diameter_mm", size.get("mesh_minor_axis_mm"))
        return (
            f"{diameter:g} mm is inside the published clamping range "
            f"{window['min']:g}–{window['max']:g} mm."
        )
    if quality == "nominal_type":
        return (
            f"Modeled diameter {size['outer_diameter_mm']:g} mm matches catalogue "
            f"type {product['nominal_diameter_mm']:g} mm."
        )
    if size["product_type"] == "duct_rectangular":
        return (
            "Product is specified for rectangular ducts. "
            f"This duct is {size.get('width_mm')} × {size.get('height_mm')} mm; "
            "the datasheet does not publish a size window."
        )
    return "Product is specified for this element type and does not publish a size window."


def _spacing_for(sizes: list[dict], guidance: list[dict]) -> tuple[list[dict], list[str]]:
    attached = []
    assumptions = []
    for item in guidance:
        if item["id"] == "copper-tube-spacing-din1988-2-as-cited":
            for size in sizes:
                if size["product_type"] != "pipe":
                    continue
                diameter = size.get("outer_diameter_mm")
                if diameter is None:
                    continue
                for row in item["rows"]:
                    if abs(diameter - row["outer_diameter_mm"]) <= SPACING_TOLERANCE_MM:
                        attached.append(
                            {
                                "guidance_id": item["id"],
                                "outer_diameter_mm": diameter,
                                "table_outer_diameter_mm": row["outer_diameter_mm"],
                                "horizontal_m": row["horizontal_m"],
                                "vertical_m": None,
                                "sources": item["sources"],
                            }
                        )
                        if abs(diameter - row["outer_diameter_mm"]) > 0.02:
                            assumptions.append(
                                f"Spacing row {row['outer_diameter_mm']:g} mm "
                                f"({row['horizontal_m']:g} m horizontal) is attached to modeled "
                                f"OD {diameter:g} mm, which is within {SPACING_TOLERANCE_MM:g} mm. "
                                "The table is for copper and stainless tube; the IFC material is unnamed."
                            )
                        else:
                            assumptions.append(
                                f"Spacing row {row['outer_diameter_mm']:g} mm "
                                f"({row['horizontal_m']:g} m horizontal) matches the modeled OD. "
                                "Applying it still assumes copper or stainless tube; the IFC material is unnamed."
                            )
        elif item["id"] == "lindab-duct-suspension-spacing":
            for size in sizes:
                for row in item["rows"]:
                    if not row.get("table_row"):
                        continue
                    if size["product_type"] == "duct_round" and row.get("shape") == "round":
                        diameter = size.get("outer_diameter_mm")
                        if diameter is not None and row.get("diameter_mm") == diameter:
                            attached.append(
                                {
                                    "guidance_id": item["id"],
                                    "horizontal_m": row["horizontal_m"],
                                    "size": f"Ø{diameter:g} mm",
                                    "sources": item["sources"],
                                }
                            )
                    if size["product_type"] == "duct_rectangular" and row.get("shape") == "rectangular":
                        if (
                            row.get("width_mm") == size.get("width_mm")
                            and row.get("height_mm") == size.get("height_mm")
                        ):
                            attached.append(
                                {
                                    "guidance_id": item["id"],
                                    "horizontal_m": row["horizontal_m"],
                                    "size": f"{size['width_mm']:g}×{size['height_mm']:g} mm",
                                    "sources": item["sources"],
                                }
                            )
            rectangular = [size for size in sizes if size["product_type"] == "duct_rectangular"]
            tabulated = {
                (row.get("width_mm"), row.get("height_mm"))
                for row in item["rows"]
                if row.get("table_row") and row.get("shape") == "rectangular"
            }
            for size in rectangular:
                key = (size.get("width_mm"), size.get("height_mm"))
                if key not in tabulated:
                    assumptions.append(
                        "Lindab's rectangular size table does not list "
                        f"{size.get('width_mm')}×{size.get('height_mm')} mm. "
                        "The same section states a 2.4 m maximum for horizontal rectangular duct, "
                        "which is not a size-table row and is not applied as a spacing value."
                    )
        elif item["id"] == "en-12236-duct-support-strength":
            if any(size["product_type"].startswith("duct_") for size in sizes):
                attached.append(
                    {
                        "guidance_id": item["id"],
                        "horizontal_m": None,
                        "requirement": item["notes"],
                        "sources": item["sources"],
                    }
                )
    return attached, assumptions


def _companions(database: dict, threads: set[str], want_channel: bool, substrate: str | None) -> tuple[list[dict], list[str]]:
    found = []
    assumptions = []
    for product in database["products"]:
        if product["role"] != "companion":
            continue
        types = set(product["element_types"])
        product_threads = set(product["connection_threads"])
        if "threaded_rod" in types and product_threads & threads:
            found.append(_public_product(product, "companion", "Connection thread matches the clamp or hanger."))
        elif "ceiling_anchor" in types and substrate == "concrete" and product_threads & threads:
            found.append(
                _public_product(
                    product,
                    "companion",
                    "Concrete hammer-set anchor whose internal thread matches the rod.",
                )
            )
        elif "channel" in types and want_channel:
            found.append(
                _public_product(
                    product,
                    "companion",
                    "Strut channel used as a trapeze rail under a rectangular duct.",
                )
            )
            assumptions.append(
                "Hilti MQ-41/3 is attached as a trapeze rail. ETA-18/0119 fastens this "
                "channel through its back holes with an M12 bolt, which is not the M8/M10 "
                "thread of the LUW hanger."
            )
    if substrate == "concrete" and threads and not any(
        "ceiling_anchor" in item["element_types"] for item in found
    ):
        missing = ", ".join(sorted(threads))
        assumptions.append(
            f"No concrete anchor in the database has internal thread {missing}."
        )
    if substrate and substrate != "concrete":
        assumptions.append(
            f"Substrate {substrate!r} does not use the concrete hammer-set anchors in this database."
        )
    return found, assumptions


def _gap_text(kind: str | None, sizes: list[dict]) -> str:
    if kind == "duct_flex":
        minor = sizes[0].get("mesh_minor_axis_mm") if sizes else None
        if minor is None:
            return (
                "Flex-duct diameter could not be recovered from the mesh, "
                "and no flex-duct hanger is in the database."
            )
        return (
            f"No product has a clamping range covering flex-duct mesh minor axis {minor:g} mm. "
            "Sikla PLU type 150 is a spiral-seam clamp for nominal 150 mm and is not applied."
        )
    if kind == "air_terminal":
        return "No diffuser or grille fixing is in the database."
    if kind == "sanitary_fixture":
        return "No sanitary carrier or fixture bracket is in the database."
    if kind == "water_heater":
        return "No water-heater support is in the database. The proxy is a floor-standing appliance, not a suspended pipe."
    if kind == "stove":
        return "No stove or boiler support is in the database. The element is floor-standing equipment."
    if kind == "air_handling_unit":
        return "No air-handling-unit frame is in the database."
    if kind in PIPE_KINDS and not sizes:
        return "No outside diameter was recovered, so no pipe clamp can be selected."
    if kind in {"duct_fitting", "duct_accessory"} and not sizes:
        return "No connected duct size was recovered, so no duct hanger can be selected."
    if sizes:
        bits = []
        for size in sizes:
            if size["product_type"] == "pipe":
                bits.append(f"OD {size.get('outer_diameter_mm')} mm")
            elif size["product_type"] == "duct_round":
                bits.append(f"round duct {size.get('outer_diameter_mm')} mm")
            elif size["product_type"] == "duct_rectangular":
                bits.append(f"{size.get('width_mm')}×{size.get('height_mm')} mm")
        return "No published product range covers " + ", ".join(bits) + "."
    return "No mounting product in the database applies to this element type."


def feasible_mountings(
    element: dict,
    database: dict | None = None,
    *,
    substrate: str | None = None,
) -> dict:
    """Return mounting products that fit ``element``.

    ``element`` needs ``kind`` plus size fields (``outer_diameter_mm`` or
    ``outer_diameters_mm``, duct ``width_mm`` / ``height_mm``, or a radiator
    ``bbox_mm``). ``substrate`` is optional. Concrete anchors are included only
    when it is ``"concrete"``.

    Status is ``matched`` when every required size hits a published clamping
    range or a catalogue nominal diameter, ``matched_with_assumption`` when the
    only hits are kind-level products with no size window, and ``unmatched``
    when any required size has no product.
    """
    data = database if database is not None else load_database()
    kind = element.get("kind")
    sizes = sizes_of(element)
    matches = []
    assumptions = []
    size_results = []
    threads: set[str] = set()
    want_channel = False
    all_sized = bool(sizes)
    any_kind_only = False
    for size in sizes:
        hits = []
        for product in data["products"]:
            quality = _match_quality(product, size)
            if quality is None:
                continue
            hits.append((product, quality))
        sized_hits = [hit for hit in hits if hit[1] in SIZED_MATCHES]
        chosen = sized_hits or hits
        if not chosen:
            all_sized = False
        if chosen and not sized_hits:
            any_kind_only = True
            all_sized = False
        for product, quality in chosen:
            public = _public_product(product, quality, _why(product, size, quality))
            if public["id"] not in {item["id"] for item in matches}:
                matches.append(public)
            threads.update(product["connection_threads"])
            if quality == "kind_only":
                assumptions.extend(product["assumptions"])
            if size["product_type"] == "duct_rectangular":
                want_channel = True
        size_results.append(
            {
                "size": size,
                "product_ids": [product["id"] for product, _quality in chosen],
            }
        )

    if kind in {"pipe_fitting", "pipe_accessory"} and matches:
        assumptions.append(
            "Clamp size is the connected pipe's outside diameter. "
            "The cited pipe-support tables place the clamp on the tube, not on the fitting or valve."
        )
    if kind in {"duct_fitting", "duct_accessory"} and matches:
        assumptions.append(
            "Hanger size is taken from the connected duct. The fitting or damper is assumed to be carried by that duct support."
        )

    guidance, spacing_assumptions = _spacing_for(sizes, data["guidance"])
    # Spacing notes are only useful once a support actually matches.
    if matches:
        assumptions.extend(spacing_assumptions)
    else:
        guidance = [item for item in guidance if item["guidance_id"] == "en-12236-duct-support-strength"]

    companions, companion_notes = _companions(data, threads, want_channel and bool(matches), substrate)
    if matches:
        assumptions.extend(companion_notes)

    if not sizes or not matches or any(not row["product_ids"] for row in size_results):
        status = "unmatched"
    elif all_sized and not any_kind_only:
        status = "matched"
    else:
        status = "matched_with_assumption"

    # Unique assumption lines, stable order.
    unique_assumptions = []
    for note in assumptions:
        if note not in unique_assumptions:
            unique_assumptions.append(note)

    return {
        "kind": kind,
        "status": status,
        "matches": matches if status != "unmatched" else [],
        "rejected_partial": matches if status == "unmatched" else [],
        "companions": companions if status != "unmatched" else [],
        "guidance": guidance if status != "unmatched" else [],
        "assumptions": unique_assumptions if status != "unmatched" else [],
        "gap": None if status != "unmatched" else _gap_text(kind, sizes),
    }


def coverage_report(inventory: dict, database: dict | None = None) -> dict:
    """Match every inventory group and roll the result up by model."""
    data = database if database is not None else load_database()
    models = {}
    gaps = []
    for model_name, model in inventory["models"].items():
        groups = []
        counts = {"matched": 0, "matched_with_assumption": 0, "unmatched": 0}
        element_counts = {"matched": 0, "matched_with_assumption": 0, "unmatched": 0}
        for group in model["groups"]:
            result = feasible_mountings(group, data)
            status = result["status"]
            counts[status] += 1
            element_counts[status] += group["count"]
            row = {
                "kind": group["kind"],
                "size_label": group["size_label"],
                "count": group["count"],
                "status": status,
                "product_ids": [item["id"] for item in result["matches"]],
                "assumptions": result["assumptions"],
                "gap": result["gap"],
            }
            groups.append(row)
            if status == "unmatched":
                gaps.append(
                    {
                        "model": model_name,
                        "kind": group["kind"],
                        "size_label": group["size_label"],
                        "count": group["count"],
                        "gap": result["gap"],
                    }
                )
        models[model_name] = {
            "file": model["file"],
            "groups": groups,
            "summary": {
                "group_count": len(groups),
                "groups": counts,
                "elements": element_counts,
            },
        }
    return {
        "substrate_assumed_for_anchors": None,
        "note": (
            "Concrete anchors are not counted in this coverage. The architecture "
            "model's ceilings are gypsum on metal stud under timber joists, so a "
            "concrete hammer-set anchor does not match the soffit. Pass "
            "substrate='concrete' to feasible_mountings when the soffit is concrete."
        ),
        "models": models,
        "gaps": gaps,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=INVENTORY_PATH)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data" / "inventory" / "coverage.json",
    )
    args = parser.parse_args(argv)
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    report = coverage_report(inventory)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    for name, model in report["models"].items():
        summary = model["summary"]
        print(
            f"{name}: groups {summary['groups']} elements {summary['elements']}"
        )
    print(f"gaps: {len(report['gaps'])} → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
