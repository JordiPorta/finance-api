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
