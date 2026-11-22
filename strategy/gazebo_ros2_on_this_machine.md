# Gazebo and ROS 2 on this machine

Step-by-step setup for the laptop this repo is developed on, so the overhead-drill simulation in [simulate_overhead_drilling.md](simulate_overhead_drilling.md) can run here. That note is the robot, the scenes, and the report. This note is the install and the first commands.

Checked on 22 Nov 2026: Ubuntu 24.04.5 LTS, kernel 7.0.0-43-generic, ROS 2 Jazzy already sourced from `~/.bashrc`. Gazebo was not installed yet. The Jazzy apt package that provides it is `ros-jazzy-gz-sim-vendor` 0.0.13, which vendors Gazebo Harmonic (`gz-sim` 8.15.0). The bridge meta-package is `ros-jazzy-ros-gz` 1.0.25.

## What is already on the machine

| Piece | State |
| --- | --- |
| OS | Ubuntu 24.04.5, amd64, X11 session (`DISPLAY` is set) |
| CPU / RAM / disk | 12 threads, 16 GB RAM, about 314 GB free on `/` |
| GPU | Intel Tiger Lake UHD drives the desktop. NVIDIA GeForce RTX 3050 Laptop, driver 595.99 open, `prime-select` is `on-demand` |
| ROS 2 | Jazzy desktop at `/opt/ros/jazzy`. `~/.bashrc` sources it, then `~/ros2_ws/install/setup.bash` |
| `~/ros2_ws` | Personal tutorial packages (`my_py_pkg`, `turtle_sample_task`, and others). Leave them there |
| `colcon` | Installed (`ros-dev-tools`) |
| Gazebo, Nav2, MoveIt, `ros2_control` | Not installed |
| Planner | Python 3.12 venv in this repo (`.venv`). It stays a separate program from ROS |

Two shells, two jobs. The planner shell has `.venv` active and never sources ROS. The simulation shell has Jazzy sourced and never activates `.venv`. They meet through the target file the design note describes (`examples/out/`, gitignored).

## Install only the Jazzy Gazebo

Harmonic is the simulator paired with Jazzy. It arrives as a vendor package inside `/opt/ros/jazzy`, and the command is `gz sim`. A second copy from the Gazebo project apt repository, or a `ros-kilted-*` / `ros-rolling-*` package, would put another `libgz` on the same machine. The ROS apt repository on this computer already indexes those other distros. Install names that start with `ros-jazzy-`.

Classic Gazebo (`gazebo`, `gazebo_ros_pkgs`, `ign gazebo`) is a different program and is not the one this distro uses.

## 1. Confirm the shell

Open a new terminal. `~/.bashrc` has already sourced Jazzy and the home workspace.

```bash
echo "$ROS_DISTRO"
# jazzy

which ros2
# /opt/ros/jazzy/bin/ros2

ros2 doctor
```

`ros2 doctor` may print warnings about the network or about optional packages. Jazzy itself is fine when `echo "$ROS_DISTRO"` prints `jazzy` and `ros2 pkg list` includes `rclpy`.

## 2. Install the bridge, which pulls Harmonic

```bash
sudo apt update
sudo apt install ros-jazzy-ros-gz
```

That meta-package depends on `ros-jazzy-ros-gz-bridge`, `ros-jazzy-ros-gz-sim`, `ros-jazzy-ros-gz-image`, and `ros-jazzy-ros-gz-sim-demos`. `ros-jazzy-ros-gz-sim` depends on `ros-jazzy-gz-sim-vendor`, which is Harmonic 8.15.0. Expect a download on the order of a gigabyte. The free space on `/` covers it.

Open a new terminal so `PATH` picks up the new executables, then:

```bash
gz sim --versions
```

The Gazebo Sim line should be major version 8. `which gz` should be under `/opt/ros/jazzy`.

## 3. Open a stock world

Still in a terminal where Jazzy is sourced:

```bash
gz sim shapes.sdf
```

A window should show a ground plane and a few primitive shapes. Close it from the window, or press Ctrl-C in the terminal.

If the window is black or the process exits on the first frame, the on-demand NVIDIA GPU is the next try. The desktop stays on the Intel chip until a program asks for the RTX 3050:

```bash
__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia gz sim shapes.sdf
```

While that window is open, a second terminal should list a `gz` process:

```bash
nvidia-smi
```

If the Intel run was fine, keep using it for the shapes world. Use the offload prefix when a later scene (sensors, a full storey) is too slow. Put the prefix in the shell for that session rather than in `~/.bashrc`, so the rest of the desktop stays on the Intel GPU:

```bash
export __NV_PRIME_RENDER_OFFLOAD=1
export __GLX_VENDOR_LIBRARY_NAME=nvidia
```

The session is X11, so leave `QT_QPA_PLATFORM` unset.

Server only, no window, for the same world. `-s` is the server, `-r` starts the clock, `-v4` prints warnings:

```bash
gz sim -s -r -v4 shapes.sdf
```

Ctrl-C after a few seconds. This is the mode a long duplex replay will use. The GUI is for the concrete bay, where there are five holes to watch.

## 4. Drive a stock robot from a ROS topic

This checks the bridge, the simulator, and RViz together. On 16 GB, Gazebo and RViz at once is the heavy case. Start without RViz first:

```bash
ros2 launch ros_gz_sim_demos diff_drive.launch.py rviz:=false
```

The launch file starts `gz sim -r diff_drive.sdf` and a `parameter_bridge`. In a second terminal (Jazzy sourced):

```bash
ros2 topic list
```

`/model/vehicle_blue/cmd_vel` and `/model/vehicle_blue/odometry` should be there. Publish a twist and watch the blue vehicle move:

