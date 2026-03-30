// app.js — Home screen organizer frontend
"use strict";

// ── State ──────────────────────────────────────────────────────────────────
let state = {
  layout: null,      // { dock: [...], pages: [[...], ...] }
  apps: {},          // bundle_id -> display_name
  icons: {},         // bundle_id -> data-URI or null
  currentPage: 0,
  dirty: false,
};

// ── DOM refs ───────────────────────────────────────────────────────────────
const statusDot   = document.getElementById("status-dot");
const deviceName  = document.getElementById("device-name");
const btnLoad     = document.getElementById("btn-load");
const btnSave     = document.getElementById("btn-save");
const pageTabs    = document.getElementById("page-tabs");
const iconGrid    = document.getElementById("icon-grid");
const dockGrid    = document.getElementById("dock-grid");
const overlay     = document.getElementById("message-overlay");
const overlayMsg  = document.getElementById("overlay-message");
const overlayBtn  = document.getElementById("overlay-btn");
const sidebar     = document.getElementById("sidebar-apps");
const toast       = document.getElementById("toast");

// ── Toast ──────────────────────────────────────────────────────────────────
function showToast(msg, isError = false) {
  toast.textContent = msg;
  toast.className = "show" + (isError ? " error" : "");
  setTimeout(() => { toast.className = ""; }, 2500);
}

// ── Overlay ────────────────────────────────────────────────────────────────
function showOverlay(html, btnLabel, onBtn) {
  overlayMsg.innerHTML = html;
  overlayBtn.textContent = btnLabel;
  overlayBtn.onclick = onBtn;
  overlay.classList.remove("hidden");
}
function hideOverlay() { overlay.classList.add("hidden"); }

// ── Status dot ─────────────────────────────────────────────────────────────
function setStatus(state) {
  statusDot.className = state; // "connected" | "error" | "loading" | ""
}

// ── App icon (lazy-loaded) ─────────────────────────────────────────────────
async function fetchIcon(bundleId) {
  if (state.icons[bundleId] !== undefined) return state.icons[bundleId];
  state.icons[bundleId] = null; // mark as requested
  try {
    const r = await fetch(`/api/icon/${encodeURIComponent(bundleId)}`);
    if (r.ok) {
      const j = await r.json();
      if (j.png_b64) {
        state.icons[bundleId] = `data:image/png;base64,${j.png_b64}`;
        updateIconsInDOM(bundleId, state.icons[bundleId]);
      }
    }
  } catch (_) {}
  return state.icons[bundleId];
}

function updateIconsInDOM(bundleId, src) {
  document.querySelectorAll(`[data-bundle="${CSS.escape(bundleId)}"] .app-icon`).forEach(el => {
    el.innerHTML = `<img src="${src}" alt="">`;
  });
}

// ── Render helpers ─────────────────────────────────────────────────────────
function appLabel(bundleId) {
  return state.apps[bundleId] || bundleId.split(".").pop();
}

function makeAppCell(bundleId, draggable = true) {
  const cell = document.createElement("div");
  cell.className = "app-cell";
  cell.dataset.bundle = bundleId;
  if (draggable) cell.setAttribute("draggable", "true");

  const iconDiv = document.createElement("div");
  iconDiv.className = "app-icon";

  if (state.icons[bundleId]) {
    iconDiv.innerHTML = `<img src="${state.icons[bundleId]}" alt="">`;
  } else {
    iconDiv.textContent = appLabel(bundleId).slice(0, 3).toUpperCase();
    fetchIcon(bundleId); // load async
  }

  const nameDiv = document.createElement("div");
  nameDiv.className = "app-name";
  nameDiv.textContent = appLabel(bundleId);

  cell.appendChild(iconDiv);
  cell.appendChild(nameDiv);
  return cell;
}

function makeFolderCell(folder) {
  const cell = document.createElement("div");
  cell.className = "folder-cell";
  cell.dataset.folderName = folder.name;

  const folderIcon = document.createElement("div");
  folderIcon.className = "folder-icon";

  // Show up to 9 mini icons
  const flat = folder.pages.flat().slice(0, 9);
  flat.forEach(bid => {
    const mini = document.createElement("div");
    mini.className = "folder-mini-icon";
    folderIcon.appendChild(mini);
  });

  const nameDiv = document.createElement("div");
  nameDiv.className = "folder-name";
  nameDiv.textContent = folder.name || "Folder";

  cell.appendChild(folderIcon);
  cell.appendChild(nameDiv);
  return cell;
}

// ── Page rendering ─────────────────────────────────────────────────────────
function renderPageTabs() {
  pageTabs.innerHTML = "";
  state.layout.pages.forEach((_, i) => {
    const tab = document.createElement("button");
    tab.className = "page-tab" + (i === state.currentPage ? " active" : "");
    tab.textContent = i + 1;
    tab.onclick = () => { state.currentPage = i; renderCurrentPage(); renderPageTabs(); };
    pageTabs.appendChild(tab);
  });
  const addBtn = document.createElement("button");
  addBtn.id = "btn-add-page";
  addBtn.textContent = "+";
  addBtn.title = "Add page";
  addBtn.onclick = addPage;
  pageTabs.appendChild(addBtn);
}

