# How to work with this tool

The MEP drill planner reads an MEP IFC and proposes where hangers can go. Use the local page for the usual job: pick a model, look at it in 3D, place hangers, move or delete them, and write a clash PDF. The files stay on this computer.

Coordinates are metres, in the same system as the IFC.

## Start the page

From the repo root, once per machine:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Each session:

```powershell
python -m src.ui
```

The browser opens at `http://127.0.0.1:8765`. Add `--no-browser` if you want to open that address yourself, or `--port 8770` to use another port.

The 3D view downloads That Open Engine and the web-ifc WASM from the network the first time. Placement, extraction, and the PDF do not need that download.

## Choose the model

**Sample models** lists the public IFCs in `examples/`. Select the one whose pipes or ducts should be hung. The line under **Selected** is the model every button uses.

**Open a file** takes an IFC from this computer. Drop it on the panel or use **Browse**. You can drop several files. They are copied into `examples/uploads/` and do not replace the samples. Select one of them the same way as a sample.

Do not put a real project IFC into git. Samples and anonymised models are the ones this repo is meant to keep.

## Include other files in the clash check

Each file has a **For clashes** tick. Tick architecture when it holds beams, and tick the other trades when a rod can hit them. The selected model is always included. Its own runs are the ones that receive hangers. A ticked file is clash geometry only: its services and beams can block a rod, and its runs are not hung.

## Look at the model in 3D

**View in 3D** draws the selected model, every file ticked **For clashes**, and, after placement, the hanger rods. **Open in window** puts that same set in its own browser window. Allow pop-ups for this site if the window does not appear.

The status line under **Model** names the files and the overall size when the view is ready.

### Move the camera

- Drag to orbit.
- Scroll to zoom.
- Right-drag to pan.

**Fit** frames everything. **Orbit** and **Plan** switch the navigation mode. **Orthographic** toggles to a parallel view; the button then reads **Perspective**. **Reset view** restores the orbit camera, clears cuts and colors, and shows every category again.

### Select an element and read its properties

Click an element. It highlights, and the **Properties** panel on the right lists its name, category, global ID, other attributes, and property sets. A hanger also shows `Pset_DrillMount` (status, trade, and storey).

- Shift-click adds another element.
- Ctrl-click toggles an element.
- Click empty space to clear the 3D selection.

A click that turns into a drag does not select. Double-click is reserved for cutting, described below.

### Frame hangers from the list

After hangers are placed, click a line in the **Objects** list or a row in the mounting table. The view highlights that rod and frames it. The status line reads `Framed M-0001.`

Shift-click or Ctrl-click selects several hangers. The camera frames all of them, and the status line reads `Framed 3 hangers.` The form on the right still edits the last hanger you clicked, and its note says how many are framed.

Arrow keys move the single selection when the object list has focus. Choosing hangers before the view has finished loading frames them when the models are ready. The separate viewer window follows the same selection.

### Show, hide, and cut

The tools on the left of the view:

- **Models** shows or hides each loaded file, including architecture, the other trades, and **Hangers**.
- **Storey** keeps one level. Hangers stay when their storey name matches.
- The category list shows or hides IFC classes in the building models.
- **Mounting** shows or hides the rods, then filters **Non-problematic**, **Moved**, and **Clashing**, and **Sanitary**, **Heating / cooling**, **Ventilation**, and **Other**.
- **By category** colors the building by IFC class. **Tint ticked** colors the ticked classes. **Reset color** restores the file colors. **Fade** makes the model translucent.
- **Height**, **Side**, and **Depth** cut the model. 100% is the whole model. Double-click a face to cut there. Delete or Backspace removes the cut under the pointer. **Clear cuts** removes every cut.

## Extract anchor points

**Extract anchor points** lists a candidate at the top of each MEP element’s bounding box. It does not space hangers and it does not run the clash check. The table shows id, element, and X, Y, Z. The first 25 rows are shown; **Show all points** opens the rest.

The file is `examples/out/<model>-points.json`.

## Place hangers

**Place mounting points** is the main operation.

1. Select the MEP model.
2. Tick the other IFCs that a rod can hit.
3. Click **Place mounting points**.

