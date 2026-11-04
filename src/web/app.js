const REASONS = {
  regular_70: "Even 70%",
  respaced_90_95: "Respaced to 90–95%",
  shifted_into_90_95: "Moved into 90–95%",
  shifted_under_95: "Moved under 95%",
  unresolved_clash: "Unresolved clash",
  user_moved: "Moved by hand",
};

const state = {
  files: [],
  selectedId: null,
  clashIds: new Set(),
  points: [],
  shown: 25,
  mountingPoints: [],
  runs: [],
  mountingShown: 25,
  mountingFilter: "adjusted",
  selectedHangerId: null,
  selectedHangerIds: [],
  anchorHangerId: null,
  history: [],
  future: [],
  busy: false,
};

const samplesEl = document.querySelector("#samples");
const uploadsEl = document.querySelector("#uploads");
const samplesStatus = document.querySelector("#samples-status");
const banner = document.querySelector("#banner");
const selectedTitle = document.querySelector("#selected-title");
const selectedMeta = document.querySelector("#selected-meta");
const viewBtn = document.querySelector("#view");
const viewWindowBtn = document.querySelector("#view-window");
const extractBtn = document.querySelector("#extract");
const placeBtn = document.querySelector("#place");
const drawingsBtn = document.querySelector("#drawings");
const resultsEl = document.querySelector("#results");
const mountingEl = document.querySelector("#mounting");
const mountingMeta = document.querySelector("#mounting-meta");
const mountingNote = document.querySelector("#mounting-note");
const mountingFilters = document.querySelector("#mounting-filters");
const mountingRows = document.querySelector("#mounting-rows");
const showAllMountingBtn = document.querySelector("#show-all-mounting");
const undoBtn = document.querySelector("#undo");
const redoBtn = document.querySelector("#redo");
const editStatus = document.querySelector("#edit-status");
const hangerObjects = document.querySelector("#hanger-objects");
const hangerEditor = document.querySelector("#hanger-editor");
const hangerEditorEmpty = document.querySelector("#hanger-editor-empty");
const hangerEditorTitle = document.querySelector("#hanger-editor-title");
const hangerEditorMeta = document.querySelector("#hanger-editor-meta");
const hangerStation = document.querySelector("#hanger-station");
const hangerX = document.querySelector("#hanger-x");
const hangerY = document.querySelector("#hanger-y");
const hangerZ = document.querySelector("#hanger-z");
const hangerApply = document.querySelector("#hanger-apply");
const hangerDelete = document.querySelector("#hanger-delete");
const resultsMeta = document.querySelector("#results-meta");
const typesEl = document.querySelector("#types");
const rowsEl = document.querySelector("#rows");
const showAllBtn = document.querySelector("#show-all");
const drop = document.querySelector("#drop");
const fileInput = document.querySelector("#file-input");
let viewerWindow = null;

function selectedFile() {
  return state.files.find((file) => file.id === state.selectedId) || null;
}

function showBanner(message) {
  banner.hidden = !message;
  banner.textContent = message || "";
}

function fileCard(file) {
  const card = document.createElement("div");
  card.className = "file";
  const pick = document.createElement("label");
  pick.className = "file-pick";
  const input = document.createElement("input");
  input.type = "radio";
  input.name = "ifc";
  input.value = file.id;
  input.checked = file.id === state.selectedId;
  input.addEventListener("change", () => select(file.id));

  const body = document.createElement("span");
  const title = document.createElement("span");
  title.className = "file-title";
  title.textContent = file.title;
  const name = document.createElement("span");
  name.className = "file-name";
  name.textContent = file.name;
  const meta = document.createElement("span");
  meta.className = "file-meta";
  const bits = [file.size, file.schema, file.detail].filter(Boolean);
  meta.textContent = bits.join(" · ");
  body.append(title, name, meta);
  pick.append(input, body);

  const clash = document.createElement("label");
  clash.className = "clash-pick";
  const box = document.createElement("input");
  box.type = "checkbox";
  const always = file.id === state.selectedId;
  box.checked = always || state.clashIds.has(file.id);
  box.disabled = always;
  box.setAttribute(
    "aria-label",
    always
      ? `${file.name} is included in the clash check`
      : `Include ${file.name} in the clash check`,
  );
  box.addEventListener("change", () => {
    if (box.checked) state.clashIds.add(file.id);
    else state.clashIds.delete(file.id);
    mountingEl.hidden = true;
    renderSelection();
  });
  const clashText = document.createElement("span");
  clashText.textContent = "For clashes";
  clash.title = always
    ? "This model is included in the clash check."
    : "Include this model’s services and beams in the clash check. Its runs are not hung.";
  clash.append(box, clashText);
  card.append(pick, clash);
  return card;
}