function renderCurrentPage() {
  iconGrid.innerHTML = "";
  const page = state.layout.pages[state.currentPage] || [];

  page.forEach((item, idx) => {
    let cell;
    if (item.type === "app") {
      cell = makeAppCell(item.id);
    } else if (item.type === "folder") {
      cell = makeFolderCell(item);
    }
    if (cell) {
      cell.dataset.idx = idx;
      iconGrid.appendChild(cell);
    }
  });

  // Placeholder for empty slots
  const GRID_SIZE = 24;
  for (let i = page.length; i < GRID_SIZE; i++) {
    const ph = document.createElement("div");
    ph.className = "app-cell placeholder";
    ph.dataset.idx = i;
    iconGrid.appendChild(ph);
  }

  initSortable(iconGrid, "page");
}

function renderDock() {
  dockGrid.innerHTML = "";
  state.layout.dock.forEach((bundleId, idx) => {
    const cell = makeAppCell(bundleId);
    cell.dataset.dockIdx = idx;
    dockGrid.appendChild(cell);
  });
  initSortable(dockGrid, "dock");
}

function renderSidebar() {
  sidebar.innerHTML = "";
  const sorted = Object.entries(state.apps).sort((a, b) => a[1].localeCompare(b[1]));
  sorted.forEach(([bid, name]) => {
    const row = document.createElement("div");
    row.className = "sidebar-app";
    row.dataset.bundle = bid;
    row.setAttribute("draggable", "true");

    const iconEl = document.createElement("div");
    iconEl.className = "app-icon-sm";
    if (state.icons[bid]) {
      iconEl.innerHTML = `<img src="${state.icons[bid]}" alt="">`;
    } else {
      iconEl.textContent = name.slice(0, 2).toUpperCase();
    }

    const label = document.createElement("span");
    label.className = "app-label";
    label.textContent = name;

    row.appendChild(iconEl);
    row.appendChild(label);
    sidebar.appendChild(row);
  });
}

// ── SortableJS drag-drop ───────────────────────────────────────────────────
let sortableInstances = {};

function initSortable(el, zone) {
  if (sortableInstances[zone]) sortableInstances[zone].destroy();

  sortableInstances[zone] = Sortable.create(el, {
    group: "icons",
    animation: 150,
    ghostClass: "sortable-ghost",
    dragClass: "sortable-drag",
    filter: ".placeholder",
    onEnd(evt) {
      syncStateFromDOM();
      markDirty();
    },
  });
}

function syncStateFromDOM() {
  // Rebuild current page from DOM order
  const page = [];
  iconGrid.querySelectorAll(".app-cell:not(.placeholder), .folder-cell").forEach(cell => {
    if (cell.dataset.bundle) {
      page.push({ type: "app", id: cell.dataset.bundle });
    } else if (cell.dataset.folderName !== undefined) {
      // Find original folder data
      const orig = state.layout.pages[state.currentPage].find(
        f => f.type === "folder" && f.name === cell.dataset.folderName
      );
      if (orig) page.push(orig);
    }
  });
  state.layout.pages[state.currentPage] = page;

  // Rebuild dock
  const dock = [];
  dockGrid.querySelectorAll(".app-cell").forEach(cell => {
    if (cell.dataset.bundle) dock.push(cell.dataset.bundle);
  });
  state.layout.dock = dock;
}

function markDirty() {
  state.dirty = true;
  btnSave.disabled = false;
}

// ── Add / remove page ──────────────────────────────────────────────────────
function addPage() {
  state.layout.pages.push([]);
  state.currentPage = state.layout.pages.length - 1;
  renderPageTabs();
  renderCurrentPage();
  markDirty();
}

// ── Load from device ───────────────────────────────────────────────────────
async function loadLayout() {
  setStatus("loading");
  btnLoad.disabled = true;
  btnSave.disabled = true;

  try {
    const r = await fetch("/api/layout");
    const j = await r.json();

    if (!j.ok) throw new Error(j.error);

    state.layout = j.layout;
    state.apps   = j.apps;
    state.icons  = {};
    state.currentPage = 0;
    state.dirty = false;

    setStatus("connected");
    deviceName.textContent = "Connected";

    renderPageTabs();
    renderCurrentPage();
    renderDock();
    renderSidebar();

    showToast("Layout loaded from device");
  } catch (err) {
    setStatus("error");
    showOverlay(
      `<h2>Could not connect</h2><pre>${err.message}</pre>
       <p>Make sure tunneld is running as admin:</p>
       <pre>python -m pymobiledevice3 remote tunneld</pre>`,
      "Retry",
      () => { hideOverlay(); loadLayout(); }
    );
  } finally {
    btnLoad.disabled = false;
  }
}

// ── Save to device ─────────────────────────────────────────────────────────
async function saveLayout() {
  btnSave.disabled = true;
  syncStateFromDOM();

  try {
    const r = await fetch("/api/layout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state.layout),
    });
    const j = await r.json();
    if (!j.ok) throw new Error(j.error);
    state.dirty = false;
    showToast("Layout saved to device!");
  } catch (err) {
    showToast("Save failed: " + err.message, true);
    btnSave.disabled = false;
  }
}

// ── Check device on load ───────────────────────────────────────────────────
async function checkStatus() {
  setStatus("loading");
  try {
    const r = await fetch("/api/status");
    const j = await r.json();
    if (j.ok) {
      setStatus("connected");
      deviceName.textContent = `${j.device.name} · iOS ${j.device.version}`;
    } else {
      setStatus("error");
      deviceName.textContent = "Not connected";
    }
  } catch (_) {
    setStatus("error");
  }
}

// ── Wire up buttons ────────────────────────────────────────────────────────
btnLoad.addEventListener("click", loadLayout);
btnSave.addEventListener("click", saveLayout);
btnSave.disabled = true;

window.addEventListener("load", checkStatus);
