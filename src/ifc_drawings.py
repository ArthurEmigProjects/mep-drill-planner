"""Write floor plans, sections and 3D views of an IFC clash check.

The sheets use the same geometry as the hanger clash test: pipe and duct
centre-lines, other services, and beams, members and columns. A vertical
pipe or duct is fixed to the nearest wall, such as a shaft wall, and that
wall is drawn beside the riser. Slabs and ceilings stay out. A red marker
is a hanger whose fixing still hits something.

Run from the repo root:

    python -m src.ifc_drawings examples/zenodo-duplex-piping.ifc --obstacles examples/Architecture.ifc --out examples/out/zenodo-duplex-piping-views.pdf

Each extra IFC is drawn with the services. Its own runs are not hung.
"""

from __future__ import annotations

import math
from pathlib import Path

from src.mounting_points import (
    MAX_ROD_LENGTH_M,
    _clash_name,
    load_clash_context,
    plan_mounting_points,
)

# Points per millimetre. 1:100 means one metre is 10 mm on the sheet.
_MM = 72 / 25.4
_SCALE_STEPS = (5, 10, 20, 25, 50, 100, 125, 200, 250, 500, 1000, 2000, 5000, 10000)

_CATEGORY_ORDER = {"wall": 0, "structure": 1, "service": 2, "duct": 3, "pipe": 4}
_WALL_DRAW_PAD_M = 0.6


def drawable_from_obstacle(obstacle: dict) -> dict | None:
    """Turn one clash obstacle into a line or a box the sheets can draw."""
    category = obstacle.get("category")
    if category is None:
        category = "pipe" if obstacle.get("shape") == "cylinder" else "service"
    base = {
        "category": category,
        "element_id": obstacle.get("element_id"),
        "source": obstacle.get("source"),
    }
    if obstacle.get("shape") == "cylinder":
        start = obstacle.get("start")
        end = obstacle.get("end")
        if not start or not end:
            return None
        base.update(
            kind="segment",
            start=(float(start[0]), float(start[1]), float(start[2])),
            end=(float(end[0]), float(end[1]), float(end[2])),
            radius_m=float(obstacle.get("radius_m") or 0.02),
        )
        return base
    low = obstacle.get("min")
    high = obstacle.get("max")
    if not low or not high:
        return None
    base.update(
        kind="box",
        min=(float(low[0]), float(low[1]), float(low[2])),
        max=(float(high[0]), float(high[1]), float(high[2])),
    )
    return base


def build_scene(service: Path, others: list[Path] | None = None) -> dict:
    """Load every IFC in the clash check and place the hangers.

    ``others`` add beams and services that can block a rod. They do not add
    runs. Storey elevations, when the files have them, become the floor-plan
    sheets.
    """
    segments, obstacles, models = load_clash_context(service, others)
    plan = plan_mounting_points(segments, obstacles, source=service.name)
    drawables = []
    for obstacle in obstacles:
        if obstacle.get("category") == "wall":
            continue
        item = drawable_from_obstacle(obstacle)
        if item is not None:
            drawables.append(item)
    drawables.extend(host_wall_drawables(obstacles, plan["runs"]))
    hangers = [_hanger_from_point(point) for point in plan["points"]]
    scene = {
        "models": list(models),
        "storeys": read_storeys([service, *(others or [])]),
        "drawables": drawables,
        "hangers": hangers,
        "runs": {run["id"]: run for run in plan["runs"]},
        "clash_count": sum(1 for hanger in hangers if not hanger["clear"]),
        "hanger_count": len(hangers),
        "rod_length_m": MAX_ROD_LENGTH_M,
    }
    scene["bounds"] = scene_bounds(scene)
    return scene


def read_storeys(paths: list[Path]) -> list[dict]:
    """Building storeys from each IFC, one row per elevation."""
    try:
        import ifcopenshell
    except ImportError:
        return []
    found = []
    seen: list[float] = []
    for path in paths:
        if not path.is_file():
            continue
        model = ifcopenshell.open(str(path))
        schema = ifcopenshell.schema_by_name(model.schema)
        names = {entity.name() for entity in schema.entities()}
        if "IfcBuildingStorey" not in names:
            continue
        for storey in model.by_type("IfcBuildingStorey"):
            if storey.Elevation is None:
                continue
            elevation = round(float(storey.Elevation), 3)
            if any(abs(elevation - other) < 0.05 for other in seen):
                continue
            seen.append(elevation)
            found.append(
                {
                    "name": storey.Name or "Storey",
                    "elevation_m": elevation,
                    "source": path.name,
                }
            )
    found.sort(key=lambda row: row["elevation_m"])
    return found


def scene_bounds(scene: dict) -> dict:
    points = []
    for item in scene.get("drawables") or []:
        if item.get("category") == "wall":
            continue
        if item["kind"] == "segment":
            points.extend((item["start"], item["end"]))
        else:
            points.extend((item["min"], item["max"]))
    for hanger in scene.get("hangers") or []:
        points.append((hanger["x"], hanger["y"], hanger["z"]))
    if not points:
        return {"min": (0.0, 0.0, 0.0), "max": (1.0, 1.0, 1.0)}
    return {
        "min": tuple(min(point[index] for point in points) for index in range(3)),
        "max": tuple(max(point[index] for point in points) for index in range(3)),
    }


def level_bands(scene: dict) -> list[dict]:
    """Vertical slices for the floor plans.

    Storey elevations are used when any drawn element sits on them. Otherwise
    the model is split where the services jump more than 1.5 m, or kept as
    one sheet.
    """
    zmin, zmax = _z_extent(scene)
    storeys = [
        storey
        for storey in scene.get("storeys") or []
        if isinstance(storey.get("elevation_m"), (int, float))
    ]
    storeys.sort(key=lambda storey: storey["elevation_m"])
    if storeys:
        bands = []
        for index, storey in enumerate(storeys):
            z0 = float(storey["elevation_m"])
            z1 = float(storeys[index + 1]["elevation_m"]) if index + 1 < len(storeys) else zmax + 1.0
            if z1 <= z0 + 1e-6:
                continue
            bands.append(
                {
                    "name": storey.get("name") or f"Level {index + 1}",
                    "z0": z0,
                    "z1": z1,
                    "first": index == 0,
                    "last": index == len(storeys) - 1,
                }
            )
        if bands and any(band_has_content(scene, band) for band in bands):
            return bands
    return _cluster_bands(scene, zmin, zmax)


