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
let loadedFiles = [];
let mountingMeta = new Map();
let hangerByName = new Map();
let hangerByLocal = new Map();
let selection = {};
let opening = false;
let pendingFocus = null;
let focusToken = 0;
let propertyToken = 0;
const SELECT_STYLE = {
  color: new THREE.Color("#e8a317"),
  opacity: 1,
  transparent: false,
  renderedFaces: 1,
};

const MOUNT_STATUSES = [
  ["clear", "Non-problematic"],
  ["moved", "Moved"],
  ["clash", "Clashing"],
];
const MOUNT_TRADES = [
  ["sanitary", "Sanitary"],
  ["heating_cooling", "Heating / cooling"],
  ["ventilation", "Ventilation"],
  ["unknown", "Other"],
];

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
  const modelHeading = document.createElement("h3");
  modelHeading.id = "view-models-heading";
  modelHeading.textContent = "Models";
  modelHeading.hidden = true;
  const modelList = document.createElement("div");
  modelList.id = "view-models";
  modelList.className = "category-list";
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
  const mountingBlock = document.createElement("div");
  mountingBlock.id = "view-mounting-block";
  mountingBlock.hidden = true;
  const mountingHeading = document.createElement("h3");
  mountingHeading.textContent = "Mounting";
  const mountingToggle = document.createElement("label");
  const mountingInput = document.createElement("input");
  mountingInput.id = "view-mounting";
  mountingInput.type = "checkbox";
  mountingInput.checked = true;
  mountingInput.addEventListener("change", () => {
    const mounting = loadedFiles.find((file) => file.role === "mounting");
    const box = modelToggle(mounting && mounting.id);
    if (box) box.checked = mountingInput.checked;
    applyVisibility().catch((error) => status(error.message || "Could not filter the model."));
  });
  const mountingText = document.createElement("span");
  mountingText.textContent = "Show mounting elements";
  mountingToggle.append(mountingInput, mountingText);
  const statusHeading = document.createElement("h3");
  statusHeading.textContent = "Status";
  const tradeHeading = document.createElement("h3");
  tradeHeading.textContent = "Trade";
  mountingBlock.append(
    mountingHeading,
    mountingToggle,
    statusHeading,
    checkboxList("view-status", MOUNT_STATUSES),
    tradeHeading,
    checkboxList("view-trade", MOUNT_TRADES),
  );

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
    modelHeading,
    modelList,
    storeyLabel,
    categoryList,
    mountingBlock,
    colorHeading,
    colorField,
    colorRow,
    fade,
  );
  host.append(aside);
  mountProperties(host);
}

function mountProperties(host) {
  if (!host || document.querySelector("#view-properties")) return;
  const aside = document.createElement("aside");
  aside.id = "view-properties";
  aside.className = "view-properties";
  aside.hidden = true;
  aside.addEventListener("pointerdown", (event) => event.stopPropagation());
  const heading = document.createElement("h3");
  heading.textContent = "Properties";
  const empty = document.createElement("p");
  empty.id = "view-property-empty";
  empty.className = "hint";
  empty.textContent = "Click an element to read its properties. Shift-click adds another.";
  const body = document.createElement("div");
  body.id = "view-property-body";
  aside.append(heading, empty, body);
  host.append(aside);
}

function inOverlay(event) {
  return Boolean(event.target?.closest?.("#view-tools, #view-properties"));
}

function checkboxList(id, options) {
  const list = document.createElement("div");
  list.id = id;
  list.className = "category-list";
  for (const [value, label] of options) {
    const row = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = value;
    input.checked = true;
    input.addEventListener("change", () => {
      applyVisibility().catch((error) => status(error.message || "Could not filter the model."));
    });
    const text = document.createElement("span");
    text.textContent = label;
    row.append(input, text);
    list.append(row);
  }
  return list;
}

function modelById(id) {
  for (const model of fragments.list.values()) {
    if (model.modelId === id) return model;
  }
  return null;
}

function isMountingModel(model) {
  return loadedFiles.some((file) => file.role === "mounting" && file.id === model.modelId);
}

