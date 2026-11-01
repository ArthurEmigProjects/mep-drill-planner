import * as THREE from "three";
import * as OBC from "@thatopen/components";

const WASM_PATH = "https://unpkg.com/web-ifc@0.0.77/";
const PALETTE = ["#b8431f", "#1d4e89", "#2f6f4e", "#8a6a12", "#6b3fa0", "#0e7490", "#9a3412", "#3f6212", "#9f1239", "#334155"];

let components;
let world;
let fragments;
let ifcLoader;
let clipper;
let hider;
let grid;
let ready = null;
let generation = 0;
const sectionPlanes = { x: null, y: null, z: null };
let categories = [];
let storeys = [];

function status(text) {
  const node = document.querySelector("#viewer-status");
  if (node) node.textContent = text;
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function prettyCategory(name) {
  const bare = name.replace(/^IFC/i, "").replace(/_/g, " ");
  if (bare === bare.toUpperCase()) return bare.charAt(0) + bare.slice(1).toLowerCase();
  return bare.replace(/([a-z])([A-Z])/g, "$1 $2");
}

function readAttribute(data, key) {
  if (!data) return "";
  const value = data[key] ?? data[key.toLowerCase()];
  if (typeof value === "string") return value;
  if (value && typeof value.value === "string") return value.value;
  return "";
}

function combinedBox() {
  const box = new THREE.Box3();
  for (const model of fragments.list.values()) {
    const item = model.box;
    if (item && !item.isEmpty()) box.union(item);
  }
  return box.isEmpty() ? null : box;
}

function clippingPlanes() {
  const renderer = world.renderer.three;
  if (!renderer.clippingPlanes) renderer.clippingPlanes = [];
  return renderer.clippingPlanes;
}

function syncClipMaterials() {
  const planes = clippingPlanes();
  const list = fragments?.core?.models?.materials?.list;
  if (!list) return;
  for (const material of list.values()) {
    material.clippingPlanes = planes;
    material.clipShadows = true;
  }
}

function mountTools() {
  const host = document.querySelector("#viewer-canvas");
  if (!host || document.querySelector("#view-tools")) return;
  const aside = document.createElement("aside");
  aside.id = "view-tools";
  aside.className = "view-tools";
  aside.hidden = true;
  aside.addEventListener("pointerdown", (event) => event.stopPropagation());

  const viewHeading = document.createElement("h3");
  viewHeading.textContent = "View";
  const viewRow = document.createElement("div");
  viewRow.className = "view-row";
  viewRow.append(
    toolButton("Fit", () => frameModels()),
    toolButton("Orbit", () => world.camera.set("Orbit")),
    toolButton("Plan", () => world.camera.set("Plan")),
    toolButton("Orthographic", async (button) => {
      const next = world.camera.projection.current === "Orthographic" ? "Perspective" : "Orthographic";
      await world.camera.projection.set(next);
      button.textContent = next === "Orthographic" ? "Perspective" : "Orthographic";
      for (const model of fragments.list.values()) model.useCamera(world.camera.three);
      fragments.core.update(true);
    }),
    toolButton("Show all", () => showEverything()),
    toolButton("Reset view", () => resetView()),
  );

  const cutHeading = document.createElement("h3");
  cutHeading.textContent = "Cutting";
  const cutNote = document.createElement("p");
  cutNote.className = "hint";
  cutNote.textContent = "100% shows the whole model. Double-click a face to cut there. Delete removes the cut under the pointer.";

  const filterHeading = document.createElement("h3");
  filterHeading.textContent = "Filter";
  const storeyLabel = document.createElement("label");
  storeyLabel.className = "view-slider";
  const storeyText = document.createElement("span");
  storeyText.textContent = "Storey";
  const storeySelect = document.createElement("select");
  storeySelect.id = "view-storeys";
  storeySelect.addEventListener("change", () => {
    applyVisibility().catch((error) => status(error.message || "Could not filter the model."));
  });
  storeyLabel.append(storeyText, storeySelect);
  const categoryList = document.createElement("div");
  categoryList.id = "view-categories";
  categoryList.className = "category-list";

  const colorHeading = document.createElement("h3");
  colorHeading.textContent = "Color";
  const colorRow = document.createElement("div");
  colorRow.className = "view-row";
  const colorInput = document.createElement("input");
  colorInput.id = "view-color";
  colorInput.type = "color";
  colorInput.value = "#b8431f";
  const colorField = document.createElement("label");
  colorField.className = "view-color";
  const colorText = document.createElement("span");
  colorText.textContent = "Tint";
  colorField.append(colorText, colorInput);
  colorRow.append(
    toolButton("By category", () => colorByCategory()),
    toolButton("Tint ticked", () => colorCategories(tickedCategories(), colorInput.value)),
    toolButton("Reset color", () => resetColors()),
  );
  const fade = slider("Fade", "fade");
  fade.querySelector("input").value = "100";
  fade.querySelector("input").addEventListener("input", (event) => {
    const opacity = Number(event.target.value) / 100;
    setOpacity(opacity).catch((error) => status(error.message || "Could not fade the model."));
  });

  aside.append(
    viewHeading,
    viewRow,
    cutHeading,
    slider("Height", "y"),
    slider("Side", "x"),
    slider("Depth", "z"),
    toolButton("Clear cuts", () => clearCuts()),
    cutNote,
    filterHeading,
    storeyLabel,
    categoryList,
    colorHeading,
    colorField,
    colorRow,
    fade,
  );
  host.append(aside);
}

function toolButton(label, action) {
  const node = document.createElement("button");
  node.type = "button";
  node.className = "ghost";
  node.textContent = label;
  node.addEventListener("click", () => {
    Promise.resolve(action(node)).catch((error) => status(error.message || "The view change failed."));
  });
  return node;
}

function slider(label, axis) {
  const row = document.createElement("label");
  row.className = "view-slider";
  const text = document.createElement("span");
  text.textContent = label;
  const input = document.createElement("input");
  input.type = "range";
  input.min = "0";
  input.max = "100";
  input.value = "100";
  input.dataset.axis = axis;
  input.setAttribute("aria-label", label === "Height" ? "Section height" : `Section ${label.toLowerCase()}`);
  if (axis !== "fade") {
    input.addEventListener("input", () => setAxisCut(axis, Number(input.value)));
  }
  row.append(text, input);
  return row;
}

function tickedCategories() {
  return [...document.querySelectorAll("#view-categories input:checked")].map((input) => input.value);
}

async function idsForCategories(model, names) {
  if (!names.length) return [];
  const items = await model.getItemsOfCategories(names.map((name) => new RegExp(`^${escapeRegExp(name)}$`)));
  return Object.values(items).flat();
}

async function applyVisibility() {
  const ticked = new Set(tickedCategories());
  const allCategories = categories.length === 0 || ticked.size === categories.length;
  const storeyKey = document.querySelector("#view-storeys")?.value || "";
  const storey = storeys.find((item) => item.key === storeyKey) || null;
  if (allCategories && !storey) {
    await hider.set(true);
    fragments.core.update(true);
    return;
  }
  const map = {};
  for (const model of fragments.list.values()) {
    let ids = allCategories ? null : new Set(await idsForCategories(model, [...ticked]));
    if (storey && storey.modelId === model.modelId) {
      ids = ids ? new Set([...ids].filter((id) => storey.ids.has(id))) : new Set(storey.ids);
    } else if (storey) {
      ids = new Set();
    }
    map[model.modelId] = ids || new Set(await idsForCategories(model, categories));
  }
  await hider.isolate(map);
  fragments.core.update(true);
}

async function showEverything() {
  for (const input of document.querySelectorAll("#view-categories input")) input.checked = true;
  const select = document.querySelector("#view-storeys");
  if (select) select.value = "";
  const fade = document.querySelector('#view-tools input[data-axis="fade"]');
  if (fade) fade.value = "100";
  await hider.set(true);
  await setOpacity(1);
}

async function setOpacity(opacity) {
  for (const model of fragments.list.values()) await model.setOpacity(undefined, opacity);
  fragments.core.update(true);
}

async function colorByCategory() {
  let index = 0;
  for (const name of categories) {
    await colorCategories([name], PALETTE[index % PALETTE.length]);
    index += 1;
  }
}

async function colorCategories(names, hex) {
  if (!names.length) return;
  const color = new THREE.Color(hex);
  for (const model of fragments.list.values()) {
    const ids = await idsForCategories(model, names);
    if (ids.length) await model.setColor(ids, color);
  }
  fragments.core.update(true);
}

async function resetColors() {
  for (const model of fragments.list.values()) await model.resetColor(undefined);
  fragments.core.update(true);
}

function setAxisCut(axis, percent) {
  const box = combinedBox();
  const list = clippingPlanes();
  const current = sectionPlanes[axis];
  if (!box || percent >= 99.5) {
    if (current) {
      const index = list.indexOf(current);
      if (index >= 0) list.splice(index, 1);
      sectionPlanes[axis] = null;
    }
    syncClipMaterials();
    fragments?.core.update(true);
    return;
  }
  const min = box.min[axis];
  const max = box.max[axis];
  const value = min + (max - min) * (percent / 100);
  const normal = new THREE.Vector3(axis === "x" ? -1 : 0, axis === "y" ? -1 : 0, axis === "z" ? -1 : 0);
  const point = new THREE.Vector3(axis === "x" ? value : 0, axis === "y" ? value : 0, axis === "z" ? value : 0);
  const plane = current || new THREE.Plane();
  plane.setFromNormalAndCoplanarPoint(normal, point);
  if (!current) {
    sectionPlanes[axis] = plane;
    list.push(plane);
  }
  syncClipMaterials();
  fragments.core.update(true);
}

function clearCuts() {
  if (clipper) clipper.deleteAll();
  for (const axis of ["x", "y", "z"]) setAxisCut(axis, 100);
  for (const input of document.querySelectorAll("#view-tools input[data-axis]")) {
    if (input.dataset.axis !== "fade") input.value = "100";
  }
  syncClipMaterials();
  fragments?.core.update(true);
}

async function resetView() {
  clearCuts();
  await showEverything();
  await resetColors();
  await world.camera.projection.set("Perspective");
  world.camera.set("Orbit");
  const ortho = [...document.querySelectorAll("#view-tools button")].find((node) => node.textContent === "Perspective");
  if (ortho) ortho.textContent = "Orthographic";
  await frameModels();
}

function collectIds(node, into) {
  if (typeof node?.localId === "number") into.add(node.localId);
  for (const child of node?.children || []) collectIds(child, into);
}

function isStorey(node) {
  return String(node?.category || "").toUpperCase().includes("BUILDINGSTOREY");
}

async function loadStoreys() {
  storeys = [];
  for (const model of fragments.list.values()) {
    let tree;
    try {
      tree = await model.getSpatialStructure();
    } catch {
      continue;
    }
    const found = [];
    const walk = (node) => {
      if (isStorey(node)) found.push(node);
      for (const child of node?.children || []) walk(child);
    };
    walk(tree);
    for (const node of found) {
      const ids = new Set();
      collectIds(node, ids);
      let name = `Storey ${storeys.length + 1}`;
      if (typeof node.localId === "number") {
        try {
          const [data] = await model.getItemsData([node.localId]);
          name = readAttribute(data, "Name") || readAttribute(data, "LongName") || name;
        } catch {
          /* the storey keeps a numbered label */
        }
      }
      storeys.push({ key: `${model.modelId}:${node.localId}`, modelId: model.modelId, name, ids });
    }
  }
}

async function refreshTools() {
  const tools = document.querySelector("#view-tools");
  const list = document.querySelector("#view-categories");
  const select = document.querySelector("#view-storeys");
  if (!tools || !list || !select) return;
  categories = [];
  const seen = new Set();
  for (const model of fragments.list.values()) {
    const names = await model.getCategories();
    const geometric = new Set(await model.getItemsIdsWithGeometry());
    const items = names.length
      ? await model.getItemsOfCategories(names.map((name) => new RegExp(`^${escapeRegExp(name)}$`)))
      : {};
    for (const name of names) {
      const ids = items[name] || [];
      if (!ids.some((id) => geometric.has(id)) || seen.has(name)) continue;
      seen.add(name);
      categories.push(name);
    }
  }
  categories.sort((a, b) => prettyCategory(a).localeCompare(prettyCategory(b)));
  list.replaceChildren(...categories.map((name) => {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = name;
    input.checked = true;
    input.addEventListener("change", () => {
      applyVisibility().catch((error) => status(error.message || "Could not filter the model."));
    });
    const text = document.createElement("span");
    text.textContent = prettyCategory(name);
    text.title = name;
    label.append(input, text);
    return label;
  }));
  if (!categories.length) {
    const empty = document.createElement("p");
    empty.className = "hint";
    empty.textContent = "This model has no categories.";
    list.append(empty);
  }
  await loadStoreys();
  select.replaceChildren();
  const all = document.createElement("option");
  all.value = "";
  all.textContent = "All storeys";
  select.append(all);
  for (const storey of storeys) {
    const option = document.createElement("option");
    option.value = storey.key;
    option.textContent = storey.name;
    select.append(option);
  }
  select.hidden = storeys.length === 0;
  select.parentElement.hidden = storeys.length === 0;
  tools.hidden = false;
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
  world.renderer.three.localClippingEnabled = true;
  clippingPlanes();
  world.camera = new OBC.OrthoPerspectiveCamera(components);
  await world.camera.controls.setLookAt(12, 8, 12, 0, 0, 0);
  components.init();
  grid = components.get(OBC.Grids).create(world);
  world.camera.projection.onChanged.add(() => {
    if (grid && "fade" in grid) grid.fade = world.camera.projection.current === "Perspective";
  });

  const workerUrl = await OBC.FragmentsManager.getWorker();
  fragments = components.get(OBC.FragmentsManager);
  fragments.init(workerUrl);
  world.camera.controls.addEventListener("update", () => fragments.core.update());
  fragments.list.onItemSet.add(({ value: model }) => {
    model.useCamera(world.camera.three);
    world.scene.three.add(model.object);
    model.getClippingPlanesEvent = () => clippingPlanes();
    fragments.core.update(true);
  });
  fragments.core.models.materials.list.onItemSet.add(({ value: material }) => {
    if (!("isLodMaterial" in material && material.isLodMaterial)) {
      material.polygonOffset = true;
      material.polygonOffsetUnits = 1;
      material.polygonOffsetFactor = Math.random();
      material.clipShadows = true;
      material.clippingPlanes = clippingPlanes();
    }
  });

  ifcLoader = components.get(OBC.IfcLoader);
  await ifcLoader.setup({
    autoSetWasm: false,
    wasm: { path: WASM_PATH, absolute: true },
    webIfc: { COORDINATE_TO_ORIGIN: false },
  });
  hider = components.get(OBC.Hider);
  components.get(OBC.Raycasters).get(world);
  clipper = components.get(OBC.Clipper);
  clipper.enabled = true;
  if (clipper.config) clipper.config.enabled = true;
  container.addEventListener("dblclick", () => {
    if (!clipper?.enabled) return;
    try {
      clipper.create(world);
    } catch (error) {
      status(error.message || "Could not cut at that point.");
    }
  });
  window.addEventListener("keydown", (event) => {
    const typing = event.target instanceof HTMLInputElement
      || event.target instanceof HTMLTextAreaElement
      || event.target instanceof HTMLSelectElement;
    if (typing || !clipper?.enabled) return;
    if (event.key === "Delete" || event.key === "Backspace") {
      event.preventDefault();
      try {
        clipper.delete(world);
      } catch (error) {
        status(error.message || "Could not remove that cut.");
      }
    }
  });
  mountTools();
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
  const box = combinedBox();
  if (!box) return null;
  await world.camera.controls.fitToBox(box, true, {
    paddingTop: 0.15,
    paddingBottom: 0.15,
    paddingLeft: 0.15,
    paddingRight: 0.15,
  });
  for (const model of fragments.list.values()) model.useCamera(world.camera.three);
  fragments.core.update(true);
  const size = box.getSize(new THREE.Vector3());
  if (clipper?.config) clipper.config.size = Math.max(size.x, size.y, size.z);
  return size;
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
  const tools = document.querySelector("#view-tools");
  if (tools) tools.hidden = true;
  status("Starting the viewer…");
  await ensure();
  if (token !== generation) return;
  clearCuts();
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
  await refreshTools();
  if (token !== generation) return;
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