```bash
ros2 topic pub /model/vehicle_blue/cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.5}, angular: {z: 0.3}}"
```

Ctrl-C the publisher, then Ctrl-C the launch.

Repeat once with RViz, which is the launch default:

```bash
ros2 launch ros_gz_sim_demos diff_drive.launch.py
```

If the machine starts swapping, close that and stay with `rviz:=false`. The IFC viewer in `python -m src.ui` is also an OpenGL process. Close the browser tab before a Gazebo GUI session.

The same launch through the ROS entry point, useful later because it sets `GZ_SIM_RESOURCE_PATH` from package exports:

```bash
ros2 launch ros_gz_sim gz_sim.launch.py gz_args:="shapes.sdf"
```

Headless through that entry point:

```bash
ros2 launch ros_gz_sim gz_sim.launch.py gz_args:="-s -r shapes.sdf"
```

## 5. Keep the drill workspace inside this repo

`~/ros2_ws` is the tutorial workspace and is already on the overlay from `~/.bashrc`. The drill packages go in this repo, which is what [simulate_overhead_drilling.md](simulate_overhead_drilling.md) specifies:

```text
sim/ros2_ws/src/mep_drill_description
sim/ros2_ws/src/mep_drill_gazebo
sim/ros2_ws/src/mep_drill_mission
```

Create the workspace when the first package is written. An empty `src` builds nothing useful, so this step waits for that package.

```bash
cd /home/arthur-emig/GitHub/mep-drill-planner
mkdir -p sim/ros2_ws/src
cd sim/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

Sourcing `/opt/ros/jazzy/setup.bash` again does not drop `~/ros2_ws` if `~/.bashrc` already sourced it. That is acceptable: the tutorial package names do not overlap `mep_drill_*`. Runtime order after you source this workspace is drill, then tutorials, then Jazzy.

Build and run from a shell that has not activated `.venv`. `colcon` and `ros2` use the system Python 3.12 that Jazzy was built for.

Each new terminal that should see the drill packages:

```bash
source /opt/ros/jazzy/setup.bash
source /home/arthur-emig/GitHub/mep-drill-planner/sim/ros2_ws/install/setup.bash
```

Add that second line to `~/.bashrc` only after the workspace exists and `install/setup.bash` is present. Until then a missing file would print an error on every shell.

When a tutorial node and the drill sim are both running, give the sim its own domain so the graphs stay apart:

```bash
export ROS_DOMAIN_ID=42
```

The default domain is 0, which is what the tutorial workspace uses. One domain is fine while only one graph is up.

`use_sim_time` is on for every drill launch. Nodes that use the wall clock will disagree with Gazebo’s clock.

## 6. Add the rest of the stack as each package needs it

Install the next row when that work starts. The shapes world and the diff-drive demo need only step 2.

| When | Packages |
| --- | --- |
| URDF, joint sliders, robot state | `ros-jazzy-xacro` `ros-jazzy-joint-state-publisher-gui` (`robot_state_publisher` is already in the Jazzy desktop) |
| Mast and base drives simulated through `ros2_control` | `ros-jazzy-ros2-control` `ros-jazzy-ros2-controllers` `ros-jazzy-gz-ros2-control` |
| Base driving between stances | `ros-jazzy-navigation2` `ros-jazzy-nav2-bringup` |
| Mast and fine stage, collision-aware | `ros-jazzy-moveit` |

```bash
sudo apt install ros-jazzy-xacro ros-jazzy-joint-state-publisher-gui
```

Repeat with the names from the row you are starting. Nav2 and MoveIt are large. They are not required to prove Gazebo.

## 7. Follow the design order once the window works

[simulate_overhead_drilling.md](simulate_overhead_drilling.md) splits the work so a Gazebo install never blocks the result the planner trusts.

1. Exporter and geometric test in `src/`, under `unittest`, in the planner venv. No `gz`, no `ros2`.
2. Concrete bay in Gazebo. Five holes, one drill cycle each, markers left in the slab. This is the first scene to watch with the GUI.
3. One duplex storey. Floor map from the architecture IFC. Prefer `gz sim -s` for the full pass, and open the GUI to look at a short stretch.
4. Head-envelope feedback, then wall mounts, then a camera when perception needs a recorded image.

The geometric report is the result. The Gazebo run is the check that the motion between those poses is watchable and stays clear of the services.

When `sim/ros2_ws` exists, `sim/README.md` should carry the two launch commands and point back here for the apt packages. The shape of those launches, from the design note:

```bash
source /opt/ros/jazzy/setup.bash
source /home/arthur-emig/GitHub/mep-drill-planner/sim/ros2_ws/install/setup.bash
ros2 launch mep_drill_gazebo concrete_bay.launch.py
```

and a second launch that takes a target file exported from one storey. Both set `use_sim_time`. A server-only argument belongs on the storey launch.

Crop to one storey in Gazebo. A few hundred points in one physics run is the case the geometric test scores, in `examples/out/`, gitignored like the other outputs.

## 8. Done when

- `gz sim --versions` reports Gazebo Sim 8.
- `gz sim shapes.sdf` opens a window, and `gz sim -s -r shapes.sdf` runs without one.
- `ros2 launch ros_gz_sim_demos diff_drive.launch.py rviz:=false` starts, and a `Twist` on `/model/vehicle_blue/cmd_vel` moves the blue vehicle.
- The planner still runs with `.venv` and `python -m src.ui`, in a shell that has not sourced the drill workspace.
- `~/ros2_ws` still builds on its own.

After that, the next file to write is the exporter in `src/`, not another simulator package.