function modelToggle(modelId) {
  if (!modelId) return null;
  return [...document.querySelectorAll("#view-models input")].find((input) => input.dataset.modelId === modelId) || null;
}

function modelLabel(file) {
  const name = file.name.toLowerCase();
  if (file.role === "mounting" || name.includes("mounting")) return "Hangers";
  if (name.includes("architecture")) return "Architecture";
  if (name.includes("ventilation")) return "Ventilation";
  if (name.includes("heating") || name.includes("cooling")) return "Heating / cooling";
  if (name.includes("piping")) return "Piping";
  if (name.includes("mep")) return "MEP";
  const stem = file.name.replace(/\.ifc$/i, "").replace(/[-_]+/g, " ");
  return stem.charAt(0).toUpperCase() + stem.slice(1);
}

function modelLabels(files) {
  const labels = files.map(modelLabel);
  const counts = new Map();
  for (const label of labels) counts.set(label, (counts.get(label) || 0) + 1);
  return labels.map((label, index) => (counts.get(label) > 1 ? `${label} · ${files[index].name}` : label));
}

function allModelsShown() {
  const inputs = [...document.querySelectorAll("#view-models input")];
  return inputs.length === 0 || inputs.every((input) => input.checked);
}

function paintModelToggles() {
  const list = document.querySelector("#view-models");
  const heading = document.querySelector("#view-models-heading");
  if (!list) return;
  const labels = modelLabels(loadedFiles);
  list.replaceChildren(...loadedFiles.map((file, index) => {
    const row = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = true;
    input.dataset.modelId = file.id;
    input.addEventListener("change", () => {
      if (file.role === "mounting") {
        const master = document.querySelector("#view-mounting");
        if (master) master.checked = input.checked;
      }
      applyVisibility().catch((error) => status(error.message || "Could not filter the model."));
    });
    const text = document.createElement("span");
    text.textContent = labels[index];
    text.title = file.name;
    row.append(input, text);
    return row;
  }));
  const empty = loadedFiles.length === 0;
  list.hidden = empty;
  if (heading) heading.hidden = empty;
}

function checkedValues(selector) {
  return new Set(
    [...document.querySelectorAll(`${selector} input:checked`)]
      .filter((input) => !input.parentElement.hidden)
      .map((input) => input.value),
  );
}

