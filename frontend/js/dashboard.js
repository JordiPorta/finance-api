// ============ Dashboard: cashflow + expenses by category ============

const Dashboard = {
  async load() {
    const period = $("dash-month").value || monthNow();
    $("cat-month-label").textContent = period;

    // Selected month plus the 5 before it.
    const months = [];
    for (let i = 5; i >= 0; i--) months.push(shiftMonth(period, -i));

    const [flows, cats] = await Promise.all([
      Promise.all(months.map((m) => Api.get("/stats/cashflow", { period: m }))),
      Api.get("/stats/expenses/by-category", { period }),
    ]);

    // --- KPIs for the selected month ---
    const cur = flows[flows.length - 1];
    $("kpi-income").textContent = Fmt.money(cur.income);
    $("kpi-expenses").textContent = Fmt.money(cur.expenses);

    const net = $("kpi-net");
    net.textContent = Fmt.money(cur.net);
    net.className = `kpi-value ${cur.net >= 0 ? "pos" : "neg"}`;

    const savings = $("kpi-savings");
    if (cur.income > 0) {
      const rate = (cur.net / cur.income) * 100;
      savings.textContent = Fmt.pct(rate);
      savings.className = `kpi-value ${rate >= 0 ? "pos" : "neg"}`;
    } else {
      savings.textContent = "—";
      savings.className = "kpi-value";
    }

    // --- 6-month cashflow bars ---
    cashflowBars(
      $("cashflow-chart"),
      flows.map((f, i) => ({
        label: months[i].slice(2), // "26-07"
        income: f.income,
        expense: f.expenses,
      }))
    );

    // --- Expenses by category ---
    const wrap = $("category-bars");
    const total = cats.reduce((s, c) => s + c.total, 0);
    if (!cats.length) {
      wrap.innerHTML = '<div class="empty">NO EXPENSES THIS MONTH</div>';
      return;
    }
    const maxCat = Math.max(...cats.map((c) => c.total));
    wrap.innerHTML = cats
      .map(
        (c) => `
      <div class="cat-row">
        <div class="cat-name" title="${esc(c.category)}">${esc(c.category)}</div>
        <div class="cat-track">
          <div class="cat-fill" style="width:${((c.total / maxCat) * 100).toFixed(1)}%;
               ${c.color ? `background:${esc(c.color)}` : ""}"></div>
        </div>
        <div class="cat-amount">${Fmt.money(c.total)}</div>
        <div class="cat-pct">${Fmt.pct((c.total / total) * 100)}</div>
      </div>`
      )
      .join("");
  },
};

$("dash-month").value = monthNow();
$("dash-month").addEventListener("change", () => {
  Dashboard.load().catch((e) => flash(e.message, "error"));
});
