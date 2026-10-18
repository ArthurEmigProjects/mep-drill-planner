"""Inventory mountable MEP elements in the Zenodo duplex IFC models.

The files are IFC2X3, so pipes and ducts are IfcFlowSegment / IfcFlowFitting
rather than the IFC4 classes IfcPipeSegment and IfcDuctSegment. Nominal
diameter is not a reliable property on segments (it is missing, or stored as
an empty-unwrapped IfcPropertyListValue on some fittings). Sizes below come
from the swept profile, and for rectangular ducts from the port-to-port axis,
because the Revit export puts the run length into the profile instead of the
extrusion depth.

Run from the repo root:

    python -m src.inventory_elements
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data" / "inventory" / "zenodo_duplex_mountable.json"

# Arthur's commit names, then the names already used in examples/.
MODEL_CANDIDATES = {
    "piping": ("Piping.ifc", "zenodo-duplex-piping.ifc"),
    "ventilation": ("Ventilation.ifc", "zenodo-duplex-ventilation.ifc"),
    "heating_and_cooling": (
        "HeatingAndCooling.ifc",
        "zenodo-duplex-heating-and-cooling.ifc",
    ),
    "architecture": ("Architecture.ifc", "zenodo-duplex-architecture.ifc"),
}

# ASTM B88 outside diameters (inch fraction × 25.4 mm), used only as a note
# when a modeled diameter lands on one. The IFC itself has no material name.
COPPER_OD_MM = {
    9.525: '3/8 in OD (1/4 in nominal copper tube)',
    12.7: '1/2 in OD (3/8 in nominal copper tube)',
    15.875: '5/8 in OD (1/2 in nominal copper tube)',
    19.05: '3/4 in OD (5/8 in nominal copper tube)',
    22.225: '7/8 in OD (3/4 in nominal copper tube)',
    41.275: '1.625 in OD (1-1/2 in nominal copper tube)',
    104.775: '4.125 in OD (4 in nominal copper tube)',
}

DATASET = {
    "title": "DuplexModel+MEP",
    "creators": "Teclaw, Wojciech",
    "year": 2024,
    "doi": "10.5281/zenodo.10610773",
    "url": "https://zenodo.org/records/10610773",
    "license": "CC BY 4.0",
}


def resolve_models(examples: Path | None = None) -> dict[str, Path]:
    folder = examples or (ROOT / "examples")
    found = {}
    missing = []
    for key, names in MODEL_CANDIDATES.items():
        path = next((folder / name for name in names if (folder / name).is_file()), None)
        if path is None:
            missing.append(key)
        else:
            found[key] = path
    if missing:
        raise SystemExit(
            "Missing IFC model(s): "
            + ", ".join(missing)
            + f". Looked in {folder} for {MODEL_CANDIDATES}."
        )
    return found


def _as_vec(direction, size: int = 3):
    import numpy as np

    if direction is None:
        return None
    values = list(direction.DirectionRatios)
    vector = np.zeros(size, dtype=float)
    vector[: min(size, len(values))] = values[:size]
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        return vector
    return vector / norm


def _placement_point(element):
    import ifcopenshell.util.placement as placement
    import numpy as np

    if element.ObjectPlacement is None:
        return None
    matrix = placement.get_local_placement(element.ObjectPlacement)
    return np.array(matrix[:3, 3], dtype=float)


def _psets(element) -> dict:
    import ifcopenshell.util.element as element_util

    try:
        return element_util.get_psets(element) or {}
    except Exception:
        return {}


def _category(element) -> str | None:
    requirements = _psets(element).get("Pset_ProductRequirements") or {}
    category = requirements.get("Category")
    return str(category) if category else None


def _roughness_m(element) -> float | None:
    shading = _psets(element).get("Pset_ElementShading") or {}
    value = shading.get("Roughness")
    return float(value) if isinstance(value, (int, float)) else None


def _list_and_enum_props(element) -> dict:
    """Read property types IfcOpenShell's get_psets leaves empty.

    NominalDiameter is an IfcPropertyListValue (metres). Shape is an
    IfcPropertyEnumeratedValue. Both come back as None from get_psets.
    """
    found: dict = {}
    for rel in getattr(element, "IsDefinedBy", []) or []:
        if not rel.is_a("IfcRelDefinesByProperties"):
            continue
        definition = rel.RelatingPropertyDefinition
        if not definition.is_a("IfcPropertySet"):
            continue
        for prop in definition.HasProperties or []:
            if prop.is_a("IfcPropertyListValue") and prop.Name == "NominalDiameter":
                values = []
                for wrapped in prop.ListValues or []:
                    raw = getattr(wrapped, "wrappedValue", None)
                    if raw is not None:
                        values.append(round(float(raw) * 1000.0, 3))
                if values:
                    found.setdefault("nominal_diameter_mm", []).extend(values)
            elif prop.is_a("IfcPropertyEnumeratedValue") and prop.Name == "Shape":
                for wrapped in prop.EnumerationValues or []:
                    raw = getattr(wrapped, "wrappedValue", None)
                    if raw:
                        found["shape_property"] = str(raw)
    return found


def _type_info(element) -> dict:
    info = {"type_name": None, "predefined_type": None}
    for rel in getattr(element, "IsTypedBy", []) or []:
        relating = rel.RelatingType
        info["type_name"] = getattr(relating, "Name", None)
        predefined = getattr(relating, "PredefinedType", None)
        if predefined is not None:
            info["predefined_type"] = str(predefined)
    # IFC2X3 flow occurrences have no PredefinedType of their own.
    own = getattr(element, "PredefinedType", None)
    if own is not None:
        info["predefined_type"] = str(own)
    return info


def _systems(element) -> list[dict]:
    systems = []
    for rel in getattr(element, "HasAssignments", []) or []:
        if not rel.is_a("IfcRelAssignsToGroup"):
            continue
        group = rel.RelatingGroup
        if group is None or not group.is_a("IfcSystem"):
            continue
        systems.append(
            {
                "name": group.Name,
                "object_type": getattr(group, "ObjectType", None),
            }
        )
    return systems


def _material_name(element) -> str | None:
    for rel in getattr(element, "HasAssociations", []) or []:
        if not rel.is_a("IfcRelAssociatesMaterial"):
            continue
        name = _material_label(rel.RelatingMaterial)
        if name:
            return name
    for rel in getattr(element, "IsTypedBy", []) or []:
        relating = rel.RelatingType
        for assoc in getattr(relating, "HasAssociations", []) or []:
            if assoc.is_a("IfcRelAssociatesMaterial"):
                name = _material_label(assoc.RelatingMaterial)
                if name:
                    return name
    return None


def _material_label(material) -> str | None:
    if material is None:
        return None
    if material.is_a("IfcMaterial"):
        name = (material.Name or "").strip()
        return name or None
    if material.is_a("IfcMaterialList"):
        for item in material.Materials or []:
            label = _material_label(item)
            if label:
                return label
    if material.is_a("IfcMaterialLayerSetUsage"):
        return _material_label(material.ForLayerSet)
    if material.is_a("IfcMaterialLayerSet"):
        for layer in material.MaterialLayers or []:
            label = _material_label(layer.Material)
            if label:
                return label
    return None


def _walk(entity, seen: set | None = None):
    if seen is None:
        seen = set()
    if entity is None or not hasattr(entity, "is_a"):
        return
    identifier = entity.id()
    if identifier in seen:
        return
    seen.add(identifier)
    yield entity
    for attr in entity:
        if hasattr(attr, "is_a"):
            yield from _walk(attr, seen)
        elif isinstance(attr, (list, tuple)):
            for item in attr:
                if hasattr(item, "is_a"):
                    yield from _walk(item, seen)


def _circle_diameter_mm(element) -> float | None:
    for entity in _walk(element.Representation):
        if entity.is_a("IfcCircleProfileDef"):
            return round(float(entity.Radius) * 2000.0, 3)
    return None


def _rect_axes(element) -> dict | None:
    """Local axes of the single rectangular extrusion, with lengths in metres."""
    import numpy as np

    solids = [
        entity
        for entity in _walk(element.Representation)
        if entity.is_a("IfcExtrudedAreaSolid")
        and entity.SweptArea.is_a("IfcRectangleProfileDef")
    ]
    if len(solids) != 1:
        return None
    solid = solids[0]
    profile = solid.SweptArea
    position = solid.Position
    axis = _as_vec(position.Axis) if position and position.Axis else np.array([0.0, 0.0, 1.0])
    ref = (
        _as_vec(position.RefDirection)
        if position and position.RefDirection
        else np.array([1.0, 0.0, 0.0])
    )
    y_axis = np.cross(axis, ref)
    profile_position = profile.Position
    if profile_position is not None and profile_position.RefDirection is not None:
        profile_ref = _as_vec(profile_position.RefDirection, 2)
    else:
        profile_ref = np.array([1.0, 0.0])
    profile_x = profile_ref[0] * ref + profile_ref[1] * y_axis
    profile_y = (-profile_ref[1]) * ref + profile_ref[0] * y_axis
    extruded = _as_vec(solid.ExtrudedDirection)
    extruded_world = extruded[0] * ref + extruded[1] * y_axis + extruded[2] * axis
    return {
        "px": (profile_x, float(profile.XDim)),
        "py": (profile_y, float(profile.YDim)),
        "ex": (extruded_world, float(solid.Depth)),
    }


def _ports(model, element) -> list:
    ports = []
    for rel in model.get_inverse(element):
        if rel.is_a("IfcRelConnectsPortToElement"):
            ports.append(rel.RelatingPort)
    return ports


def _port_direction(model, element):
    import numpy as np

    points = []
    for port in _ports(model, element):
        point = _placement_point(port)
        if point is not None:
            points.append(point)
    if len(points) < 2:
        return None, None
    delta = points[1] - points[0]
    length = float(np.linalg.norm(delta))
    if length == 0.0:
        return None, None
    return delta / length, length


def rectangular_cross_section(axes: dict, port_direction) -> dict | None:
    """Split a rectangular extrusion into width, height and run length.

    The export's profile is not the duct cross-section: one of the three edge
    lengths is the run. The port-to-port direction picks that edge. Of the
    other two, the one closer to world Z is the height.
    """
    import numpy as np

    if port_direction is None:
        return None
    length_key = max(
        axes, key=lambda key: abs(float(np.dot(axes[key][0], port_direction)))
    )
    cross = [(key, axes[key][0], axes[key][1]) for key in axes if key != length_key]
    cross.sort(key=lambda item: -abs(float(np.dot(item[1], np.array([0.0, 0.0, 1.0])))))
    return {
        "width_mm": round(cross[1][2] * 1000.0, 1),
        "height_mm": round(cross[0][2] * 1000.0, 1),
        "length_m": round(axes[length_key][1], 4),
    }


def _bbox_mm(element) -> tuple[float, float, float] | None:
    import ifcopenshell.geom

    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    try:
        shape = ifcopenshell.geom.create_shape(settings, element)
    except Exception:
        return None
    verts = shape.geometry.verts
    if len(verts) < 3:
        return None
    xs, ys, zs = verts[0::3], verts[1::3], verts[2::3]
    return (
        round((max(xs) - min(xs)) * 1000.0, 1),
        round((max(ys) - min(ys)) * 1000.0, 1),
        round((max(zs) - min(zs)) * 1000.0, 1),
    )


def _world_bbox(element):
    import ifcopenshell.geom

    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    try:
        shape = ifcopenshell.geom.create_shape(settings, element)
    except Exception:
        return None
    verts = shape.geometry.verts
    if len(verts) < 3:
        return None
    xs, ys, zs = verts[0::3], verts[1::3], verts[2::3]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def _mesh_minor_axis_mm(element) -> float | None:
    """Smallest local bounding-box edge of a faceted flex duct.

    Straight flex ducts expose the tube diameter as one bbox edge. A duct that
    bends in all three axes does not, so this returns None unless one edge is
    in the 100–180 mm band and strictly smaller than the other two.
    """
    points = []
    for entity in _walk(element.Representation):
        if entity.is_a("IfcCartesianPoint"):
            coords = list(entity.Coordinates)
            if len(coords) >= 3:
                points.append(coords[:3])
    if len(points) < 4:
        return None
    import numpy as np

    array = np.array(points, dtype=float)
    extents = (array.max(0) - array.min(0)) * 1000.0
    ordered = sorted(float(value) for value in extents)
    minor, middle, major = ordered
    if 100.0 <= minor <= 180.0 and minor < middle - 20.0 and minor < major - 20.0:
        return round(minor, 1)
    return None


def classify(name: str | None, category: str | None, ifc_class: str) -> str:
    text = (name or "").lower()
    cat = (category or "").lower()
    if "radiator" in text:
        return "radiator"
    if "flex" in text or "flex duct" in cat:
        return "duct_flex"
    if cat == "ducts" or text.startswith("rectangular duct") or text.startswith("round duct"):
        return "duct_segment"
    # Polish duct families are "Kolano prostokątne" / "Redukcja prostokąt w okrąg".
    # Pipe fittings in the same model are "Kolano - ogólne", so the bare word
    # is not enough to call something a duct.
    if "duct fitting" in cat or any(token in text for token in ("prostok", "okrąg", "okrag")):
        return "duct_fitting"
    if "air terminal" in cat or "dyfuzor" in text or "diffus" in text or text.startswith(
        ("exhaust:", "supply:")
    ):
        return "air_terminal"
    if "damper" in text or "duct accessor" in cat:
        return "duct_accessory"
    if ifc_class == "IfcEnergyConversionDevice" or text.startswith("stove"):
        return "stove"
    if "ahu" in text or "air handling" in text or "airhandling" in text:
        return "air_handling_unit"
    if "waterheater" in text.replace(" ", "") or "water heater" in text:
        return "water_heater"
    if any(token in text for token in ("sink", "lavatory", "water closet")):
        return "sanitary_fixture"
    if (
        "pipe fitting" in cat
        or "elbow" in text
        or "transition" in text
        or "tee" in text
        or "endcap" in text
        or "end cap" in text
    ):
        return "pipe_fitting"
    if "valve" in text or "meter" in text or "pipe accessor" in cat:
        return "pipe_accessory"
    if cat == "pipes" or "pipe types" in text:
        return "pipe_segment"
    return "other"


def _family(kind: str, name: str | None) -> str | None:
    text = (name or "").lower()
    if kind == "duct_segment":
        if text.startswith("round"):
            return "round"
        if text.startswith("rectangular"):
            return "rectangular"
    if kind == "duct_flex":
        return "round_flex"
    if "elbow" in text or "kolano" in text:
        return "elbow"
    if "transition" in text or "redukcja" in text:
        return "transition"
    if "czwórnik" in text or "czwornik" in text or "cross" in text:
        return "cross"
    if "tee" in text or "trójnik" in text or "trojnik" in text:
        return "tee"
    if "endcap" in text or "end cap" in text:
        return "cap"
    if "damper" in text:
        return "volume_damper"
    if "dyfuzor zasil" in text or "supply diffus" in text or text.startswith("supply"):
        return "supply"
    if "dyfuzor zwrot" in text or "return diffus" in text:
        return "return"
    if text.startswith("exhaust"):
        return "exhaust"
    if kind == "radiator":
        return "panel"
    return None


def _copper_note(diameter_mm: float | None) -> str | None:
    if diameter_mm is None:
        return None
    for listed, label in COPPER_OD_MM.items():
        if abs(diameter_mm - listed) <= 0.02:
            return (
                f"Modeled outside diameter {diameter_mm} mm matches {label}. "
                "The IFC material name is empty, so this is a size observation only."
            )
    if abs(diameter_mm - 15.0) <= 0.02:
        return (
            "Modeled outside diameter is exactly 15.0 mm, the outside diameter "
            "of metric 15 mm copper tube, unlike the inch-series diameters of "
            "the other pipe segments. Material is still not stored in the IFC."
        )
    if abs(diameter_mm - 9.52) <= 0.02:
        return (
            "Modeled outside diameter is 9.52 mm, 0.005 mm below 3/8 in "
            "(9.525 mm). Treated as the modeled value, not rounded up."
        )
    return None


def _neighbour_map(model) -> dict[int, list]:
    """element id → elements connected through a single port pair."""
    neighbours: dict[int, list] = defaultdict(list)
    for rel in model.by_type("IfcRelConnectsPorts"):
        left = rel.RelatingPort
        right = rel.RelatedPort
        left_element = _port_host(model, left)
        right_element = _port_host(model, right)
        if left_element is None or right_element is None:
            continue
        if left_element.id() == right_element.id():
            continue
        neighbours[left_element.id()].append(right_element)
        neighbours[right_element.id()].append(left_element)
    return neighbours


def _port_host(model, port):
    if port is None:
        return None
    for rel in model.get_inverse(port):
        if rel.is_a("IfcRelConnectsPortToElement"):
            return rel.RelatedElement
    return None


def _connected_diameters(element, neighbours, diameter_of: dict[int, float]) -> list[float]:
    """Outside diameters of sized segments reached from each connection.

    Walks through fittings (up to four hops) so a reducer reports both ends
    even when another fitting sits between it and the pipe.
    """
    found = []
    seen = {element.id()}
    frontier = [element]
    for _ in range(4):
        nxt = []
        for current in frontier:
            for other in neighbours.get(current.id(), []):
                if other.id() in seen:
                    continue
                seen.add(other.id())
                diameter = diameter_of.get(other.id())
                if diameter is not None:
                    found.append(diameter)
                else:
                    nxt.append(other)
        frontier = nxt
    # Unique, stable order.
    return sorted(set(found))


def _connected_duct_sizes(element, neighbours, duct_size_of: dict[int, dict]) -> list[dict]:
    found = []
    seen = {element.id()}
    frontier = [element]
    for _ in range(3):
        nxt = []
        for current in frontier:
            for other in neighbours.get(current.id(), []):
                if other.id() in seen:
                    continue
                seen.add(other.id())
                size = duct_size_of.get(other.id())
                if size is not None:
                    found.append(size)
                else:
                    nxt.append(other)
        frontier = nxt
    unique = []
    for size in found:
        if size not in unique:
            unique.append(size)
    return unique


def _blank_group() -> dict:
    return {
        "count": 0,
        "systems": Counter(),
        "example_ids": [],
        "total_length_m": 0.0,
        "assumptions": [],
    }


def _key_from(parts: dict) -> tuple:
    return tuple(sorted((name, _freeze(value)) for name, value in parts.items()))


def _freeze(value):
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze(item)) for key, item in value.items()))
    return value


def _unfreeze_key(key: tuple) -> dict:
    return {name: _thaw(value) for name, value in key}


def _thaw(value):
    if isinstance(value, tuple):
        if (
            value
            and all(isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str) for item in value)
        ):
            return {item[0]: _thaw(item[1]) for item in value}
        return [_thaw(item) for item in value]
    return value


def inventory_mep(path: Path) -> dict:
    import ifcopenshell

    model = ifcopenshell.open(str(path))
    neighbours = _neighbour_map(model)
    occurrences = []
    for ifc_class in (
        "IfcFlowSegment",
        "IfcFlowFitting",
        "IfcFlowTerminal",
        "IfcFlowController",
        "IfcEnergyConversionDevice",
        "IfcBuildingElementProxy",
    ):
        if ifc_class not in {entity.name() for entity in ifcopenshell.schema_by_name(model.schema).entities()}:
            continue
        occurrences.extend(model.by_type(ifc_class))

    prepared = []
    diameter_of: dict[int, float] = {}
    duct_size_of: dict[int, dict] = {}
    for element in occurrences:
        name = element.Name
        category = _category(element)
        kind = classify(name, category, element.is_a())
        extra = _list_and_enum_props(element)
        type_info = _type_info(element)
        record = {
            "element": element,
            "id": element.id(),
            "global_id": element.GlobalId,
            "ifc_class": element.is_a(),
            "name": name,
            "kind": kind,
            "family": _family(kind, name),
            "category": category,
            "predefined_type": type_info["predefined_type"],
            "type_name": type_info["type_name"],
            "material": _material_name(element),
            "roughness_m": _roughness_m(element),
            "systems": _systems(element),
            "shape_property": extra.get("shape_property"),
            "nominal_diameter_property_mm": sorted(set(extra.get("nominal_diameter_mm") or [])),
            "outer_diameter_mm": None,
            "width_mm": None,
            "height_mm": None,
            "mesh_minor_axis_mm": None,
            "bbox_mm": None,
            "length_m": None,
            "size_method": None,
            "assumptions": [],
        }
        if kind in {"pipe_segment", "duct_segment"}:
            diameter = _circle_diameter_mm(element)
            if diameter is not None:
                record["outer_diameter_mm"] = diameter
                record["shape"] = "round"
                record["size_method"] = "circle_profile"
                if kind == "pipe_segment":
                    diameter_of[element.id()] = diameter
                    note = _copper_note(diameter)
                    if note:
                        record["assumptions"].append(note)
            else:
                axes = _rect_axes(element)
                direction, length = _port_direction(model, element)
                section = rectangular_cross_section(axes, direction) if axes else None
                if section is not None:
                    record["width_mm"] = section["width_mm"]
                    record["height_mm"] = section["height_mm"]
                    record["length_m"] = section["length_m"]
                    record["shape"] = "rectangular"
                    record["size_method"] = "port_axis_against_extrusion"
                    duct_size_of[element.id()] = {
                        "shape": "rectangular",
                        "width_mm": section["width_mm"],
                        "height_mm": section["height_mm"],
                    }
                elif kind == "duct_segment":
                    record["shape"] = record["shape_property"].lower() if record["shape_property"] else None
        if kind == "duct_segment" and record["outer_diameter_mm"] is not None:
            duct_size_of[element.id()] = {
                "shape": "round",
                "outer_diameter_mm": record["outer_diameter_mm"],
            }
            direction, length = _port_direction(model, element)
            if length is not None:
                record["length_m"] = round(length, 4)
        if kind == "pipe_segment" and record["length_m"] is None:
            direction, length = _port_direction(model, element)
            if length is not None:
                record["length_m"] = round(length, 4)
        if kind == "duct_flex":
            record["shape"] = "round"
            record["mesh_minor_axis_mm"] = _mesh_minor_axis_mm(element)
            record["size_method"] = (
                "faceted_bbox_minor_axis" if record["mesh_minor_axis_mm"] else "unresolved"
            )
            if record["mesh_minor_axis_mm"] is None:
                record["assumptions"].append(
                    "Flex duct bends in more than one axis, so the mesh bounding "
                    "box does not expose a tube diameter."
                )
            else:
                record["assumptions"].append(
                    "mesh_minor_axis_mm is the smallest edge of the faceted mesh, "
                    "not a nominal diameter written in the IFC."
                )
        if kind in {
            "radiator",
            "stove",
            "water_heater",
            "air_terminal",
            "sanitary_fixture",
            "duct_accessory",
            "air_handling_unit",
        }:
            bbox = _bbox_mm(element)
            # Sort so a mirrored copy of the same body lands in one size group.
            record["bbox_mm"] = sorted(bbox) if bbox else None
            record["size_method"] = "world_bbox" if bbox else "unresolved"
        prepared.append(record)

    for record in prepared:
        element = record["element"]
        kind = record["kind"]
        if kind in {"pipe_fitting", "pipe_accessory"}:
            diameters = _connected_diameters(element, neighbours, diameter_of)
            record["connected_outer_diameters_mm"] = diameters
            record["size_method"] = "connected_segment_profile" if diameters else "unresolved"
            if not diameters:
                record["assumptions"].append(
                    "No sized pipe segment within four port hops, so no outside diameter was assigned."
                )
        elif kind in {"duct_fitting", "duct_accessory"}:
            sizes = _connected_duct_sizes(element, neighbours, duct_size_of)
            record["connected_duct_sizes"] = sizes
            record["size_method"] = "connected_duct_segment" if sizes else "unresolved"
        else:
            record["connected_outer_diameters_mm"] = []
            record["connected_duct_sizes"] = []

    groups: dict = {}
    for record in prepared:
        label, identity = _group_identity(record)
        key = _key_from(identity)
        bucket = groups.get(key)
        if bucket is None:
            bucket = _blank_group()
            groups[key] = bucket
        bucket["count"] += 1
        if record["length_m"]:
            bucket["total_length_m"] += record["length_m"]
        for system in record["systems"]:
            bucket["systems"][(system["name"], system["object_type"])] += 1
        if len(bucket["example_ids"]) < 3:
            bucket["example_ids"].append(record["global_id"])
        bucket["assumptions"].extend(record["assumptions"])
        bucket["label"] = label

    rows = []
    for key, bucket in groups.items():
        row = _unfreeze_key(key)
        row["size_label"] = bucket["label"]
        row["count"] = bucket["count"]
        row["total_length_m"] = round(bucket["total_length_m"], 3) if bucket["total_length_m"] else None
        row["systems"] = [
            {"name": name, "object_type": object_type, "count": count}
            for (name, object_type), count in sorted(
                bucket["systems"].items(), key=lambda item: (-item[1], str(item[0][0]))
            )
        ]
        row["example_global_ids"] = bucket["example_ids"]
        assumptions = []
        for note in bucket["assumptions"]:
            if note not in assumptions:
                assumptions.append(note)
        props = row.get("nominal_diameter_property_mm") or []
        diameters = row.get("outer_diameters_mm") or []
        if props and diameters and not any(
            any(abs(prop - diameter) <= 0.2 for diameter in diameters) for prop in props
        ):
            assumptions.append(
                "NominalDiameter on the fitting is "
                + ", ".join(f"{value:g}" for value in props)
                + " mm, which does not match the connected profile outside diameter "
                + ", ".join(f"{value:g}" for value in diameters)
                + " mm. Support selection uses the profile diameter."
            )
        row["assumptions"] = assumptions
        row["insulation"] = None
        rows.append(row)
    rows.sort(key=lambda row: (row["kind"], -row["count"], row["size_label"]))
    return {
        "file": path.name,
        "schema": model.schema,
        "element_count": len(prepared),
        "groups": rows,
    }


def _group_identity(record: dict) -> tuple[str, dict]:
    kind = record["kind"]
    base = {
        "kind": kind,
        "ifc_class": record["ifc_class"],
        "predefined_type": record["predefined_type"],
        "family": record["family"],
        "shape": record.get("shape") or record.get("shape_property"),
        "material": record["material"],
        "size_method": record["size_method"],
    }
    if kind == "pipe_segment":
        diameter = record["outer_diameter_mm"]
        base.update(
            {
                "outer_diameter_mm": diameter,
                "width_mm": None,
                "height_mm": None,
                "outer_diameters_mm": [diameter] if diameter is not None else [],
            }
        )
        label = f"OD {diameter} mm" if diameter is not None else "OD unknown"
        return label, base
    if kind == "duct_segment" and record.get("shape") == "rectangular":
        base.update(
            {
                "outer_diameter_mm": None,
                "width_mm": record["width_mm"],
                "height_mm": record["height_mm"],
                "outer_diameters_mm": [],
            }
        )
        label = f"{record['width_mm']} × {record['height_mm']} mm"
        return label, base
    if kind == "duct_segment" and record["outer_diameter_mm"] is not None:
        diameter = record["outer_diameter_mm"]
        base.update(
            {
                "outer_diameter_mm": diameter,
                "width_mm": None,
                "height_mm": None,
                "outer_diameters_mm": [diameter],
            }
        )
        return f"OD {diameter} mm", base
    if kind == "duct_flex":
        minor = record["mesh_minor_axis_mm"]
        base.update(
            {
                "outer_diameter_mm": None,
                "width_mm": None,
                "height_mm": None,
                "outer_diameters_mm": [],
                "mesh_minor_axis_mm": minor,
            }
        )
        label = f"mesh minor axis {minor} mm" if minor is not None else "diameter unresolved"
        return label, base
    if kind in {"pipe_fitting", "pipe_accessory"}:
        diameters = record.get("connected_outer_diameters_mm") or []
        base.update(
            {
                "outer_diameter_mm": diameters[0] if len(diameters) == 1 else None,
                "width_mm": None,
                "height_mm": None,
                "outer_diameters_mm": diameters,
                "nominal_diameter_property_mm": record["nominal_diameter_property_mm"],
            }
        )
        if diameters:
            label = "OD " + " / ".join(f"{value:g}" for value in diameters) + " mm"
        elif record["nominal_diameter_property_mm"]:
            label = "property DN " + "/".join(
                f"{value:g}" for value in record["nominal_diameter_property_mm"]
            ) + " mm (not used as OD)"
        else:
            label = "size unresolved"
        return label, base
    if kind in {"duct_fitting", "duct_accessory"}:
        sizes = record.get("connected_duct_sizes") or []
        # Group on the sorted connected sizes so identical fittings stay together.
        base.update(
            {
                "outer_diameter_mm": None,
                "width_mm": None,
                "height_mm": None,
                "outer_diameters_mm": [],
                "connected_duct_sizes": sizes,
            }
        )
        if not sizes:
            return "connected duct unresolved", base
        parts = []
        for size in sizes:
            if size.get("shape") == "round":
                parts.append(f"Ø{size['outer_diameter_mm']:g}")
            else:
                parts.append(f"{size['width_mm']:g}×{size['height_mm']:g}")
        return "connected " + ", ".join(parts) + " mm", base
    bbox = record.get("bbox_mm")
    base.update(
        {
            "outer_diameter_mm": None,
            "width_mm": None,
            "height_mm": None,
            "outer_diameters_mm": [],
            "bbox_mm": bbox,
        }
    )
    if bbox:
        ordered = " × ".join(f"{value:g}" for value in sorted(bbox))
        return f"bbox {ordered} mm", base
    return "size unresolved", base


def _type_name(name: str | None) -> str | None:
    """Drop the trailing Revit element id, including a ':184483:1' suffix."""
    if not name:
        return None
    parts = name.split(":")
    while len(parts) > 1 and parts[-1].isdigit():
        parts.pop()
    return ":".join(parts)


def _layer_sets(model) -> list[dict]:
    rows = []
    for layer_set in model.by_type("IfcMaterialLayerSet"):
        layers = []
        total = 0.0
        for layer in layer_set.MaterialLayers or []:
            thickness = float(layer.LayerThickness or 0.0)
            total += thickness
            material = layer.Material.Name if layer.Material else None
            layers.append({"material": material, "thickness_mm": round(thickness * 1000.0, 1)})
        rows.append(
            {
                "name": layer_set.LayerSetName,
                "total_thickness_mm": round(total * 1000.0, 1),
                "layers": layers,
            }
        )
    return rows


def inventory_architecture(path: Path) -> dict:
    import ifcopenshell

    model = ifcopenshell.open(str(path))
    storeys = []
    for storey in model.by_type("IfcBuildingStorey"):
        storeys.append(
            {
                "name": storey.Name,
                "elevation_m": None if storey.Elevation is None else round(float(storey.Elevation), 3),
            }
        )
    storeys.sort(key=lambda row: (row["elevation_m"] is None, row["elevation_m"] or 0.0))

    def summarise(element, predefined: str | None):
        box = _world_bbox(element)
        if box is None:
            return None
        xmin, xmax, ymin, ymax, zmin, zmax = box
        return {
            "name": element.Name,
            "predefined_type": predefined,
            "thickness_mm": round((zmax - zmin) * 1000.0, 1),
            "z_min_m": round(zmin, 3),
            "z_max_m": round(zmax, 3),
            "xy": (xmin, xmax, ymin, ymax),
        }

    slabs = []
    for element in model.by_type("IfcSlab"):
        row = summarise(element, str(element.PredefinedType) if element.PredefinedType else None)
        if row:
            slabs.append(row)
    ceilings = []
    for element in model.by_type("IfcCovering"):
        predefined = str(element.PredefinedType) if getattr(element, "PredefinedType", None) else None
        if predefined != "CEILING":
            continue
        row = summarise(element, predefined)
        if row:
            ceilings.append(row)
    beams = []
    for element in model.by_type("IfcBeam"):
        row = summarise(element, None)
        if row:
            beams.append(row)

    gaps = []
    for ceiling in ceilings:
        cx0, cx1, cy0, cy1 = ceiling["xy"]
        overhead = []
        for candidate in slabs + beams:
            if candidate["z_min_m"] < ceiling["z_max_m"] - 0.01:
                continue
            ox0, ox1, oy0, oy1 = candidate["xy"]
            separated = cx1 < ox0 or ox1 < cx0 or cy1 < oy0 or oy1 < cy0
            if separated:
                continue
            overhead.append(candidate)
        if not overhead:
            continue
        nearest = min(overhead, key=lambda item: item["z_min_m"])
        gap_mm = round((nearest["z_min_m"] - ceiling["z_max_m"]) * 1000.0, 1)
        overhead_name = _type_name(nearest["name"])
        gaps.append(
            {
                "ceiling_z_max_m": ceiling["z_max_m"],
                "ceiling_thickness_mm": ceiling["thickness_mm"],
                "overhead_name": overhead_name,
                "overhead_z_min_m": nearest["z_min_m"],
                "gap_mm": gap_mm,
            }
        )

    gap_summary = []
    gap_counts: dict = {}
    for row in gaps:
        key = tuple(row.values())
        bucket = gap_counts.get(key)
        if bucket is None:
            bucket = dict(row)
            bucket["count"] = 0
            gap_counts[key] = bucket
            gap_summary.append(bucket)
        bucket["count"] += 1
    observations = []
    layer_sets = _layer_sets(model)
    layer_text = " ".join(
        (layer["material"] or "") for item in layer_sets for layer in item["layers"]
    )
    if "Wood - Dimensional Lumber" in layer_text or "plywood" in layer_text.lower():
        observations.append(
            "The floor and roof build-ups above the rooms use dimensional lumber "
            "and plywood, not a concrete soffit."
        )
    if any(item["name"] and "Gypsum" in item["name"] for item in ceilings):
        observations.append(
            "Ceilings are compound gypsum board on a metal-stud layer (57 mm in "
            "the material layer set), so a concrete ceiling anchor does not match "
            "this model's soffit."
        )
    if any("Concrete" in (layer["material"] or "") for item in layer_sets for layer in item["layers"]):
        observations.append(
            "Concrete in this architecture model is the slab on grade and the "
            "foundation walls, not the ceiling the MEP hangers would reach."
        )
    def by_type(rows):
        grouped = {}
        for row in rows:
            type_name = _type_name(row["name"])
            key = (type_name, row["predefined_type"], row["thickness_mm"], row["z_min_m"], row["z_max_m"])
            bucket = grouped.get(key)
            if bucket is None:
                bucket = {
                    "type_name": type_name,
                    "predefined_type": row["predefined_type"],
                    "thickness_mm": row["thickness_mm"],
                    "z_min_m": row["z_min_m"],
                    "z_max_m": row["z_max_m"],
                    "count": 0,
                }
                grouped[key] = bucket
            bucket["count"] += 1
        return list(grouped.values())

    return {
        "file": path.name,
        "schema": model.schema,
        "storeys": storeys,
        "slabs": by_type(slabs),
        "ceilings": by_type(ceilings),
        "beams": by_type(beams),
        "material_layer_sets": layer_sets,
        "ceiling_to_structure_gaps": gap_summary,
        "observations": observations,
    }


def build_inventory(examples: Path | None = None) -> dict:
    paths = resolve_models(examples)
    mep = {}
    for key in ("piping", "ventilation", "heating_and_cooling"):
        mep[key] = inventory_mep(paths[key])
    return {
        "dataset": DATASET,
        "units": {
            "length": "mm unless a field name ends in _m",
            "model_coordinates": "m",
        },
        "notes": [
            "IFC2X3 export: pipes and ducts are IfcFlowSegment, not IfcPipeSegment / IfcDuctSegment.",
            "Segment property sets have length and roughness, not nominal diameter. "
            "Outside diameter is the circle-profile diameter.",
            "Rectangular duct profiles mix run length into the profile. Width and height "
            "are the two edges that are not the port-to-port direction; height is the "
            "edge closer to world Z.",
            "No insulation covering or insulation property was found on the MEP elements.",
            "On fittings, NominalDiameter is an IfcPropertyListValue and often disagrees "
            "with the connected pipe's circle-profile diameter. Groups keep both; "
            "the profile diameter is the one a clamp has to fit.",
            "Material entities on the MEP models are unnamed.",
        ],
        "models": mep,
        "architecture": inventory_architecture(paths["architecture"]),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--examples",
        type=Path,
        default=ROOT / "examples",
        help="Directory containing the duplex IFC files",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Inventory JSON path")
    args = parser.parse_args(argv)
    inventory = build_inventory(args.examples)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    for key, model in inventory["models"].items():
        print(f"{key}: {model['element_count']} elements, {len(model['groups'])} size groups → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
