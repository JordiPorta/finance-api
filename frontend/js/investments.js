// ============ Investments: progress, projection, buy log, xlsx import ============

const Investments = {
  positions: [],
  accounts: [],
  selectedId: null,
  progress: null,
  _bound: false,

  async load() {
    const [summary, accounts] = await Promise.all([
      Api.get("/investments/summary"),
      Api.get("/accounts/"),
    ]);
    this.positions = summary.positions;
    this.accounts = accounts;
    this.bindOnce();

    // Position selector (keep selection across reloads)
    const sel = $("prog-position");
    if (!this.positions.some((p) => p.id === this.selectedId)) {
      this.selectedId = this.positions.length ? this.positions[0].id : null;
    }
    sel.innerHTML = this.positions
      .map(
        (p) =>
          `<option value="${p.id}" ${p.id === this.selectedId ? "selected" : ""}>${esc(p.asset.ticker)}</option>`
      )
      .join("");

    // Import account selector
    $("import-account").innerHTML = this.accounts
      .map((a) => `<option value="${a.id}">${esc(a.name)}</option>`)
      .join("");

    this.renderPositions();

    if (this.selectedId === null) {
      this.progress = null;
      ["kpi-invested", "kpi-value", "kpi-return", "kpi-fees"].forEach(
        (id) => ($(id).textContent = "—")
      );
      $("progress-chart").innerHTML =
        '<div class="empty">NO POSITIONS — IMPORT YOUR EXCEL BELOW OR BUY VIA THE API</div>';
      $("projection-chart").innerHTML = '<div class="empty">NO DATA TO PROJECT</div>';
      $("proj-summary").innerHTML = "";
      $("oplog-tbody").innerHTML =
        '<tr><td colspan="8"><div class="empty">NO OPERATIONS</div></td></tr>';
      return;
    }
    await this.loadProgress();
  },

  renderPositions() {
    const tbody = $("inv-tbody");
    if (!this.positions.length) {
      tbody.innerHTML =
        '<tr><td colspan="8"><div class="empty">NO OPEN POSITIONS</div></td></tr>';
      return;
    }
    tbody.innerHTML = this.positions
      .map(
        (p) => `
      <tr>
        <td><strong>${esc(p.asset.ticker)}</strong></td>
        <td class="desc">${esc(p.asset.name)}</td>
        <td><span class="chip">${esc(p.asset.type.toUpperCase())}</span></td>
        <td class="num">${Fmt.num(p.shares)}</td>
        <td class="num">${Fmt.money(p.avg_buy_price, p.currency)}</td>
        <td class="num">${Fmt.money(p.invested, p.currency)}</td>
        <td class="num">${p.asset.last_price != null ? Fmt.money(p.asset.last_price, p.currency) : "—"}</td>
        <td>${esc(p.currency)}</td>
      </tr>`
      )
      .join("");
  },

  async loadProgress() {
    const [progress, history] = await Promise.all([
      Api.get(`/investments/${this.selectedId}/progress`),
      Api.get(`/investments/${this.selectedId}/history`),
    ]);
    this.progress = progress;
    const pts = progress.points;
    const last = pts[pts.length - 1];

    // --- KPIs ---------------------------------------------------------------
    const value = progress.current_value ?? (last ? last.value : null);
    const ret = progress.current_return_pct ?? (last ? last.return_pct : null);
    $("kpi-invested").textContent = Fmt.money(progress.total_invested);
    $("kpi-value").textContent = value != null ? Fmt.money(value) : "—";
    const kr = $("kpi-return");
    kr.textContent = ret != null ? `${ret >= 0 ? "+" : ""}${Fmt.pct(ret * 100)}` : "—";
    kr.classList.toggle("pos", ret != null && ret >= 0);
    kr.classList.toggle("neg", ret != null && ret < 0);
    $("kpi-fees").textContent = Fmt.money(progress.total_fees);

    // --- Progress chart -----------------------------------------------------
    multiLineChart($("progress-chart"), {
      labels: pts.map((p) => p.date),
      series: [
        { name: "VALUE", cls: "value", values: pts.map((p) => p.value) },
        { name: "INVESTED", cls: "invested", values: pts.map((p) => p.invested) },
      ],
    });

    // --- Buy log (ops without splits align 1:1 with progress points) --------
    const ops = history.filter((o) => o.type !== "split");
    const rows = ops.map((o, i) => ({ op: o, pt: pts[i] })).reverse();
    $("oplog-tbody").innerHTML = rows.length
      ? rows
          .map(
            ({ op, pt }) => `
      <tr>
        <td>${esc(op.date)}</td>
        <td class="num">${op.type === "sell" ? "−" : ""}${Fmt.money(op.amount ?? op.shares * op.price)}</td>
        <td class="num">${Fmt.money(op.price)}</td>
        <td class="num">${Fmt.num(op.shares)}</td>
        <td class="num">${Fmt.money(op.fees)}</td>
        <td class="num">${pt ? Fmt.money(pt.value) : "—"}</td>
        <td class="num ${pt && pt.return_pct >= 0 ? "pos" : "neg"}">${pt ? (pt.return_pct >= 0 ? "+" : "") + Fmt.pct(pt.return_pct * 100) : "—"}</td>
        <td class="desc note-cell" title="${esc(op.note || "")}">${esc(op.note || "")}</td>
      </tr>`
          )
          .join("")
      : '<tr><td colspan="8"><div class="empty">NO OPERATIONS</div></td></tr>';

    // --- Prefills -----------------------------------------------------------
    if (progress.asset.last_price != null) $("cur-price").value = progress.asset.last_price;
    if (!$("proj-monthly").value && pts.length > 1) {
      const months = Math.max(
        1,
        (new Date(last.date) - new Date(pts[0].date)) / (1000 * 3600 * 24 * 30.44)
      );
      $("proj-monthly").value = Math.round(progress.total_invested / months / 50) * 50;
    }
    this.project();
  },

  // DCA simulation: compound the current value monthly and add the contribution.
  project() {
    const p = this.progress;
    if (!p || !p.points.length) return;
    const last = p.points[p.points.length - 1];
    const V0 = p.current_value ?? last.value;
    const I0 = p.total_invested;
    const monthly = Number($("proj-monthly").value) || 0;
    const months = Math.max(1, Math.min(120, Number($("proj-months").value) || 12));
    const annual = Number($("proj-return").value) || 0;
    const band = Math.abs(Number($("proj-band").value) || 0);

    const simulate = (annualPct) => {
      const g = Math.pow(1 + annualPct / 100, 1 / 12) - 1;
      const out = [V0];
      let v = V0;
      for (let k = 0; k < months; k++) {
        v = v * (1 + g) + monthly;
        out.push(v);
      }
      return out;
    };

    const now = new Date();
    const labels = [];
    for (let k = 0; k <= months; k++) {
      const d = new Date(now.getFullYear(), now.getMonth() + k, 1);
      labels.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
    }
    const expected = simulate(annual);
    const lower = simulate(annual - band);
    const upper = simulate(annual + band);
    const invested = labels.map((_, k) => I0 + monthly * k);

    multiLineChart($("projection-chart"), {
      labels,
      series: [
        { name: `EXPECTED (${annual}%/y)`, cls: "proj", dashed: true, values: expected },
        { name: "INVESTED", cls: "invested", values: invested },
      ],
      band: { upper, lower, cls: "proj" },
    });

    const IN = I0 + monthly * months;
    const gain = expected[months] - IN;
    $("proj-summary").innerHTML =
      `IN ${months} MONTHS: <b>${Fmt.money(expected[months])}</b> ` +
      `(range ${Fmt.money(lower[months])} – ${Fmt.money(upper[months])}) · ` +
      `INVESTED <b>${Fmt.money(IN)}</b> · ` +
      `GAIN <b class="${gain >= 0 ? "pos" : "neg"}">${gain >= 0 ? "+" : ""}${Fmt.money(gain)}</b>`;
  },

  bindOnce() {
    if (this._bound) return;
    this._bound = true;

    $("prog-position").addEventListener("change", (e) => {
      this.selectedId = Number(e.target.value);
      this.loadProgress().catch((err) => flash(err.message, "error"));
    });

    $("import-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const file = $("import-file").files[0];
      if (!file) return;
      const fd = new FormData();
      fd.append("account_id", $("import-account").value);
      fd.append("file", file);
      try {
        const res = await Api.upload("/investments/import/xlsx", fd);
        const msg = `IMPORTED ${res.imported} · SKIPPED ${res.skipped}` +
          (res.errors.length ? ` · ERRORS ${res.errors.length}` : "");
        flash(msg, res.errors.length ? "error" : "ok");
        if (res.errors.length) console.warn("Import errors:", res.errors);
        $("import-file").value = "";
        await this.load();
      } catch (err) {
        flash(err.message, "error");
      }
    });

    $("price-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!this.progress) return;
      try {
        await Api.patch(`/investments/assets/${this.progress.asset.id}/price`, {
          price: Number($("cur-price").value),
        });
        flash("PRICE UPDATED");
        await this.load();
      } catch (err) {
        flash(err.message, "error");
      }
    });

    $("split-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      if (this.selectedId === null) return;
      const ratio = Number($("split-ratio").value);
      const date = $("split-date").value;
      if (!ratio || !date) return flash("RATIO AND DATE REQUIRED", "error");
      try {
        await Api.post(`/investments/${this.selectedId}/split`, { ratio, date });
        flash(`SPLIT ${ratio}:1 REGISTERED`);
        $("split-ratio").value = "";
        await this.load();
      } catch (err) {
        flash(err.message, "error");
      }
    });

    $("proj-form").addEventListener("submit", (e) => {
      e.preventDefault();
      this.project();
    });
  },
};
