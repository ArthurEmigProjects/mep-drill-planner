"""Change a placed hanger list without running placement again.

A station edit slides the hanger along its run and keeps whatever offset the
placement gave it, so a wall fixing stays on the wall. An X/Y/Z edit moves
the point itself and leaves the station alone. Delete drops that hanger.
Replace swaps in a whole list, which is how undo puts the previous hangers back.
"""

from __future__ import annotations

import copy

from .mounting_ifc import annotate_mountings
from .mounting_points import _annotate_gaps, _round_numbers, _status_from_points

ALLOWED_REASONS = frozenset(
    {
        "regular_70",
        "respaced_90_95",
        "shifted_into_90_95",
        "shifted_under_95",
        "unresolved_clash",
        "user_moved",
    }
)


class HangerEditError(ValueError):
    """The edit does not fit the saved placement."""


def attach_mounting_counts(plan: dict) -> dict:
    """Add the counts the page shows on top of a placement."""
    counts: dict[str, int] = {}
    for point in plan["points"]:
        reason = point["reason"]
        counts[reason] = counts.get(reason, 0) + 1
    plan["count"] = len(plan["points"])
    plan["run_count"] = len(plan["runs"])
    plan["reason_counts"] = counts
    plan["adjusted_count"] = sum(
        count for reason, count in counts.items() if reason != "regular_70"
    )
    plan["clash_count"] = sum(1 for point in plan["points"] if not point["clear"])
    return plan


def edit_hangers(plan: dict, operation: dict) -> dict:
    """Return a new plan with one move, one delete, or a replaced hanger list."""
    if not isinstance(plan, dict) or not isinstance(operation, dict):
        raise HangerEditError("Edit must describe one change to a placement.")
    if not isinstance(plan.get("points"), list) or not isinstance(plan.get("runs"), list):
        raise HangerEditError("The saved placement has no hanger list.")
    working = copy.deepcopy(plan)
    kind = operation.get("op")
    if kind == "move":
        _move(working, operation)
    elif kind == "delete":
        _delete(working, operation)
    elif kind == "replace":
        _replace(working, operation)
    else:
        raise HangerEditError("Unknown edit.")
    _refresh(working)
    annotate_mountings(working)
    return _round_numbers(working)


def _move(plan: dict, operation: dict) -> None:
    point = _hanger(plan, operation)
    run = _run(plan, point["run_id"])
    if operation.get("station_m") is not None:
        station = _station(operation.get("station_m"), run)
        delta = station - float(point["station_m"])
        direction = _direction(run)
        point["x"] = float(point["x"]) + direction[0] * delta
        point["y"] = float(point["y"]) + direction[1] * delta
        point["z"] = float(point["z"]) + direction[2] * delta
        point["station_m"] = station
    elif all(operation.get(axis) is not None for axis in ("x", "y", "z")):
        point["x"] = _finite(operation.get("x"), "X")
        point["y"] = _finite(operation.get("y"), "Y")
        point["z"] = _finite(operation.get("z"), "Z")
    else:
        raise HangerEditError("Give a station along the run, or X, Y and Z.")
    point["reason"] = "user_moved"


def _delete(plan: dict, operation: dict) -> None:
    point = _hanger(plan, operation)
    plan["points"] = [item for item in plan["points"] if item["id"] != point["id"]]


def _replace(plan: dict, operation: dict) -> None:
    raw_points = operation.get("points")
    if not isinstance(raw_points, list):
        raise HangerEditError("Undo needs the hanger list.")
    plan["points"] = [_clean_point(plan, raw) for raw in raw_points]


def _refresh(plan: dict) -> None:
    runs = {run["id"]: run for run in plan["runs"]}
    grouped: dict[str, list] = {}
    seen: set[str] = set()
    for point in plan["points"]:
        hanger_id = str(point.get("id") or "")
        if hanger_id in seen:
            raise HangerEditError(f"Hanger {hanger_id} is listed twice.")
        seen.add(hanger_id)
        if point.get("run_id") not in runs:
            raise HangerEditError(f"Hanger {hanger_id} is not on a known run.")
        grouped.setdefault(point["run_id"], []).append(point)
    for run in plan["runs"]:
        owned = grouped.get(run["id"], [])
        had = bool(run.get("point_ids"))
        if not owned and not had:
            continue
        ordered = sorted(owned, key=lambda item: (float(item["station_m"]), str(item["id"])))
        _annotate_gaps(ordered)
        run["point_ids"] = [item["id"] for item in ordered]
        if ordered:
            length = _length(run)
            run["cantilever_start_m"] = ordered[0]["station_m"]
            run["cantilever_end_m"] = length - float(ordered[-1]["station_m"])
            run["status"] = _status_from_points(ordered)
        else:
            run.pop("cantilever_start_m", None)
            run.pop("cantilever_end_m", None)
            run["status"] = "no_hangers"


def _clean_point(plan: dict, raw) -> dict:
    if not isinstance(raw, dict):
        raise HangerEditError("Each hanger must be an object.")
    hanger_id = str(raw.get("id") or "").strip()
    if not hanger_id:
        raise HangerEditError("A hanger is missing an id.")
    run = _run(plan, str(raw.get("run_id") or ""))
    point = dict(raw)
    point["id"] = hanger_id
    point["run_id"] = run["id"]
    point["x"] = _finite(raw.get("x"), "X")
    point["y"] = _finite(raw.get("y"), "Y")
    point["z"] = _finite(raw.get("z"), "Z")
    point["station_m"] = _station(raw.get("station_m"), run)
    reason = str(raw.get("reason") or "user_moved")
    if reason not in ALLOWED_REASONS:
        raise HangerEditError(f"Unknown hanger reason {reason}.")
    point["reason"] = reason
    if "clear" not in raw:
        point["clear"] = reason != "unresolved_clash"
    else:
        point["clear"] = bool(raw.get("clear"))
    return point


def _hanger(plan: dict, operation: dict) -> dict:
    hanger_id = str(operation.get("hanger_id") or "").strip()
    if not hanger_id:
        raise HangerEditError("Choose a hanger.")
    for point in plan["points"]:
        if str(point.get("id")) == hanger_id:
            return point
    raise HangerEditError(f"No hanger named {hanger_id}.")


def _run(plan: dict, run_id: str) -> dict:
    for run in plan["runs"]:
        if run.get("id") == run_id:
            return run
    raise HangerEditError(f"No run named {run_id}.")


def _length(run: dict) -> float:
    try:
        return float(run["length_m"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HangerEditError(f"Run {run.get('id')} has no length.") from exc


def _direction(run: dict) -> list[float]:
    raw = run.get("direction")
    if not isinstance(raw, (list, tuple)) or len(raw) != 3:
        raise HangerEditError(
            f"Run {run.get('id')} has no direction. Edit X, Y and Z instead."
        )
    return [_finite(raw[0], "Direction"), _finite(raw[1], "Direction"), _finite(raw[2], "Direction")]


def _station(value, run: dict) -> float:
    station = _finite(value, "Station")
    length = _length(run)
    if station < -1e-4 or station > length + 1e-4:
        raise HangerEditError(f"Station must sit on the run, from 0 to {length:.3f} m.")
    return min(max(station, 0.0), length)


def _finite(value, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise HangerEditError(f"{label} must be a number.") from exc
    if number != number or number in {float("inf"), float("-inf")}:
        raise HangerEditError(f"{label} must be a finite number.")
    return number
