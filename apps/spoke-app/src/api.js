// Spoke app talks mainly to site-service (/site); reads hub stock (/inv) for context.
import { authHeader, logout } from "./auth.js";

const BASES = { site: "/site", inv: "/inv", proc: "/proc" };

export const PHASE_NAMES = {
  1: "Excavation & footing", 2: "Foundation & plinth beam", 3: "RCC superstructure",
  4: "Masonry / brickwork", 5: "Roofing / terrace slab", 6: "Internal plastering",
  7: "External plastering", 8: "Flooring & tiling", 9: "MEP & finishing",
};

async function req(base, path, opts = {}) {
  const res = await fetch(BASES[base] + path, {
    headers: { "Content-Type": "application/json", ...authHeader() },
    ...opts,
  });
  if (res.status === 401) {
    logout();
    throw new Error("Session expired");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.status === 204 ? null : res.json();
}

const body = (b) => ({ method: "POST", body: JSON.stringify(b) });

export const site = {
  phases: () => req("site", "/phases"),
  spokes: () => req("site", "/spokes"),
  spoke: (id) => req("site", `/spokes/${id}`),
  createSpoke: (b) => req("site", "/spokes", body(b)),
  addArea: (id, area, action = "add") => req("site", `/spokes/${id}/areas`, body({ area, action })),
  dashboard: (id) => req("site", `/spokes/${id}/dashboard`),
  territory: (id) => req("site", `/spokes/${id}/sites`),
  intake: (b) => req("site", "/intake", body(b)),
  consumers: () => req("site", "/consumers"),
  updateConsumer: (id, b) => req("site", `/consumers/${id}`, { method: "PATCH", body: JSON.stringify(b) }),
  sites: () => req("site", "/sites"),
  siteDetail: (id) => req("site", `/sites/${id}`),
  createSite: (b) => req("site", "/sites", body(b)),
  updateSite: (id, b) => req("site", `/sites/${id}`, { method: "PATCH", body: JSON.stringify(b) }),
  submitBoq: (id, lines) => req("site", `/sites/${id}/boq/submit`, body({ lines })),
  submitFinalBoq: (id, lines) => req("site", `/sites/${id}/boq/final`, body({ lines })),
  boqs: (id) => req("site", `/sites/${id}/boqs`),
  boqStockCheck: (id) => req("site", `/sites/${id}/boq-stock-check`),
  boqChanges: (siteId) => req("site", `/boq-changes${siteId ? `?site_id=${siteId}` : ""}`),
  ackBoqChange: (reqId) => req("site", `/boq-changes/${reqId}/ack`, { method: "POST" }),
  previewBudget: (id) => req("site", `/sites/${id}/budget`),
  projectFinance: (id) => req("site", `/sites/${id}/finance`),
  updateFinance: (id, b) => req("site", `/sites/${id}/finance`, { method: "PATCH", body: JSON.stringify(b) }),
  financePartners: () => req("site", "/finance-partners"),
  createFinancePartner: (b) => req("site", "/finance-partners", body(b)),
  documents: (id, kind) => req("site", `/sites/${id}/documents${kind ? `?kind=${kind}` : ""}`),
  uploadDocument: async (id, file, kind = "design", note = "") => {
    const fd = new FormData(); fd.append("file", file); fd.append("kind", kind); fd.append("note", note);
    const res = await fetch(`/site/sites/${id}/documents`, { method: "POST", headers: { ...authHeader() }, body: fd });
    if (res.status === 401) { logout(); throw new Error("Session expired"); }
    if (!res.ok) { let d = res.statusText; try { d = (await res.json()).detail || d; } catch {} throw new Error(typeof d === "string" ? d : JSON.stringify(d)); }
    return res.json();
  },
  downloadDocument: async (docId, filename) => {
    const res = await fetch(`/site/documents/${docId}`, { headers: { ...authHeader() } });
    if (!res.ok) throw new Error("Download failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = filename || `document-${docId}`;
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  },
  plan: (id) => req("site", `/sites/${id}/plan`, { method: "POST" }),
  setBom: (id, lines) => req("site", `/sites/${id}/bom`, body({ lines })),
  setPhaseDates: (id, seq, b) => req("site", `/sites/${id}/phases/${seq}/dates`, body(b)),
  phaseChanges: (siteId) => req("site", `/phase-changes?site_id=${siteId}`),
  decideChange: (id, approve) => req("site", `/phase-changes/${id}/decide`, body({ approve })),
  notifications: (spokeId) => req("site", `/notifications${spokeId ? `?spoke_id=${spokeId}` : ""}`),
  start: (id) => req("site", `/sites/${id}/start`, { method: "POST" }),
  completePhase: (id, seq) => req("site", `/sites/${id}/phases/${seq}/complete`, { method: "POST" }),
  confirmDelivery: (dispatchId) => req("site", `/dispatches/${dispatchId}/confirm`, { method: "POST" }),
  backfill: (id) => req("site", `/sites/${id}/backfill`, { method: "POST" }),
};

export const inv = {
  stock: () => req("inv", "/inventory"),
  productStock: (m) => req("inv", `/product-stock${m ? `?material_id=${m}` : ""}`),
  materials: () => req("inv", "/materials"),
  products: (m) => req("inv", `/products${m ? `?material_id=${m}` : ""}`),
  searchProducts: (q) => req("inv", `/products/search?q=${encodeURIComponent(q)}`),
};

export const proc = {
  createOrderRequest: (b) => req("proc", "/procurement/order-requests", body(b)),
  orderRequests: (status) => req("proc", `/procurement/order-requests${status ? `?status=${status}` : ""}`),
  bomOptimize: (b) => req("proc", "/procurement/bom-optimize", body(b)),
  bomExtract: async (file) => {
    const fd = new FormData(); fd.append("file", file);
    const res = await fetch("/proc/procurement/bom-extract", { method: "POST", headers: { ...authHeader() }, body: fd });
    if (res.status === 401) { logout(); throw new Error("Session expired"); }
    if (!res.ok) { let d = res.statusText; try { d = (await res.json()).detail || d; } catch {} throw new Error(typeof d === "string" ? d : JSON.stringify(d)); }
    return res.json();
  },
};

export const TIERS = ["individual", "contractor", "commercial", "government"];
export const CTYPES = ["economy", "standard", "premium"];
export const inr = (n) => "₹" + Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });
