// API layer, each service is reached through its own nginx path-proxy (mapped to /api/v1).
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
  products: (m) => req("inv", `/products${m ? `?material_id=${m}` : ""}`),
  searchProducts: (q) => req("inv", `/products/search?q=${encodeURIComponent(q)}`),
  createProduct: (b) => req("inv", "/products", body(b)),
  stock: () => req("inv", "/inventory"),
  productStock: (m) => req("inv", `/product-stock${m ? `?material_id=${m}` : ""}`),
  lowStock: () => req("inv", "/product-stock/low"),
  ledger: (m) => req("inv", `/inventory/${m}/ledger`),
  inbound: (b) => req("inv", "/inventory/inbound", body(b)),
  productInbound: (b) => req("inv", "/inventory/product-inbound", body(b)),
  adjust: (b) => req("inv", "/inventory/adjust", body(b)),
};

export const proc = {
  vendors: () => req("proc", "/vendors"),
  vendor: (id) => req("proc", `/vendors/${id}`),
  addVendor: (b) => req("proc", "/vendors", body(b)),
  deactivateVendor: (id) => req("proc", `/vendors/${id}`, { method: "DELETE" }),
  vendorRequests: (status) => req("proc", `/vendor-requests${status ? `?status=${status}` : ""}`),
  requestVendor: (b) => req("proc", "/vendor-requests", body(b)),
  decideVendor: (id, approve) => req("proc", `/vendor-requests/${id}/decide`, body({ approve })),
  setPrice: (id, b) => req("proc", `/vendors/${id}/prices`, { method: "PUT", body: JSON.stringify(b) }),
  market: (m) => req("proc", `/prices/${m}`),
  plan: (b) => req("proc", "/procurement/plan", body(b)),
  analyze: (b) => req("proc", "/procurement/analyze", body(b)),
  createOrder: (b) => req("proc", "/procurement/orders", body(b)),
  orders: () => req("proc", "/procurement/orders"),
  receive: (id) => req("proc", `/procurement/orders/${id}/receive`, { method: "POST" }),
  llmStatus: () => req("proc", "/procurement/llm-status"),
  scout: (material_id) => req("proc", "/procurement/scout", body({ material_id })),
  externalOffers: (m) => req("proc", `/external-offers${m ? `?material_id=${m}` : ""}`),
  bomOptimize: (b) => req("proc", "/procurement/bom-optimize", body(b)),
  priceDrops: () => req("proc", "/market/price-drops"),
  marketScan: (category) => req("proc", "/market/scan", body({ category: category || "" })),
  alerts: () => req("proc", "/market/alerts"),
  createAlert: (b) => req("proc", "/market/alerts", body(b)),
  deleteAlert: (id) => req("proc", `/market/alerts/${id}`, { method: "DELETE" }),
};

export const price = {
  margins: () => req("price", "/margins"),
  setMargin: (b) => req("price", "/margins", { method: "PUT", body: JSON.stringify(b) }),
  price: (m, tier) => req("price", `/price/${m}${tier ? `?tier=${tier}` : ""}`),
  priceProduct: (id, tier) => req("price", `/price-product/${id}${tier ? `?tier=${tier}` : ""}`),
  sellingPrices: (tier) => req("price", `/selling-prices${tier ? `?tier=${tier}` : ""}`),
};

export const pay = {
  config: () => req("pay", "/payments/config"),
  list: () => req("pay", "/payments"),
  create: (b) => req("pay", "/payments", body(b)),
};

export const site = {
  sites: () => req("site", "/sites"),
  siteDetail: (id) => req("site", `/sites/${id}`),
  consumers: () => req("site", "/consumers"),
  spokes: () => req("site", "/spokes"),
  backfillAll: () => req("site", "/backfill", { method: "POST" }),
  phaseChanges: (status) => req("site", `/phase-changes${status ? `?status=${status}` : ""}`),
  decideChange: (id, approve) => req("site", `/phase-changes/${id}/decide`, body({ approve })),
  notifications: () => req("site", "/notifications"),
  schedulerTick: () => req("site", "/scheduler/tick", { method: "POST" }),
  setBom: (id, lines) => req("site", `/sites/${id}/bom`, body({ lines })),
  phaseNeeds: (id) => req("site", `/sites/${id}/phase-needs`),
};

export const PHASE_NAMES = {
  1: "Excavation & footing", 2: "Foundation & plinth beam", 3: "RCC superstructure",
  4: "Masonry / brickwork", 5: "Roofing / terrace slab", 6: "Internal plastering",
  7: "External plastering", 8: "Flooring & tiling", 9: "MEP & finishing",
};

export const TIERS = ["individual", "contractor", "commercial", "government"];
export const MATERIALS = ["cement", "steel", "sand", "aggregate", "bricks"];
export const inr = (n) =>
  "₹" + Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });
