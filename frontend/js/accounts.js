// ============ Accounts: create + list + delete ============

const Accounts = {
  async load() {
    const accounts = await Api.get("/accounts/");
    const tbody = $("acc-tbody");

    if (!accounts.length) {
      tbody.innerHTML =
        '<tr><td colspan="5"><div class="empty">NO ACCOUNTS YET — CREATE YOUR FIRST ONE ABOVE</div></td></tr>';
      return;
    }

    tbody.innerHTML = accounts
      .map(
        (a) => `
      <tr>
        <td><strong>${esc(a.name)}</strong></td>
        <td><span class="chip">${esc(a.type.toUpperCase())}</span></td>
        <td>${esc(a.currency)}</td>
        <td>${esc(String(a.created_at).slice(0, 10))}</td>
        <td><button class="row-del" data-id="${a.id}" title="Delete account">✕</button></td>
      </tr>`
      )
      .join("");

    tbody.querySelectorAll(".row-del").forEach((btn) =>
      btn.addEventListener("click", async () => {
        if (!confirm("Delete this account? Its transactions will be orphaned.")) return;
        try {
          await Api.del(`/accounts/${btn.dataset.id}`);
          flash("ACCOUNT DELETED");
          await Accounts.load();
        } catch (e) {
          flash(e.message, "error");
        }
      })
    );
  },
};

$("account-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const acc = await Api.post("/accounts/", {
      name: $("acc-name").value.trim(),
      type: $("acc-type").value,
      currency: $("acc-currency").value.trim().toUpperCase() || "EUR",
    });
    $("acc-name").value = "";
    flash(`ACCOUNT "${acc.name}" CREATED`);
    await Accounts.load();
  } catch (err) {
    flash(err.message, "error");
  }
});
