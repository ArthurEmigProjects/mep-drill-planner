import * as THREE from "three";
import * as OBC from "@thatopen/components";

const WASM_PATH = "https://unpkg.com/web-ifc@0.0.77/";

let components;
let world;
let fragments;
let ifcLoader;
let ready = null;
let generation = 0;

function status(text) {
  const node = document.querySelector("#viewer-status");
  if (node) node.textContent = text;
}

async function start() {
  const container = document.querySelector("#viewer-canvas");
  components = new OBC.Components();
  const worlds = components.get(OBC.Worlds);
  world = worlds.create();
  world.scene = new OBC.SimpleScene(components);
  world.scene.setup();
  world.scene.three.background = new THREE.Color("#d5dde4");
  world.renderer = new OBC.SimpleRenderer(components, container);
  world.camera = new OBC.OrthoPerspectiveCamera(components);
  await world.camera.controls.setLookAt(12, 8, 12, 0, 0, 0);
  components.init();
  components.get(OBC.Grids).create(world);

  const workerUrl = await OBC.FragmentsManager.getWorker();
  fragments = components.get(OBC.FragmentsManager);
  fragments.init(workerUrl);
  world.camera.controls.addEventListener("update", () => fragments.core.update());
  fragments.list.onItemSet.add(({ value: model }) => {
    model.useCamera(world.camera.three);
    world.scene.three.add(model.object);
    fragments.core.update(true);
  });
  fragments.core.models.materials.list.onItemSet.add(({ value: material }) => {
    if (!("isLodMaterial" in material && material.isLodMaterial)) {
      material.polygonOffset = true;
      material.polygonOffsetUnits = 1;
      material.polygonOffsetFactor = Math.random();
    }
  });

  ifcLoader = components.get(OBC.IfcLoader);
  await ifcLoader.setup({
    autoSetWasm: false,
    wasm: { path: WASM_PATH, absolute: true },
    webIfc: { COORDINATE_TO_ORIGIN: false },
  });
}

function ensure() {
  if (!ready) {
    ready = start().catch((error) => {
      ready = null;
      throw error;
    });
  }
  return ready;
}

async function frameModels() {
  const box = new THREE.Box3();
  for (const model of fragments.list.values()) {
    const item = model.box;
    if (!item || item.isEmpty()) continue;
    box.union(item);
  }
  if (box.isEmpty()) return null;
  await world.camera.controls.fitToBox(box, true, {
    paddingTop: 0.15,
    paddingBottom: 0.15,
    paddingLeft: 0.15,
    paddingRight: 0.15,
  });
  fragments.core.update(true);
  return box.getSize(new THREE.Vector3());
}

async function clearModels() {
  const ids = [...fragments.list.keys()];
  await Promise.all(ids.map((id) => fragments.core.disposeModel(id)));
}

async function loadOne(file, index, total, token) {
  status(`Reading ${file.name} (${index} of ${total})…`);
  const response = await fetch(`/api/ifc?id=${encodeURIComponent(file.id)}`);
  if (!response.ok) {
    let message = `Could not read ${file.name}.`;
    try {
      const data = await response.json();
      if (data.error) message = data.error;
    } catch {
      /* the body was not JSON */
    }
    throw new Error(message);
  }
  const buffer = new Uint8Array(await response.arrayBuffer());
  if (token !== generation) return;
  status(`Converting ${file.name} (${index} of ${total}). Large models take a while.`);
  await ifcLoader.load(buffer, false, file.id);
}

function labelForId(id) {
  const raw = id.includes(":") ? id.slice(id.indexOf(":") + 1) : id;
  return raw.replace(/^[0-9a-f]{8}-/i, "");
}

function filesFromQuery() {
  if (document.body.dataset.page !== "viewer") return null;
  const params = new URLSearchParams(location.search);
  const ids = [];
  const primary = params.get("id");
  if (primary) ids.push(primary);
  for (const extra of params.getAll("clash")) {
    if (extra && !ids.includes(extra)) ids.push(extra);
  }
  return ids.map((id) => ({ id, name: labelForId(id) }));
}

async function open(files) {
  const token = ++generation;
  const section = document.querySelector("#viewer");
  if (section) {
    section.hidden = false;
    section.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
  const heading = document.querySelector("#viewer-title");
  if (heading && files.length) heading.textContent = files.map((file) => file.name).join(", ");
  if (document.body.dataset.page === "viewer" && files[0]) {
    document.title = `${files[0].name} · MEP drill planner`;
  }
  status("Starting the viewer…");
  await ensure();
  if (token !== generation) return;
  await clearModels();
  if (token !== generation) return;
  let index = 0;
  for (const file of files) {
    index += 1;
    await loadOne(file, index, files.length, token);
    if (token !== generation) return;
  }
  const size = await frameModels();
  const names = files.map((file) => file.name).join(", ");
  if (!size) {
    status(`${names} · no geometry to frame`);
    return;
  }
  const extent = `${size.x.toFixed(1)} × ${size.y.toFixed(1)} × ${size.z.toFixed(1)} m`;
  const label = files.length === 1 ? names : `${files.length} models · ${names}`;
  status(`${label} · ${extent}`);
}

window.MepViewer = { open };

const requested = filesFromQuery();
if (requested) {
  if (!requested.length) {
    status("No model was selected.");
  } else {
    open(requested).catch((error) => status(error.message || "Could not open the model."));
  }
}
