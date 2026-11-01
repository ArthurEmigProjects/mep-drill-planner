Is there a possibility to visualize mounting elements (non-problematic, moved, or clashing) in the IFC viewer? I want to have a separate IFC for them which i can show or hide in the IFC viewer. The aforementioned classes of the mounting elements should be filterable. Also I want to distinguish if mounting elements are for sanitary, or heating/cooling, or ventilation

Yes. The placement data and the viewer already have the pieces. What is missing is a generated hanger IFC and two filters that the category checkboxes do not provide.

Each placed hanger already has a position, a mount direction, an anchor, and a `reason`. Those reasons are the three classes:

| Class | `reason` |
|---|---|
| Non-problematic | `regular_70` |
| Moved | `shifted_into_90_95`, `shifted_under_95`, and `respaced_90_95` (the whole run was re-pitched) |
| Clashing | `unresolved_clash`, or any point with `clear: false` |

Trade is not on the point yet. Each run already stores `system_names` from `IfcSystem`. On the Zenodo duplex the split is also the file: `zenodo-duplex-piping.ifc` is sanitary, `HeatingAndCooling.ifc` is heating/cooling, `zenodo-duplex-ventilation.ifc` is ventilation. A mixed file such as the buildingSMART duplex MEP model has to take the trade from the run’s system names. Copy that trade onto every point when the IFC is written.

**One extra IFC.** After placement, write something like `examples/out/<stem>-mountings.ifc` with ifcopenshell. One element per hanger: a short rod from the service to the anchor, in the same metres and the same coordinates as the source. The viewer already loads models with `COORDINATE_TO_ORIGIN: false`, so this file will sit on the pipes and ducts. Keep it out of the clash list. A ticked clash file is treated as obstacles and is not given hangers of its own.

Give every element a property set, for example `Pset_DrillMount`, with `Status` (`clear`, `moved`, `clash`) and `Trade` (`sanitary`, `heating_cooling`, `ventilation`), and color the solids by status (green, amber, red). The picture is then readable before any filter is touched.

**Show and hide.** The viewer already loads several IFCs as separate fragment models (`id` plus repeated `clash` parameters). Add this file as its own model, with its own checkbox. `Hider` already isolates by model id, so that checkbox only has to drop or restore that model’s ids.

**Filter status and trade inside that model.** The existing category list will not do this. It groups every loaded model by IFC class, so three hanger classes only appear as three checkboxes if they are three different IFC classes, and those checkboxes would also hide the same class in the building. Status and trade are properties, so the viewer needs two checkbox groups that read `Pset_DrillMount` on the mounting model only and then call `hider.isolate`.

One existing behavior has to change with this, or a storey pick will hide every hanger: choosing a storey currently keeps only the model that owns that storey and clears the others. The mounting file should be kept when the storey name matches, using the same storey names as the source.