// ============ API client ============
// Override the API base from the browser console with:
//   localStorage.setItem('fin_api_base', 'https://my-api.example.com'); location.reload();
const API_BASE = localStorage.getItem("fin_api_base") || "http://localhost:8000";

const Api = {
  token: () => localStorage.getItem("fin_token"),
  setToken: (t) => localStorage.setItem("fin_token", t),
  clearToken: () => localStorage.removeItem("fin_token"),

  async request(path, { method = "GET", body, formData, params } = {}) {
    const url = new URL(API_BASE + path);
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
      }
    }

    const headers = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const token = Api.token();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    let res;
    try {
      res = await fetch(url, {
        method,
        headers,
        // FormData sets its own multipart Content-Type boundary.
        body: formData !== undefined ? formData : body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch (_) {
      throw new Error(`API unreachable at ${API_BASE} — is the server running?`);
    }

    // Expired/invalid token: drop it and force re-login.
    if (res.status === 401 && Api.token()) {
      Api.clearToken();
      App.showLogin("SESSION EXPIRED — LOG IN AGAIN");
      throw new Error("Session expired");
    }

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const data = await res.json();
        if (data.detail) {
          detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
        }
      } catch (_) {}
      throw new Error(detail);
    }

    if (res.status === 204) return null;
    return res.json();
  },

  get: (path, params) => Api.request(path, { params }),
  post: (path, body) => Api.request(path, { method: "POST", body }),
  put: (path, body) => Api.request(path, { method: "PUT", body }),
  patch: (path, body) => Api.request(path, { method: "PATCH", body }),
  del: (path) => Api.request(path, { method: "DELETE" }),
  upload: (path, formData) => Api.request(path, { method: "POST", formData }),
};
