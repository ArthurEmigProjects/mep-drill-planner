"""Write placed hangers as a separate IFC the viewer can show or hide.

Each hanger is a short rod. ``Pset_DrillMount`` records ``Status``
(``clear``, ``moved``, ``clash``) and ``Trade`` (``sanitary``,
``heating_cooling``, ``ventilation``). The same two values are stored on
``ObjectType`` and ``Tag`` so the viewer can read them from the element.
Rods are coloured green, amber, or red by status. Storey names are copied
from the source model so a storey filter keeps the hangers on that level.
"""

from __future__ import annotations

import time
from pathlib import Path

ROD_RADIUS_M = 0.025
ROD_STUB_M = 0.35
MIN_ROD_M = 0.02

STATUS_COLOURS = {
    "clear": (0.184, 0.435, 0.306),
    "moved": (0.855, 0.647, 0.125),
    "clash": (0.722, 0.110, 0.110),
}

_FILE_TRADES = {
    "zenodo-duplex-piping.ifc": "sanitary",
    "piping.ifc": "sanitary",
    "zenodo-duplex-ventilation.ifc": "ventilation",
    "ventilation.ifc": "ventilation",
    "heatingandcooling.ifc": "heating_cooling",
    "zenodo-duplex-heating-and-cooling.ifc": "heating_cooling",
}

_SANITARY = ("domestic", "sewage", "sanitary", "waste", "storm", "soil", "potable", "kanalizacja", "sewer")
_HEATING = ("hydronic", "heating", "cooling", "chilled", "radiator", "condenser", "hot water")
_VENTILATION = (
    "exhaustair",
    "returnair",
    "supplyair",
    "ventilation",
    "hvac",
    "powietrze",
    "exhaust",
    "supply air",
    "return air",
    "duct",
)


def trade_for_file(source: str | None) -> str | None:
    """Trade implied by a single-discipline duplex file name."""
    if not source:
        return None
    return _FILE_TRADES.get(Path(source).name.lower())


def trade_from_systems(names: list[str] | tuple, kind: str | None = None) -> str:
    """Trade from IfcSystem names, then from a duct run with no system."""
    text = " ".join(str(name) for name in names if name).lower()
    if any(token in text for token in _SANITARY):
        return "sanitary"
    if any(token in text for token in _HEATING):
        return "heating_cooling"
    if any(token in text for token in _VENTILATION):
        return "ventilation"
    if kind == "duct_segment":
        return "ventilation"
    return "unknown"


def status_for_point(point: dict) -> str:
    """``clear``, ``moved``, or ``clash`` from the placement reason."""
    if point.get("clear") is False or point.get("reason") == "unresolved_clash":
        return "clash"
    reason = str(point.get("reason") or "")
    if reason.startswith("shifted_") or reason == "respaced_90_95":
        return "moved"
    return "clear"


def annotate_mountings(plan: dict) -> dict:
    """Copy status, trade, and system names onto every placed point."""
    file_trade = trade_for_file(plan.get("source"))
    runs = {run["id"]: run for run in plan.get("runs") or []}
    for point in plan.get("points") or []:
        run = runs.get(point.get("run_id")) or {}
        names = list(run.get("system_names") or [])
        point["system_names"] = names
        point["status"] = status_for_point(point)
        point["trade"] = file_trade or trade_from_systems(names, point.get("kind") or run.get("kind"))
    return plan


def write_mounting_ifc(plan: dict, out: Path, source: Path | None = None) -> Path:
    """Write one rod per hanger. Coordinates stay in the source model's metres."""
    import ifcopenshell
    import ifcopenshell.guid

    storeys = _source_storeys(source) if source is not None else []
    model = ifcopenshell.file(schema="IFC4")
    owner = _owner_history(model)
    context, body, world = _context(model)
    project, building = _project(model, owner, world, context)
    groups = _storey_groups(model, owner, world, building, plan.get("points") or [], storeys)
    styles = {
        status: _surface_style(model, status, colour)
        for status, colour in STATUS_COLOURS.items()
    }
    for storey, points in groups:
        elements = []
        for point in points:
            status = point.get("status") or status_for_point(point)
            trade = point.get("trade") or "unknown"
            element = _rod(model, owner, body, world, point, status, trade, styles, storey.Name)
            _pset(model, owner, element, status, trade, storey.Name)
            elements.append(element)
        if elements:
            model.create_entity(
                "IfcRelContainedInSpatialStructure",
                GlobalId=ifcopenshell.guid.new(),
                OwnerHistory=owner,
                RelatedElements=elements,
                RelatingStructure=storey,
            )
    out.parent.mkdir(parents=True, exist_ok=True)
    model.write(str(out))
    return out


