// Consumer portal is read-only over site-service.
async function req(path) {
  const res = await fetch("/site" + path, { headers: { "Content-Type": "application/json" } });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json();
}

export const site = {
  consumers: () => req("/consumers"),
  sites: () => req("/sites"),
  siteDetail: (id) => req(`/sites/${id}`),
};

export const PHASE_NAMES = {
  1: "Excavation & footing", 2: "Foundation & plinth", 3: "RCC superstructure",
  4: "Masonry / brickwork", 5: "Roofing / slab", 6: "Internal plastering",
  7: "External plastering", 8: "Flooring & tiling", 9: "MEP & finishing",
};

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

// Selected consumer persists locally (stands in for login until identity-service lands).
export const store = {
  get: () => localStorage.getItem("consmat_consumer") || "",
  set: (id) => localStorage.setItem("consmat_consumer", id),
};
