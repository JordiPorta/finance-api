// ============ Investments: open positions + summary ============

const Investments = {
  async load() {
    const summary = await Api.get("/investments/summary");

    $("kpi-invested").textContent = Fmt.money(summary.total_invested);
    $("kpi-positions").textContent = summary.open_positions;

    const tbody = $("inv-tbody");
    if (!summary.positions.length) {
      tbody.innerHTML =
        '<tr><td colspan="7"><div class="empty">NO OPEN POSITIONS</div></td></tr>';
      return;
    }

    tbody.innerHTML = summary.positions
      .map(
        (p) => `
      <tr>
        <td><strong>${esc(p.asset.ticker)}</strong></td>
        <td class="desc">${esc(p.asset.name)}</td>
        <td><span class="chip">${esc(p.asset.type.toUpperCase())}</span></td>
        <td class="num">${Fmt.num(p.shares)}</td>
        <td class="num">${Fmt.money(p.avg_buy_price, p.currency)}</td>
        <td class="num">${Fmt.money(p.invested, p.currency)}</td>
        <td>${esc(p.currency)}</td>
      </tr>`
      )
      .join("");
  },
};