def band_has_content(scene: dict, band: dict) -> bool:
    for item in scene.get("drawables") or []:
        if _overlaps_band(_item_z(item), band):
            return True
    for hanger in scene.get("hangers") or []:
        if _overlaps_band((hanger["z"], hanger["z"]), band):
            return True
    return False


def pages_for_scene(scene: dict) -> list[dict]:
    """Sheet list: cover, one plan per level, two building sections, clash sections, 3D."""
    bounds = scene.get("bounds") or scene_bounds(scene)
    scene = {**scene, "bounds": bounds}
    pages: list[dict] = [{"kind": "cover", "title": "Clash drawings"}]
    bands = [band for band in level_bands(scene) if band_has_content(scene, band)]
    if not bands and (scene.get("drawables") or scene.get("hangers")):
        zmin, zmax = _z_extent(scene)
        bands = [
            {
                "name": "All levels",
                "z0": zmin - 1.0,
                "z1": zmax + 1.0,
                "first": True,
                "last": True,
            }
        ]
    for band in bands:
        pages.append({"kind": "plan", "title": f"{band['name']} · floor plan", "band": band})
    horizontal = _long_axis(bounds)
    for kind, axis in (("Long section", horizontal), ("Cross section", "y" if horizontal == "x" else "x")):
        plane = building_section_plane(scene, axis)
        cut = "Y" if axis == "x" else "X"
        value = plane["origin"][1] if axis == "x" else plane["origin"][0]
        pages.append(
            {
                "kind": "section",
                "title": f"{kind} · cut {cut} = {value:.2f} m",
                "axis": axis,
                "plane": plane,
            }
        )
    for hanger in clash_hangers(scene):
        pages.append(
            {
                "kind": "clash_section",
                "title": f"{hanger['id']} · section",
                "hanger_id": hanger["id"],
            }
        )
    pages.append({"kind": "axon", "title": "3D views", "crop": False})
    if scene.get("clash_count"):
        pages.append({"kind": "axon", "title": "Clashes · 3D", "crop": True})
    return pages


