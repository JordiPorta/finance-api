// ============ Formatting & small helpers ============

const Fmt = {
  money(n, currency = "EUR") {
    try {
      return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(n);
    } catch (_) {
      return `${Number(n).toFixed(2)} ${currency}`;
    }
  },

  // Compact axis labels: 12500 -> "12.5K"
  compact(n) {
    const abs = Math.abs(n);
    if (abs >= 1e6) return (n / 1e6).toFixed(1) + "M";
    if (abs >= 1e3) return (n / 1e3).toFixed(1) + "K";
    return Number(n).toFixed(0);
  },

  num(n, decimals = 4) {
    return Number(n)
      .toFixed(decimals)
      .replace(/\.?0+$/, "");
  },

  pct(n) {
    return `${n.toFixed(1)}%`;
  },
};

function esc(s) {
  return String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

function $(id) {
  return document.getElementById(id);
}

function monthNow() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function shiftMonth(period, delta) {
  let [y, m] = period.split("-").map(Number);
  m += delta;
  y += Math.floor((m - 1) / 12);
  m = ((((m - 1) % 12) + 12) % 12) + 1;
  return `${y}-${String(m).padStart(2, "0")}`;
}

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

let _toastTimer = null;
function flash(message, type = "ok") {
  const t = $("toast");
  t.textContent = message;
  t.className = `toast ${type}`;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => t.classList.add("hidden"), 3500);
}
