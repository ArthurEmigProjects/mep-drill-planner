# Simulating overhead drilling with ROS 2

Ideas for roadmap step 11: a mobile machine visits the ceiling points from `*-mounting-points.json` and rehearses an upward drill, in ROS 2 Jazzy and Gazebo. The machines named in the README (Hilti Jaibot, fischer BauBot) are the kind of job this imitates. The simulation uses a robot model we author ourselves.

The planner already decides where a hanger rod can go. The simulation answers the next question: can a machine on the floor stand there, reach that point, and feed a bit into the face above it without hitting the services.

## What an overhead drill is, in this repo

A ceiling point stores the top of the pipe or duct, not the hole. `mount` is `ceiling`, `mount_direction` is `[0, 0, 1]`, and `anchor` is empty. The coordinates are metres in the IFC frame. The rod the clash check imagines starts just above that crown and runs upward at most `MAX_ROD_LENGTH_M` (2 m), with a radius of 10 mm. Slabs and ceilings are left out of that check on purpose: the rod is supposed to meet them. Beams and other services are the things it must miss.

The hole the bit cuts is the first structural face that ray hits. Finding that face is the first piece of work, and it can be done in this repo before any ROS install.

Wall points are a different job. A riser is fixed sideways: `mount` is `wall`, `mount_direction` is horizontal, and `anchor` is the point on the wall face. The same mission file can carry them, and the first simulation runs only the ceiling points.

## Two scenes, because the sample building and the drill are different jobs

The Zenodo duplex architecture has gypsum ceilings under timber joists, with a clear gap of about 238 mm on level 1 and 343 mm on level 2. Concrete in that model is the slab on grade and the foundation walls. The catalogue treats fischer EA II as a concrete anchor, and the coverage report already refuses those anchors when the substrate is not concrete. A floor-standing drill of the Jaibot kind works under an exposed structural soffit, with the hanger dropping from the hole it just cut.

So the same mission format loads two worlds.

**Duplex storey.** One storey of piping or ventilation, plus the architecture file. The base drives the real floor plan. The mast reaches toward whatever the upward ray hits within 2 m. Many points will come back as `no_substrate` or as a hit on gypsum or timber. That result is useful: it says the sample building is a navigation and clearance scene, and it keeps the sim honest about the catalogue.

**Concrete bay.** A flat concrete slab, a floor, a few columns, and a handful of ceiling points projected up to that soffit. This is where the feed, the bit diameter, and the hole depth mean something. The EA II notes already cite a 27 mm hole depth, a 10 mm bit for M8, and a 12 mm bit for M10. Those numbers stay a launch parameter until the catalogue stores them as fields. The bay is small enough to watch one drill cycle from approach to retract.

A point marked `unresolved_clash` stays out of both scenes. The rod was not given a free station. A separate pass can send those ids through on purpose, and the expected result is a collision with the service or beam the planner named in `clashing_element_ids`.

## Stack

| Piece | Role |
| --- | --- |
| ROS 2 Jazzy | Graph, TF, `ros2_control`, launch. Matches the roadmap. Ubuntu 24.04. |
| Gazebo Harmonic (`gz sim` via `ros_gz`) | The world, the drives, and contact. The simulator Jazzy is paired with. |
| MoveIt 2 | Collision-aware plans for the mast and the fine stage. |
| Nav2 | The base moving between stances on a static floor map. |
| `ros2_control` | One hardware interface simulated in Gazebo, so a later real machine replaces the sim backend and keeps the controllers. |

Isaac Sim can consume the same target file later, if a camera or a depth image is worth a GPU. Step 12 is perception. The first sim localizes from the simulator's own pose.

Gazebo is the picture someone watches. The regression check is a headless geometric test in this repo's existing `unittest` run: no ROS, no physics. Gazebo stays optional for CI.

## Robot we can publish

A vertical hole wants a vertical axis. The stand-in is a differential-drive base, a prismatic mast, a short horizontal stage, and a spindle.

Starting sizes, as parameters, not as a claim about either commercial machine:

| Joint | Range | Job |
| --- | --- | --- |
| Base | floor, yaw ±π | Park near the point. Footprint about 0.7 m by 1.0 m. |
| Mast | 0 to about 3 m | Bring the head up under the soffit. Stroke sized from the storey, once the IFC is measured. |
| Fine stage | ±0.20 m in X and Y of the head | Cover the residual after the base stops within 0.15 m of the stance. |
| Feed | 0 to 40 mm along the bit | The 27 mm hole fits, and the head stays below the soffit. |
| Spindle | continuous | Visual. No cutting force. |

The head is a box wider than the 10 mm rod. A station that is clear for the rod can still be blocked for the head. That disagreement is one of the results worth writing down (`blocked_by_head`).