function renderFiles() {
  const samples = state.files.filter((file) => file.origin === "sample");
  const uploads = state.files.filter((file) => file.origin === "upload");
  samplesEl.replaceChildren(...samples.map(fileCard));
  uploadsEl.replaceChildren(...uploads.map(fileCard));
  samplesStatus.textContent = samples.length
    ? `${samples.length} in examples/`
    : "No sample IFCs in examples/";
  renderSelection();
}

function clashFiles() {
  return state.files.filter((file) => state.clashIds.has(file.id) && file.id !== state.selectedId);
}

function filesForViewer(file) {
  const files = [{ id: file.id, name: file.name, role: "service" }];
  for (const extra of clashFiles()) {
    files.push({ id: extra.id, name: extra.name, role: "clash" });
  }
  if (file.mounting_id) {
    const name = `${file.name.replace(/\.ifc$/i, "")}-mountings.ifc`;
    files.push({ id: file.mounting_id, name, role: "mounting" });
  }
  return files;
}

function renderSelection() {
  const file = selectedFile();
  viewBtn.disabled = !file || state.busy;
  viewWindowBtn.disabled = !file || state.busy;
  extractBtn.disabled = !file || state.busy;
  placeBtn.disabled = !file || state.busy;
  drawingsBtn.disabled = !file || state.busy;
  if (!file) {
    selectedTitle.textContent = "No model yet";
    selectedMeta.textContent = "Choose a sample or open a file. Extraction runs on the model shown here.";
    return;
  }
  selectedTitle.textContent = file.title;
  const extras = clashFiles();
  const bits = [file.name, file.size, file.schema].filter(Boolean);
  if (extras.length) {
    bits.push(`clashes also ${extras.map((item) => item.name).join(", ")}`);
  }
  selectedMeta.textContent = bits.join(" · ");
}

function select(id) {
  state.selectedId = id;
  state.clashIds.delete(id);
  resultsEl.hidden = true;
  mountingEl.hidden = true;
  renderFiles();
}

function reasonLabel(reason) {
  return REASONS[reason] || reason;
}

function reasonClass(point) {
  if (point.reason === "unresolved_clash" || point.clear === false) return "clash";
  if (point.reason === "user_moved" || String(point.reason).startsWith("shifted_")) return "shifted";
  if (point.reason === "respaced_90_95") return "respaced";
  return "regular";
}

function reasonRank(point) {
  const kind = reasonClass(point);
  if (kind === "clash") return 0;
  if (kind === "shifted") return 1;
  if (kind === "respaced") return 2;
  return 3;
}

function metres(value) {
  if (value === null || value === undefined || value === "") return "";
  return Number(value).toFixed(3);
}

function gapLabel(point) {
  if (point.spacing_ratio === null || point.spacing_ratio === undefined) return "";
  return `${Math.round(point.spacing_ratio * 100)}%`;
}

async function loadFiles() {
  const response = await fetch("/api/files");
  if (!response.ok) throw new Error("Could not list IFC files");
  const data = await response.json();
  state.files = data.files;
  if (!data.ifcopenshell) {
    showBanner("ifcopenshell is not installed for this Python. You can still choose a file; extraction needs: pip install -r requirements.txt");
  }
  renderFiles();
}

function renderResults(data) {
  state.points = data.points || [];
  state.shown = 25;
  resultsEl.hidden = false;
  const count = data.count ?? state.points.length;
  resultsMeta.textContent = `${count} points saved to ${data.out}`;

  const counts = new Map();
  for (const point of state.points) {
    counts.set(point.element_type, (counts.get(point.element_type) || 0) + 1);
  }
  typesEl.replaceChildren(
    ...[...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([type, n]) => {
        const chip = document.createElement("span");
        chip.className = "chip";
        chip.textContent = `${type} ${n}`;
        return chip;
      }),
  );
  paintRows();
  resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
}