def _source_storeys(source: Path) -> list[dict]:
    from src.ifc_drawings import read_storeys

    if not source.is_file():
        return []
    return [row for row in read_storeys([source]) if row.get("source") == source.name]


def _storey_groups(model, owner, world, building, points, storeys):
    import ifcopenshell.guid

    usable = [row for row in storeys if isinstance(row.get("elevation_m"), (int, float))]
    usable.sort(key=lambda row: row["elevation_m"])
    if not usable:
        usable = [{"name": "Mountings", "elevation_m": 0.0}]
    created = []
    for row in usable:
        storey = model.create_entity(
            "IfcBuildingStorey",
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=owner,
            Name=row.get("name") or "Storey",
            ObjectPlacement=_local_placement(model, world),
            CompositionType="ELEMENT",
            Elevation=float(row["elevation_m"]),
        )
        created.append((storey, row))
    model.create_entity(
        "IfcRelAggregates",
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=owner,
        RelatingObject=building,
        RelatedObjects=[storey for storey, _row in created],
    )
    buckets = {id(storey): [] for storey, _row in created}
    for point in points:
        storey = _storey_for_z(float(point["z"]), created)
        buckets[id(storey)].append(point)
    return [(storey, buckets[id(storey)]) for storey, _row in created]


def _storey_for_z(z: float, created):
    chosen = created[0][0]
    for storey, row in created:
        if float(row["elevation_m"]) <= z + 0.05:
            chosen = storey
        else:
            break
    return chosen


def _rod(model, owner, body, world, point, status, trade, styles, storey):
    import ifcopenshell.guid

    start, end = _rod_ends(point)
    solid = _extrusion(model, start, end)
    model.create_entity("IfcStyledItem", Item=solid, Styles=[styles.get(status, styles["clear"])])
    shape = model.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=body,
        RepresentationIdentifier="Body",
        RepresentationType="SweptSolid",
        Items=[solid],
    )
    product_shape = model.create_entity("IfcProductDefinitionShape", Representations=[shape])
    return model.create_entity(
        "IfcBuildingElementProxy",
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=owner,
        Name=str(point.get("id") or "hanger"),
        Description=str(storey or ""),
        ObjectType=status,
        ObjectPlacement=_local_placement(model, world),
        Representation=product_shape,
        Tag=trade,
        PredefinedType="NOTDEFINED",
    )


def _rod_ends(point: dict) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    start = (float(point["x"]), float(point["y"]), float(point["z"]))
    anchor = point.get("anchor")
    if isinstance(anchor, (list, tuple)) and len(anchor) >= 3:
        end = (float(anchor[0]), float(anchor[1]), float(anchor[2]))
        if _norm(_sub(end, start)) >= MIN_ROD_M:
            return start, end
    direction = point.get("mount_direction") or (0.0, 0.0, 1.0)
    axis, length = _unit(tuple(direction[:3]))
    if length < 1e-9:
        axis = (0.0, 0.0, 1.0)
    return start, _add(start, _scale(axis, ROD_STUB_M))


def _extrusion(model, start, end):
    delta = _sub(end, start)
    depth = _norm(delta)
    axis, _length = _unit(delta)
    helper = (1.0, 0.0, 0.0) if abs(axis[0]) < 0.9 else (0.0, 1.0, 0.0)
    ref, _ref_length = _unit(_sub(helper, _scale(axis, _dot(helper, axis))))
    position = model.create_entity(
        "IfcAxis2Placement3D",
        Location=model.create_entity("IfcCartesianPoint", Coordinates=start),
        Axis=model.create_entity("IfcDirection", DirectionRatios=axis),
        RefDirection=model.create_entity("IfcDirection", DirectionRatios=ref),
    )
    profile = model.create_entity(
        "IfcCircleProfileDef",
        ProfileType="AREA",
        ProfileName="Rod",
        Radius=ROD_RADIUS_M,
    )
    return model.create_entity(
        "IfcExtrudedAreaSolid",
        SweptArea=profile,
        Position=position,
        ExtrudedDirection=model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0)),
        Depth=depth,
    )


