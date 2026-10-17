const state = {
  files: [],
  selectedId: null,
  points: [],
  shown: 25,
  busy: false,
};

const samplesEl = document.querySelector("#samples");
const uploadsEl = document.querySelector("#uploads");
const samplesStatus = document.querySelector("#samples-status");
const banner = document.querySelector("#banner");
const selectedTitle = document.querySelector("#selected-title");
const selectedMeta = document.querySelector("#selected-meta");
const extractBtn = document.querySelector("#extract");
const resultsEl = document.querySelector("#results");
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
  const label = document.createElement("label");
  label.className = "file";
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
  label.append(input, body);
  return label;
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

function renderSelection() {
  const file = selectedFile();
  extractBtn.disabled = !file || state.busy;
  if (!file) {
    selectedTitle.textContent = "No model yet";
    selectedMeta.textContent = "Choose a sample or open a file. Extraction runs on the model shown here.";
    return;
  }
  selectedTitle.textContent = file.title;
  const bits = [file.name, file.size, file.schema].filter(Boolean);
  selectedMeta.textContent = bits.join(" · ");
}

function select(id) {
  state.selectedId = id;
  resultsEl.hidden = true;
  renderFiles();
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

async function upload(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".ifc")) {
    showBanner("Choose a file that ends in .ifc.");
    return;
  }
  showBanner("");
  extractBtn.disabled = true;
  samplesStatus.textContent = `Opening ${file.name}…`;
  try {
    const response = await fetch("/api/uploads", {
      method: "POST",
      headers: { "X-Filename": file.name },
      body: file,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Upload failed");
    state.files = [data.file, ...state.files.filter((item) => item.id !== data.file.id)];
    state.selectedId = data.file.id;
    resultsEl.hidden = true;
    renderFiles();
  } catch (error) {
    showBanner(error.message);
    renderFiles();
  }
}

document.querySelector("#browse").addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
  const file = fileInput.files && fileInput.files[0];
  fileInput.value = "";
  upload(file);
});

drop.addEventListener("dragover", (event) => {
  event.preventDefault();
  drop.classList.add("hot");
});
drop.addEventListener("dragleave", () => drop.classList.remove("hot"));
drop.addEventListener("drop", (event) => {
  event.preventDefault();
  drop.classList.remove("hot");
  const file = event.dataTransfer.files && event.dataTransfer.files[0];
  upload(file);
});

extractBtn.addEventListener("click", extract);
showAllBtn.addEventListener("click", () => {
  state.shown = state.points.length;
  paintRows();
});

loadFiles().catch((error) => {
  samplesStatus.textContent = "Could not load files";
  showBanner(error.message);
});
