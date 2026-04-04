/**
 * API client — calls the FastAPI backend on Cloud Run.
 * The base URL is set via VITE_API_URL environment variable.
 */

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const { token, ...rest } = options;
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${API_BASE}${path}`, { ...rest, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

// ── Subscriptions ────────────────────────────────────────────────────────────

export const getSubscriptions = (token) =>
  request("/subscriptions", { token });

export const createSubscription = (token, data) =>
  request("/subscriptions", {
    method: "POST",
    token,
    body: JSON.stringify(data),
  });

export const updateSubscription = (token, id, data) =>
  request(`/subscriptions/${id}`, {
    method: "PATCH",
    token,
    body: JSON.stringify(data),
  });

export const deleteSubscription = (token, id) =>
  request(`/subscriptions/${id}`, { method: "DELETE", token });

// ── Editions (archive) ───────────────────────────────────────────────────────

export const getEditions = (token, subscriptionId) =>
  request(`/editions?subscription_id=${subscriptionId}`, { token });
