// Shared helpers used across all pages.
const API_BASE = "";

function getToken() {
  return localStorage.getItem("cp_token");
}

function setToken(token) {
  localStorage.setItem("cp_token", token);
}

function clearToken() {
  localStorage.removeItem("cp_token");
}

function requireAuth() {
  if (!getToken()) {
    window.location.href = "/login";
  }
}

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = Object.assign(
    { "Content-Type": "application/json" },
    options.headers || {},
    token ? { Authorization: `Bearer ${token}` } : {}
  );
  const res = await fetch(API_BASE + path, { ...options, headers });
  if (res.status === 401) {
    clearToken();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

function logout() {
  clearToken();
  window.location.href = "/login";
}

// Highlight active sidebar link + wire logout button, if present on the page.
document.addEventListener("DOMContentLoaded", () => {
  const path = window.location.pathname;
  document.querySelectorAll(".nav a").forEach((a) => {
    if (a.getAttribute("href") === path) a.classList.add("active");
  });
  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) logoutBtn.addEventListener("click", logout);
});