function paintRows() {
  const slice = state.points.slice(0, state.shown);
  rowsEl.replaceChildren(
    ...slice.map((point) => {
      const row = document.createElement("tr");
      for (const [value, numeric] of [
        [point.id, false],
        [point.element_type, false],
        [point.x, true],
        [point.y, true],
        [point.z, true],
      ]) {
        const cell = document.createElement("td");
        if (numeric) cell.className = "num";
        cell.textContent = value;
        row.append(cell);
      }
      return row;
    }),
  );
  const more = state.points.length > state.shown;
  showAllBtn.hidden = !more;
  showAllBtn.textContent = `Show all ${state.points.length} points`;
}

async function extract() {
  const file = selectedFile();
  if (!file || state.busy) return;
  state.busy = true;
  extractBtn.textContent = "Extracting…";
  renderSelection();
  showBanner("");
  try {
    const response = await fetch("/api/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: file.id }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Extraction failed");
    renderResults(data);
  } catch (error) {
    showBanner(error.message);
  } finally {
    state.busy = false;
    extractBtn.textContent = "Extract anchor points";
    renderSelection();
  }
}

async function uploadMany(list) {
  const incoming = [...list];
  if (!incoming.length) return;
  const accepted = incoming.filter((file) => file.name.toLowerCase().endsWith(".ifc"));
  if (!accepted.length) {
    showBanner("Choose a file that ends in .ifc.");
    return;
  }
  if (accepted.length < incoming.length) {
    showBanner("Skipped a file that does not end in .ifc.");
  } else {
    showBanner("");
  }
  viewBtn.disabled = true;
  viewWindowBtn.disabled = true;
  extractBtn.disabled = true;
  placeBtn.disabled = true;
  drawingsBtn.disabled = true;
  const uploaded = [];
  try {
    for (const file of accepted) {
      samplesStatus.textContent = `Opening ${file.name}…`;
      const response = await fetch("/api/uploads", {
        method: "POST",
        headers: { "X-Filename": file.name },
        body: file,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Upload failed");
      uploaded.push(data.file);
      state.files = [data.file, ...state.files.filter((item) => item.id !== data.file.id)];
    }
    state.selectedId = uploaded[0].id;
    state.clashIds.delete(uploaded[0].id);
    for (const file of uploaded.slice(1)) state.clashIds.add(file.id);
    resultsEl.hidden = true;
    mountingEl.hidden = true;
    renderFiles();
  } catch (error) {
    showBanner(error.message);
    renderFiles();
  }
}

document.querySelector("#browse").addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
  const files = fileInput.files ? [...fileInput.files] : [];
  fileInput.value = "";
  uploadMany(files);
});

drop.addEventListener("dragover", (event) => {
  event.preventDefault();
  drop.classList.add("hot");
});
drop.addEventListener("dragleave", () => drop.classList.remove("hot"));
drop.addEventListener("drop", (event) => {
  event.preventDefault();
  drop.classList.remove("hot");
  uploadMany(event.dataTransfer.files || []);
});

function filteredMountingPoints() {
  const points = state.mountingPoints;
  if (state.mountingFilter === "adjusted") {
    return points.filter((point) => point.reason !== "regular_70");
  }
  if (state.mountingFilter === "clash") {
    return points.filter((point) => reasonClass(point) === "clash");
  }
  return points;
}

function renderMounting(data) {
  state.history = [];
  state.future = [];
  state.selectedHangerId = null;
  state.selectedHangerIds = [];
  state.anchorHangerId = null;
  state.mountingShown = 25;
  const points = data.points || [];
  const adjusted = data.adjusted_count ?? points.filter((point) => point.reason !== "regular_70").length;
  state.mountingFilter = adjusted > 0 ? "adjusted" : "all";
  adoptPlan(data);
  if (editStatus) editStatus.textContent = "";
  mountingEl.scrollIntoView({ behavior: "smooth", block: "start" });
}