def building_section_plane(scene: dict, axis: str) -> dict:
    """Vertical cut. ``axis`` is the horizontal direction drawn across the sheet.

    The cut is placed on a clash when there is one, so the section shows the
    collision instead of an empty slice of the building.
    """
    bounds = scene.get("bounds") or scene_bounds(scene)
    clashes = [hanger for hanger in scene.get("hangers") or [] if not hanger["clear"]]
    if axis == "x":
        span = bounds["max"][1] - bounds["min"][1]
        values = [hanger["y"] for hanger in clashes] or [
            (bounds["min"][1] + bounds["max"][1]) / 2.0
        ]
        cut = sorted(values)[len(values) // 2]
        return {
            "origin": (0.0, cut),
            "normal": (0.0, 1.0),
            "depth": max(2.0, min(8.0, span * 0.45 if span > 1e-6 else 4.0)),
        }
    span = bounds["max"][0] - bounds["min"][0]
    values = [hanger["x"] for hanger in clashes] or [
        (bounds["min"][0] + bounds["max"][0]) / 2.0
    ]
    cut = sorted(values)[len(values) // 2]
    return {
        "origin": (cut, 0.0),
        "normal": (1.0, 0.0),
        "depth": max(2.0, min(8.0, span * 0.45 if span > 1e-6 else 4.0)),
    }


def plane_for_hanger(scene: dict, hanger: dict) -> dict:
    """A cut looking along the run, so the pipe is seen in section and the fixing in elevation.

    A wall bracket is shown from the side, so the line from the riser to the
    wall lies in the sheet.
    """
    if hanger.get("mount") == "wall":
        direction = hanger.get("mount_direction") or (1.0, 0.0, 0.0)
        nx, ny = -float(direction[1]), float(direction[0])
        if abs(nx) < 1e-9 and abs(ny) < 1e-9:
            nx, ny = 1.0, 0.0
        return {
            "origin": (float(hanger["x"]), float(hanger["y"])),
            "normal": (nx, ny),
            "depth": 0.8,
        }
    run = (scene.get("runs") or {}).get(hanger.get("run_id")) or {}
    direction = run.get("direction") or (1.0, 0.0, 0.0)
    length = math.hypot(float(direction[0]), float(direction[1]))
    if length < 1e-6:
        normal = (1.0, 0.0)
    else:
        normal = (float(direction[0]) / length, float(direction[1]) / length)
    return {
        "origin": (float(hanger["x"]), float(hanger["y"])),
        "normal": normal,
        "depth": 0.55,
    }


def clash_hangers(scene: dict, limit: int = 6, separation_m: float = 0.8) -> list[dict]:
    """Unresolved hangers far enough apart that each sheet shows a different spot."""
    clashes = [hanger for hanger in scene.get("hangers") or [] if not hanger["clear"]]
    clashes.sort(key=lambda hanger: (hanger["z"], hanger["x"], hanger["y"], hanger["id"]))
    chosen = []
    for hanger in clashes:
        if all(
            math.hypot(hanger["x"] - other["x"], hanger["y"] - other["y"]) >= separation_m
            for other in chosen
        ):
            chosen.append(hanger)
        if len(chosen) >= limit:
            break
    return chosen or clashes[:limit]


def plan_primitives(scene: dict, band: dict) -> list[dict]:
    """Top view of one level. Y is up the sheet."""
    primitives = []
    items = [
        item
        for item in scene.get("drawables") or []
        if _overlaps_band(_item_z(item), band)
    ]
    items.sort(key=lambda item: _CATEGORY_ORDER.get(item["category"], 1))
    for item in items:
        dashed = bool(item.get("source"))
        if item["kind"] == "box":
            primitives.append(
                {
                    "op": "rect",
                    "u0": item["min"][0],
                    "v0": item["min"][1],
                    "u1": item["max"][0],
                    "v1": item["max"][1],
                    "color": item["category"],
                    "weight": "ghost" if item["category"] == "wall" else "body",
                    "dashed": dashed,
                }
            )
            continue
        start, end = item["start"], item["end"]
        if math.hypot(end[0] - start[0], end[1] - start[1]) < 1e-4:
            primitives.append(
                {
                    "op": "circle",
                    "u": start[0],
                    "v": start[1],
                    "r": item["radius_m"],
                    "color": item["category"],
                    "weight": "body",
                    "dashed": dashed,
                }
            )
        else:
            primitives.append(
                {
                    "op": "line",
                    "u0": start[0],
                    "v0": start[1],
                    "u1": end[0],
                    "v1": end[1],
                    "width_m": item["radius_m"] * 2.0,
                    "color": item["category"],
                    "weight": "body",
                    "dashed": dashed,
                }
            )
    for hanger in scene.get("hangers") or []:
        if not _overlaps_band((hanger["z"], hanger["z"]), band):
            continue
        primitives.append(_marker(hanger["x"], hanger["y"], hanger, label=False))
        _append_plan_support(primitives, hanger, scene)
    return primitives


def section_primitives(
    scene: dict,
    plane: dict,
    *,
    depth: float,
    thickness: float,
    symmetric: bool,
    window: tuple[float, float, float, float] | None = None,
) -> list[dict]:
    """Project services onto a vertical cut.

    ``window`` is ``(u_min, u_max, z_min, z_max)`` in section coordinates.
    A symmetric cut keeps both sides of the plane. A building section keeps
    the side that holds more clashes and ghosts what lies beyond the cut.
    """
    ux, uy = _sheet_u(plane["normal"])
    look = 1.0 if symmetric else _look_sign(scene, plane)
    primitives = []
    for item in scene.get("drawables") or []:
        dashed = bool(item.get("source"))
        if item["kind"] == "segment":
            primitives.extend(
                _section_segment(
                    item, plane, ux, uy, look, depth, thickness, symmetric, dashed, window
                )
            )
        else:
            primitives.extend(
                _section_box(
                    item, plane, ux, uy, look, depth, thickness, symmetric, dashed, window
                )
            )
    for hanger in scene.get("hangers") or []:
        u, _v, distance = _section_point(hanger["x"], hanger["y"], hanger["z"], plane, ux, uy, look)
        if not _in_slab(distance, depth, thickness, symmetric):
            continue
        if window is not None and not (window[0] <= u <= window[1] and window[2] <= hanger["z"] <= window[3]):
            continue
        primitives.append(_marker(u, hanger["z"], hanger, label=True))
        _append_section_support(
            primitives, hanger, scene, plane, ux, uy, look, depth, thickness, symmetric, window
        )
    return primitives


def axon_primitives(scene: dict, *, flip: bool, crop: tuple | None = None) -> list[dict]:
    """Isometric edges. ``flip`` mirrors the horizontal axes for a second view."""
    primitives = []
    for item in scene.get("drawables") or []:
        if crop is not None and not _hits_crop(item, crop):
            continue
        dashed = bool(item.get("source"))
        if item["kind"] == "segment":
            projected = _project_segment(item["start"], item["end"], flip)
            if projected is None:
                continue
            (u0, v0, d0), (u1, v1, d1) = projected
            primitives.append(
                {
                    "op": "line",
                    "u0": u0,
                    "v0": v0,
                    "u1": u1,
                    "v1": v1,
                    "depth": (d0 + d1) / 2.0,
                    "width_m": item["radius_m"] * 2.0,
                    "color": item["category"],
                    "weight": "body",
                    "dashed": dashed,
                }
            )
            continue
        for start, end in _box_edges(item["min"], item["max"]):
            projected = _project_segment(start, end, flip)
            if projected is None:
                continue
            (u0, v0, d0), (u1, v1, d1) = projected
            primitives.append(
                {
                    "op": "line",
                    "u0": u0,
                    "v0": v0,
                    "u1": u1,
                    "v1": v1,
                    "depth": (d0 + d1) / 2.0,
                    "color": item["category"],
                    "weight": "ghost" if item["category"] in ("structure", "wall") else "body",
                    "dashed": dashed,
                }
            )
    for hanger in scene.get("hangers") or []:
        if crop is not None and not _point_in_crop(hanger, crop):
            continue
        u, v, depth = _project_point(hanger["x"], hanger["y"], hanger["z"], flip)
        primitives.append({**_marker(u, v, hanger, label=False), "depth": depth})
        segment = _support_segment(hanger, scene)
        if segment is None:
            continue
        projected = _project_segment(segment[0], segment[1], flip)
        if projected is None:
            continue
        (u0, v0, d0), (u1, v1, d1) = projected
        primitives.append(
            {
                "op": "line",
                "u0": u0,
                "v0": v0,
                "u1": u1,
                "v1": v1,
                "depth": max(d0, d1) + 1.0,
                "color": _support_color(hanger),
                "weight": "cut",
                "dashed": False,
            }
        )
    primitives.sort(key=lambda item: item.get("depth", 0.0))
    return primitives


def clash_crop(scene: dict, pad_m: float = 1.5) -> tuple | None:
    clashes = [hanger for hanger in scene.get("hangers") or [] if not hanger["clear"]]
    if not clashes:
        return None
    xs = [hanger["x"] for hanger in clashes]
    ys = [hanger["y"] for hanger in clashes]
    zs = [hanger["z"] for hanger in clashes]
    return (
        min(xs) - pad_m,
        min(ys) - pad_m,
        min(zs) - pad_m,
        max(xs) + pad_m,
        max(ys) + pad_m,
        max(zs) + pad_m + 1.0,
    )


def clip_to_range(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    d0: float,
    d1: float,
    lo: float,
    hi: float,
) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    """The part of a segment whose signed distance lies inside ``[lo, hi]``."""
    if hi < lo:
        return None
    if abs(d1 - d0) < 1e-12:
        if lo - 1e-9 <= d0 <= hi + 1e-9:
            return start, end
        return None
    enter = (lo - d0) / (d1 - d0)
    leave = (hi - d0) / (d1 - d0)
    t0 = max(0.0, min(enter, leave))
    t1 = min(1.0, max(enter, leave))
    if t1 < t0 - 1e-9:
        return None
    if t0 > 1.0 or t1 < 0.0:
        return None
    return _lerp(start, end, t0), _lerp(start, end, t1)


def render_scene(scene: dict, destination: Path) -> list[str]:
    """Write the sheet list to ``destination`` and return the page titles."""
    try:
        from reportlab.lib.pagesizes import A3, landscape
        from reportlab.pdfgen import canvas as pdfcanvas
    except ImportError as exc:
        raise SystemExit("reportlab is not installed. Run: pip install reportlab") from exc

    destination.parent.mkdir(parents=True, exist_ok=True)
    pages = pages_for_scene(scene)
    pdf = pdfcanvas.Canvas(str(destination), pagesize=landscape(A3), pageCompression=0)
    pdf.setTitle("Clash drawings · " + ", ".join(scene.get("models") or []))
    for index, page in enumerate(pages):
        if index:
            pdf.showPage()
        _draw_page(pdf, scene, page, index, len(pages), landscape(A3))
    pdf.save()
    return [page["title"] for page in pages]


def write_ifc_drawings(
    service: Path, others: list[Path] | None, destination: Path
) -> dict:
    """Place hangers for ``service`` and write the clash PDF."""
    scene = build_scene(service, others)
    titles = render_scene(scene, destination)
    return {
        "path": destination,
        "pages": titles,
        "page_count": len(titles),
        "clash_count": scene["clash_count"],
        "hanger_count": scene["hanger_count"],
        "models": scene["models"],
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ifc", type=Path, help="MEP IFC whose pipes and ducts are hung")
    parser.add_argument(
        "--obstacles",
        type=Path,
        nargs="*",
        default=[],
        help="Extra IFC files drawn and included in the clash check",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output PDF path (default: examples/out/<name>-views.pdf)",
    )
    args = parser.parse_args(argv)
    destination = args.out
    if destination is None:
        destination = Path("examples") / "out" / f"{args.ifc.stem}-views.pdf"
    try:
        written = write_ifc_drawings(args.ifc, args.obstacles, destination)
    except FileNotFoundError as exc:
        print(f"File not found: {exc.filename or exc}", file=sys.stderr)
        return 1
    except SystemExit:
        raise
    print(
        f"{written['page_count']} sheets · {written['hanger_count']} hangers · "
        f"{written['clash_count']} clashing → {written['path']}"
    )
    return 0


def _hanger_from_point(point: dict) -> dict:
    return {
        "id": point["id"],
        "x": float(point["x"]),
        "y": float(point["y"]),
        "z": float(point["z"]),
        "clear": bool(point["clear"]),
        "reason": point.get("reason") or "",
        "clashing_element_ids": list(point.get("clashing_element_ids") or []),
        "run_id": point.get("run_id"),
        "mount": point.get("mount") or "ceiling",
        "mount_direction": point.get("mount_direction"),
        "anchor": point.get("anchor"),
    }


def _z_extent(scene: dict) -> tuple[float, float]:
    bounds = scene.get("bounds") or scene_bounds(scene)
    return float(bounds["min"][2]), float(bounds["max"][2])


def _item_z(item: dict) -> tuple[float, float]:
    if item["kind"] == "segment":
        return (
            min(item["start"][2], item["end"][2]),
            max(item["start"][2], item["end"][2]),
        )
    return item["min"][2], item["max"][2]


def _overlaps_band(z_range: tuple[float, float], band: dict) -> bool:
    zmin, zmax = z_range
    lo = -1e9 if band.get("first") else band["z0"]
    hi = 1e9 if band.get("last") else band["z1"]
    return zmax >= lo and zmin < hi


def _cluster_bands(scene: dict, zmin: float, zmax: float) -> list[dict]:
    mids = []
    for item in scene.get("drawables") or []:
        low, high = _item_z(item)
        mids.append((low + high) / 2.0)
    for hanger in scene.get("hangers") or []:
        mids.append(hanger["z"])
    if not mids:
        return [{"name": "All levels", "z0": 0.0, "z1": 1.0, "first": True, "last": True}]
    mids.sort()
    groups = [[mids[0]]]
    for value in mids[1:]:
        if value - groups[-1][-1] > 1.5:
            groups.append([value])
        else:
            groups[-1].append(value)
    if len(groups) == 1:
        return [
            {
                "name": "All levels",
                "z0": zmin - 1.0,
                "z1": zmax + 1.0,
                "first": True,
                "last": True,
            }
        ]
    bands = []
    for index, group in enumerate(groups):
        bands.append(
            {
                "name": f"Level {index + 1}",
                "z0": min(group) - 0.4,
                "z1": max(group) + 0.4,
                "first": index == 0,
                "last": index == len(groups) - 1,
            }
        )
    for index in range(len(bands) - 1):
        mid = (max(groups[index]) + min(groups[index + 1])) / 2.0
        bands[index]["z1"] = mid
        bands[index + 1]["z0"] = mid
    bands[0]["z0"] = zmin - 1.0
    bands[-1]["z1"] = zmax + 1.0
    return bands


def _long_axis(bounds: dict) -> str:
    dx = bounds["max"][0] - bounds["min"][0]
    dy = bounds["max"][1] - bounds["min"][1]
    return "x" if dx >= dy else "y"


def _marker(u: float, v: float, hanger: dict, label: bool) -> dict:
    if not hanger["clear"] or hanger.get("reason") == "unresolved_clash":
        kind = "clash"
    elif hanger.get("reason") not in (None, "", "regular_70"):
        kind = "moved"
    else:
        kind = "clear"
    text = hanger["id"] if label and kind == "clash" else None
    # Spread ids that share a spot so the sheet stays readable.
    stagger = 0
    if text:
        try:
            stagger = int(text.rsplit("-", 1)[-1]) % 4 * 8
        except ValueError:
            stagger = 0
    return {"op": "marker", "u": u, "v": v, "marker": kind, "label": text, "label_dy": stagger}


def _sheet_u(normal: tuple[float, float]) -> tuple[float, float]:
    nx, ny = normal
    ux, uy = -ny, nx
    if ux < -1e-9 or (abs(ux) <= 1e-9 and uy < 0):
        ux, uy = -ux, -uy
    return ux, uy


def _section_point(x, y, z, plane, ux, uy, look):
    ox, oy = plane["origin"]
    nx, ny = plane["normal"]
    distance = ((x - ox) * nx + (y - oy) * ny) * look
    along = (x - ox) * ux + (y - oy) * uy
    return along, z, distance


def _look_sign(scene: dict, plane: dict) -> float:
    clashes = [hanger for hanger in scene.get("hangers") or [] if not hanger["clear"]]
    if not clashes:
        return 1.0
    nx, ny = plane["normal"]
    ox, oy = plane["origin"]
    score = 0
    for hanger in clashes:
        distance = (hanger["x"] - ox) * nx + (hanger["y"] - oy) * ny
        score += 1 if distance >= 0 else -1
    return 1.0 if score >= 0 else -1.0


def _in_slab(distance: float, depth: float, thickness: float, symmetric: bool) -> bool:
    if symmetric:
        return abs(distance) <= depth + 1e-9
    return -thickness - 1e-9 <= distance <= depth + 1e-9


def _weight_for(distance: float, thickness: float) -> str:
    return "cut" if abs(distance) <= thickness + 1e-9 else "ghost"


def _slab(depth: float, thickness: float, symmetric: bool) -> tuple[float, float]:
    if symmetric:
        return -depth, depth
    return -thickness, depth


def _section_segment(item, plane, ux, uy, look, depth, thickness, symmetric, dashed, window):
    start, end = item["start"], item["end"]
    _u0, _v0, d0 = _section_point(start[0], start[1], start[2], plane, ux, uy, look)
    _u1, _v1, d1 = _section_point(end[0], end[1], end[2], plane, ux, uy, look)
    lo, hi = _slab(depth, thickness, symmetric)
    clipped = clip_to_range(start, end, d0, d1, lo, hi)
    primitives = []
    if clipped is not None:
        a, b = clipped
        ua, va, da = _section_point(a[0], a[1], a[2], plane, ux, uy, look)
        ub, vb, db = _section_point(b[0], b[1], b[2], plane, ux, uy, look)
        piece = _clip_window(ua, va, ub, vb, window)
        if piece is not None:
            (ua, va), (ub, vb) = piece
            primitives.append(
                {
                    "op": "line",
                    "u0": ua,
                    "v0": va,
                    "u1": ub,
                    "v1": vb,
                    "width_m": item["radius_m"] * 2.0,
                    "color": item["category"],
                    "weight": _weight_for((da + db) / 2.0, thickness),
                    "dashed": dashed,
                }
            )
    if d0 == d1 or abs(d1 - d0) < 1e-12:
        return primitives
    if d0 * d1 > 0:
        return primitives
    t = -d0 / (d1 - d0)
    if not 0.0 <= t <= 1.0:
        return primitives
    point = _lerp(start, end, t)
    direction = _sub(end, start)
    horizontal = math.hypot(direction[0], direction[1])
    if horizontal < 1e-6:
        return primitives
    nx, ny = plane["normal"]
    length = _norm(direction)
    along = abs(direction[0] * nx + direction[1] * ny) / length if length > 1e-9 else 0.0
    if along < 0.65:
        return primitives
    u, v, _distance = _section_point(point[0], point[1], point[2], plane, ux, uy, look)
    if window is not None and not (window[0] <= u <= window[1] and window[2] <= v <= window[3]):
        return primitives
    primitives.append(
        {
            "op": "circle",
            "u": u,
            "v": v,
            "r": item["radius_m"],
            "color": item["category"],
            "weight": "cut",
            "dashed": dashed,
        }
    )
    return primitives


def _section_box(item, plane, ux, uy, look, depth, thickness, symmetric, dashed, window):
    lo, hi = _slab(depth, thickness, symmetric)
    primitives = []
    for start, end in _box_edges(item["min"], item["max"]):
        _u0, _v0, d0 = _section_point(start[0], start[1], start[2], plane, ux, uy, look)
        _u1, _v1, d1 = _section_point(end[0], end[1], end[2], plane, ux, uy, look)
        clipped = clip_to_range(start, end, d0, d1, lo, hi)
        if clipped is None:
            continue
        a, b = clipped
        if _norm(_sub(a, b)) < 1e-4:
            continue
        ua, va, da = _section_point(a[0], a[1], a[2], plane, ux, uy, look)
        ub, vb, db = _section_point(b[0], b[1], b[2], plane, ux, uy, look)
        piece = _clip_window(ua, va, ub, vb, window)
        if piece is None:
            continue
        (ua, va), (ub, vb) = piece
        primitives.append(
            {
                "op": "line",
                "u0": ua,
                "v0": va,
                "u1": ub,
                "v1": vb,
                "color": item["category"],
                "weight": _weight_for((da + db) / 2.0, thickness),
                "dashed": dashed,
            }
        )
    return primitives


def _clip_window(u0, v0, u1, v1, window):
    if window is None:
        return (u0, v0), (u1, v1)
    umin, umax, vmin, vmax = window
    start = (u0, v0, 0.0)
    end = (u1, v1, 0.0)
    clipped = clip_to_range(start, end, u0, u1, umin, umax)
    if clipped is None:
        return None
    (u0, v0, _), (u1, v1, _) = clipped
    clipped = clip_to_range((u0, v0, 0.0), (u1, v1, 0.0), v0, v1, vmin, vmax)
    if clipped is None:
        return None
    (u0, v0, _), (u1, v1, _) = clipped
    return (u0, v0), (u1, v1)


def host_wall_drawables(obstacles: list[dict], runs: list[dict]) -> list[dict]:
    """The piece of each host wall next to the riser it carries.

    A full wall would stretch the sheet across the building. Only the face
    beside the vertical run is drawn.
    """
    groups: dict[tuple, list[dict]] = {}
    for run in runs:
        wall_id = run.get("wall_element_id")
        if not wall_id:
            continue
        groups.setdefault((wall_id, run.get("wall_source")), []).append(run)
    drawables = []
    for obstacle in obstacles:
        if obstacle.get("category") != "wall":
            continue
        runs_for_wall = groups.get((obstacle.get("element_id"), obstacle.get("source")))
        if not runs_for_wall:
            continue
        clipped = _clip_wall_to_runs(obstacle, runs_for_wall)
        if clipped is None:
            continue
        item = drawable_from_obstacle(clipped)
        if item is not None:
            drawables.append(item)
    return drawables


def _clip_wall_to_runs(obstacle: dict, runs: list[dict]) -> dict | None:
    xs = []
    ys = []
    zs = []
    for run in runs:
        for point in (run.get("origin"), run.get("end")):
            if not point:
                continue
            xs.append(float(point[0]))
            ys.append(float(point[1]))
            zs.append(float(point[2]))
    if not xs:
        return None
    pad = _WALL_DRAW_PAD_M
    low, high = obstacle["min"], obstacle["max"]
    clipped_min = (
        max(float(low[0]), min(xs) - pad),
        max(float(low[1]), min(ys) - pad),
        max(float(low[2]), min(zs) - pad),
    )
    clipped_max = (
        min(float(high[0]), max(xs) + pad),
        min(float(high[1]), max(ys) + pad),
        min(float(high[2]), max(zs) + pad),
    )
    if any(clipped_min[index] >= clipped_max[index] - 1e-6 for index in range(3)):
        return None
    copy = dict(obstacle)
    copy["min"] = clipped_min
    copy["max"] = clipped_max
    return copy


def _support_color(hanger: dict) -> str:
    if not hanger["clear"] or hanger.get("reason") == "unresolved_clash":
        return "clash"
    if hanger.get("reason") not in (None, "", "regular_70"):
        return "moved"
    return "clear"


def _support_segment(hanger: dict, scene: dict):
    """Line from the service to its fixing. Ceiling rods are drawn only when they clash."""
    anchor = hanger.get("anchor")
    if hanger.get("mount") == "wall" and anchor and len(anchor) >= 3:
        start = (float(hanger["x"]), float(hanger["y"]), float(hanger["z"]))
        end = (float(anchor[0]), float(anchor[1]), float(anchor[2]))
        if _norm(_sub(end, start)) < 1e-4:
            return None
        return start, end
    if hanger["clear"]:
        return None
    top = _rod_top(hanger, scene)
    if top <= hanger["z"] + 1e-4:
        return None
    return (float(hanger["x"]), float(hanger["y"]), float(hanger["z"])), (
        float(hanger["x"]),
        float(hanger["y"]),
        top,
    )


def _append_plan_support(primitives: list[dict], hanger: dict, scene: dict) -> None:
    segment = _support_segment(hanger, scene)
    if segment is None:
        return
    start, end = segment
    if math.hypot(end[0] - start[0], end[1] - start[1]) < 1e-4:
        return
    primitives.append(
        {
            "op": "line",
            "u0": start[0],
            "v0": start[1],
            "u1": end[0],
            "v1": end[1],
            "color": _support_color(hanger),
            "weight": "cut",
            "dashed": False,
        }
    )


def _append_section_support(
    primitives, hanger, scene, plane, ux, uy, look, depth, thickness, symmetric, window
) -> None:
    segment = _support_segment(hanger, scene)
    if segment is None:
        return
    start, end = segment
    _u0, _v0, d0 = _section_point(start[0], start[1], start[2], plane, ux, uy, look)
    _u1, _v1, d1 = _section_point(end[0], end[1], end[2], plane, ux, uy, look)
    lo, hi = _slab(depth, thickness, symmetric)
    clipped = clip_to_range(start, end, d0, d1, lo, hi)
    if clipped is None:
        return
    a, b = clipped
    ua, va, _da = _section_point(a[0], a[1], a[2], plane, ux, uy, look)
    ub, vb, _db = _section_point(b[0], b[1], b[2], plane, ux, uy, look)
    piece = _clip_window(ua, va, ub, vb, window)
    if piece is None:
        return
    (ua, va), (ub, vb) = piece
    if math.hypot(ub - ua, vb - va) < 1e-4:
        return
    primitives.append(
        {
            "op": "line",
            "u0": ua,
            "v0": va,
            "u1": ub,
            "v1": vb,
            "color": _support_color(hanger),
            "weight": "cut",
            "dashed": False,
        }
    )


def _rod_top(hanger: dict, scene: dict) -> float:
    cap = hanger["z"] + float(scene.get("rod_length_m") or MAX_ROD_LENGTH_M)
    top = hanger["z"] + 0.35
    hits = set(hanger.get("clashing_element_ids") or [])
    for item in scene.get("drawables") or []:
        if _clash_name(item) not in hits:
            continue
        zmin, zmax = _item_z(item)
        if zmax < hanger["z"]:
            continue
        if zmin > hanger["z"]:
            top = min(cap, max(top, zmin))
        else:
            top = min(cap, max(top, hanger["z"] + 0.35))
    return min(top, cap)


def _box_edges(low, high):
    x0, y0, z0 = low
    x1, y1, z1 = high
    corners = [
        (x0, y0, z0),
        (x1, y0, z0),
        (x1, y1, z0),
        (x0, y1, z0),
        (x0, y0, z1),
        (x1, y0, z1),
        (x1, y1, z1),
        (x0, y1, z1),
    ]
    pairs = (
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 0),
        (4, 5),
        (5, 6),
        (6, 7),
        (7, 4),
        (0, 4),
        (1, 5),
        (2, 6),
        (3, 7),
    )
    return [(corners[a], corners[b]) for a, b in pairs]


def _project_point(x, y, z, flip: bool) -> tuple[float, float, float]:
    cos30 = math.cos(math.radians(30))
    sin30 = math.sin(math.radians(30))
    if flip:
        horizontal = (-x + y) * cos30
    else:
        horizontal = (x - y) * cos30
    vertical = z + (x + y) * sin30
    # Smaller depth is further from the camera and is drawn first.
    return horizontal, vertical, -(x + y)


def _project_segment(start, end, flip: bool):
    a = _project_point(start[0], start[1], start[2], flip)
    b = _project_point(end[0], end[1], end[2], flip)
    if math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-6:
        return None
    return a, b


def _hits_crop(item: dict, crop: tuple) -> bool:
    x0, y0, z0, x1, y1, z1 = crop
    if item["kind"] == "segment":
        low = tuple(min(item["start"][i], item["end"][i]) for i in range(3))
        high = tuple(max(item["start"][i], item["end"][i]) for i in range(3))
    else:
        low, high = item["min"], item["max"]
    return not (
        high[0] < x0 or low[0] > x1 or high[1] < y0 or low[1] > y1 or high[2] < z0 or low[2] > z1
    )


def _point_in_crop(hanger: dict, crop: tuple) -> bool:
    x0, y0, z0, x1, y1, z1 = crop
    return x0 <= hanger["x"] <= x1 and y0 <= hanger["y"] <= y1 and z0 <= hanger["z"] <= z1


def _lerp(start, end, t: float):
    return tuple(start[index] + (end[index] - start[index]) * t for index in range(3))


def _sub(left, right):
    return tuple(left[index] - right[index] for index in range(3))


def _norm(vector) -> float:
    return math.sqrt(sum(component * component for component in vector))


_COLORS = {
    "pipe": (0.12, 0.33, 0.58),
    "duct": (0.78, 0.40, 0.09),
    "service": (0.40, 0.38, 0.34),
    "structure": (0.48, 0.45, 0.40),
    "wall": (0.55, 0.60, 0.64),
    "clash": (0.70, 0.14, 0.08),
    "moved": (0.72, 0.40, 0.10),
    "clear": (0.13, 0.42, 0.28),
    "ink": (0.11, 0.10, 0.08),
    "muted": (0.37, 0.34, 0.30),
    "line": (0.83, 0.80, 0.74),
    "paper": (0.98, 0.97, 0.95),
}


def _draw_page(pdf, scene, page, index: int, total: int, page_size) -> None:
    width, height = page_size
    kind = page["kind"]
    if kind == "cover":
        _draw_cover(pdf, scene, width, height)
        _chrome(pdf, page["title"], scene, None, width, height, index, total, note=None)
        return
    if kind == "axon":
        _draw_axon_page(pdf, scene, page, width, height)
        _chrome(
            pdf,
            page["title"],
            scene,
            None,
            width,
            height,
            index,
            total,
            note="Isometric. The vertical coefficient is true; the note 1:N is that scale.",
        )
        return
    frame = _Frame(pdf, 40, 48, width - 80, height - 96)
    ratio = None
    if kind == "plan":
        primitives = plan_primitives(scene, page["band"])
        ratio = frame.draw(primitives, square=True)
    elif kind == "section":
        plane = page["plane"]
        primitives = section_primitives(
            scene,
            plane,
            depth=plane["depth"],
            thickness=0.2,
            symmetric=False,
        )
        ratio = frame.draw(primitives, square=True)
    else:
        hanger = next(
            (item for item in scene.get("hangers") or [] if item["id"] == page.get("hanger_id")),
            None,
        )
        if hanger is not None:
            plane = plane_for_hanger(scene, hanger)
            if hanger.get("mount") == "wall":
                window = (-2.2, 2.2, hanger["z"] - 0.6, hanger["z"] + 0.6)
            else:
                window = (-1.0, 1.0, hanger["z"] - 0.45, hanger["z"] + 1.15)
            primitives = section_primitives(
                scene,
                plane,
                depth=plane["depth"],
                thickness=0.16,
                symmetric=True,
                window=window,
            )
            ratio = frame.draw(primitives, square=True, bounds=window)
    _chrome(pdf, page["title"], scene, ratio, width, height, index, total, note=None)


def _draw_axon_page(pdf, scene, page, width, height) -> None:
    crop = clash_crop(scene) if page.get("crop") else None
    gap = 18
    frame_w = (width - 80 - gap) / 2.0
    left = _Frame(pdf, 40, 48, frame_w, height - 96)
    right = _Frame(pdf, 40 + frame_w + gap, 48, frame_w, height - 96)
    left_ratio = left.draw(axon_primitives(scene, flip=False, crop=crop), square=True)
    right_ratio = right.draw(axon_primitives(scene, flip=True, crop=crop), square=True)
    pdf.setFillColorRGB(*_COLORS["muted"])
    pdf.setFont("Helvetica", 8)
    pdf.drawString(40, height - 46, "View from −Y")
    pdf.drawString(40 + frame_w + gap, height - 46, "View from −X")
    if left_ratio or right_ratio:
        pdf.drawRightString(width - 40, height - 46, f"vertical 1:{left_ratio or right_ratio}")


class _Frame:
    def __init__(self, pdf, x, y, w, h):
        self.pdf = pdf
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.ratio = None
        self.ppm = 1.0
        self.u0 = 0.0
        self.v0 = 0.0
        self.left = x
        self.bottom = y

    def draw(self, primitives: list[dict], *, square: bool, bounds=None) -> int | None:
        if bounds is not None:
            u0, u1, v0, v1 = bounds
        else:
            u0, v0, u1, v1 = _primitive_bounds(primitives)
        if u1 < u0 or v1 < v0 or not primitives:
            self._empty()
            return None
        span_u = max(u1 - u0, 0.2)
        span_v = max(v1 - v0, 0.2)
        pad_u = max(0.25, span_u * 0.04)
        pad_v = max(0.25, span_v * 0.04)
        u0 -= pad_u
        u1 += pad_u
        v0 -= pad_v
        v1 += pad_v
        span_u = u1 - u0
        span_v = v1 - v0
        self.ratio, self.ppm = _choose_scale(span_u, span_v, self.w, self.h, square)
        drawn_w = span_u * self.ppm
        drawn_h = span_v * self.ppm
        self.left = self.x + (self.w - drawn_w) / 2.0
        self.bottom = self.y + (self.h - drawn_h) / 2.0
        self.u0 = u0
        self.v0 = v0
        self.pdf.saveState()
        self.pdf.setLineCap(1)
        self.pdf.setLineJoin(1)
        for primitive in primitives:
            self._paint(primitive)
        self.pdf.restoreState()
        return self.ratio

    def _empty(self) -> None:
        self.pdf.setFillColorRGB(*_COLORS["muted"])
        self.pdf.setFont("Helvetica", 10)
        self.pdf.drawString(self.x, self.y + self.h / 2.0, "Nothing in this view.")

    def _paint(self, primitive: dict) -> None:
        op = primitive["op"]
        if op == "marker":
            self._marker(primitive)
            return
        color = _COLORS.get(primitive.get("color"), _COLORS["service"])
        if primitive.get("weight") == "ghost":
            color = tuple(channel + (1.0 - channel) * 0.55 for channel in color)
        self.pdf.setStrokeColorRGB(*color)
        width = 1.15 if primitive.get("weight") == "cut" else 0.7
        if primitive.get("weight") == "ghost":
            width = 0.35
        model_width = primitive.get("width_m")
        if model_width:
            width = max(width, model_width * self.ppm)
            width = min(width, 3.5)
        self.pdf.setLineWidth(width)
        if primitive.get("dashed"):
            self.pdf.setDash([3, 2])
        else:
            self.pdf.setDash()
        if op == "line":
            x0, y0 = self._pt(primitive["u0"], primitive["v0"])
            x1, y1 = self._pt(primitive["u1"], primitive["v1"])
            self.pdf.line(x0, y0, x1, y1)
        elif op == "rect":
            x0, y0 = self._pt(primitive["u0"], primitive["v0"])
            x1, y1 = self._pt(primitive["u1"], primitive["v1"])
            self.pdf.rect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0), stroke=1, fill=0)
        elif op == "circle":
            x, y = self._pt(primitive["u"], primitive["v"])
            radius = max(0.8, primitive["r"] * self.ppm)
            self.pdf.circle(x, y, radius, stroke=1, fill=0)

    def _marker(self, primitive: dict) -> None:
        color = _COLORS[primitive["marker"]]
        x, y = self._pt(primitive["u"], primitive["v"])
        self.pdf.setFillColorRGB(*color)
        self.pdf.setDash()
        radius = 3.2 if primitive["marker"] == "clash" else 2.2
        self.pdf.circle(x, y, radius, stroke=0, fill=1)
        if primitive["marker"] == "clash":
            self.pdf.setStrokeColorRGB(*color)
            self.pdf.setLineWidth(0.8)
            self.pdf.circle(x, y, radius + 2.0, stroke=1, fill=0)
        label = primitive.get("label")
        if label:
            self.pdf.setFillColorRGB(*_COLORS["ink"])
            self.pdf.setFont("Helvetica", 6.5)
            self.pdf.drawString(x + 5, y + 3 + primitive.get("label_dy", 0), label[:48])

    def _pt(self, u: float, v: float) -> tuple[float, float]:
        return (
            self.left + (u - self.u0) * self.ppm,
            self.bottom + (v - self.v0) * self.ppm,
        )


