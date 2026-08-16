// API layer — each service is reached through its own nginx path-proxy (mapped to /api/v1).
import { authHeader, logout } from "./auth.js";

const BASES = { inv: "/inv", proc: "/proc", site: "/site", price: "/price", pay: "/pay" };

async function req(base, path, opts = {}) {
  const res = await fetch(BASES[base] + path, {
    headers: { "Content-Type": "application/json", ...authHeader() },
    ...opts,
  });
  if (res.status === 401) {
    logout(); // token missing/expired → back to login
    throw new Error("Session expired");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.status === 204 ? null : res.json();
}

const body = (b) => ({ method: "POST", body: JSON.stringify(b) });

export const inv = {
  materials: () => req("inv", "/materials"),
  stock: () => req("inv", "/inventory"),
  ledger: (m) => req("inv", `/inventory/${m}/ledger`),
  inbound: (b) => req("inv", "/inventory/inbound", body(b)),
  adjust: (b) => req("inv", "/inventory/adjust", body(b)),
};

export const proc = {
  vendors: () => req("proc", "/vendors"),
  vendor: (id) => req("proc", `/vendors/${id}`),
  addVendor: (b) => req("proc", "/vendors", body(b)),
  setPrice: (id, b) => req("proc", `/vendors/${id}/prices`, { method: "PUT", body: JSON.stringify(b) }),
  market: (m) => req("proc", `/prices/${m}`),
  plan: (b) => req("proc", "/procurement/plan", body(b)),
  analyze: (b) => req("proc", "/procurement/analyze", body(b)),
  createOrder: (b) => req("proc", "/procurement/orders", body(b)),
  orders: () => req("proc", "/procurement/orders"),
  receive: (id) => req("proc", `/procurement/orders/${id}/receive`, { method: "POST" }),
  llmStatus: () => req("proc", "/procurement/llm-status"),
};

export const price = {
  margins: () => req("price", "/margins"),
  setMargin: (b) => req("price", "/margins", { method: "PUT", body: JSON.stringify(b) }),
  price: (m, tier) => req("price", `/price/${m}${tier ? `?tier=${tier}` : ""}`),
  sellingPrices: (tier) => req("price", `/selling-prices${tier ? `?tier=${tier}` : ""}`),
};

export const pay = {
  config: () => req("pay", "/payments/config"),
  list: () => req("pay", "/payments"),
  create: (b) => req("pay", "/payments", body(b)),
};

export const TIERS = ["individual", "contractor", "commercial", "government"];
export const MATERIALS = ["cement", "steel", "sand", "aggregate", "bricks"];
export const inr = (n) =>
  "₹" + Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });
