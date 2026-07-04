// ============ Hand-rolled charts (no dependencies) ============

// Grouped income/expense bars, one column per month.
// rows: [{label, income, expense}]
function cashflowBars(container, rows) {
  if (!rows.length) {
    container.innerHTML = '<div class="empty">NO DATA</div>';
    return;
  }
  const max = Math.max(1, ...rows.flatMap((r) => [r.income, r.expense]));
  container.innerHTML = rows
    .map(
      (r) => `
    <div class="cf-col">
      <div class="cf-bars">
        <div class="cf-bar income" style="height:${((r.income / max) * 100).toFixed(1)}%"
             title="${esc(r.label)} IN: ${Fmt.money(r.income)}"></div>
        <div class="cf-bar expense" style="height:${((r.expense / max) * 100).toFixed(1)}%"
             title="${esc(r.label)} OUT: ${Fmt.money(r.expense)}"></div>
      </div>
      <div class="cf-label">${esc(r.label)}</div>
    </div>`
    )
    .join("");
}

// Multi-series SVG line chart with crosshair + tooltip.
// opts: {
//   labels: ["2025-08-21", ...],                     // shared x axis
//   series: [{name, values, cls, dashed}],           // values aligned to labels, null = gap
//   band:   {upper, lower, cls},                     // optional shaded range (aligned to labels)
//   height,
// }
function multiLineChart(container, { labels, series, band = null, height = 260 }) {
  if (!labels.length || !series.length) {
    container.innerHTML = '<div class="empty">NO DATA</div>';
    return;
  }

  const W = 860, H = height, L = 66, R = 14, T = 14, B = 28;
  const all = series
    .flatMap((s) => s.values)
    .concat(band ? band.upper.concat(band.lower) : [])
    .filter((v) => v !== null && v !== undefined);
  let min = Math.min(...all);
  let max = Math.max(...all);
  if (min === max) {
    min -= Math.abs(min) * 0.1 + 1;
    max += Math.abs(max) * 0.1 + 1;
  }
  const pad = (max - min) * 0.08;
  min -= pad;
  max += pad;

  const X = (i) =>
    labels.length === 1 ? L + (W - L - R) / 2 : L + ((W - L - R) * i) / (labels.length - 1);
  const Y = (v) => T + (H - T - B) * (1 - (v - min) / (max - min));

  const TICKS = 4;
  let grid = "";
  for (let t = 0; t <= TICKS; t++) {
    const v = min + ((max - min) * t) / TICKS;
    const y = Y(v).toFixed(1);
    grid +=
      `<line class="grid" x1="${L}" y1="${y}" x2="${W - R}" y2="${y}"/>` +
      `<text class="tick" x="${L - 8}" y="${+y + 3}" text-anchor="end">${Fmt.compact(v)}</text>`;
  }

  const pathOf = (values) => {
    let d = "", started = false;
    values.forEach((v, i) => {
      if (v === null || v === undefined) { started = false; return; }
      d += `${started ? "L" : "M"}${X(i).toFixed(1)},${Y(v).toFixed(1)} `;
      started = true;
    });
    return d.trim();
  };

  let bandSvg = "";
  if (band) {
    const up = [], down = [];
    band.upper.forEach((v, i) => { if (v !== null && v !== undefined) up.push([i, v]); });
    band.lower.forEach((v, i) => { if (v !== null && v !== undefined) down.push([i, v]); });
    if (up.length && down.length) {
      const d =
        up.map(([i, v], k) => `${k ? "L" : "M"}${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(" ") +
        " " +
        down.reverse().map(([i, v]) => `L${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(" ") +
        " Z";
      bandSvg = `<path class="band ${band.cls || ""}" d="${d}"/>`;
    }
  }

  const lines = series
    .map(
      (s) =>
        `<path class="mline ${s.cls || ""}${s.dashed ? " dashed" : ""}" d="${pathOf(s.values)}"/>`
    )
    .join("");

  const xLabels =
    `<text class="tick" x="${X(0).toFixed(1)}" y="${H - 8}" text-anchor="start">${esc(labels[0])}</text>` +
    (labels.length > 1
      ? `<text class="tick" x="${X(labels.length - 1).toFixed(1)}" y="${H - 8}" text-anchor="end">${esc(labels[labels.length - 1])}</text>`
      : "");

  const legend =
    `<div class="legend">` +
    series.map((s) => `<span><i class="dot ${s.cls || ""}"></i>${esc(s.name)}</span>`).join("") +
    `</div>`;

  container.innerHTML = `
    <div class="mchart-wrap">
      <svg class="linechart mchart" viewBox="0 0 ${W} ${H}">
        ${grid}${bandSvg}${lines}
        <line class="xhair hidden" y1="${T}" y2="${H - B}" x1="0" x2="0"/>
        ${xLabels}
        <rect class="hover-rect" x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}" fill="transparent"/>
      </svg>
      <div class="chart-tip hidden"></div>
    </div>
    ${legend}`;

  // --- hover layer: nearest x index -> crosshair + tooltip -------------------
  const svg = container.querySelector("svg");
  const xhair = svg.querySelector(".xhair");
  const tip = container.querySelector(".chart-tip");
  const wrap = container.querySelector(".mchart-wrap");

  svg.addEventListener("mousemove", (e) => {
    const rect = svg.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * W;
    const i = Math.max(
      0,
      Math.min(labels.length - 1, Math.round(((px - L) / (W - L - R)) * (labels.length - 1)))
    );
    const x = X(i);
    xhair.setAttribute("x1", x);
    xhair.setAttribute("x2", x);
    xhair.classList.remove("hidden");

    const rows = series
      .filter((s) => s.values[i] !== null && s.values[i] !== undefined)
      .map(
        (s) =>
          `<div><i class="dot ${s.cls || ""}"></i>${esc(s.name)} <b>${Fmt.money(s.values[i])}</b></div>`
      )
      .join("");
    tip.innerHTML = `<div class="tip-date">${esc(labels[i])}</div>${rows}`;
    tip.classList.remove("hidden");
    const wrapRect = wrap.getBoundingClientRect();
    const tipX = (x / W) * wrapRect.width;
    tip.style.left = `${Math.min(tipX + 12, wrapRect.width - tip.offsetWidth - 4)}px`;
    tip.style.top = "10px";
  });
  svg.addEventListener("mouseleave", () => {
    xhair.classList.add("hidden");
    tip.classList.add("hidden");
  });
}

// SVG line + area chart.
// points: [{label, value}]
function lineChart(container, points, { height = 240, emptyMsg = "NO DATA" } = {}) {
  if (!points.length) {
    container.innerHTML = `<div class="empty">${esc(emptyMsg)}</div>`;
    return;
  }

  const W = 860, H = height, L = 66, R = 14, T = 14, B = 28;
  const vals = points.map((p) => p.value);
  let min = Math.min(...vals);
  let max = Math.max(...vals);
  if (min === max) {
    min -= Math.abs(min) * 0.1 + 1;
    max += Math.abs(max) * 0.1 + 1;
  }
  const pad = (max - min) * 0.08;
  min -= pad;
  max += pad;

  const X = (i) =>
    points.length === 1 ? L + (W - L - R) / 2 : L + ((W - L - R) * i) / (points.length - 1);
  const Y = (v) => T + (H - T - B) * (1 - (v - min) / (max - min));

  const TICKS = 4;
  let grid = "";
  for (let t = 0; t <= TICKS; t++) {
    const v = min + ((max - min) * t) / TICKS;
    const y = Y(v).toFixed(1);
    grid +=
      `<line class="grid" x1="${L}" y1="${y}" x2="${W - R}" y2="${y}"/>` +
      `<text class="tick" x="${L - 8}" y="${+y + 3}" text-anchor="end">${Fmt.compact(v)}</text>`;
  }

  const path = points
    .map((p, i) => `${i ? "L" : "M"}${X(i).toFixed(1)},${Y(p.value).toFixed(1)}`)
    .join(" ");
  const area =
    `${path} L${X(points.length - 1).toFixed(1)},${(H - B).toFixed(1)} ` +
    `L${X(0).toFixed(1)},${(H - B).toFixed(1)} Z`;

  const dots = points
    .map(
      (p, i) =>
        `<circle cx="${X(i).toFixed(1)}" cy="${Y(p.value).toFixed(1)}" r="3">` +
        `<title>${esc(p.label)}: ${Fmt.money(p.value)}</title></circle>`
    )
    .join("");

  const xLabels =
    `<text class="tick" x="${X(0).toFixed(1)}" y="${H - 8}" text-anchor="start">${esc(points[0].label)}</text>` +
    (points.length > 1
      ? `<text class="tick" x="${X(points.length - 1).toFixed(1)}" y="${H - 8}" text-anchor="end">${esc(points[points.length - 1].label)}</text>`
      : "");

  container.innerHTML = `
    <svg class="linechart" viewBox="0 0 ${W} ${H}">
      <defs>
        <linearGradient id="nw-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#ffb020" stop-opacity="0.25"/>
          <stop offset="100%" stop-color="#ffb020" stop-opacity="0"/>
        </linearGradient>
      </defs>
      ${grid}
      <path class="area" d="${area}"/>
      <path class="line" d="${path}"/>
      ${dots}
      ${xLabels}
    </svg>`;
}
