"use strict";

const el = id => document.getElementById(id);
const number = new Intl.NumberFormat("vi-VN");
const bins = [
  { max: 5, label: "1–5", color: "#d6edc4" },
  { max: 25, label: "6–25", color: "#94d4a4" },
  { max: 100, label: "26–100", color: "#4aaa8c" },
  { max: 500, label: "101–500", color: "#22796b" },
  { max: Infinity, label: "Trên 500", color: "#16483e" },
];

function formatDay(iso) {
  const [, month, day] = iso.split("-");
  return day + "/" + month;
}

async function loadJSON(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error("HTTP " + response.status + " — " + path);
  return response.json();
}

function summarize(demand, calendar, filters) {
  const days = calendar.filter(day => day >= filters.start && day <= filters.end);
  const cells = new Map();
  const selectedDaily = [];
  let orders = 0;
  let observed = 0;

  for (const day of days) {
    if (!demand.calendar[day]) {
      selectedDaily.push({ day, orders: null });
      continue;
    }
    observed += 1;
    let selectedOrders = 0;
    for (const [cell, region, aoi, count] of demand.orders_by_date[day] || []) {
      if (filters.region && String(region) !== filters.region) continue;
      if (filters.aoi && String(aoi) !== filters.aoi) continue;
      cells.set(cell, (cells.get(cell) || 0) + count);
      orders += count;
      if (cell === filters.selectedCell) selectedOrders += count;
    }
    selectedDaily.push({ day, orders: selectedOrders });
  }
  return { days, observed, cells, orders, selectedDaily };
}

function status(state, message, onMap = true) {
  const label = el("filter_status");
  label.dataset.state = state;
  label.textContent = message;
  el("map_notice").textContent = message;
  el("map_notice").hidden = !onMap;
}

function svgElement(name, attributes) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  return node;
}

function drawChart(series) {
  const chart = el("chart");
  chart.replaceChildren();
  if (!series.length) return;

  const max = Math.max(1, ...series.map(day => day.orders || 0));
  const plotted = series.filter(day => day.orders !== null).length;
  const baseline = 105;
  const step = 600 / series.length;
  const svg = svgElement("svg", {
    viewBox: "0 0 600 112", preserveAspectRatio: "none", role: "img",
    "aria-label": "Biểu đồ số đơn mỗi ngày của ô đã chọn",
  });
  svg.append(svgElement("line", { x1: 0, x2: 600, y1: 8, y2: 8, stroke: "#d9e5df" }));
  series.forEach(({ day, orders }, index) => {
    const missing = orders === null;
    const height = missing ? 97 : orders * 97 / max;
    const bar = svgElement("rect", {
      x: index * step, y: baseline - Math.max(1, height), width: step * .87,
      height: Math.max(1, height), fill: missing ? "#dbe4df" : "#22796b",
    });
    const title = svgElement("title", {});
    title.textContent = formatDay(day) + " · " +
      (missing ? "Thiếu quan sát" : number.format(orders) + " đơn");
    bar.append(title);
    svg.append(bar);
  });
  svg.append(svgElement("line", { x1: 0, x2: 600, y1: baseline, y2: baseline, stroke: "#8da69a" }));
  const labels = document.createElement("div");
  labels.className = "chart_labels";
  for (const label of [formatDay(series[0].day),
    plotted ? "Trục dọc 0–" + number.format(max) + " đơn" : "Thiếu quan sát",
    formatDay(series.at(-1).day)]) {
    const span = document.createElement("span");
    span.textContent = label;
    labels.append(span);
  }
  chart.append(svg, labels);
}

function initialize(geometry, demand) {
  const calendar = Object.keys(demand.calendar).sort();
  if (!calendar.length || !geometry.features.length) throw new Error("Dữ liệu bản đồ trống.");

  const begin = calendar[0];
  const end = calendar.at(-1);
  const features = new Map(geometry.features.map(feature => [feature.id, feature]));
  const map = L.map("map", { scrollWheelZoom: false, minZoom: 3, zoomSnap: .25 });
  const tileLayer = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  });
  let tileFailed = false;
  tileLayer.on("loading", () => { tileFailed = false; });
  tileLayer.on("tileerror", () => { tileFailed = true; el("tile_status").hidden = false; });
  tileLayer.on("load", () => { el("tile_status").hidden = !tileFailed; });
  tileLayer.addTo(map);

  const bounds = L.geoJSON(geometry).getBounds();
  function fitMap() {
    map.fitBounds(bounds, { padding: [22, 22], maxZoom: 14 });
  }
  fitMap();
  el("fit_map").addEventListener("click", fitMap);
  el("fit_map").disabled = false;

  const visible = L.geoJSON().addTo(map);
  let selectedCell = null;
  const form = el("filters");
  const start = el("start_date");
  const finish = el("end_date");
  const region = el("region");
  const aoi = el("aoi");
  for (const input of [start, finish]) {
    input.min = begin;
    input.max = end;
  }
  start.defaultValue = begin;
  finish.defaultValue = end;
  start.value = begin;
  finish.value = end;
  const regions = new Set();
  const types = new Set();
  for (const rows of Object.values(demand.orders_by_date)) {
    for (const [, regionId, aoiType] of rows) {
      regions.add(regionId);
      types.add(aoiType);
    }
  }
  for (const id of [...regions].sort((a, b) => a - b)) region.add(new Option("Vùng " + id, id));
  for (const type of [...types].sort((a, b) => a - b)) aoi.add(new Option("Loại " + type, type));
  el("filter_fields").disabled = false;
  el("map_subtitle").textContent = "Lưới H3 mức " + demand.h3_resolution;

  for (const bin of bins) {
    const item = document.createElement("li");
    const swatch = document.createElement("span");
    swatch.className = "swatch";
    swatch.style.backgroundColor = bin.color;
    swatch.setAttribute("aria-hidden", "true");
    item.append(swatch, bin.label);
    el("legend").append(item);
  }

  function updateDetail(result) {
    el("clear_cell").hidden = !selectedCell;
    el("chart_area").hidden = !selectedCell || !result;
    if (!selectedCell) {
      el("cell_label").textContent = "Chọn một ô trên bản đồ để xem chuỗi ngày.";
      return;
    }
    let label = "Ô " + selectedCell;
    if (result && result.observed) label += " · " + number.format(result.cells.get(selectedCell) || 0) + " đơn";
    if (result && !result.observed) label += " · Không có ngày quan sát";
    el("cell_label").textContent = label;
    drawChart(result ? result.selectedDaily : []);
  }

  function styleCell(cell, count) {
    const active = selectedCell === cell;
    const bin = bins.find(entry => count <= entry.max);
    return {
      color: active ? "#9d4214" : "#285748",
      weight: active ? 3 : 1,
      fillColor: bin.color,
      fillOpacity: count ? .82 : 0,
      opacity: 1,
    };
  }

  function updateSelection(cell) {
    const previous = selectedCell;
    selectedCell = cell;
    update();
    if (previous !== cell && cell) el("cell_label").scrollIntoView({ block: "nearest" });
  }

  function renderCells(result) {
    visible.clearLayers();
    if (!result) return;
    const ids = new Set(result.cells.keys());
    if (selectedCell && result.observed) ids.add(selectedCell);
    visible.addData([...ids].map(id => features.get(id)));
    visible.eachLayer(layer => {
      const id = layer.feature.id;
      const count = result.cells.get(id) || 0;
      layer.setStyle(styleCell(id, count));
      const label = "Ô " + id + " · " + number.format(count) + " đơn";
      const tip = document.createElement("span");
      tip.textContent = label;
      layer.bindTooltip(tip).on("click", () => updateSelection(id));
      const path = layer.getElement();
      path.setAttribute("data-cell-id", id);
      path.setAttribute("tabindex", "0");
      path.setAttribute("role", "button");
      path.setAttribute("aria-pressed", String(selectedCell === id));
      path.setAttribute("aria-label", label);
      path.addEventListener("keydown", event => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          updateSelection(id);
          map.getContainer().querySelector('[data-cell-id="' + id + '"]')?.focus();
        }
      });
    });
  }

  function update() {
    if (!start.value || !finish.value || start.value < begin || finish.value > end || start.value > finish.value) {
      status("invalid", "Chọn khoảng ngày hợp lệ từ " + formatDay(begin) + " đến " + formatDay(end) + ".");
      for (const id of ["order_total", "cell_total", "day_total"]) el(id).textContent = "—";
      renderCells(null);
      updateDetail(null);
      return;
    }

    const result = summarize(demand, calendar, {
      start: start.value, end: finish.value, region: region.value, aoi: aoi.value, selectedCell,
    });
    const { days, observed, cells, orders } = result;
    el("order_total").textContent = observed ? number.format(orders) : "—";
    el("cell_total").textContent = observed ? number.format(cells.size) : "—";
    el("day_total").textContent = observed + "/" + days.length;

    const missing = days.length - observed;
    const missingNote = missing ? " " + missing + " ngày thiếu quan sát." : "";
    if (!observed) {
      status("unobserved", "Khoảng ngày này thiếu quan sát.");
    } else if (!orders) {
      status("empty", "Không có đơn theo bộ lọc đã chọn." + missingNote);
    } else {
      status("ready", missing ? missingNote.trim() : "Tất cả ngày trong khoảng đều có dữ liệu.", false);
    }
    renderCells(result);
    updateDetail(result);
  }

  form.addEventListener("change", update);
  form.addEventListener("submit", event => event.preventDefault());
  form.addEventListener("reset", () => setTimeout(update, 0));
  el("clear_cell").addEventListener("click", () => updateSelection(null));
  update();
}

(async function run() {
  try {
    if (!window.L) throw new Error("Không tải được Leaflet.");
    const [geometry, demand] = await Promise.all([
      loadJSON("./data/h3_cells.geojson"),
      loadJSON("./data/daily_cell_demand.json"),
    ]);
    initialize(geometry, demand);
  } catch (error) {
    console.error(error);
    status("error", "Không tải được bản đồ. Kiểm tra kết nối và mở trang qua máy chủ HTTP.");
  }
}());
