"""Place hanger points along straight pipe and duct runs.

A run is a straight, same-size chain of segments. Points are spaced evenly
along it. The largest gap is kept to 70% of the spacing the catalogue allows
for that size, so the hangers sit on a regular pitch with some spare.

Each point is then checked upward. The rod is a vertical line from the top of
the pipe or duct. If it meets another service or a beam, the run is spaced
again so every gap between hangers falls between 90% and 95% of the allowed
spacing, which is as wide as the correction may go. A hanger is never pushed
so far that a gap exceeds 95%. If no clear position exists inside that limit,
the point stays and is reported as a clash.

Run from the repo root:

    python -m src.mounting_points examples/HeatingAndCooling.ifc --out examples/out/mounting-points.json
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from src.mounting import feasible_mountings, load_database

ROOT = Path(__file__).resolve().parents[1]

# The strategy's two pitches, as fractions of the catalogue maximum.
INITIAL_SPACING_RATIO = 0.70
ADJUSTED_SPACING_MIN_RATIO = 0.90
ADJUSTED_SPACING_MAX_RATIO = 0.95

# A moved hanger must not land on top of its neighbour.
MIN_SUPPORT_GAP_M = 0.05
# Sit this far off a blocked station so the rod is outside the obstacle.
EDGE_CLEARANCE_M = 0.001
# Rod used only for the clash test, not as a selected product.
ROD_RADIUS_M = 0.01
ROD_START_CLEARANCE_M = 0.002
MAX_ROD_LENGTH_M = 2.0
# Sample the run when turning exact hits into station intervals.
SAMPLE_STEP_M = 0.01
# Search pitch for an alternative regular layout inside the 90–95% band.
BAND_STEP_M = 0.025

# Straighter than this (and within the lateral tolerance) is one run.
_ALIGNMENT_COS = math.cos(math.radians(5.0))
_LATERAL_TOLERANCE_M = 0.02
# Above this slope the cited tables are horizontal spacings and do not apply.
_HORIZONTAL_SLOPE = math.sin(math.radians(15.0))

_LINEAR_KINDS = {"pipe_segment", "duct_segment"}


class PlacementError(ValueError):
    """A length or a spacing was not usable."""


def even_stations(length: float, max_spacing: float) -> list[float]:
    """Stations from 0 to ``length`` whose equal gaps are at most ``max_spacing``.

    Both ends are included, so a straight run is held at each end. The gap is
    the length divided into the smallest number of equal parts that stays
    under the cap.
    """
    if max_spacing <= 0:
        raise PlacementError("max_spacing must be positive")
    if length < 0:
        raise PlacementError("length must be non-negative")
    if length <= 1e-9:
        return [0.0]
    # The tiny subtraction keeps an exact multiple on one span. A bare ceil
    # of a value that should be 3.0 is sometimes 3.0000000002 and would
    # open an extra span.
    spans = max(1, math.ceil(length / max_spacing - 1e-6))
    step = length / spans
    return [i * step for i in range(spans + 1)]


def max_support_spacing_m(element: dict, database: dict | None = None) -> tuple[float | None, str | None]:
    """Smallest cited horizontal spacing for ``element``, and the guidance id.

    Returns ``(None, None)`` when the catalogue has no spacing row for the size.
    Several rows can match; the shortest one is the limit the hangers must keep.
    """
    result = feasible_mountings(element, database)
    rows = [
        item
        for item in result["guidance"]
        if isinstance(item.get("horizontal_m"), (int, float))
    ]
    if not rows:
        return None, None
    chosen = min(rows, key=lambda item: item["horizontal_m"])
    return float(chosen["horizontal_m"]), chosen.get("guidance_id")


def plan_stations(
    length: float,
    maximum_spacing_m: float,
    blocked_intervals: list[tuple[float, float]] | None = None,
) -> list[dict]:
    """Place stations along one straight run of ``length`` metres.

    ``blocked_intervals`` are ranges of station, in metres, where the vertical
    rod hits something. Each result is ``{"station_m", "reason"}``.

    Reasons:

    - ``regular_70`` — even pitch, every gap at most 70% of the maximum
    - ``respaced_90_95`` — a clash forced a new even pitch inside 90–95%
    - ``shifted_into_90_95`` — the even 90–95% pitch could not miss the clash,
      and this hanger was moved so one neighbouring gap is inside that band
    - ``shifted_under_95`` — moved to the nearest clear station that still
      keeps every gap at or under 95%
    - ``unresolved_clash`` — every station inside the 95% limit is blocked
    """
    if maximum_spacing_m <= 0:
        raise PlacementError("maximum spacing must be positive")
    if length < 0:
        raise PlacementError("length must be non-negative")
    blocked = _merge_intervals(blocked_intervals or [])
    initial = even_stations(length, INITIAL_SPACING_RATIO * maximum_spacing_m)
    if not any(_is_blocked(station, blocked) for station in initial):
        return [{"station_m": station, "reason": "regular_70"} for station in initial]

    layout = _best_band_layout(length, maximum_spacing_m, blocked)
    if layout is not None:
        return [{"station_m": station, "reason": "respaced_90_95"} for station in layout]

    stations = list(initial)
    reasons = ["regular_70"] * len(stations)
    for index in range(len(stations)):
        if not _is_blocked(stations[index], blocked):
            continue
        moved = _shift_station(index, stations, length, maximum_spacing_m, blocked)
        if moved is None:
            reasons[index] = "unresolved_clash"
            continue
        stations[index], reasons[index] = moved
    return [
        {"station_m": station, "reason": reason}
        for station, reason in zip(stations, reasons)
    ]


def detect_runs(segments: list[dict]) -> list[dict]:
    """Group collinear, same-size, connected segments into straight runs.

    A segment needs ``global_id``, ``kind``, ``start`` and ``end`` (centre-line,
    metres), a size (``outer_diameter_mm`` or ``width_mm`` and ``height_mm``),
    and ``adjacent_ids`` for the segments it meets through a fitting. An elbow
    is not collinear, so it ends the run. A reducer changes size, so it ends
    the run. ``fitting_ids`` are optional ids the clash test should ignore,
    because those fittings belong to the run rather than crossing it.
    """
    by_id = {}
    for segment in segments:
        if segment.get("kind") not in _LINEAR_KINDS:
            continue
        if _segment_length(segment) < 1e-4:
            continue
        by_id[segment["global_id"]] = segment

    parent = {key: key for key in by_id}

    def find(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for segment in by_id.values():
        for other_id in segment.get("adjacent_ids") or []:
            other = by_id.get(other_id)
            if other is None:
                continue
            if _can_join(segment, other):
                parent[find(other_id)] = find(segment["global_id"])

    groups: dict[str, list[dict]] = {}
    for segment in by_id.values():
        groups.setdefault(find(segment["global_id"]), []).append(segment)

    runs = [_run_from_members(members) for members in groups.values()]
    runs.sort(key=lambda run: (_round_point(run["origin"]), run["element_ids"][0]))
    return runs


def rod_hits_obstacle(
    x: float,
    y: float,
    z_top: float,
    obstacle: dict,
    *,
    rod_radius_m: float = ROD_RADIUS_M,
    max_rod_length_m: float = MAX_ROD_LENGTH_M,
) -> bool:
    """Whether a vertical rod from the top of a service hits ``obstacle``.

    The rod starts just above ``z_top`` and extends ``max_rod_length_m``.
    A cylinder obstacle is a round pipe or duct about its centre-line. A box
    is a rectangular duct, a fitting, or a beam.
    """
    z0 = z_top + ROD_START_CLEARANCE_M
    z1 = z_top + max_rod_length_m
    if obstacle.get("shape") == "cylinder":
        distance = _segment_distance(
            (x, y, z0),
            (x, y, z1),
            tuple(obstacle["start"]),
            tuple(obstacle["end"]),
        )
        return distance <= obstacle["radius_m"] + rod_radius_m + 1e-9
    low, high = obstacle["min"], obstacle["max"]
    if x < low[0] - rod_radius_m or x > high[0] + rod_radius_m:
        return False
    if y < low[1] - rod_radius_m or y > high[1] + rod_radius_m:
        return False
    return low[2] <= z1 and high[2] >= z0


def plan_mounting_points(
    segments: list[dict],
    obstacles: list[dict] | None = None,
    database: dict | None = None,
    *,
    source: str | None = None,
    rod_radius_m: float = ROD_RADIUS_M,
    max_rod_length_m: float = MAX_ROD_LENGTH_M,
) -> dict:
    """Detect runs and place a hanger point on each one that has a spacing.

    ``obstacles`` use the same shape as :func:`rod_hits_obstacle`. An obstacle
    whose ``element_id`` is one of the run's own segments or fittings is
    ignored for that run.
    """
    catalogue = database if database is not None else load_database()
    clash_obstacles = list(obstacles or [])
    runs = detect_runs(segments)
    run_rows = []
    point_rows = []
    for index, run in enumerate(runs, start=1):
        run_id = f"R-{index:04d}"
        placed = _place_run(
            run,
            run_id,
            clash_obstacles,
            catalogue,
            rod_radius_m=rod_radius_m,
            max_rod_length_m=max_rod_length_m,
            first_point_index=len(point_rows) + 1,
        )
        run_rows.append(placed["run"])
        point_rows.extend(placed["points"])
    return {
        "source": source,
        "units": "m",
        "spacing_rule": {
            "initial_ratio_of_maximum": INITIAL_SPACING_RATIO,
            "adjusted_minimum_ratio_of_maximum": ADJUSTED_SPACING_MIN_RATIO,
            "adjusted_maximum_ratio_of_maximum": ADJUSTED_SPACING_MAX_RATIO,
        },
        "rod": {
            "radius_m": rod_radius_m,
            "max_length_m": max_rod_length_m,
            "start_clearance_m": ROD_START_CLEARANCE_M,
        },
        "runs": run_rows,
        "points": point_rows,
    }


def load_ifc(path: Path) -> tuple[list[dict], list[dict]]:
    """Read straight segments and clash obstacles from an IFC file.

    Segments are pipe and duct runs with two ports. Other flow parts become
    boxes. Beams, members and columns become boxes too. Slabs, walls and
    ceilings are left out: the rod is meant to reach the soffit, and a wall
    box would fill the whole storey.
    """
    try:
        import ifcopenshell
    except ImportError as exc:
        raise SystemExit(
            "ifcopenshell is not installed. Run: pip install -r requirements.txt"
        ) from exc

    model = ifcopenshell.open(str(path))
    segments = _segments_from_model(model)
    obstacles = _obstacles_for_segments(segments)
    obstacles.extend(_other_flow_boxes(model, {segment["global_id"] for segment in segments}))
    obstacles.extend(_structural_boxes(model))
    return segments, obstacles


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
        help="Extra IFC files whose services or beams can block a rod",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("examples/out/mounting-points.json"),
        help="Output JSON path",
    )
    parser.add_argument("--max-rod-length", type=float, default=MAX_ROD_LENGTH_M)
    parser.add_argument("--rod-radius", type=float, default=ROD_RADIUS_M)
    args = parser.parse_args(argv)

    if not args.ifc.is_file():
        print(f"File not found: {args.ifc}", file=sys.stderr)
        return 1
    for extra in args.obstacles:
        if not extra.is_file():
            print(f"File not found: {extra}", file=sys.stderr)
            return 1

    segments, obstacles = load_ifc(args.ifc)
    for extra in args.obstacles:
        _extra_segments, extra_obstacles = load_ifc(extra)
        obstacles.extend(extra_obstacles)
    plan = plan_mounting_points(
        segments,
        obstacles,
        source=args.ifc.name,
        rod_radius_m=args.rod_radius,
        max_rod_length_m=args.max_rod_length,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(_round_numbers(plan), indent=2), encoding="utf-8")
    _print_summary(plan, args.out)
    return 0


def _place_run(
    run: dict,
    run_id: str,
    obstacles: list[dict],
    database: dict,
    *,
    rod_radius_m: float,
    max_rod_length_m: float,
    first_point_index: int,
) -> dict:
    element = _spacing_element(run)
    limit, guidance_id = max_support_spacing_m(element, database)
    row = _run_row(run, run_id, limit, guidance_id)
    if limit is None:
        row["status"] = "no_spacing_guidance"
        row["note"] = "No cited spacing row covers this size."
        return {"run": row, "points": []}
    if abs(run["direction"][2]) > _HORIZONTAL_SLOPE:
        row["status"] = "skipped_not_horizontal"
        row["note"] = (
            "The run is steeper than 15 degrees. The cited spacing is for a horizontal service."
        )
        return {"run": row, "points": []}
    if run["length_m"] < 1e-4:
        row["status"] = "too_short"
        return {"run": row, "points": []}

    host_ids = set(run["element_ids"]) | set(run.get("fitting_ids") or [])
    relevant = [
        obstacle
        for obstacle in obstacles
        if obstacle.get("element_id") not in host_ids
        and _near_run(run, obstacle, rod_radius_m, max_rod_length_m)
    ]

    def exact_ids(station: float) -> list[str]:
        return _clashing_ids(run, station, relevant, rod_radius_m, max_rod_length_m)

    intervals = _sample_blocked(run, relevant, rod_radius_m, max_rod_length_m)
    planned = plan_stations(run["length_m"], limit, intervals)
    for _ in range(3):
        missed = [
            item["station_m"]
            for item in planned
            if item["reason"] != "unresolved_clash" and exact_ids(item["station_m"])
        ]
        if not missed:
            break
        intervals = _merge_intervals(
            intervals + [(station - SAMPLE_STEP_M, station + SAMPLE_STEP_M) for station in missed]
        )
        planned = plan_stations(run["length_m"], limit, intervals)

    points = []
    for offset, item in enumerate(planned):
        clashes = exact_ids(item["station_m"])
        reason = item["reason"]
        if clashes and reason != "unresolved_clash":
            reason = "unresolved_clash"
        x, y, z = _point_on_run(run, item["station_m"])
        points.append(
            {
                "id": f"M-{first_point_index + offset:04d}",
                "run_id": run_id,
                "element_id": _element_at_station(run, item["station_m"]),
                "kind": run["kind"],
                "x": x,
                "y": y,
                "z": z,
                "station_m": item["station_m"],
                "max_spacing_m": limit,
                "reason": reason,
                "clear": not clashes,
                "clashing_element_ids": clashes,
            }
        )
    _annotate_gaps(points)
    row["status"] = _status_from_points(points)
    row["point_ids"] = [point["id"] for point in points]
    if points:
        row["cantilever_start_m"] = points[0]["station_m"]
        row["cantilever_end_m"] = run["length_m"] - points[-1]["station_m"]
    return {"run": row, "points": points}


def _run_row(run: dict, run_id: str, limit: float | None, guidance_id: str | None) -> dict:
    origin = run["origin"]
    direction = run["direction"]
    length = run["length_m"]
    return {
        "id": run_id,
        "kind": run["kind"],
        "size_label": _size_label(run),
        "system_names": list(run.get("system_names") or []),
        "length_m": length,
        "max_spacing_m": limit,
        "spacing_guidance_id": guidance_id,
        "element_ids": list(run["element_ids"]),
        "origin": list(origin),
        "direction": list(direction),
        "end": [origin[i] + direction[i] * length for i in range(3)],
        "point_ids": [],
        "status": None,
        "note": None,
    }


def _status_from_points(points: list[dict]) -> str:
    reasons = [point["reason"] for point in points]
    if any(reason == "unresolved_clash" for reason in reasons):
        return "placed_with_unresolved_clashes"
    if any(reason == "respaced_90_95" for reason in reasons):
        return "placed_respaced"
    if any(reason.startswith("shifted_") for reason in reasons):
        return "placed_adjusted"
    return "placed_initial"


def _annotate_gaps(points: list[dict]) -> None:
    for index, point in enumerate(points):
        previous = None if index == 0 else point["station_m"] - points[index - 1]["station_m"]
        nxt = None if index == len(points) - 1 else points[index + 1]["station_m"] - point["station_m"]
        point["spacing_to_previous_m"] = previous
        point["spacing_to_next_m"] = nxt
        gaps = [gap for gap in (previous, nxt) if gap is not None]
        limit = point["max_spacing_m"]
        point["spacing_ratio"] = max(gaps) / limit if gaps and limit else None


def _sample_blocked(run, obstacles, rod_radius_m, max_rod_length_m) -> list[tuple[float, float]]:
    hits = []
    length = run["length_m"]
    station = 0.0
    while True:
        if _clashing_ids(run, station, obstacles, rod_radius_m, max_rod_length_m):
            hits.append(station)
        if station >= length - 1e-12:
            break
        station = min(length, station + SAMPLE_STEP_M)
    if not hits:
        return []
    groups = [[hits[0], hits[0]]]
    for hit in hits[1:]:
        if hit - groups[-1][1] <= SAMPLE_STEP_M * 1.5:
            groups[-1][1] = hit
        else:
            groups.append([hit, hit])
    return _merge_intervals(
        (max(0.0, start - SAMPLE_STEP_M / 2), end + SAMPLE_STEP_M / 2) for start, end in groups
    )


def _clashing_ids(run, station, obstacles, rod_radius_m, max_rod_length_m) -> list[str]:
    x, y, z = _point_on_run(run, station)
    found = []
    for obstacle in obstacles:
        if rod_hits_obstacle(
            x,
            y,
            z,
            obstacle,
            rod_radius_m=rod_radius_m,
            max_rod_length_m=max_rod_length_m,
        ):
            identifier = obstacle.get("element_id")
            if identifier and identifier not in found:
                found.append(identifier)
    return found


def _point_on_run(run: dict, station: float) -> tuple[float, float, float]:
    origin = run["origin"]
    direction = run["direction"]
    return (
        origin[0] + station * direction[0],
        origin[1] + station * direction[1],
        origin[2] + station * direction[2] + _section_rise(run),
    )


def _section_rise(run: dict) -> float:
    """Metres from the centre-line up to the top of the section."""
    if run.get("outer_diameter_mm"):
        return run["outer_diameter_mm"] / 2000.0
    if run.get("height_mm"):
        return run["height_mm"] / 2000.0
    return 0.0


def _element_at_station(run: dict, station: float) -> str | None:
    nearest = None
    nearest_distance = None
    for start, end, element_id in run["spans"]:
        if start - 1e-6 <= station <= end + 1e-6:
            return element_id
        distance = start - station if station < start else station - end
        if nearest_distance is None or distance < nearest_distance:
            nearest = element_id
            nearest_distance = distance
    return nearest


def _spacing_element(run: dict) -> dict:
    if run["kind"] == "pipe_segment":
        diameter = run.get("outer_diameter_mm")
        return {
            "kind": "pipe_segment",
            "outer_diameter_mm": diameter,
            "outer_diameters_mm": [diameter] if diameter is not None else [],
        }
    if run.get("width_mm") is not None:
        return {
            "kind": "duct_segment",
            "shape": "rectangular",
            "width_mm": run.get("width_mm"),
            "height_mm": run.get("height_mm"),
        }
    return {
        "kind": "duct_segment",
        "shape": "round",
        "outer_diameter_mm": run.get("outer_diameter_mm"),
        "outer_diameters_mm": [run["outer_diameter_mm"]] if run.get("outer_diameter_mm") else [],
    }


def _size_label(run: dict) -> str:
    if run.get("outer_diameter_mm"):
        return f"OD {run['outer_diameter_mm']:g} mm"
    if run.get("width_mm") is not None:
        return f"{run['width_mm']:g} × {run['height_mm']:g} mm"
    return "size unknown"


def _near_run(run, obstacle, rod_radius_m, max_rod_length_m) -> bool:
    """Drop obstacles whose box cannot meet the rod anywhere along the run."""
    origin = run["origin"]
    end = _add(origin, _scale(run["direction"], run["length_m"]))
    rise = _section_rise(run)
    z_low = min(origin[2], end[2]) + rise + ROD_START_CLEARANCE_M
    z_high = max(origin[2], end[2]) + rise + max_rod_length_m
    low, high = _obstacle_bounds(obstacle)
    if high[2] < z_low or low[2] > z_high:
        return False
    return not (
        high[0] < min(origin[0], end[0]) - rod_radius_m
        or low[0] > max(origin[0], end[0]) + rod_radius_m
        or high[1] < min(origin[1], end[1]) - rod_radius_m
        or low[1] > max(origin[1], end[1]) + rod_radius_m
    )


def _obstacle_bounds(obstacle: dict) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    if obstacle.get("shape") == "cylinder":
        start, end = obstacle["start"], obstacle["end"]
        radius = obstacle["radius_m"]
        return (
            (
                min(start[0], end[0]) - radius,
                min(start[1], end[1]) - radius,
                min(start[2], end[2]) - radius,
            ),
            (
                max(start[0], end[0]) + radius,
                max(start[1], end[1]) + radius,
                max(start[2], end[2]) + radius,
            ),
        )
    return tuple(obstacle["min"]), tuple(obstacle["max"])


def _best_band_layout(
    length: float,
    maximum_spacing_m: float,
    blocked: list[tuple[float, float]],
) -> list[float] | None:
    """Even stations whose gaps lie in the 90–95% band and miss ``blocked``.

    The target inside the band is its middle. Layouts that still hold both
    ends of the run win over a shifted pattern with the same pitch. Among
    those, the smaller unsupported end length wins.
    """
    low = ADJUSTED_SPACING_MIN_RATIO * maximum_spacing_m
    high = ADJUSTED_SPACING_MAX_RATIO * maximum_spacing_m
    target = (low + high) / 2
    seen: set[tuple[float, ...]] = set()
    layouts: list[list[float]] = []

    def add(stations: list[float]) -> None:
        if len(stations) < 2:
            return
        spans = [stations[i + 1] - stations[i] for i in range(len(stations) - 1)]
        if any(span < low - 1e-6 or span > high + 1e-6 for span in spans):
            return
        if stations[0] > high + 1e-6 or length - stations[-1] > high + 1e-6:
            return
        if any(_is_blocked(station, blocked) for station in stations):
            return
        key = tuple(round(station, 5) for station in stations)
        if key in seen:
            return
        seen.add(key)
        layouts.append(stations)

    if length >= low:
        first_count = math.ceil(length / high - 1e-6)
        last_count = math.floor(length / low + 1e-6)
        for count in range(max(1, first_count), last_count + 1):
            step = length / count
            add([i * step for i in range(count + 1)])

    for spacing in _inclusive_steps(low, high, BAND_STEP_M):
        for offset in _inclusive_steps(0.0, high, BAND_STEP_M):
            stations = []
            station = offset
            while station <= length + 1e-9 and len(stations) < 10000:
                stations.append(station)
                nxt = station + spacing
                if nxt > length + 1e-9:
                    break
                station = nxt
            add(stations)

    if not layouts:
        return None

    def score(stations: list[float]) -> tuple:
        spans = [stations[i + 1] - stations[i] for i in range(len(stations) - 1)]
        mean = sum(spans) / len(spans)
        holds_ends = stations[0] <= 1e-4 and abs(stations[-1] - length) <= 1e-4
        cantilever = max(stations[0], length - stations[-1])
        return (
            0 if holds_ends else 1,
            abs(mean - target),
            cantilever,
            -len(stations),
            stations[0],
        )

    return min(layouts, key=score)


def _shift_station(
    index: int,
    stations: list[float],
    length: float,
    maximum_spacing_m: float,
    blocked: list[tuple[float, float]],
) -> tuple[float, str] | None:
    """Move one blocked station without letting a gap exceed 95% of the maximum."""
    cap = ADJUSTED_SPACING_MAX_RATIO * maximum_spacing_m
    band_low = ADJUSTED_SPACING_MIN_RATIO * maximum_spacing_m
    window_low, window_high = _shift_window(index, stations, length, cap)
    selectable = _clear_ranges(window_low, window_high, blocked, EDGE_CLEARANCE_M)
    if not selectable:
        return None
    original = stations[index]
    is_end = index == 0 or index == len(stations) - 1
    if not is_end:
        band_ranges = []
        previous = stations[index - 1]
        nxt = stations[index + 1]
        band_ranges.append((previous + band_low, previous + cap))
        band_ranges.append((nxt - cap, nxt - band_low))
        usable = []
        for start, end in band_ranges:
            usable.extend(_clip_ranges(selectable, start, end))
        if usable:
            return _closest(usable, original), "shifted_into_90_95"
    return _closest(selectable, original), "shifted_under_95"


def _shift_window(index: int, stations: list[float], length: float, cap: float) -> tuple[float, float]:
    previous = stations[index - 1] if index > 0 else None
    nxt = stations[index + 1] if index + 1 < len(stations) else None
    low = 0.0 if previous is None else previous + MIN_SUPPORT_GAP_M
    high = length if nxt is None else nxt - MIN_SUPPORT_GAP_M
    if previous is not None:
        high = min(high, previous + cap)
    else:
        high = min(high, cap)
    if nxt is not None:
        low = max(low, nxt - cap)
    else:
        low = max(low, length - cap)
    return low, high


def _clear_ranges(
    low: float,
    high: float,
    blocked: list[tuple[float, float]],
    edge: float,
) -> list[tuple[float, float]]:
    """Sub-ranges of ``[low, high]`` that sit outside every blocked interval.

    A range that touches a blocked interval is pulled back by ``edge``, so the
    chosen station is not still inside the closed interval.
    """
    if high < low:
        return []
    overlapping = [
        (max(start, low), min(end, high))
        for start, end in blocked
        if end >= low and start <= high
    ]
    overlapping = _merge_intervals(overlapping)
    ranges = []
    cursor = low
    for start, end in overlapping:
        if start > cursor:
            gap_end = start - edge
            if gap_end >= cursor:
                ranges.append((cursor, gap_end))
        cursor = max(cursor, end + edge)
    if cursor <= high:
        ranges.append((cursor, high))
    return [(start, end) for start, end in ranges if end >= start]


def _clip_ranges(
    ranges: list[tuple[float, float]],
    low: float,
    high: float,
) -> list[tuple[float, float]]:
    clipped = []
    for start, end in ranges:
        left = max(start, low)
        right = min(end, high)
        if right >= left:
            clipped.append((left, right))
    return clipped


def _closest(ranges: list[tuple[float, float]], target: float) -> float:
    best = None
    best_distance = None
    for start, end in ranges:
        if start <= target <= end:
            candidate = target
        elif target < start:
            candidate = start
        else:
            candidate = end
        distance = abs(candidate - target)
        if best is None or distance < best_distance - 1e-12 or (
            abs(distance - best_distance) <= 1e-12 and candidate < best
        ):
            best = candidate
            best_distance = distance
    if best is None:
        raise PlacementError("no station to choose")
    return best


def _is_blocked(station: float, intervals: list[tuple[float, float]]) -> bool:
    return any(start - 1e-9 <= station <= end + 1e-9 for start, end in intervals)


def _merge_intervals(intervals) -> list[tuple[float, float]]:
    ordered = sorted((start, end) for start, end in intervals if end >= start)
    merged: list[list[float]] = []
    for start, end in ordered:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(start, end) for start, end in merged]


def _inclusive_steps(start: float, stop: float, step: float) -> list[float]:
    values = []
    index = 0
    while True:
        value = start + index * step
        if value > stop + step * 1e-6:
            break
        values.append(value)
        index += 1
        if index > 100000:
            break
    if not values or values[-1] < stop - 1e-6:
        values.append(stop)
    return values


def _can_join(left: dict, right: dict) -> bool:
    if left["kind"] != right["kind"]:
        return False
    if not _same_size(left, right):
        return False
    return _collinear(left, right)


def _same_size(left: dict, right: dict) -> bool:
    left_diameter = left.get("outer_diameter_mm")
    right_diameter = right.get("outer_diameter_mm")
    if left_diameter is not None or right_diameter is not None:
        if left_diameter is None or right_diameter is None:
            return False
        return abs(left_diameter - right_diameter) <= 0.2
    if left.get("width_mm") is None or right.get("width_mm") is None:
        return False
    return (
        abs(left["width_mm"] - right["width_mm"]) <= 1.0
        and abs(left["height_mm"] - right["height_mm"]) <= 1.0
    )


def _collinear(left: dict, right: dict) -> bool:
    direction, length = _unit(_sub(left["end"], left["start"]))
    other, other_length = _unit(_sub(right["end"], right["start"]))
    if length < 1e-6 or other_length < 1e-6:
        return False
    if abs(_dot(direction, other)) < _ALIGNMENT_COS:
        return False
    for point in (right["start"], right["end"]):
        offset = _sub(point, left["start"])
        along = _dot(offset, direction)
        lateral = _norm(_sub(offset, _scale(direction, along)))
        if lateral > _LATERAL_TOLERANCE_M:
            return False
    return True


def _run_from_members(members: list[dict]) -> dict:
    points = [point for member in members for point in (member["start"], member["end"])]
    longest = max(members, key=_segment_length)
    axis, _length = _unit(_sub(longest["end"], longest["start"]))
    origin = min(points, key=lambda point: _dot(point, axis))
    far = max(points, key=lambda point: _dot(point, axis))
    delta = _sub(far, origin)
    length = _norm(delta)
    direction = _scale(delta, 1.0 / length) if length > 1e-9 else axis

    def project(point) -> float:
        return _dot(_sub(point, origin), direction)

    ordered = sorted(members, key=lambda member: min(project(member["start"]), project(member["end"])))
    spans = []
    for member in ordered:
        start = project(member["start"])
        end = project(member["end"])
        spans.append((min(start, end), max(start, end), member["global_id"]))
    systems = tuple(
        sorted({name for member in members for name in (member.get("system_names") or ())})
    )
    fittings = []
    for member in ordered:
        for fitting_id in member.get("fitting_ids") or []:
            if fitting_id not in fittings:
                fittings.append(fitting_id)
    first = ordered[0]
    return {
        "kind": first["kind"],
        "system_names": systems,
        "outer_diameter_mm": first.get("outer_diameter_mm"),
        "width_mm": first.get("width_mm"),
        "height_mm": first.get("height_mm"),
        "origin": origin,
        "direction": direction,
        "length_m": length,
        "element_ids": [member["global_id"] for member in ordered],
        "fitting_ids": fittings,
        "spans": spans,
    }


def _segment_length(segment: dict) -> float:
    return _norm(_sub(segment["end"], segment["start"]))


def _segments_from_model(model) -> list[dict]:
    from src.inventory_elements import (
        _category,
        _circle_diameter_mm,
        _neighbour_map,
        _placement_point,
        _port_direction,
        _ports,
        _rect_axes,
        _systems,
        classify,
        rectangular_cross_section,
    )

    neighbours = _neighbour_map(model)
    prepared = []
    for element in _by_type_if_present(model, "IfcFlowSegment"):
        kind = classify(element.Name, _category(element), element.is_a())
        if kind not in _LINEAR_KINDS:
            continue
        endpoints = _endpoints(model, element, _ports, _placement_point)
        if endpoints is None:
            continue
        diameter = _circle_diameter_mm(element)
        width = height = None
        if diameter is None:
            axes = _rect_axes(element)
            direction, _port_length = _port_direction(model, element)
            section = rectangular_cross_section(axes, direction) if axes and direction is not None else None
            if section is None:
                continue
            width = section["width_mm"]
            height = section["height_mm"]
        systems = tuple(sorted({system["name"] for system in _systems(element) if system.get("name")}))
        prepared.append(
            {
                "step_id": element.id(),
                "element": element,
                "global_id": element.GlobalId,
                "kind": kind,
                "system_names": systems,
                "start": endpoints[0],
                "end": endpoints[1],
                "outer_diameter_mm": diameter,
                "width_mm": width,
                "height_mm": height,
            }
        )

    segment_ids = {item["step_id"] for item in prepared}
    for item in prepared:
        adjacent, fittings = _linked_ids(item["element"], neighbours, segment_ids)
        item["adjacent_ids"] = adjacent
        item["fitting_ids"] = fittings
        del item["element"]
        del item["step_id"]
    return prepared


def _endpoints(model, element, ports, placement_point):
    points = []
    for port in ports(model, element):
        point = placement_point(port)
        if point is None:
            continue
        points.append((float(point[0]), float(point[1]), float(point[2])))
    best = None
    best_distance = -1.0
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            distance = _norm(_sub(points[j], points[i]))
            if distance > best_distance:
                best = (points[i], points[j])
                best_distance = distance
    if best is None or best_distance < 1e-4:
        return None
    return best


def _linked_ids(element, neighbours, segment_ids) -> tuple[list[str], list[str]]:
    """Next segments through fittings, and the fittings that touch this segment.

    Only the fittings on the segment itself are ignored during the clash test.
    A radiator or terminal further along stays an obstacle. The walk still
    crosses a chain of fittings so two pipes with a coupling between them are
    neighbours.
    """
    adjacent = []
    fittings = []
    seen = {element.id()}
    frontier = []
    for other in neighbours.get(element.id(), []):
        if other.id() in seen:
            continue
        seen.add(other.id())
        if other.id() in segment_ids:
            adjacent.append(other.GlobalId)
        else:
            fittings.append(other.GlobalId)
            frontier.append(other)
    while frontier:
        nxt = []
        for current in frontier:
            for other in neighbours.get(current.id(), []):
                if other.id() in seen:
                    continue
                seen.add(other.id())
                if other.id() in segment_ids:
                    adjacent.append(other.GlobalId)
                else:
                    nxt.append(other)
        frontier = nxt
    return adjacent, fittings


def _obstacles_for_segments(segments: list[dict]) -> list[dict]:
    obstacles = []
    for segment in segments:
        if segment.get("outer_diameter_mm"):
            obstacles.append(
                {
                    "element_id": segment["global_id"],
                    "shape": "cylinder",
                    "start": segment["start"],
                    "end": segment["end"],
                    "radius_m": segment["outer_diameter_mm"] / 2000.0,
                }
            )
        elif segment.get("width_mm") is not None and segment.get("height_mm") is not None:
            low, high = _rectangular_bounds(
                segment["start"],
                segment["end"],
                segment["width_mm"] / 1000.0,
                segment["height_mm"] / 1000.0,
            )
            obstacles.append(
                {
                    "element_id": segment["global_id"],
                    "shape": "box",
                    "min": low,
                    "max": high,
                }
            )
    return obstacles


def _rectangular_bounds(start, end, width_m, height_m):
    """Axis-aligned box of a straight rectangular duct."""
    delta = _sub(end, start)
    half_width = width_m / 2.0
    half_height = height_m / 2.0
    horizontal = math.hypot(delta[0], delta[1])
    if horizontal < 1e-9:
        pad = math.hypot(half_width, half_height)
        low_z = min(start[2], end[2])
        high_z = max(start[2], end[2])
        return (
            (start[0] - pad, start[1] - pad, low_z),
            (start[0] + pad, start[1] + pad, high_z),
        )
    across_x = abs(-delta[1] / horizontal) * half_width
    across_y = abs(delta[0] / horizontal) * half_width
    length = math.hypot(horizontal, delta[2])
    vertical = half_height * (horizontal / length) + half_width * (abs(delta[2]) / length)
    return (
        (
            min(start[0], end[0]) - across_x,
            min(start[1], end[1]) - across_y,
            min(start[2], end[2]) - vertical,
        ),
        (
            max(start[0], end[0]) + across_x,
            max(start[1], end[1]) + across_y,
            max(start[2], end[2]) + vertical,
        ),
    )


def _other_flow_boxes(model, segment_global_ids: set[str]) -> list[dict]:
    from src.inventory_elements import _world_bbox

    boxes = []
    for class_name in (
        "IfcFlowSegment",
        "IfcFlowFitting",
        "IfcFlowTerminal",
        "IfcFlowController",
        "IfcEnergyConversionDevice",
    ):
        for element in _by_type_if_present(model, class_name):
            if element.GlobalId in segment_global_ids:
                continue
            box = _world_bbox(element)
            if box is None:
                continue
            boxes.append(_box_obstacle(element.GlobalId, box))
    return boxes


def _structural_boxes(model) -> list[dict]:
    from src.inventory_elements import _world_bbox

    boxes = []
    for class_name in ("IfcBeam", "IfcMember", "IfcColumn"):
        for element in _by_type_if_present(model, class_name):
            box = _world_bbox(element)
            if box is None:
                continue
            boxes.append(_box_obstacle(element.GlobalId, box))
    return boxes


def _box_obstacle(element_id: str, box: tuple) -> dict:
    xmin, xmax, ymin, ymax, zmin, zmax = box
    return {
        "element_id": element_id,
        "shape": "box",
        "min": (xmin, ymin, zmin),
        "max": (xmax, ymax, zmax),
    }


def _by_type_if_present(model, class_name: str):
    import ifcopenshell

    schema = ifcopenshell.schema_by_name(model.schema)
    names = {entity.name() for entity in schema.entities()}
    if class_name not in names:
        return []
    return model.by_type(class_name)


def _print_summary(plan: dict, out: Path) -> None:
    counts: dict[str, int] = {}
    for run in plan["runs"]:
        counts[run["status"]] = counts.get(run["status"], 0) + 1
    unresolved = sum(1 for point in plan["points"] if not point["clear"])
    print(
        f"runs {len(plan['runs'])} {counts} · "
        f"points {len(plan['points'])} ({unresolved} clashing) → {out}"
    )


def _round_numbers(value):
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, dict):
        return {key: _round_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_round_numbers(item) for item in value]
    if isinstance(value, tuple):
        return [_round_numbers(item) for item in value]
    return value


def _round_point(point) -> tuple[float, float, float]:
    return (round(point[0], 4), round(point[1], 4), round(point[2], 4))


def _sub(left, right) -> tuple[float, float, float]:
    return (left[0] - right[0], left[1] - right[1], left[2] - right[2])


def _add(left, right) -> tuple[float, float, float]:
    return (left[0] + right[0], left[1] + right[1], left[2] + right[2])


def _scale(vector, factor: float) -> tuple[float, float, float]:
    return (vector[0] * factor, vector[1] * factor, vector[2] * factor)


def _dot(left, right) -> float:
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2]


def _norm(vector) -> float:
    return math.sqrt(_dot(vector, vector))


def _unit(vector) -> tuple[tuple[float, float, float], float]:
    length = _norm(vector)
    if length < 1e-12:
        return (0.0, 0.0, 0.0), 0.0
    return _scale(vector, 1.0 / length), length


def _segment_distance(a0, a1, b0, b1) -> float:
    """Shortest distance between two finite segments.

    The clamping follows Ericson, Real-Time Collision Detection: after one
    endpoint is pinned to a segment end, the other parameter is recomputed.
    """
    d1 = _sub(a1, a0)
    d2 = _sub(b1, b0)
    difference = _sub(a0, b0)
    a = _dot(d1, d1)
    e = _dot(d2, d2)
    f = _dot(d2, difference)
    if a <= 1e-12 and e <= 1e-12:
        return _norm(_sub(a0, b0))
    if a <= 1e-12:
        s = 0.0
        t = _clamp(f / e, 0.0, 1.0)
    elif e <= 1e-12:
        t = 0.0
        s = _clamp(-_dot(d1, difference) / a, 0.0, 1.0)
    else:
        b = _dot(d1, d2)
        c = _dot(d1, difference)
        denom = a * e - b * b
        s = 0.0 if denom == 0.0 else _clamp((b * f - c * e) / denom, 0.0, 1.0)
        t = (b * s + f) / e
        if t < 0.0:
            t = 0.0
            s = _clamp(-c / a, 0.0, 1.0)
        elif t > 1.0:
            t = 1.0
            s = _clamp((b - c) / a, 0.0, 1.0)
    closest_a = _add(a0, _scale(d1, s))
    closest_b = _add(b0, _scale(d2, t))
    return _norm(_sub(closest_a, closest_b))


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


if __name__ == "__main__":
    raise SystemExit(main())
