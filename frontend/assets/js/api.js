// window.API_BASE_URL comes from config.js (empty string = same-origin,
// used for local dev; a real URL like "https://your-backend.onrender.com"
// once deployed separately - see build.js / vercel.json).
const BASE = window.API_BASE_URL || "";

function authHeaders() {
  const token = localStorage.getItem("auth_token");
  return token ? { Authorization: "Bearer " + token } : {};
}

async function handleResponse(r) {
  if (r.status === 401) {
    // Token missing/invalid/logged-out elsewhere - store.js listens for
    // this to drop back to the login screen (see store.js's
    // handleUnauthorized() and the window listener at the bottom of that file).
    localStorage.removeItem("auth_token");
    window.dispatchEvent(new CustomEvent("auth:unauthorized"));
  }
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export const api = {
  async get(path) {
    const r = await fetch(BASE + path, { headers: authHeaders() });
    return handleResponse(r);
  },
  async post(path, body) {
    const r = await fetch(BASE + path, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(body || {}),
    });
    return handleResponse(r);
  },
  // multipart/form-data (file uploads) - no Content-Type header here on
  // purpose, the browser sets it (with the right boundary) from the
  // FormData body itself; setting it manually breaks the upload.
  async postForm(path, formData) {
    const r = await fetch(BASE + path, {
      method: "POST",
      headers: authHeaders(),
      body: formData,
    });
    return handleResponse(r);
  },
  async put(path, body) {
    const r = await fetch(BASE + path, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(body || {}),
    });
    return handleResponse(r);
  },
  async patch(path, body) {
    const r = await fetch(BASE + path, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(body || {}),
    });
    return handleResponse(r);
  },
  async del(path) {
    const r = await fetch(BASE + path, { method: "DELETE", headers: authHeaders() });
    return handleResponse(r);
  },
};
