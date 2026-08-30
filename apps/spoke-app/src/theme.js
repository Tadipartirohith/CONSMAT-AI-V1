// Theme preference: 'dark' (default) | 'light' | 'system'. Applied via data-theme on <html>.
const KEY = "consmat_theme";

export function getThemePref() {
  try { return localStorage.getItem(KEY) || "dark"; } catch { return "dark"; }
}
export function resolveTheme(pref) {
  if (pref === "system") {
    try { return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"; }
    catch { return "dark"; }
  }
  return pref === "light" ? "light" : "dark";
}
export function applyTheme(pref) {
  const r = resolveTheme(pref);
  const el = document.documentElement;
  if (r === "light") el.setAttribute("data-theme", "light");
  else el.removeAttribute("data-theme");   // dark is the default :root
}
export function setThemePref(pref) {
  try { localStorage.setItem(KEY, pref); } catch { /* ignore */ }
  applyTheme(pref);
}
export function initTheme() { applyTheme(getThemePref()); }
