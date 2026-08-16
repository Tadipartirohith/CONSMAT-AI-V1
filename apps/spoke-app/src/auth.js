// Auth: login via identity-service (/id proxy), token in localStorage, attached to every request.
const TKEY = "consmat_token";
const UKEY = "consmat_user";

export function getToken() {
  return localStorage.getItem(TKEY) || "";
}
export function getUser() {
  try { return JSON.parse(localStorage.getItem(UKEY) || "null"); } catch { return null; }
}
export function authHeader() {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}
export function logout() {
  localStorage.removeItem(TKEY);
  localStorage.removeItem(UKEY);
  window.location.href = "/";
}
export async function login(email, password) {
  const res = await fetch("/id/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    let d = "Login failed";
    try { d = (await res.json()).detail || d; } catch {}
    throw new Error(d);
  }
  const data = await res.json();
  localStorage.setItem(TKEY, data.access_token);
  localStorage.setItem(UKEY, JSON.stringify(data.user));
  return data.user;
}
