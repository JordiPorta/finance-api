// ============ App shell: routing + session bootstrap ============

const Views = {
  dashboard: Dashboard,
  accounts: Accounts,
  transactions: Transactions,
  investments: Investments,
  networth: NetWorth,
};

const App = {
  showLogin(message) {
    $("app").classList.add("hidden");
    $("login-view").classList.remove("hidden");
    $("auth-api-base").textContent = API_BASE;
    if (message) authError(message);
  },

  async showApp() {
    const me = await Api.get("/auth/me");
    $("user-email").textContent = me.email;
    $("login-view").classList.add("hidden");
    $("app").classList.remove("hidden");
    this.route();
  },

  route() {
    const name = (location.hash || "#/dashboard").replace("#/", "");
    const view = Views[name] ? name : "dashboard";

    document.querySelectorAll(".view").forEach((v) => v.classList.add("hidden"));
    $(`view-${view}`).classList.remove("hidden");
    document
      .querySelectorAll("#nav a")
      .forEach((a) => a.classList.toggle("active", a.dataset.view === view));

    Views[view].load().catch((e) => flash(e.message, "error"));
  },
};

window.addEventListener("hashchange", () => {
  if (!$("app").classList.contains("hidden")) App.route();
});

// --- Bootstrap ---
(async () => {
  if (!Api.token()) {
    App.showLogin();
    return;
  }
  try {
    await App.showApp();
  } catch (_) {
    // Token invalid/expired or API down — Api.request already cleared the token on 401.
    App.showLogin();
  }
})();
