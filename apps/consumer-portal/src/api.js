// Consumer portal: reads site-service (/site), prices via pricing-service (/price), pays via
// payment-service (/pay). All same-origin through the app's nginx path-proxy.
import { authHeader, logout } from "./auth.js";

async function req(base, path, opts = {}) {
  const res = await fetch(base + path, {
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
  consumers: () => req("/site", "/consumers"),
  sites: () => req("/site", "/sites"),
  siteDetail: (id) => req("/site", `/sites/${id}`),
  notifications: (consumerId) => req("/site", `/notifications?consumer_id=${encodeURIComponent(consumerId)}`),
  markAllRead: (consumerId) => req("/site", `/notifications/read-all?consumer_id=${encodeURIComponent(consumerId)}`, body({})),
  documents: (id, kind) => req("/site", `/sites/${id}/documents${kind ? `?kind=${kind}` : ""}`),
  downloadDocument: async (docId, filename) => {
    const res = await fetch(`/site/documents/${docId}`, { headers: { ...authHeader() } });
    if (!res.ok) throw new Error("Download failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = filename || `document-${docId}`;
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  },
  // Auth-fetch a document as an object URL for inline display (e.g. a project cover image).
  imageUrl: async (docId) => {
    const res = await fetch(`/site/documents/${docId}`, { headers: { ...authHeader() } });
    if (!res.ok) throw new Error("image load failed");
    return URL.createObjectURL(await res.blob());
  },
};

// Public (no login) - a prospective customer submits an enquiry that gets geofence-routed.
export const publicApi = {
  enquire: async (b) => {
    const res = await fetch("/site/enquiries", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b) });
    if (!res.ok) { let d = res.statusText; try { d = (await res.json()).detail || d; } catch {} throw new Error(typeof d === "string" ? d : JSON.stringify(d)); }
    return res.json();
  },
};

export const price = {
  quote: (b) => req("/price", "/quote", body(b)),
};

export const pay = {
  forRef: (ref, consumerId) =>
    req("/pay", `/payments?ref=${encodeURIComponent(ref)}&consumer_id=${encodeURIComponent(consumerId)}`),
  create: (b) => req("/pay", "/payments", body(b)),
};

export const PHASE_NAMES = {
  1: "Excavation & footing", 2: "Foundation & plinth", 3: "RCC superstructure",
  4: "Masonry / brickwork", 5: "Roofing / slab", 6: "Internal plastering",
  7: "External plastering", 8: "Flooring & tiling", 9: "MEP & finishing",
};

export const inr = (n) => "₹" + Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });

export function progressOf(siteLike) {
  const phases = siteLike.phases || [];
  const done = phases.filter((p) => p.status === "done").length;
  const total = phases.length || 9;
  const current = phases.find((p) => p.status === "in_progress");
  return {
    done, total,
    pct: siteLike.status === "completed" ? 100 : Math.round((done / total) * 100),
    currentSeq: current?.phase_seq ?? null,
  };
}