function adoptPlan(data) {
  const points = (data.points || []).slice().sort((a, b) => reasonRank(a) - reasonRank(b) || a.id.localeCompare(b.id));
  state.mountingPoints = points;
  if (data.runs) state.runs = data.runs;
  if (useSelectionOverride) {
    state.selectedHangerId = selectionOverride;
    state.selectedHangerIds = selectionOverride ? [selectionOverride] : [];
    state.anchorHangerId = selectionOverride;
    useSelectionOverride = false;
  }
  state.selectedHangerIds = state.selectedHangerIds.filter((id) => points.some((point) => point.id === id));
  if (state.selectedHangerId && !points.some((point) => point.id === state.selectedHangerId)) {
    state.selectedHangerId = state.selectedHangerIds[0] || null;
  }
  mountingEl.hidden = false;
  const count = data.count ?? points.length;
  const adjusted = data.adjusted_count ?? points.filter((point) => point.reason !== "regular_70").length;
  const clashes = data.clash_count ?? points.filter((point) => point.clear === false).length;
  const models = data.clash_models || [];
  const also = models.length > 1 ? ` · also ${models.slice(1).join(", ")}` : "";
  const ifc = data.mounting_out ? ` · ${data.mounting_out}` : "";
  mountingMeta.textContent = `${count} hangers on ${data.run_count ?? (data.runs || state.runs).length} runs · ${adjusted} adjusted · ${clashes} still clashing${also} · ${data.out}${ifc}`;
  const file = selectedFile();
  if (file) file.mounting_id = data.mounting_ifc || null;
  paintMountingFilters(data.reason_counts || {});
  paintMountingRows();
  paintObjects();
  paintEditor();
  paintHistory();
}

function paintMountingFilters(counts) {
  const adjusted = state.mountingPoints.filter((point) => point.reason !== "regular_70").length;
  const clashes = state.mountingPoints.filter((point) => reasonClass(point) === "clash").length;
  const choices = [
    ["adjusted", `Adjusted ${adjusted}`],
    ["clash", `Still clashing ${clashes}`],
    ["all", `All ${state.mountingPoints.length}`],
  ];
  mountingFilters.replaceChildren(
    ...choices.map(([id, label]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `chip filter${state.mountingFilter === id ? " on" : ""}`;
      button.textContent = label;
      button.addEventListener("click", () => {
        state.mountingFilter = id;
        state.mountingShown = 25;
        paintMountingFilters(counts);
        paintMountingRows();
      });
      return button;
    }),
  );
  const listed = Object.entries(counts)
    .filter(([, count]) => count > 0)
    .map(([reason, count]) => `${reasonLabel(reason)} ${count}`);
  mountingNote.textContent = listed.length
    ? listed.join(" · ")
    : "No hanger was placed. The runs have no cited spacing, or none are horizontal.";
}

function paintMountingRows() {
  const visible = filteredMountingPoints();
  const slice = visible.slice(0, state.mountingShown);
  mountingRows.replaceChildren(
    ...slice.map((point) => {
      const row = document.createElement("tr");
      row.className = `hanger-row ${reasonClass(point)}${hangerIsOn(point.id) ? " on" : ""}`;
      row.dataset.hangerId = point.id;
      row.addEventListener("click", (event) => {
        const ordered = [...mountingRows.querySelectorAll("[data-hanger-id]")].map((item) => item.dataset.hangerId);
        selectHanger(point.id, event, ordered);
      });
      const reason = document.createElement("td");
      const badge = document.createElement("span");
      badge.className = `badge ${reasonClass(point)}`;
      badge.textContent = reasonLabel(point.reason);
      badge.title = point.clear === false && point.clashing_element_ids && point.clashing_element_ids.length
        ? `Rod hits ${point.clashing_element_ids.join(", ")}`
        : point.reason;
      reason.append(badge);
      const cells = [
        [point.id, false],
        [point.run_id, false],
      ];
      for (const [value, numeric] of cells) {
        const cell = document.createElement("td");
        if (numeric) cell.className = "num";
        cell.textContent = value;
        row.append(cell);
      }
      row.append(reason);
      for (const value of [metres(point.station_m), gapLabel(point), metres(point.x), metres(point.y), metres(point.z)]) {
        const cell = document.createElement("td");
        cell.className = "num";
        cell.textContent = value;
        row.append(cell);
      }
      return row;
    }),
  );
  if (!slice.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 8;
    cell.className = "empty";
    cell.textContent = state.mountingFilter === "adjusted"
      ? "No hanger was adjusted. Every placed station kept the even 70% pitch."
      : "No hanger is in this group.";
    row.append(cell);
    mountingRows.append(row);
  }
  const more = visible.length > state.mountingShown;
  showAllMountingBtn.hidden = !more;
  showAllMountingBtn.textContent = `Show all ${visible.length} mounting points`;
}

async function placeMountingPoints() {
  const file = selectedFile();
  if (!file || state.busy) return;
  state.busy = true;
  placeBtn.textContent = "Placing…";
  renderSelection();
  showBanner("");
  try {
    const response = await fetch("/api/mounting-points", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id: file.id,
        obstacle_ids: clashFiles().map((item) => item.id),
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Placement failed");
    renderMounting(data);
  } catch (error) {
    showBanner(error.message);
  } finally {
    state.busy = false;
    placeBtn.textContent = "Place mounting points";
    renderSelection();
  }
}

async function downloadDrawings() {
  const file = selectedFile();
  if (!file || state.busy) return;
  state.busy = true;
  drawingsBtn.textContent = "Drawing…";
  renderSelection();
  showBanner("");
  try {
    const response = await fetch("/api/drawings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id: file.id,
        obstacle_ids: clashFiles().map((item) => item.id),
      }),
    });
    const type = response.headers.get("Content-Type") || "";
    if (!response.ok || !type.includes("pdf")) {
      const data = await response.json();
      throw new Error(data.error || "Could not draw the PDF");
    }
    const blob = await response.blob();
    const saved = response.headers.get("X-Saved-To");
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = file.name.replace(/\.ifc$/i, "") + "-views.pdf";
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    showBanner(saved ? `Saved ${saved}` : "Clash drawings downloaded.");
  } catch (error) {
    showBanner(error.message);
  } finally {
    state.busy = false;
    drawingsBtn.textContent = "Clash drawings PDF";
    renderSelection();
  }
}

async function viewModel() {
  const file = selectedFile();
  if (!file || state.busy) return;
  if (!window.MepViewer) {
    showBanner("The 3D viewer did not start. It downloads That Open Engine on first use, so reload once the network is available.");
    return;
  }
  state.busy = true;
  viewBtn.textContent = "Opening…";
  renderSelection();
  showBanner("");
  try {
    await window.MepViewer.open(filesForViewer(file));
    if (state.selectedHangerIds.length) focusViewerOnHangers(state.selectedHangerIds);
  } catch (error) {
    showBanner(error.message);
    const node = document.querySelector("#viewer-status");
    if (node) node.textContent = error.message;
  } finally {
    state.busy = false;
    viewBtn.textContent = "View in 3D";
    renderSelection();
  }
}

function viewerWindowUrl(file) {
  const params = new URLSearchParams();
  params.set("id", file.id);
  for (const extra of clashFiles()) params.append("clash", extra.id);
  if (file.mounting_id) params.append("mounting", file.mounting_id);
  return `/viewer?${params}`;
}

function openViewerWindow() {
  const file = selectedFile();
  if (!file || state.busy) return;
  viewerWindow = window.open(viewerWindowUrl(file), "mep-ifc-viewer", "popup,width=1280,height=800");
  if (!viewerWindow) {
    showBanner("The browser blocked the viewer window. Allow pop-ups for this site, or use View in 3D.");
  }
}

viewBtn.addEventListener("click", viewModel);
viewWindowBtn.addEventListener("click", openViewerWindow);
extractBtn.addEventListener("click", extract);
placeBtn.addEventListener("click", placeMountingPoints);
drawingsBtn.addEventListener("click", downloadDrawings);
showAllMountingBtn.addEventListener("click", () => {
  state.mountingShown = filteredMountingPoints().length;
  paintMountingRows();
});
showAllBtn.addEventListener("click", () => {
  state.shown = state.points.length;
  paintRows();
});

function clonePoints(points) {
  return JSON.parse(JSON.stringify(points));
}

function runsById() {
  return new Map(state.runs.map((run) => [run.id, run]));
}

function selectedHanger() {
  return state.mountingPoints.find((point) => point.id === state.selectedHangerId) || null;
}

function listedRuns() {
  const known = new Map(state.runs.map((run) => [run.id, run]));
  const ids = new Set(state.mountingPoints.map((point) => point.run_id));
  for (const run of state.runs) {
    if (run.status === "no_hangers") ids.add(run.id);
  }
  return [...ids]
    .sort((a, b) => String(a).localeCompare(String(b)))
    .map((id) => known.get(id) || { id });
}

function nearNumber(left, right) {
  return Math.abs(Number(left) - Number(right)) <= 0.00051;
}

function paintHistory() {
  if (!undoBtn || !redoBtn) return;
  undoBtn.disabled = state.busy || state.history.length === 0;
  redoBtn.disabled = state.busy || state.future.length === 0;
}

function paintObjects() {
  if (!hangerObjects) return;
  const hadFocus = document.activeElement === hangerObjects;
  const runs = runsById();
  const groups = listedRuns().map((run) => {
    const group = document.createElement("div");
    const header = document.createElement("div");
    header.className = "object-run";
    const hangers = state.mountingPoints
      .filter((point) => point.run_id === run.id)
      .slice()
      .sort((a, b) => a.station_m - b.station_m || a.id.localeCompare(b.id));
    const stored = runs.get(run.id) || run;
    const kind = stored.kind || stored.size_label || "run";
    const length = stored.length_m === undefined ? "" : `${Number(stored.length_m).toFixed(3)} m`;
    header.textContent = [run.id, kind, length, `${hangers.length} hangers`].filter(Boolean).join(" · ");
    group.append(header);
    for (const point of hangers) {
      const line = document.createElement("button");
      line.type = "button";
      line.className = `object-line${hangerIsOn(point.id) ? " on" : ""}`;
      line.dataset.hangerId = point.id;
      line.setAttribute("role", "option");
      line.setAttribute("aria-selected", hangerIsOn(point.id) ? "true" : "false");
      const ident = document.createElement("span");
      ident.textContent = point.id;
      const badge = document.createElement("span");
      badge.className = `badge ${reasonClass(point)}`;
      badge.textContent = reasonLabel(point.reason);
      const where = document.createElement("span");
      where.className = "where";
      where.textContent = `${metres(point.station_m)} m`;
      line.append(ident, badge, where);
      line.addEventListener("click", (event) => selectHanger(point.id, event));
      group.append(line);
    }
    return group;
  });
  hangerObjects.replaceChildren(...groups);
  if (!groups.length) {
    const empty = document.createElement("p");
    empty.className = "hint hanger-editor-empty";
    empty.textContent = "No hanger was placed.";
    hangerObjects.append(empty);
  }
  if (hadFocus) hangerObjects.focus();
}

let useSelectionOverride = false;
let selectionOverride = null;

function paintEditor() {
  const point = selectedHanger();
  if (hangerEditor) hangerEditor.hidden = !point;
  if (hangerEditorEmpty) hangerEditorEmpty.hidden = Boolean(point);
  if (!point) {
    paintHistory();
    return;
  }
  const locked = state.busy;
  if (!locked) {
    const run = runsById().get(point.run_id);
    const bits = [point.run_id, reasonLabel(point.reason)];
    if (run && run.size_label) bits.push(run.size_label);
    if (state.selectedHangerIds.length > 1) bits.push(`framing ${state.selectedHangerIds.length}`);
    hangerEditorTitle.textContent = point.id;
    hangerEditorMeta.textContent = point.clear === false
      ? `${bits.join(" · ")}. The rod was clashing. A move does not run the clash check again.`
      : bits.join(" · ");
    hangerStation.value = metres(point.station_m);
    hangerStation.max = run && run.length_m !== undefined ? String(run.length_m) : "";
    hangerX.value = metres(point.x);
    hangerY.value = metres(point.y);
    hangerZ.value = metres(point.z);
  }
  hangerStation.disabled = locked;
  hangerX.disabled = locked;
  hangerY.disabled = locked;
  hangerZ.disabled = locked;
  hangerApply.disabled = locked;
  hangerDelete.disabled = locked;
  paintHistory();
}

