// ============ Transactions: filters + list + create ============

const Transactions = {
  accounts: [],
  categories: [],

  async load() {
    [this.accounts, this.categories] = await Promise.all([
      Api.get("/accounts/"),
      Api.get("/categories/"),
    ]);
    this.renderSelects();

    // First-run guidance: no accounts → banner + auto-open the account form.
    const noAccounts = this.accounts.length === 0;
    $("no-account-hint").classList.toggle("hidden", !noAccounts);
    if (noAccounts) $("new-account-form").classList.remove("hidden");

    await this.loadTable();
  },

  renderSelects() {
    const accOpts = this.accounts
      .map((a) => `<option value="${a.id}">${esc(a.name)} [${esc(a.type.toUpperCase())}]</option>`)
      .join("");
    const catOpts = this.categories
      .map((c) => `<option value="${c.id}">${esc(c.name)}</option>`)
      .join("");

    const keep = (sel) => sel.value; // preserve current selection across re-render
    const fill = (id, first, opts) => {
      const sel = $(id);
      const prev = keep(sel);
      sel.innerHTML = first + opts;
      if ([...sel.options].some((o) => o.value === prev)) sel.value = prev;
    };

    fill("tx-account", this.accounts.length ? "" : '<option value="">— create an account first —</option>', accOpts);
    fill("tx-category", '<option value="">—</option>', catOpts);
    fill("f-account", '<option value="">ALL</option>', accOpts);
    fill("f-category", '<option value="">ALL</option>', catOpts);
  },

  filters() {
    return {
      from_date: $("f-from").value,
      to_date: $("f-to").value,
      category_id: $("f-category").value,
      account_id: $("f-account").value,
      type: $("f-type").value,
    };
  },

  async loadTable() {
    const rows = await Api.get("/transactions/", this.filters());
    const accById = Object.fromEntries(this.accounts.map((a) => [a.id, a]));
    const catById = Object.fromEntries(this.categories.map((c) => [c.id, c]));

    const tbody = $("tx-tbody");
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="7"><div class="empty">NO TRANSACTIONS</div></td></tr>';
      $("tx-footer").textContent = "";
      return;
    }

    tbody.innerHTML = rows
      .map((t) => {
        const acc = accById[t.account_id];
        const cat = t.category_id ? catById[t.category_id] : null;
        const sign = t.type === "income" ? "+" : "−";
        return `
        <tr>
          <td>${esc(t.date)}</td>
          <td class="desc">${esc(t.description || "—")}</td>
          <td>${
            cat
              ? `<span class="cat-chip-dot" style="background:${esc(cat.color || "#718096")}"></span>${esc(cat.name)}`
              : '<span class="muted">—</span>'
          }</td>
          <td>${acc ? esc(acc.name) : t.account_id}</td>
          <td><span class="chip ${esc(t.type)}">${esc(t.type.toUpperCase())}</span></td>
          <td class="num ${t.type === "income" ? "pos" : "neg"}">${sign}${Fmt.money(t.amount, acc?.currency || "EUR")}</td>
          <td><button class="row-del" data-id="${t.id}" title="Delete">✕</button></td>
        </tr>`;
      })
      .join("");

    const income = rows.filter((t) => t.type === "income").reduce((s, t) => s + t.amount, 0);
    const expense = rows.filter((t) => t.type === "expense").reduce((s, t) => s + t.amount, 0);
    $("tx-footer").textContent =
      `${rows.length} RESULTS · IN ${Fmt.money(income)} · OUT ${Fmt.money(expense)} · NET ${Fmt.money(income - expense)}`;

    tbody.querySelectorAll(".row-del").forEach((btn) =>
      btn.addEventListener("click", async () => {
        if (!confirm("Delete this transaction?")) return;
        try {
          await Api.del(`/transactions/${btn.dataset.id}`);
          flash("TRANSACTION DELETED");
          await this.loadTable();
        } catch (e) {
          flash(e.message, "error");
        }
      })
    );
  },
};

// --- Filters auto-apply ---
["f-from", "f-to", "f-category", "f-account", "f-type"].forEach((id) =>
  $(id).addEventListener("change", () =>
    Transactions.loadTable().catch((e) => flash(e.message, "error"))
  )
);
$("f-clear").addEventListener("click", () => {
  ["f-from", "f-to", "f-category", "f-account", "f-type"].forEach((id) => ($(id).value = ""));
  Transactions.loadTable().catch((e) => flash(e.message, "error"));
});

// --- New transaction ---
$("tx-date").value = todayISO();
$("tx-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!$("tx-account").value) {
    flash("CREATE AN ACCOUNT FIRST (+ new)", "error");
    return;
  }
  try {
    await Api.post("/transactions/", {
      account_id: Number($("tx-account").value),
      category_id: $("tx-category").value ? Number($("tx-category").value) : null,
      amount: Number($("tx-amount").value),
      type: $("tx-type").value,
      description: $("tx-description").value.trim() || null,
      date: $("tx-date").value,
    });
    $("tx-amount").value = "";
    $("tx-description").value = "";
    flash("TRANSACTION ADDED");
    await Transactions.loadTable();
  } catch (err) {
    flash(err.message, "error");
  }
});

// --- Quick-create: account ---
$("toggle-new-account").addEventListener("click", (e) => {
  e.preventDefault();
  $("new-account-form").classList.toggle("hidden");
  $("new-category-form").classList.add("hidden");
});
$("new-account-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const acc = await Api.post("/accounts/", {
      name: $("na-name").value.trim(),
      type: $("na-type").value,
      currency: $("na-currency").value.trim().toUpperCase() || "EUR",
    });
    $("na-name").value = "";
    $("new-account-form").classList.add("hidden");
    flash(`ACCOUNT "${acc.name}" CREATED`);
    Transactions.accounts = await Api.get("/accounts/");
    Transactions.renderSelects();
    $("tx-account").value = acc.id;
    $("no-account-hint").classList.add("hidden");
  } catch (err) {
    flash(err.message, "error");
  }
});

// --- Quick-create: category ---
$("toggle-new-category").addEventListener("click", (e) => {
  e.preventDefault();
  $("new-category-form").classList.toggle("hidden");
  $("new-account-form").classList.add("hidden");
});
$("new-category-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const cat = await Api.post("/categories/", {
      name: $("nc-name").value.trim(),
      type: $("nc-type").value,
      color: $("nc-color").value,
    });
    $("nc-name").value = "";
    $("new-category-form").classList.add("hidden");
    flash(`CATEGORY "${cat.name}" CREATED`);
    Transactions.categories = await Api.get("/categories/");
    Transactions.renderSelects();
    $("tx-category").value = cat.id;
  } catch (err) {
    flash(err.message, "error");
  }
});