A 6-DoF arm on the same base is a second description, for wall mounts and for reaches that must fold around a duct. An overhead pose is a common wrist singularity for that kind of arm, so the ceiling job stays on the mast. Both descriptions publish a `drill_tip` frame and a `drill_axis` that points into the material (up, for a ceiling).

Frames, all Z-up and metres, which matches the IFC and REP-103:

- `map` — the building. IFC coordinates, after the shift below.
- `odom` — identity with `map` while localization is ground truth.
- `base_link`, mast and stage joints, `drill_tip`.
- one frame per hole, origin on the face, Z into the material.

If a storey's coordinates sit hundreds of metres from the origin, subtract that storey's minimum corner and store the offset next to the targets. Physics and the static map behave better near the origin. The report adds the offset back so ids still match the planner's metres.

## From a mounting point to a drill target

A small exporter, living next to the planner so the tests can import it, reads one mounting-points file plus the architecture IFC and the service IFCs.

For each ceiling point with `clear: true`:

1. Start the ray at `(x, y, z)` plus the same small clearance the rod uses, direction `mount_direction`.
2. Intersect the slabs, beams, members, and ceiling coverings. Reuse the box and cylinder shapes the clash check already uses, and add the slabs and coverings that check leaves out.
3. Walk the hits from the crown upward. A covering whose top is below the crown is finished ceiling under the service, so it is not the host. A beam hit on a point the planner called clear is a report, not a hole. The first remaining slab or structural face within 2 m is the host.
4. Write the hole position, the axis, the substrate name taken from the IFC class and predefined type, and the source point id.

Target file (YAML or JSON, one per scene):

```yaml
frame_id: map
origin_shift_m: [0.0, 0.0, 0.0]
source: examples/out/zenodo-duplex-piping-mounting-points.json
targets:
  - id: M-0001
    run_id: R-0003
    mount: ceiling
    service_point_m: [12.40, 3.15, 2.85]
    hole_m: [12.40, 3.15, 3.40]
    axis: [0.0, 0.0, 1.0]
    substrate: concrete
    hole_depth_m: 0.027
    bit_diameter_m: 0.010
```

`substrate` is whatever the ray hit (`concrete`, `gypsum`, `timber`, `unknown`). The concrete bay sets `concrete` because the slab was built that way. The duplex writes the class it actually found. The drill feed runs for every reached hole; the report keeps the substrate so a concrete anchor is not implied for gypsum.

Collision geometry in the world is those same primitives: cylinders for round services, boxes for ducts, beams, columns, walls, and slabs. Visual meshes from IfcOpenShell can be added later, as visuals only, with collision left on the primitives. Then the sim and the clash check are looking at the same shapes.

Crop to one storey. A few hundred points in one physics run is a film nobody watches. The geometric test can score every point; Gazebo runs one storey, or the concrete bay, as a demonstration.

## Motion

**Order.** Group by storey, then by `run_id`, and inside that walk nearest-neighbor in the floor plane. Finishing a run before crossing the floor keeps the base from weaving. An optimal tour is unnecessary at this size.

**Stance.** The head has to end with the bit axis on the hole, so the base parks where the fine stage can cover the hole's XY. Candidates sit on a ring around the hole at a radius the stage and the base footprint allow. A candidate dies if the inflated footprint meets a wall or a column in the base's height band (roughly 0.05 m to 1.2 m above the floor). Services above that band stay out of the floor map. They stay in the 3D scene the mast checks.

**Floor map.** Rasterize walls and columns in that height band to a 5 cm occupancy grid, one image per storey, for Nav2. The base goal is the stance and a yaw that points the stage's long travel in a consistent direction, so plans are comparable.

**Reach.** With the base parked, MoveIt brings the mast and the stage to a standoff pose: tip on the axis, about 150 mm below the face, head clear of every service. The last motion is a straight line along `drill_axis`, from that standoff to the face. The retract is the same line in reverse. A free-space plan is the wrong tool for the feed; it will swing the bit.

**Cycle.**

1. `navigate` — Nav2 to the stance.
2. `align` — stage and mast to the standoff. Fail as `unreachable_mast` or `blocked_by_head` when the plan collides or the stroke is short.
3. `approach` — Cartesian line to the face.
4. `drill` — extend the feed joint to `hole_depth_m` while the spindle spins. The head link is forbidden to touch the slab. The bit link may.
5. `retract` — feed home, then mast back to a travel height.
6. `mark` — spawn a visual cylinder at the hole, diameter of the bit, depth of the hole, collision off, colored by outcome.

States the mission node publishes: `idle`, `navigate`, `align`, `approach`, `drill`, `retract`, `failed`. A Python sequencer is enough for this cycle. A behavior tree is the place to grow recovery (back up, try the next stance) once there is more than one recovery.

