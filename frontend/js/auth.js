// ============ Login / Register ============

function authError(msg) {
  const el = $("auth-error");
  if (!msg) {
    el.classList.add("hidden");
    return;
  }
  el.textContent = msg;
  el.classList.remove("hidden");
}

$("show-register").addEventListener("click", (e) => {
  e.preventDefault();
  authError(null);
  $("login-form").classList.add("hidden");
  $("register-form").classList.remove("hidden");
  $("auth-sub").textContent = "NEW OPERATOR REGISTRATION";
});

$("show-login").addEventListener("click", (e) => {
  e.preventDefault();
  authError(null);
  $("register-form").classList.add("hidden");
  $("login-form").classList.remove("hidden");
  $("auth-sub").textContent = "AUTHENTICATION REQUIRED";
});

$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  authError(null);
  try {
    const data = await Api.post("/auth/login", {
      email: $("login-email").value.trim(),
      password: $("login-password").value,
    });
    Api.setToken(data.access_token);
    await App.showApp();
  } catch (err) {
    authError(err.message.toUpperCase());
  }
});

$("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  authError(null);
  const email = $("reg-email").value.trim();
  const password = $("reg-password").value;
  try {
    await Api.post("/auth/register", {
      email,
      password,
      name: $("reg-name").value.trim(),
    });
    // Auto-login after successful registration.
    const data = await Api.post("/auth/login", { email, password });
    Api.setToken(data.access_token);
    await App.showApp();
  } catch (err) {
    authError(err.message.toUpperCase());
  }
});

$("logout-btn").addEventListener("click", () => {
  Api.clearToken();
  App.showLogin();
});
