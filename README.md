# mep-drill-planner

Turn an MEP IFC model into a list of ceiling anchor / drill points that a construction robot (or a human installer) can execute.

**Mission fit**
1. Pre-construction design automation: rule-check spacing, edge distances, and clashes before anyone drills.
2. Construction-site robotics: feed the same points into a ROS 2 simulation (later), then into robots such as Hilti Jaibot or fischer BauBot.

## Progress

| Step | Status | What's done |
|------|--------|-------------|
| **0. Scaffold** | Done | Repo layout, `requirements.txt` (ifcopenshell), venv, `.gitignore`, public GitHub at [HombreOso/mep-drill-planner](https://github.com/HombreOso/mep-drill-planner) |
| **1. Demo extractor** | Done | `--demo` writes 3 synthetic points to JSON (`id`, `x/y/z`, type, reason) |
| **2. IFC → points** | Done (v0.1) | `extract_anchor_points` loads IFC, skips entity types missing from the file's schema (IFC2X3-safe), takes top-of-bbox as hanger candidates from FlowSegment / FlowFitting / BuildingElementProxy (and IFC4 duct/pipe/cable types when present) |
| **3. Public sample IFCs** | Done | Three CC BY 4.0 models under `examples/` (Zenodo ventilation + piping, buildingSMART Duplex MEP); sources attributed below |
| **4. Sample runs** | Done | Ventilation **320** pts · Piping **439** pts · Duplex MEP **785** pts → `examples/out/*-points.json` (local only; gitignored) |
| **5. Mounting database** | Done | Inventory of the Zenodo duplex MEP sizes, plus a sourced catalogue of pipe clamps, duct hangers, rods, channel and concrete anchors (`data/mounting_elements/`) |
| **6. Rule checks** | Not started | Spacing, edge distance, structure clash |
| **7. HTML report** | Not started | Human-readable map / table of points + rule failures |
| **8. ROS 2 sim** | Not started | Mobile base + arm visits points (e.g. Gazebo / Jazzy) |
| **9. Perception** | Later | PyImageSearch / CV: verify as-built holes from site photos |

**Current focus:** tighten candidates (ceiling-level / hanger-like only), then rules + HTML report.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Put an anonymised MEP IFC next to the command, then:
python -m src.extract_anchor_points path/to/model.ifc --out examples/out/points.json
```

Without an IFC yet, generate demo points:

```bash
python -m src.extract_anchor_points --demo --out examples/out/points.json
```

## Point JSON schema

```json
{
  "source": "model.ifc",
  "units": "m",
  "points": [
    {
      "id": "P-0001",
      "element_id": "3Abc...",
      "element_type": "IfcCableCarrierSegment",
      "x": 12.40,
      "y": 3.15,
      "z": 2.85,
      "reason": "hanger_from_bbox_top"
    }
  ]
}
```

## Roadmap

| Milestone | Status | What |
|-----------|--------|------|
| **v0.1** | Done | IFC → points JSON on public MEP samples (schema-safe extractor) |
| **v0.2** | Next | Ceiling/hanger filtering · spacing + edge-distance rules · HTML report |
| **v0.3** | Planned | ROS 2 Jazzy sim: mobile base + arm visits points |
| **later** | Planned | Perception / PyImageSearch: verify as-built holes from site photos |

## Sample IFC sources

Public MEP sample models used under `examples/` (CC BY 4.0):

- **Zenodo DuplexModel+MEP** (Teclaw, 2024), DOI [10.5281/zenodo.10610773](https://doi.org/10.5281/zenodo.10610773) — `zenodo-duplex-ventilation.ifc` (Ventilation.ifc), `zenodo-duplex-piping.ifc` (Piping.ifc), `HeatingAndCooling.ifc`, and `Architecture.ifc`.
- **buildingSMART Duplex Apartment** `Duplex_MEP_20110907.ifc` — cite as BSI (2020) Duplex Apartment Test Files; saved as `buildingsmart-duplex-mep.ifc` (from [buildingsmart-community/Community-Sample-Test-Files](https://github.com/buildingsmart-community/Community-Sample-Test-Files)).

```bash
python -m src.extract_anchor_points examples/zenodo-duplex-ventilation.ifc --out examples/out/zenodo-duplex-ventilation-points.json
python -m src.extract_anchor_points examples/zenodo-duplex-piping.ifc --out examples/out/zenodo-duplex-piping-points.json
python -m src.extract_anchor_points examples/buildingsmart-duplex-mep.ifc --out examples/out/buildingsmart-duplex-mep-points.json
```

## Mounting-element database

The v0.2 spacing rules need a catalogue of supports that actually fit the pipes, ducts and devices in the sample models. Two pieces live under `data/`:

| Path | What it is |
|------|------------|
| `src/inventory_elements.py` | Reads the four Zenodo duplex IFCs and writes one JSON inventory |
| `data/inventory/zenodo_duplex_mountable.json` | Size groups: IFC class, kind, system, outside diameter or duct cross-section, material, insulation, count |
| `data/inventory/coverage.json` | Same groups after matching, with gaps |
| `data/mounting_elements/products.json` | Manufacturer products and spacing guidance |
| `data/mounting_elements/schema.json` | JSON Schema (draft 2020-12) for that file |
| `src/mounting.py` | Loader, `feasible_mountings()`, and the coverage report |
| `src/mounting_statistics.py` | Statistics of the catalogue, the duplex inventory and the coverage |
| `data/mounting_elements/statistics/` | The same report as Markdown, text, Word, PDF and Excel |

```bash
python -m src.inventory_elements
python -m src.mounting
python -m src.mounting_statistics
python -m unittest discover -s tests
```

`python -m src.mounting_statistics` writes `data/mounting_elements/statistics/mounting_elements_statistics.md`, `.txt`, `.docx`, `.pdf` and `.xlsx`. The five files carry the same tables: catalogue composition, clamp-window coverage, published loads, guidance spacing, inventory counts and lengths, match status, unmatched gaps, and the architecture ceiling gaps. Word, PDF and Excel need `python-docx`, `reportlab` and `openpyxl` when regenerating; those writers are not required to read the IFC models.

`feasible_mountings(element, substrate=None)` takes a dict with `kind` and a size (an inventory group is valid input) and returns primary products, companion rods / channel / anchors, attached guidance, assumptions, and a gap string when nothing fits.

**Product fields.** `manufacturer`, `product_line`, `name`, `article_number`, `element_types` (`pipe`, `duct_round`, `duct_rectangular`, `duct_flex`, `radiator`, `threaded_rod`, `channel`, `ceiling_anchor`), `role` (`primary` or `companion`), `outer_diameter_mm` (`min`/`max` or null), `nominal_diameter_mm`, `connection_threads`, `load_rating` (`value`, `unit`, `kind` or null), `max_support_spacing`, `anchor` (type, thread, substrate), `assumptions`, `notes`, `sources` (`title`, `url`, `accessed`). Empty values are JSON `null` or `[]`. A field is filled only when a cited page stated it.

**How a match is decided.**

- A pipe, fitting or valve matches when every required outside diameter falls inside a published clamping window (0.02 mm tolerance, so 19.05 mm is inside 19–24 and outside 15–19). Fitting and valve sizes are the connected tube diameters, with the assumption that the clamp sits on the tube.
- A round duct matches a catalogue nominal diameter within 1 mm (Sikla PLU type 150). A rectangular duct matches Sikla LUW only as `matched_with_assumption`: the catalogue states a 0.8 kN nominal load and M8/M10, and does not publish a width × height window.
- Status is `matched` when every required size has a published range or nominal type, `matched_with_assumption` when the only hit is kind-level, and `unmatched` when any required size has no product. A partial hit on a multi-size element is not returned as a match.
- Spacing is not stored on the products (`max_support_spacing` is null). Cited tables live in `guidance[]` and are attached when a row is within 0.5 mm of a pipe OD, or when a duct size is an exact table row.
- Threaded rods are companions whose thread is in the union of the matched clamps' connection threads. Concrete anchors (fischer EA II) are companions only when `substrate="concrete"`.

**What the duplex models contain.** Pipes are IFC2X3 `IfcFlowSegment` / `IfcFlowFitting`. Outside diameters come from the circle profile, not from `NominalDiameter` (that property, where present, often disagrees with the profile). Modeled pipe ODs are 9.52, 12.7, 15.0, 15.875, 19.05, 22.225, 41.275 and 104.775 mm. Rectangular ducts are 150×150, 200×150, 300×150 and 300×300 mm; round ducts are 150 mm. No insulation property was found, and material entities are unnamed. The architecture model has gypsum ceilings (57 mm) under timber joists: about 238 mm clear on level 1 and 343 mm on level 2. Concrete is the slab on grade and the foundation walls, so the coverage report does not count concrete anchors.

**Limitations.**

- Würth is absent: no product page with a clamping range and article number was captured. Do not treat the catalogue as a complete market survey.
- Hilti MP-MI article numbers, ranges and M10/M12 connection are from ETA-18/0130. The 1800 N figure is from a distributor reproduction of the Hilti sheet, not from hilti.de.
- Copper spacing is the horizontal Stangenrohr table that Conex and IBP catalogues attribute to DIN 1988 Teil 2. The standard text was not read (DIN 1988-2 is withdrawn). It is attached only with an explicit assumption, because the IFC material is unnamed. Ringrohr distances are not used. 15.875, 9.52, 12.7, 19.05, 41.275 and 104.775 mm do not get a spacing row.
- Lindab horizontal spacing (circular 3.0 m, rectangular rows 2.4 m) is copied only for uninsulated, no-fire-class sizes that appear as table rows. 150×150 mm is not a row. EN 12236 is attached as strength guidance (safety factor and deflection); it has no spacing table.
- Walraven BISMAT 2000: a reseller prints "Zulässige Nutzlast 935" with no unit. That number is not stored. Fischer FRS 4" A2 has no load in the captured table.
- Sikla PLU 150 is not applied to flex-duct mesh (151.6 mm) or to flex ducts whose diameter could not be recovered.
- No product is recorded for sanitary fixtures, water heaters, stoves, air terminals, air-handling units, or flex ducts. Those groups stay unmatched.
- Radiators match the Kermi wall console only with the assumption that the IFC radiator has the Kermi lug the console is made for. It is a wall fixing, not a ceiling anchor.
- The extractor in `src/extract_anchor_points.py` is unchanged. This database does not yet generate drill points.

## Notes

- Never commit real project IFCs. Use anonymised / public sample models only.
- Built for Arthur Emig's portfolio path: computational MEP → BIM-to-robot.