The tool finds straight runs of the same size. On a horizontal run the pitch starts at 70% of the catalogue maximum, so the gaps have some spare. A rod is tested upward from the pipe or duct. If it meets another service or a beam, the hangers are moved so every gap stays between 90% and 95% of the allowed spacing. A hanger that cannot move inside that limit stays put and is marked **Unresolved clash**. A riser is fixed sideways to the nearest wall, and the same pitch is used along it.

The summary counts hangers, runs, adjusted points, and clashes. Each hanger has one of these reasons:

| Badge | Meaning |
| --- | --- |
| Even 70% | Kept the regular pitch |
| Respaced to 90–95% | The run was opened up inside the allowed band |
| Moved under 95% | This hanger was shifted to clear a clash |
| Unresolved clash | No clear station was found inside the limit |
| Moved by hand | You moved it after placement |

**Adjusted** lists everything that is not an even 70% pitch. **Still clashing** lists unresolved clashes. **All** lists every hanger. The object list is grouped by run and is not affected by that filter.

Two files are written:

- `examples/out/<model>-mounting-points.json` — the hanger list
- `examples/out/<model>-mountings.ifc` — one rod per hanger, separate from the building

Open **View in 3D** again after placement. The rods load beside the building. They are not part of the clash check.

A model with no cited spacing, or with no horizontal run the catalogue can hang, finishes with `No hanger was placed.`

## Change a hanger

Select one hanger in **Objects** or in the table.

- **Along the run** moves it along the pipe or duct and keeps a wall hanger on the wall.
- **X**, **Y**, and **Z** move the point itself. A wall hanger can leave the wall.
- **Apply** saves. If you changed the station and the coordinates, the station is what is saved.
- **Delete hanger** removes it. The next hanger on that run stays selected.
- **Undo** (Ctrl+Z) and **Redo** (Ctrl+Y, or Ctrl+Shift+Z) step through the last edits. Delete and Backspace, while the object list has focus, also delete the selected hanger.

A move does not run the clash check again. A hanger that was clashing stays marked clashing, and the reason becomes **Moved by hand**. The note under the buttons tells you to open **View in 3D** again so the rods match the saved list.

The station must stay on the run. A value past the end of the run is rejected and the file is left unchanged.

## Clash drawings

**Clash drawings PDF** writes one PDF for the selected model and the files ticked **For clashes**:

- a floor plan for each storey
- a long section
- a cross section
- a section through each unresolved clash
- isometric 3D views

The browser downloads the PDF. A copy is also saved at `examples/out/<model>-views.pdf`. The drawing uses centre-lines, fittings, beams, members, and columns. Walls, slabs, and ceilings are left out.

## Where the results go

| Action | File |
| --- | --- |
| Open a file from this computer | `examples/uploads/` |
| Extract anchor points | `examples/out/<model>-points.json` |
| Place or edit hangers | `examples/out/<model>-mounting-points.json` and `examples/out/<model>-mountings.ifc` |
| Clash drawings | `examples/out/<model>-views.pdf` |

`examples/out/` is local. Those results are not committed.

## The same work from the command line

Run these from the repo root with the virtual environment active.

Anchor candidates:

```powershell
python -m src.extract_anchor_points examples/zenodo-duplex-piping.ifc --out examples/out/zenodo-duplex-piping-points.json
```

Hangers, with the architecture model used only for clashes:

```powershell
python -m src.mounting_points examples/zenodo-duplex-piping.ifc --obstacles examples/Architecture.ifc
```

Clash PDF for that same pair:

```powershell
python -m src.ifc_drawings examples/zenodo-duplex-piping.ifc --obstacles examples/Architecture.ifc --out examples/out/zenodo-duplex-piping-views.pdf
```

Repeat `--obstacles` for each extra IFC. The page’s **For clashes** ticks are the same idea.

## What this pass does not do

Edge distance from a slab or beam is not checked yet. A move you make by hand does not repeat the clash test. The catalogue does not cover every size in the sample models, so some runs get no hanger. The viewer needs a network connection the first time it opens.