def _primitive_bounds(primitives: list[dict]) -> tuple[float, float, float, float]:
    us = []
    vs = []
    for primitive in primitives:
        if primitive["op"] == "line" or primitive["op"] == "rect":
            us.extend((primitive["u0"], primitive["u1"]))
            vs.extend((primitive["v0"], primitive["v1"]))
        else:
            us.append(primitive["u"])
            vs.append(primitive["v"])
            if primitive["op"] == "circle":
                us.extend((primitive["u"] - primitive["r"], primitive["u"] + primitive["r"]))
                vs.extend((primitive["v"] - primitive["r"], primitive["v"] + primitive["r"]))
    if not us:
        return 0.0, 0.0, 1.0, 1.0
    return min(us), min(vs), max(us), max(vs)


def _choose_scale(span_u: float, span_v: float, frame_w: float, frame_h: float, square: bool):
    del square
    ppm_fit = min((frame_w - 8) / span_u, (frame_h - 8) / span_v)
    ppm_fit = max(ppm_fit, 0.01)
    raw = 1000.0 / (ppm_fit / _MM)
    ratio = next((step for step in _SCALE_STEPS if step >= raw - 1e-6), None)
    if ratio is None:
        ratio = int(math.ceil(raw / 1000.0) * 1000)
    ppm = (1000.0 / ratio) * _MM
    return ratio, ppm


