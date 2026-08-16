// Spoke app talks mainly to site-service (/site); reads hub stock (/inv) for context.
const BASES = { site: "/site", inv: "/inv" };

async function req(base, path, opts = {}) {
  const res = await fetch(BASES[base] + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
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
  addArea: (id, area) => req("site", `/spokes/${id}/areas`, body({ area })),
  dashboard: (id) => req("site", `/spokes/${id}/dashboard`),
  territory: (id) => req("site", `/spokes/${id}/sites`),
  intake: (b) => req("site", "/intake", body(b)),
  consumers: () => req("site", "/consumers"),
  updateConsumer: (id, b) => req("site", `/consumers/${id}`, { method: "PATCH", body: JSON.stringify(b) }),
  sites: () => req("site", "/sites"),
  siteDetail: (id) => req("site", `/sites/${id}`),
  createSite: (b) => req("site", "/sites", body(b)),
  plan: (id) => req("site", `/sites/${id}/plan`, { method: "POST" }),
  start: (id) => req("site", `/sites/${id}/start`, { method: "POST" }),
  completePhase: (id, seq) => req("site", `/sites/${id}/phases/${seq}/complete`, { method: "POST" }),
};

export const inv = {
  stock: () => req("inv", "/inventory"),
};

export const TIERS = ["individual", "contractor", "commercial", "government"];
export const CTYPES = ["economy", "standard", "premium"];
export const inr = (n) => "₹" + Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });
