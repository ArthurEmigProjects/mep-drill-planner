const REASONS = {
  regular_70: "Even 70%",
  respaced_90_95: "Respaced to 90–95%",
  shifted_into_90_95: "Moved into 90–95%",
  shifted_under_95: "Moved under 95%",
  unresolved_clash: "Unresolved clash",
};

const state = {
  files: [],
  selectedId: null,
  clashIds: new Set(),
  points: [],
  shown: 25,
  mountingPoints: [],
  mountingShown: 25,
  mountingFilter: "adjusted",
  busy: false,
};

const samplesEl = document.querySelector("#samples");
const uploadsEl = document.querySelector("#uploads");
const samplesStatus = document.querySelector("#samples-status");
const banner = document.querySelector("#banner");
const selectedTitle = document.querySelector("#selected-title");
const selectedMeta = document.querySelector("#selected-meta");
const viewBtn = document.querySelector("#view");
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
const resultsMeta = document.querySelector("#results-meta");
const typesEl = document.querySelector("#types");
const rowsEl = document.querySelector("#rows");
const showAllBtn = document.querySelector("#show-all");
const drop = document.querySelector("#drop");
const fileInput = document.querySelector("#file-input");

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

function renderSelection() {
  const file = selectedFile();
  viewBtn.disabled = !file || state.busy;
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
  if (String(point.reason).startsWith("shifted_")) return "shifted";
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
  const points = (data.points || []).slice().sort((a, b) => reasonRank(a) - reasonRank(b) || a.id.localeCompare(b.id));
  state.mountingPoints = points;
  state.mountingShown = 25;
  const adjusted = data.adjusted_count ?? points.filter((point) => point.reason !== "regular_70").length;
  state.mountingFilter = adjusted > 0 ? "adjusted" : "all";
  mountingEl.hidden = false;
  const count = data.count ?? points.length;
  const clashes = data.clash_count ?? points.filter((point) => point.clear === false).length;
  const models = data.clash_models || [];
  const also = models.length > 1 ? ` · also ${models.slice(1).join(", ")}` : "";
  mountingMeta.textContent = `${count} hangers on ${data.run_count ?? (data.runs || []).length} runs · ${adjusted} adjusted · ${clashes} still clashing${also} · ${data.out}`;
  paintMountingFilters(data.reason_counts || {});
  paintMountingRows();
  mountingEl.scrollIntoView({ behavior: "smooth", block: "start" });
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
      row.className = reasonClass(point);
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
    await window.MepViewer.open([file, ...clashFiles()]);
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

viewBtn.addEventListener("click", viewModel);
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

loadFiles().catch((error) => {
  samplesStatus.textContent = "Could not load files";
  showBanner(error.message);
});