function hangerIsOn(id) {
  return state.selectedHangerIds.includes(id);
}

function selectHanger(id, event, orderedIds) {
  const ordered = orderedIds?.length ? orderedIds : objectIds();
  const toggle = Boolean(event && (event.ctrlKey || event.metaKey) && !event.shiftKey);
  const extend = Boolean(event?.shiftKey && state.anchorHangerId && ordered.includes(id) && ordered.includes(state.anchorHangerId));
  if (extend) {
    const start = ordered.indexOf(state.anchorHangerId);
    const end = ordered.indexOf(id);
    const [from, to] = start < end ? [start, end] : [end, start];
    state.selectedHangerIds = ordered.slice(from, to + 1);
    state.selectedHangerId = id;
  } else if (toggle) {
    const chosen = new Set(state.selectedHangerIds);
    if (chosen.has(id)) chosen.delete(id);
    else chosen.add(id);
    state.selectedHangerIds = [...chosen];
    state.selectedHangerId = chosen.has(id) ? id : (state.selectedHangerIds.at(-1) || null);
  } else {
    state.selectedHangerIds = [id];
    state.selectedHangerId = id;
    state.anchorHangerId = id;
  }
  paintObjects();
  paintMountingRows();
  paintEditor();
  const current = state.selectedHangerId;
  const line = current ? hangerObjects?.querySelector(`[data-hanger-id="${CSS.escape(current)}"]`) : null;
  if (line) line.scrollIntoView({ block: "nearest" });
  hangerObjects?.focus();
  focusViewerOnHangers(state.selectedHangerIds);
}

function focusViewerOnHangers(ids) {
  const list = [...ids];
  if (window.MepViewer?.focusHangers) {
    window.MepViewer.focusHangers(list).catch((error) => {
      const node = document.querySelector("#viewer-status");
      if (node) node.textContent = error.message || "Could not frame those hangers.";
    });
  }
  if (viewerWindow && !viewerWindow.closed) {
    viewerWindow.postMessage({ type: "mep-focus-hangers", ids: list }, window.location.origin);
  }
}

function applyViewerHangerPick(ids) {
  const known = ids.filter((id) => state.mountingPoints.some((point) => point.id === id));
  if (!known.length || mountingEl.hidden) return;
  state.selectedHangerIds = known;
  state.selectedHangerId = known[known.length - 1];
  state.anchorHangerId = state.selectedHangerId;
  paintObjects();
  paintMountingRows();
  paintEditor();
  const line = hangerObjects?.querySelector(`[data-hanger-id="${CSS.escape(state.selectedHangerId)}"]`);
  if (line) line.scrollIntoView({ block: "nearest" });
}

function objectIds() {
  return [...hangerObjects.querySelectorAll(".object-line")].map((line) => line.dataset.hangerId);
}

function neighborAfterDelete(id) {
  const point = state.mountingPoints.find((item) => item.id === id);
  if (!point) return null;
  const siblings = state.mountingPoints
    .filter((item) => item.run_id === point.run_id)
    .slice()
    .sort((a, b) => a.station_m - b.station_m || a.id.localeCompare(b.id));
  const index = siblings.findIndex((item) => item.id === id);
  const next = siblings[index + 1] || siblings[index - 1];
  return next ? next.id : null;
}

async function sendEdit(operation, mode) {
  const file = selectedFile();
  if (!file || state.busy || mountingEl.hidden) {
    useSelectionOverride = false;
    return false;
  }
  const past = clonePoints(state.mountingPoints);
  state.busy = true;
  renderSelection();
  paintHistory();
  paintEditor();
  if (editStatus) editStatus.textContent = "Saving…";
  showBanner("");
  try {
    const response = await fetch("/api/mounting-edits", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: file.id, ...operation }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not edit the hanger");
    if (mode === "undo") {
      state.history.pop();
      state.future.push(past);
    } else if (mode === "redo") {
      state.future.pop();
      state.history.push(past);
    } else {
      state.history.push(past);
      if (state.history.length > 50) state.history.shift();
      state.future = [];
    }
    adoptPlan(data);
    if (editStatus) {
      editStatus.textContent = data.mounting_out
        ? "Saved. View in 3D loads the updated rods."
        : "Saved.";
    }
    return true;
  } catch (error) {
    useSelectionOverride = false;
    if (editStatus) editStatus.textContent = "";
    showBanner(error.message);
    paintEditor();
    return false;
  } finally {
    state.busy = false;
    renderSelection();
    paintHistory();
    paintEditor();
  }
}