def _chrome(pdf, title, scene, ratio, width, height, index, total, note) -> None:
    pdf.setFillColorRGB(*_COLORS["ink"])
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, height - 26, title)
    pdf.setFillColorRGB(*_COLORS["muted"])
    pdf.setFont("Helvetica", 8)
    models = " · ".join(scene.get("models") or [])
    pdf.drawRightString(width - 40, height - 26, models[:110])
    pdf.setStrokeColorRGB(*_COLORS["line"])
    pdf.setLineWidth(0.4)
    pdf.setDash()
    pdf.line(40, height - 34, width - 40, height - 34)
    pdf.line(40, 40, width - 40, 40)
    swatches = (
        ("Pipes", "pipe"),
        ("Ducts", "duct"),
        ("Other services", "service"),
        ("Structure", "structure"),
        ("Walls", "wall"),
        ("Clash", "clash"),
        ("Moved", "moved"),
        ("Clear", "clear"),
    )
    x = 40
    for label, name in swatches:
        pdf.setFillColorRGB(*_COLORS[name])
        pdf.circle(x + 3, 26, 3, stroke=0, fill=1)
        pdf.setFillColorRGB(*_COLORS["muted"])
        pdf.setFont("Helvetica", 7.5)
        pdf.drawString(x + 9, 23, label)
        x += 62 if len(label) < 8 else 78
    pdf.setFillColorRGB(*_COLORS["muted"])
    if ratio and note is None:
        pdf.drawRightString(width - 70, 23, f"1:{ratio}")
    elif note:
        pdf.setFont("Helvetica", 7)
        pdf.drawString(40, 12, note)
    pdf.drawRightString(width - 40, 23, f"{index + 1}/{total}")