def _pset(model, owner, element, status, trade, storey):
    import ifcopenshell.guid

    properties = [
        _label(model, "Status", status),
        _label(model, "Trade", trade),
    ]
    if storey:
        properties.append(_label(model, "Storey", str(storey)))
    properties = model.create_entity(
        "IfcPropertySet",
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=owner,
        Name="Pset_DrillMount",
        HasProperties=properties,
    )
    model.create_entity(
        "IfcRelDefinesByProperties",
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=owner,
        RelatedObjects=[element],
        RelatingPropertyDefinition=properties,
    )


def _label(model, name, value):
    return model.create_entity(
        "IfcPropertySingleValue",
        Name=name,
        NominalValue=model.create_entity("IfcLabel", wrappedValue=value),
    )


def _surface_style(model, name, colour):
    rgb = model.create_entity(
        "IfcColourRgb",
        Name=name,
        Red=float(colour[0]),
        Green=float(colour[1]),
        Blue=float(colour[2]),
    )
    rendering = model.create_entity(
        "IfcSurfaceStyleRendering",
        SurfaceColour=rgb,
        Transparency=0.0,
        ReflectanceMethod="FLAT",
    )
    return model.create_entity("IfcSurfaceStyle", Name=name, Side="BOTH", Styles=[rendering])


def _owner_history(model):
    person = model.create_entity("IfcPerson", FamilyName="MEP drill planner")
    org = model.create_entity("IfcOrganization", Name="MEP drill planner")
    user = model.create_entity("IfcPersonAndOrganization", ThePerson=person, TheOrganization=org)
    app = model.create_entity(
        "IfcApplication",
        ApplicationDeveloper=org,
        Version="0.2",
        ApplicationFullName="MEP drill planner",
        ApplicationIdentifier="mep-drill-planner",
    )
    return model.create_entity(
        "IfcOwnerHistory",
        OwningUser=user,
        OwningApplication=app,
        ChangeAction="ADDED",
        CreationDate=int(time.time()),
    )


def _local_placement(model, world):
    return model.create_entity("IfcLocalPlacement", RelativePlacement=world)


def _context(model):
    origin = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0))
    axis = model.create_entity("IfcDirection", DirectionRatios=(0.0, 0.0, 1.0))
    ref = model.create_entity("IfcDirection", DirectionRatios=(1.0, 0.0, 0.0))
    world = model.create_entity("IfcAxis2Placement3D", Location=origin, Axis=axis, RefDirection=ref)
    context = model.create_entity(
        "IfcGeometricRepresentationContext",
        ContextType="Model",
        CoordinateSpaceDimension=3,
        Precision=1e-5,
        WorldCoordinateSystem=world,
    )
    body = model.create_entity(
        "IfcGeometricRepresentationSubContext",
        ContextIdentifier="Body",
        ContextType="Model",
        ParentContext=context,
        TargetView="MODEL_VIEW",
    )
    return context, body, world


def _project(model, owner, world, context):
    import ifcopenshell.guid

    length = model.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Name="METRE")
    units = model.create_entity("IfcUnitAssignment", Units=[length])
    project = model.create_entity(
        "IfcProject",
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=owner,
        Name="Mounting elements",
        RepresentationContexts=[context],
        UnitsInContext=units,
    )
    site = model.create_entity(
        "IfcSite",
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=owner,
        Name="Site",
        ObjectPlacement=_local_placement(model, world),
        CompositionType="ELEMENT",
    )
    building = model.create_entity(
        "IfcBuilding",
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=owner,
        Name="Building",
        ObjectPlacement=_local_placement(model, world),
        CompositionType="ELEMENT",
    )
    model.create_entity(
        "IfcRelAggregates",
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=owner,
        RelatingObject=project,
        RelatedObjects=[site],
    )
    model.create_entity(
        "IfcRelAggregates",
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=owner,
        RelatingObject=site,
        RelatedObjects=[building],
    )
    return project, building


def _sub(left, right):
    return (left[0] - right[0], left[1] - right[1], left[2] - right[2])


def _add(left, right):
    return (left[0] + right[0], left[1] + right[1], left[2] + right[2])


def _scale(vector, factor):
    return (vector[0] * factor, vector[1] * factor, vector[2] * factor)


def _dot(left, right):
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2]


def _norm(vector):
    return _dot(vector, vector) ** 0.5


def _unit(vector):
    length = _norm(vector)
    if length < 1e-12:
        return (0.0, 0.0, 0.0), 0.0
    return _scale(vector, 1.0 / length), length