function commitEditor() {
  const point = selectedHanger();
  if (!point || state.busy) return;
  const station = Number(hangerStation.value);
  const x = Number(hangerX.value);
  const y = Number(hangerY.value);
  const z = Number(hangerZ.value);
  if ([station, x, y, z].some((value) => Number.isNaN(value))) {
    showBanner("Station, X, Y and Z need numbers.");
    return;
  }
  const stationChanged = !nearNumber(station, point.station_m);
  const positionChanged = !nearNumber(x, point.x) || !nearNumber(y, point.y) || !nearNumber(z, point.z);
  if (!stationChanged && !positionChanged) return;
  const operation = stationChanged
    ? { op: "move", hanger_id: point.id, station_m: station }
    : { op: "move", hanger_id: point.id, x, y, z };
  sendEdit(operation, "edit");
}

function deleteSelected() {
  const point = selectedHanger();
  if (!point || state.busy) return;
  selectionOverride = neighborAfterDelete(point.id);
  useSelectionOverride = true;
  sendEdit({ op: "delete", hanger_id: point.id }, "edit");
}

function undoEdit() {
  if (state.busy || !state.history.length || mountingEl.hidden) return;
  const previous = state.history[state.history.length - 1];
  sendEdit({ op: "replace", points: previous }, "undo");
}

function redoEdit() {
  if (state.busy || !state.future.length || mountingEl.hidden) return;
  const next = state.future[state.future.length - 1];
  sendEdit({ op: "replace", points: next }, "redo");
}

if (hangerEditor) {
  hangerEditor.addEventListener("submit", (event) => {
    event.preventDefault();
    commitEditor();
  });
}
hangerDelete?.addEventListener("click", deleteSelected);
undoBtn?.addEventListener("click", undoEdit);
redoBtn?.addEventListener("click", redoEdit);

window.addEventListener("message", (event) => {
  if (event.origin !== window.location.origin) return;
  if (event.data?.type !== "mep-viewer-ready") return;
  if (!state.selectedHangerIds.length) return;
  event.source?.postMessage(
    { type: "mep-focus-hangers", ids: state.selectedHangerIds },
    window.location.origin,
  );
});

window.addEventListener("mep-hanger-picked", (event) => {
  applyViewerHangerPick(event.detail?.ids || []);
});

hangerObjects?.addEventListener("keydown", (event) => {
  const ids = objectIds();
  if (!ids.length) return;
  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    const current = ids.indexOf(state.selectedHangerId);
    const step = event.key === "ArrowDown" ? 1 : -1;
    const nextIndex = current < 0 ? 0 : Math.min(ids.length - 1, Math.max(0, current + step));
    selectHanger(ids[nextIndex]);
  }
  if (event.key === "Delete" || event.key === "Backspace") {
    event.preventDefault();
    deleteSelected();
  }
});

document.addEventListener("keydown", (event) => {
  if (!(event.ctrlKey || event.metaKey) || event.altKey || mountingEl.hidden) return;
  const tag = document.activeElement && document.activeElement.tagName;
  const inHangerField = hangerEditor && hangerEditor.contains(document.activeElement);
  if ((tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") && !inHangerField) return;
  if (inHangerField && selectedHanger()) {
    const point = selectedHanger();
    const dirty = !nearNumber(hangerStation.value, point.station_m)
      || !nearNumber(hangerX.value, point.x)
      || !nearNumber(hangerY.value, point.y)
      || !nearNumber(hangerZ.value, point.z);
    if (dirty) return;
  }
  const key = event.key.toLowerCase();
  if (key === "z" && !event.shiftKey) {
    event.preventDefault();
    undoEdit();
  } else if (key === "y" || (key === "z" && event.shiftKey)) {
    event.preventDefault();
    redoEdit();
  }
});

loadFiles().catch((error) => {
  samplesStatus.textContent = "Could not load files";
  showBanner(error.message);
});