function mountingFiltersOpen() {
  const block = document.querySelector("#view-mounting-block");
  if (!block || block.hidden) return true;
  const show = document.querySelector("#view-mounting");
  if (show && !show.checked) return false;
  const inputs = [...document.querySelectorAll("#view-status input, #view-trade input")]
    .filter((input) => !input.parentElement.hidden);
  return inputs.every((input) => input.checked);
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

async function showOnly(map) {
  // Hide and show in sequence. The engine's isolate() starts both at once,
  // and the hide can finish last, so a ticked model stays invisible.
  for (const model of fragments.list.values()) {
    const wanted = map[model.modelId] || new Set();
    const allIds = [...await model.getItemsIdsWithGeometry()];
    const hidden = [];
    const shown = [];
    for (const id of allIds) {
      if (wanted.has(id)) shown.push(id);
      else hidden.push(id);
    }
    if (hidden.length) await model.setVisible(hidden, false);
    if (shown.length) await model.setVisible(shown, true);
  }
  await fragments.core.update(true);
}

async function applyVisibility() {
  const ticked = new Set(tickedCategories());
  const allCategories = categories.length === 0 || ticked.size === categories.length;
  const storeyKey = document.querySelector("#view-storeys")?.value || "";
  if (allCategories && !storeyKey && mountingFiltersOpen() && allModelsShown()) {
    await hider.set(true);
    return;
  }
  const statusOn = checkedValues("#view-status");
  const tradeOn = checkedValues("#view-trade");
  const showMounting = document.querySelector("#view-mounting")?.checked !== false;
  const map = {};
  for (const model of fragments.list.values()) {
    const toggle = modelToggle(model.modelId);
    const mounting = isMountingModel(model);
    let ids;
    if ((toggle && !toggle.checked) || (mounting && !showMounting)) {
      ids = new Set();
    } else if (mounting || allCategories) {
      ids = new Set(await model.getItemsIdsWithGeometry());
    } else {
      ids = new Set(await idsForCategories(model, [...ticked]));
    }
    if (storeyKey && mounting && showMounting) {
      ids = new Set([...ids].filter((id) => {
        const meta = mountingMeta.get(`${model.modelId}:${id}`);
        return Boolean(meta?.storey) && meta.storey.trim().toLowerCase() === storeyKey;
      }));
    } else if (storeyKey) {
      const allowed = new Set();
      for (const storey of storeys) {
        if (storey.modelId === model.modelId && storey.nameKey === storeyKey) {
          for (const id of storey.ids) allowed.add(id);
        }
      }
      ids = new Set([...ids].filter((id) => allowed.has(id)));
    }
    if (mounting && showMounting) {
      ids = new Set([...ids].filter((id) => {
        const meta = mountingMeta.get(`${model.modelId}:${id}`);
        if (!meta) return true;
        return statusOn.has(meta.status) && tradeOn.has(meta.trade);
      }));
    }
    map[model.modelId] = ids;
  }
  await showOnly(map);
}

async function showEverything() {
  for (const input of document.querySelectorAll("#view-categories input, #view-mounting-block input, #view-models input")) {
    if (!input.parentElement.hidden) input.checked = true;
  }
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
    if (isMountingModel(model)) continue;
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

async function categoryStoreyNames(model) {
  try {
    const items = await model.getItemsOfCategories([/^IFCBUILDINGSTOREY$/i]);
    const ids = [...new Set(Object.values(items).flat().filter((id) => typeof id === "number"))];
    if (!ids.length) return [];
    const rows = await model.getItemsData(ids, {
      attributesDefault: false,
      attributes: ["Name", "LongName"],
    });
    return ids.map((id, index) => {
      const data = rowFor(rows, id, index);
      return readAttribute(data, "Name") || readAttribute(data, "LongName") || "";
    }).filter(Boolean);
  } catch {
    return [];
  }
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
    const names = await categoryStoreyNames(model);
    found.forEach((node, index) => {
      node.label = names[index] || "";
    });
    for (const node of found) {
      const ids = new Set();
      collectIds(node, ids);
      const name = node.label || node.name || node.Name || `Storey ${storeys.length + 1}`;
      storeys.push({
        key: `${model.modelId}:${node.localId}`,
        modelId: model.modelId,
        name,
        nameKey: name.trim().toLowerCase(),
        ids,
      });
    }
  }
}

async function refreshTools() {
  const tools = document.querySelector("#view-tools");
  const list = document.querySelector("#view-categories");
  const select = document.querySelector("#view-storeys");
  if (!tools || !list || !select) return;
  paintModelToggles();
  categories = [];
  const seen = new Set();
  for (const model of fragments.list.values()) {
    if (isMountingModel(model)) continue;
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
  const seenStoreys = new Set();
  const addStoreyOption = (name) => {
    const key = name.trim().toLowerCase();
    if (!key || seenStoreys.has(key)) return;
    seenStoreys.add(key);
    const option = document.createElement("option");
    option.value = key;
    option.textContent = name.trim();
    select.append(option);
  };
  for (const storey of storeys) addStoreyOption(storey.name);
  for (const meta of mountingMeta.values()) addStoreyOption(meta.storey || "");
  const mountingBlock = document.querySelector("#view-mounting-block");
  const hasMounting = loadedFiles.some((file) => file.role === "mounting");
  if (mountingBlock) mountingBlock.hidden = !hasMounting;
  for (const input of document.querySelectorAll("#view-mounting-block input")) input.checked = true;
  const other = document.querySelector('#view-trade input[value="unknown"]');
  if (other) {
    const trades = new Set([...mountingMeta.values()].map((item) => item.trade));
    other.parentElement.hidden = !trades.has("unknown");
  }
  select.hidden = storeys.length === 0;
  select.parentElement.hidden = storeys.length === 0;
  tools.hidden = false;
  const properties = document.querySelector("#view-properties");
  if (properties) properties.hidden = false;
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
  let pointer = null;
  container.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || inOverlay(event)) {
      pointer = null;
      return;
    }
    pointer = {
      x: event.clientX,
      y: event.clientY,
      id: event.pointerId,
      shift: event.shiftKey,
      toggle: event.ctrlKey || event.metaKey,
    };
  });
  container.addEventListener("pointerup", (event) => {
    if (!pointer || event.pointerId !== pointer.id) return;
    const start = pointer;
    pointer = null;
    if (inOverlay(event)) return;
    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;
    if (dx * dx + dy * dy > 25) return;
    const mode = start.shift ? "add" : start.toggle ? "toggle" : "replace";
    pickElement(mode, event.clientX, event.clientY).catch((error) => status(error.message || "Could not select that element."));
  });
  window.addEventListener("message", (event) => {
    if (event.origin !== window.location.origin) return;
    const data = event.data;
    if (!data || data.type !== "mep-focus-hangers" || !Array.isArray(data.ids)) return;
    focusHangers(data.ids).catch((error) => status(error.message || "Could not frame those hangers."));
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
  hangerByName = new Map();
  hangerByLocal = new Map();
  selection = {};
  propertyToken += 1;
  renderProperties([]);
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

function unwrapValue(value) {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  if (value && typeof value === "object") {
    if ("value" in value) return unwrapValue(value.value);
    if ("Value" in value) return unwrapValue(value.Value);
  }
  return "";
}

function psetMount(data) {
  const found = {};
  const seen = new WeakSet();
  const walk = (node, depth) => {
    if (!node || typeof node !== "object" || depth > 6 || seen.has(node)) return;
    seen.add(node);
    if (!Array.isArray(node)) {
      const name = readAttribute(node, "Name");
      if (name === "Status" || name === "Trade" || name === "Storey") {
        const value = unwrapValue(node.NominalValue ?? node.nominalValue);
        if (value) found[name] = value;
      }
    }
    const children = Array.isArray(node) ? node : Object.values(node);
    for (const child of children) {
      if (child && typeof child === "object") walk(child, depth + 1);
    }
  };
  walk(data, 0);
  return found;
}

function rowFor(rows, id, index) {
  if (Array.isArray(rows)) return rows[index] || {};
  if (rows && typeof rows === "object") return rows[id] || rows[String(id)] || {};
  return {};
}

async function indexMountings() {
  // Prefer Pset_DrillMount Status and Trade. ObjectType and Tag repeat those values.
  // Name is the hanger id, so the object list can frame the matching rod.
  mountingMeta = new Map();
  hangerByName = new Map();
  hangerByLocal = new Map();
  for (const file of loadedFiles) {
    if (file.role !== "mounting") continue;
    const model = modelById(file.id);
    if (!model) continue;
    const ids = [...await model.getItemsIdsWithGeometry()];
    if (!ids.length) continue;
    const attributes = { attributesDefault: false, attributes: ["ObjectType", "Tag", "Name", "Description"] };
    let rows = [];
    try {
      rows = await model.getItemsData(ids, {
        ...attributes,
        relations: { IsDefinedBy: { attributes: true, relations: true } },
      });
    } catch {
      try {
        rows = await model.getItemsData(ids, attributes);
      } catch {
        rows = [];
      }
    }
    ids.forEach((id, index) => {
      const data = rowFor(rows, id, index);
      const pset = psetMount(data);
      const name = readAttribute(data, "Name");
      if (name) {
        const hit = { modelId: model.modelId, localId: id, name };
        const list = hangerByName.get(name) || [];
        list.push(hit);
        hangerByName.set(name, list);
        hangerByLocal.set(`${model.modelId}:${id}`, name);
      }
      const status = pset.Status || readAttribute(data, "ObjectType");
      const trade = pset.Trade || readAttribute(data, "Tag");
      const storey = pset.Storey || readAttribute(data, "Description");
      if (!status && !trade) return;
      mountingMeta.set(`${model.modelId}:${id}`, { status, trade, storey });
    });
  }
}

function filesFromQuery() {
  if (document.body.dataset.page !== "viewer") return null;
  const params = new URLSearchParams(location.search);
  const files = [];
  const push = (id, role) => {
    if (id && !files.some((file) => file.id === id)) {
      files.push({ id, name: labelForId(id), role });
    }
  };
  push(params.get("id"), "service");
  for (const extra of params.getAll("clash")) push(extra, "clash");
  for (const extra of params.getAll("mounting")) push(extra, "mounting");
  return files;
}

function selectionCount(map) {
  let count = 0;
  for (const ids of Object.values(map)) count += ids.size;
  return count;
}

function cloneSelection(map) {
  const copy = {};
  for (const [modelId, ids] of Object.entries(map)) copy[modelId] = new Set(ids);
  return copy;
}

function hitFrom(result) {
  if (!result || typeof result.localId !== "number") return null;
  const only = fragments.list.size === 1 ? [...fragments.list.keys()][0] : "";
  const modelId = result.fragments?.modelId || result.modelId || only;
  if (!modelId) return null;
  return { modelId, localId: result.localId };
}

async function raycastHit(clientX, clientY) {
  const caster = components.get(OBC.Raycasters).get(world);
  try {
    const hit = hitFrom(await caster.castRay());
    if (hit) return hit;
  } catch {
    /* the GPU pick can miss a thin rod; the fragments raycast is the fallback */
  }
  const dom = world.renderer?.three?.domElement;
  if (!dom || typeof fragments.raycast !== "function") return null;
  try {
    return hitFrom(await fragments.raycast({
      camera: world.camera.three,
      mouse: new THREE.Vector2(clientX, clientY),
      dom,
    }));
  } catch {
    return null;
  }
}

function definitionList(rows) {
  const list = document.createElement("dl");
  for (const [label, value] of rows) {
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.textContent = value;
    list.append(term, detail);
  }
  return list;
}

function renderProperties(sections) {
  const body = document.querySelector("#view-property-body");
  const empty = document.querySelector("#view-property-empty");
  if (!body || !empty) return;
  if (!sections.length) {
    body.replaceChildren();
    empty.hidden = false;
    return;
  }
  empty.hidden = true;
  body.replaceChildren(...sections.map((section) => {
    const block = document.createElement("section");
    const title = document.createElement("h4");
    title.textContent = section.title || "Element";
    block.append(title);
    if (section.rows.length) block.append(definitionList(section.rows));
    for (const set of section.sets) {
      const heading = document.createElement("h5");
      heading.textContent = set.name;
      block.append(heading, definitionList(set.items));
    }
    return block;
  }));
}

const LEADING_ATTRIBUTES = ["GlobalId", "ObjectType", "Tag", "Description", "PredefinedType"];
const SKIP_ATTRIBUTES = new Set([
  "IsDefinedBy",
  "IsTypedBy",
  "HasAssociations",
  "ContainedInStructure",
  "Decomposes",
  "IsDecomposedBy",
  "HasAssignments",
  "HasPropertySets",
  "OwnerHistory",
  "ObjectPlacement",
  "Representation",
]);

function prettyKey(key) {
  if (key === "GlobalId") return "Global ID";
  if (key === "ObjectType") return "Object type";
  if (key === "PredefinedType") return "Predefined type";
  return key.replace(/_/g, " ");
}

function propertySets(data) {
  const sets = [];
  const seen = new WeakSet();
  const collect = (node, depth) => {
    if (!node || typeof node !== "object" || depth > 8 || seen.has(node)) return;
    seen.add(node);
    const props = node.HasProperties || node.hasProperties;
    const name = readAttribute(node, "Name");
    if (name && Array.isArray(props)) {
      const items = [];
      for (const prop of props) {
        if (!prop || typeof prop !== "object") continue;
        const label = readAttribute(prop, "Name");
        const value = unwrapValue(prop.NominalValue ?? prop.nominalValue ?? prop.EnumerationValues ?? prop.Value);
        if (label) items.push([label, value || "—"]);
      }
      if (items.length) sets.push({ name, items });
      return;
    }
    const children = Array.isArray(node) ? node : Object.values(node);
    for (const child of children) {
      if (child && typeof child === "object") collect(child, depth + 1);
    }
  };
  const branch = data?.IsDefinedBy || data?.isDefinedBy;
  if (branch) collect(branch, 0);
  return sets;
}

function describeItem(data) {
  const category = readAttribute(data, "_category") || readAttribute(data, "category");
  const name = readAttribute(data, "Name") || readAttribute(data, "LongName") || (category ? prettyCategory(category) : "Element");
  const rows = [];
  const used = new Set(["Name", "_category", "category"]);
  if (category) rows.push(["Category", prettyCategory(category)]);
  for (const key of LEADING_ATTRIBUTES) {
    const value = readAttribute(data, key);
    if (!value) continue;
    rows.push([prettyKey(key), value]);
    used.add(key);
  }
  const guid = readAttribute(data, "_guid");
  if (guid && !rows.some(([label]) => label === "Global ID")) rows.push(["Global ID", guid]);
  for (const [key, raw] of Object.entries(data || {})) {
    if (used.has(key) || key.startsWith("_") || SKIP_ATTRIBUTES.has(key)) continue;
    const value = unwrapValue(raw);
    if (!value) continue;
    rows.push([prettyKey(key), value]);
  }
  return { title: name, rows, sets: propertySets(data) };
}

async function showProperties(map) {
  const token = ++propertyToken;
  const sections = [];
  for (const [modelId, ids] of Object.entries(map)) {
    const model = modelById(modelId);
    const list = [...ids];
    if (!model || !list.length) continue;
    let rows = [];
    try {
      rows = await model.getItemsData(list, {
        attributesDefault: true,
        relations: { IsDefinedBy: { attributes: true, relations: true } },
      });
    } catch {
      try {
        rows = await model.getItemsData(list, { attributesDefault: true });
      } catch {
        rows = [];
      }
    }
    if (token !== propertyToken) return;
    list.forEach((id, index) => sections.push(describeItem(rowFor(rows, id, index))));
  }
  if (token !== propertyToken) return;
  renderProperties(sections);
}

function publishHangers(map) {
  const ids = [];
  for (const [modelId, localIds] of Object.entries(map)) {
    for (const localId of localIds) {
      const name = hangerByLocal.get(`${modelId}:${localId}`);
      if (!name) return;
      ids.push(name);
    }
  }
  if (!ids.length) return;
  window.dispatchEvent(new CustomEvent("mep-hanger-picked", { detail: { ids } }));
}

async function clearPick() {
  selection = {};
  propertyToken += 1;
  if (fragments) {
    await fragments.resetHighlight();
    fragments.core.update(true);
  }
  renderProperties([]);
}

function absorbBox(target, item, matrix) {
  if (!item || typeof item.clone !== "function" || typeof item.isEmpty !== "function" || item.isEmpty()) return false;
  const clone = item.clone();
  if (matrix && typeof clone.applyMatrix4 === "function") clone.applyMatrix4(matrix);
  target.union(clone);
  return true;
}

async function frameSelection(map) {
  const box = new THREE.Box3();
  for (const [modelId, ids] of Object.entries(map)) {
    const model = modelById(modelId);
    if (!model || !ids.size) continue;
    model.object?.updateMatrixWorld?.(true);
    const matrix = model.object?.matrixWorld;
    let boxes = [];
    try {
      const raw = await model.getBoxes([...ids]);
      boxes = Array.isArray(raw) ? raw : raw ? [raw] : [];
    } catch {
      boxes = [];
    }
    let absorbed = 0;
    for (const item of boxes) {
      if (absorbBox(box, item, matrix)) absorbed += 1;
    }
    if (absorbed) continue;
    try {
      const positions = await model.getPositions([...ids]);
      for (const point of positions) {
        if (!point) continue;
        const clone = typeof point.clone === "function" ? point.clone() : new THREE.Vector3(point.x, point.y, point.z);
        if (matrix && typeof clone.applyMatrix4 === "function") clone.applyMatrix4(matrix);
        box.expandByPoint(clone);
      }
    } catch {
      /* this element has no measurable geometry */
    }
  }
  if (box.isEmpty()) return false;
  const size = box.getSize(new THREE.Vector3());
  if (Math.max(size.x, size.y, size.z) < 0.8) box.expandByScalar(0.45);
  await world.camera.controls.fitToBox(box, true, {
    paddingTop: 0.35,
    paddingBottom: 0.35,
    paddingLeft: 0.35,
    paddingRight: 0.35,
  });
  for (const model of fragments.list.values()) model.useCamera(world.camera.three);
  fragments.core.update(true);
  return true;
}

async function commitSelection(map, { frame, fromPointer }) {
  selection = map;
  await fragments.resetHighlight();
  if (selectionCount(selection)) await fragments.highlight(SELECT_STYLE, selection);
  fragments.core.update(true);
  await showProperties(selection);
  const framed = frame ? await frameSelection(selection) : true;
  if (fromPointer) publishHangers(selection);
  return framed;
}

async function pickElement(mode, clientX, clientY) {
  if (!loadedFiles.length) return;
  const hit = await raycastHit(clientX, clientY);
  if (!hit) {
    if (mode === "replace") await clearPick();
    return;
  }
  const next = mode === "replace" ? {} : cloneSelection(selection);
  if (!next[hit.modelId]) next[hit.modelId] = new Set();
  if (mode === "toggle" && next[hit.modelId].has(hit.localId)) {
    next[hit.modelId].delete(hit.localId);
    if (!next[hit.modelId].size) delete next[hit.modelId];
  } else {
    next[hit.modelId].add(hit.localId);
  }
  if (!selectionCount(next)) {
    await clearPick();
    return;
  }
  await commitSelection(next, { frame: false, fromPointer: true });
}

async function revealHangers(wanted, token) {
  if (token !== focusToken) return;
  if (!wanted.length) {
    await clearPick();
    return;
  }
  const found = [];
  for (const id of wanted) {
    const hits = hangerByName.get(id) || [];
    if (hits.length) found.push(...hits);
  }
  if (token !== focusToken) return;
  if (!found.length) {
    status(wanted.length === 1 ? `${wanted[0]} is not in the open model.` : "Those hangers are not in the open model.");
    return;
  }
  const map = {};
  for (const hit of found) {
    if (!map[hit.modelId]) map[hit.modelId] = new Set();
    map[hit.modelId].add(hit.localId);
  }
  const framedView = await commitSelection(map, { frame: true, fromPointer: false });
  if (token !== focusToken) return;
  if (!framedView) {
    status("Those hangers have no geometry to frame.");
    return;
  }
  const framed = new Set(found.map((hit) => hit.name)).size;
  if (framed === wanted.length && framed === 1) status(`Framed ${wanted[0]}.`);
  else if (framed === wanted.length) status(`Framed ${framed} hangers.`);
  else status(`Framed ${framed} of ${wanted.length} hangers.`);
}

async function focusHangers(ids) {
  const wanted = [...new Set((ids || []).map((id) => String(id || "")).filter(Boolean))];
  pendingFocus = wanted;
  if (opening || !loadedFiles.length) return;
  const token = ++focusToken;
  pendingFocus = null;
  await revealHangers(wanted, token);
}

function tellOpenerReady() {
  if (!window.opener || window.opener === window) return;
  window.opener.postMessage({ type: "mep-viewer-ready" }, window.location.origin);
}

async function open(files) {
  const token = ++generation;
  focusToken += 1;
  opening = true;
  try {
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
    const properties = document.querySelector("#view-properties");
    if (properties) properties.hidden = true;
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
    loadedFiles = files;
    await indexMountings();
    if (token !== generation) return;
    await refreshTools();
    if (token !== generation) return;
    const extent = `${size.x.toFixed(1)} × ${size.y.toFixed(1)} × ${size.z.toFixed(1)} m`;
    const label = files.length === 1 ? names : `${files.length} models · ${names}`;
    status(`${label} · ${extent}`);
  } finally {
    if (token === generation) opening = false;
  }
  if (token !== generation) return;
  if (pendingFocus) {
    const wanted = pendingFocus;
    pendingFocus = null;
    await revealHangers(wanted, ++focusToken);
  }
  if (token === generation) tellOpenerReady();
}

window.MepViewer = { open, focusHangers };

const requested = filesFromQuery();
if (requested) {
  if (!requested.length) {
    status("No model was selected.");
  } else {
    open(requested).catch((error) => status(error.message || "Could not open the model."));
  }
}
