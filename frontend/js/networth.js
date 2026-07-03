// ============ Net worth: history chart + snapshots ============

const NetWorth = {
  async load() {
    const history = await Api.get("/stats/networth/history");

    const latest = history[history.length - 1];
    const kNet = $("kpi-nw");
    if (latest) {
      kNet.textContent = Fmt.money(latest.net);
      kNet.className = `kpi-value ${latest.net >= 0 ? "pos" : "neg"}`;
      $("kpi-nw-cash").textContent = Fmt.money(latest.liquid_cash);
      $("kpi-nw-inv").textContent = Fmt.money(latest.investments_value);
      $("kpi-nw-date").textContent = latest.date;
    } else {
      kNet.textContent = "—";
      kNet.className = "kpi-value";
      $("kpi-nw-cash").textContent = "—";
      $("kpi-nw-inv").textContent = "—";
      $("kpi-nw-date").textContent = "—";
    }

    lineChart(
      $("networth-chart"),
      history.map((s) => ({ label: s.date, value: s.net })),
      { emptyMsg: "NO SNAPSHOTS YET — TAKE ONE TO START TRACKING" }
    );

    const tbody = $("nw-tbody");
    if (!history.length) {
      tbody.innerHTML = '<tr><td colspan="6"><div class="empty">NO SNAPSHOTS</div></td></tr>';
      return;
    }
    // Newest first in the table.
    tbody.innerHTML = [...history]
      .reverse()
      .map(
        (s) => `
      <tr>
        <td>${esc(s.date)}</td>
        <td class="num">${Fmt.money(s.liquid_cash)}</td>
        <td class="num">${Fmt.money(s.investments_value)}</td>
        <td class="num">${Fmt.money(s.total_assets)}</td>
        <td class="num">${Fmt.money(s.total_liabilities)}</td>
        <td class="num ${s.net >= 0 ? "pos" : "neg"}">${Fmt.money(s.net)}</td>
      </tr>`
      )
      .join("");
  },
};

$("snapshot-btn").addEventListener("click", async () => {
  try {
    await Api.post("/stats/networth/snapshot");
    flash("SNAPSHOT SAVED");
    await NetWorth.load();
  } catch (e) {
    flash(e.message, "error");
  }
});