Contact in Gazebo is a check, not the ruler. Success is geometric: the tip is within a few millimetres of `hole_m`, and the axis is within a few degrees of the hole axis, after a collision-free approach. A contact message on the bit supports that. A contact on the head fails the point. No mesh is booleaned; the marker is the hole someone can see.

## What the geometric test scores without Gazebo

For the mast robot, most of the question is arithmetic, and it belongs in `src/` with the other tests.

- The hole exists and lies within mast stroke of a legal base height.
- Some stance on the ring has its footprint clear of walls and columns.
- The head box, swept from the standoff to the face, misses services and beams.
- The bit segment is the only body that meets the host face.

Outcomes use the same vocabulary as the Gazebo report, so a later physics run is a second opinion on a subset. A synthetic room (one slab, four walls, one beam, five points) locks the test. The duplex run is a larger case, written to `examples/out/` and left gitignored, the same way the point files are.

## Report the planner can read

```json
{
  "robot": "mast_drill_v1",
  "scene": "concrete_bay",
  "source": "examples/out/zenodo-duplex-piping-mounting-points.json",
  "origin_shift_m": [0.0, 0.0, 0.0],
  "results": [
    {
      "id": "M-0001",
      "outcome": "drilled",
      "substrate": "concrete",
      "stance_m": {"x": 11.9, "y": 3.15, "yaw": 0.0},
      "tip_error_m": 0.002,
      "axis_error_deg": 0.4,
      "head_collisions": [],
      "sim_time_s": 18.0
    }
  ]
}
```

`outcome` is one of `drilled`, `visited`, `unreachable_base`, `unreachable_mast`, `blocked_by_head`, `no_substrate`, `skipped_clash`, `skipped_wall_mount`. `visited` means the tip reached the standoff and the feed was not run (the duplex rehearsal). Ids stay `M-0001`, so a later UI row can show the badge beside the clash badge. Times are simulator time.

Edge distance is still step 10. The report can carry the horizontal distance from the hole to the host's boundary once the exporter has that polygon. A pass/fail limit waits for the rule. The number is still worth storing.

## Where the files go

ROS stays out of the planner's virtualenv. The how-to page remains a Python program that runs without Jazzy.

| Path | What it is |
| --- | --- |
| `src/sim_scene.py` (when built) | Ray, primitives, stances, geometric outcomes. Importable by `tests/`. |
| `sim/ros2_ws/src/mep_drill_description` | URDF, the mast robot, `ros2_control` transmissions. |
| `sim/ros2_ws/src/mep_drill_gazebo` | Concrete bay world, empty room, `ros_gz` bridge, marker spawner. |
| `sim/ros2_ws/src/mep_drill_mission` | Target file in, Nav2 and MoveIt calls, report out. |
| `examples/out/*-drill-report.json` | Local, gitignored, same as the other outputs. |

`sim/ros2_ws` is built with `colcon` on Ubuntu 24.04 after Jazzy is sourced. A short `sim/README.md` at the time the workspace appears is the place for the apt packages and the launch command. Until those packages exist, this note is the spec.

Launch shape, when it exists: one launch for the concrete bay with five hand-written targets, and one launch that takes a target file exported from a storey. `use_sim_time` is on. The server-only `gz sim` run is there for a headless replay; the GUI is there to watch the bay.

## Order of work

1. **Exporter and geometric test.** Ray to the host, stance filter, head sweep, synthetic room under `unittest`. This can land before Jazzy is installed, and it already tells us which duplex points a mast could reach.
2. **Concrete bay in Gazebo.** Five holes, the mast robot, one full cycle each, markers left in the slab. This is the first thing worth watching.
3. **One duplex storey.** Floor map from the architecture, targets from a real mounting-points file, outcomes mostly about reach and substrate. Report JSON written beside the other outputs.
4. **Head-envelope feedback.** Points that are `blocked_by_head` are listed by id. Showing them in the page is a separate UI change.
5. **Wall profile, then sensors.** Horizontal `drill_axis` for risers. A camera only when step 12 needs a recorded image from a known hole.

Dust extraction, bit wear, rebar, and anchor setting (the blow-in after the hole) stay out. Setting an anchor is a second pose on the same axis once the drill cycle is boring to watch.

## Decisions to take when building, not before

- Measure one duplex storey (floor Z, soffit Z, corridor width) and set the mast stroke and the base footprint from those numbers.
- Pick the fine-stage travel and the base stopping tolerance together: the stage has to cover the navigation error we actually see in the bay.
- Keep the first robot geometric and authored here. A commercial mesh can replace the visuals later without changing `drill_tip` or the target file.
- Treat the geometric report as the result the planner trusts, and the Gazebo run as the check that the motion between those poses is watchable and collision-free.