def _draw_cover(pdf, scene, width, height) -> None:
    models = scene.get("models") or []
    y = height - 64
    pdf.setFillColorRGB(*_COLORS["ink"])
    pdf.setFont("Helvetica", 10)
    lines = [
        "Floor plans, a long section, a cross section, a section at each unresolved clash,",
        "and two isometric views. Extra IFCs are drawn dashed and included in the check.",
        "A vertical pipe or duct is fixed to the nearest wall, such as a shaft wall.",
        "That wall is drawn next to the riser. Slabs and ceilings stay out.",
        "Red is a hanger whose fixing still hits something. Amber was moved off a clash. Green is clear.",
        "",
        f"Models: {', '.join(models) if models else '—'}",
        f"Hangers: {scene.get('hanger_count', 0)}",
        f"Unresolved clashes: {scene.get('clash_count', 0)}",
    ]
    for line in lines:
        pdf.drawString(40, y, line)
        y -= 14
    clashes = [hanger for hanger in scene.get("hangers") or [] if not hanger["clear"]]
    y -= 8
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(40, y, "Unresolved clashes")
    y -= 16
    pdf.setFont("Helvetica", 8)
    if not clashes:
        pdf.setFillColorRGB(*_COLORS["muted"])
        pdf.drawString(40, y, "Every placed hanger is clear.")
        return
    pdf.setFillColorRGB(*_COLORS["muted"])
    pdf.drawString(40, y, "Id")
    pdf.drawString(110, y, "X")
    pdf.drawString(170, y, "Y")
    pdf.drawString(230, y, "Z")
    pdf.drawString(290, y, "Hits")
    y -= 12
    pdf.setStrokeColorRGB(*_COLORS["line"])
    pdf.setLineWidth(0.3)
    pdf.line(40, y + 8, width - 40, y + 8)
    shown = clashes[:28]
    pdf.setFillColorRGB(*_COLORS["ink"])
    for hanger in shown:
        if y < 56:
            break
        pdf.drawString(40, y, hanger["id"])
        pdf.drawString(110, y, f"{hanger['x']:.3f}")
        pdf.drawString(170, y, f"{hanger['y']:.3f}")
        pdf.drawString(230, y, f"{hanger['z']:.3f}")
        pdf.drawString(290, y, ", ".join(hanger.get("clashing_element_ids") or [])[:90])
        y -= 11
    remaining = len(clashes) - len(shown)
    if remaining > 0 and y >= 56:
        pdf.setFillColorRGB(*_COLORS["muted"])
        pdf.drawString(40, y, f"and {remaining} more on the sheets")


if __name__ == "__main__":
    raise SystemExit(main())
