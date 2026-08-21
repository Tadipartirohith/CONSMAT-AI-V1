import { useMemo, useState } from "react";
import { site, PHASE_NAMES } from "../api.js";
import { Card, Table, Td, Badge, Button, Input, Select, useAsync } from "../components/ui.jsx";

const TOTAL_PHASES = 9;
const TONE = { green: "#22c55e", yellow: "#eab308", orange: "#f59e0b", red: "#ef4444" };
const LABEL = { green: "on track", yellow: "watch", orange: "delayed", red: "blocked" };
const daysBetween = (a, b) => Math.round((a - b) / 86400000);

function siteHealth(s, today) {
  if (s.status === "completed") return { tone: "green", reason: "completed" };
  const shorts = (s.dispatches || []).flatMap((d) => d.lines.filter((l) => l.status === "short"));
  const cur = (s.phases || []).find((p) => p.status === "in_progress");
  const end = cur?.planned_end ? new Date(cur.planned_end) : null;
  const overdue = end ? daysBetween(today, end) : null;
  if (shorts.length || (overdue != null && overdue > 3)) return { tone: "red", reason: shorts.length ? `${shorts.length} short` : `${overdue}d overdue` };
  if (overdue != null && overdue >= 0) return { tone: "orange", reason: "phase past due" };
  if (s.status === "active" && end == null) return { tone: "yellow", reason: "no phase dates" };
  if (overdue != null && overdue >= -3) return { tone: "yellow", reason: `ends in ${-overdue}d` };
  return { tone: "green", reason: "on schedule" };
}

export default function Projects() {
  const sites = useAsync(() => site.sites());
  const consumers = useAsync(() => site.consumers());
  const spokes = useAsync(() => site.spokes());
  const changes = useAsync(() => site.phaseChanges("pending"));
  const areaReqs = useAsync(() => site.areaRequests("pending"));
  const [area, setArea] = useState(null);
  const [msg, setMsg] = useState(null);
  const today = useMemo(() => new Date(), []);

  const consumerMap = Object.fromEntries((consumers.data || []).map((c) => [c.id, c]));
  const spokeMap = Object.fromEntries((spokes.data || []).map((s) => [s.id, s]));
  const areaOf = (s) => consumerMap[s.consumer_id]?.spoke_id || "unassigned";

  const areas = useMemo(() => {
    const g = {};
    for (const s of sites.data || []) {
      const aid = areaOf(s);
      (g[aid] ||= { id: aid, name: spokeMap[aid]?.name || aid, sites: [], regions: new Set(), counts: {} });
      g[aid].sites.push(s);
      if (s.location) g[aid].regions.add(s.location);
      const h = siteHealth(s, today);
      g[aid].counts[h.tone] = (g[aid].counts[h.tone] || 0) + 1;
    }
    return Object.values(g);
  }, [sites.data, consumers.data, spokes.data, today]);

  const decide = async (id, approve) => {
    setMsg(null);
    try { await site.decideChange(id, approve); setMsg({ ok: true, text: approve ? "Approved." : "Rejected." }); changes.reload(); sites.reload(); }
    catch (e) { setMsg({ ok: false, text: e.message }); }
  };
  const decideArea = async (id, approve) => {
    setMsg(null);
    try { await site.decideArea(id, approve); setMsg({ ok: true, text: approve ? "Region approved." : "Rejected." }); areaReqs.reload(); spokes.reload(); }
    catch (e) { setMsg({ ok: false, text: e.message }); }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-head text-2xl font-extrabold text-white">Projects by area</h1>
          <p className="text-xs text-muted">Manager oversight — pick a geofenced area, then drill into its projects.</p>
        </div>
        <Button size="sm" variant="ghost" onClick={() => { sites.reload(); changes.reload(); }}>Refresh</Button>
      </div>
      {msg && <p className={`text-xs ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>}

      {changes.data?.length > 0 && (
        <Card title="Phase date changes awaiting approval">
          <Table head={["Site", "Phase", "Old end", "New end", "By", ""]}>
            {changes.data.map((c) => (
              <tr key={c.id} className="border-b border-border/50">
                <Td mono>SITE-{c.site_id}</Td>
                <Td>{c.phase_seq}. {PHASE_NAMES[c.phase_seq]}</Td>
                <Td className="text-muted">{c.old_end || "-"}</Td>
                <Td>{c.new_end}</Td>
                <Td className="text-muted">{c.requested_by || c.requested_by_role}</Td>
                <Td><div className="flex gap-2"><Button size="sm" onClick={() => decide(c.id, true)}>Approve</Button><Button size="sm" variant="ghost" onClick={() => decide(c.id, false)}>Reject</Button></div></Td>
              </tr>
            ))}
          </Table>
        </Card>
      )}

      {areaReqs.data?.length > 0 && (
        <Card title="Coverage region requests awaiting approval">
          <Table head={["Spoke", "Action", "Region", "By", ""]}>
            {areaReqs.data.map((r) => (
              <tr key={r.id} className="border-b border-border/50">
                <Td mono>{r.spoke_id}</Td>
                <Td><Badge tone={r.action === "remove" ? "bad" : "ok"}>{r.action}</Badge></Td>
                <Td>{r.area}</Td>
                <Td className="text-muted">{r.requested_by || r.requested_by_role}</Td>
                <Td><div className="flex gap-2"><Button size="sm" onClick={() => decideArea(r.id, true)}>Approve</Button><Button size="sm" variant="ghost" onClick={() => decideArea(r.id, false)}>Reject</Button></div></Td>
              </tr>
            ))}
          </Table>
        </Card>
      )}

      {!area ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {areas.length === 0 && <p className="text-sm text-muted">No projects yet.</p>}
          {areas.map((a) => (
            <button key={a.id} onClick={() => setArea(a.id)} className="border border-border bg-panel p-4 text-left hover:border-accent">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-white">📍 {a.name}</span>
                <span className="text-[11px] text-muted">{a.sites.length} project(s)</span>
              </div>
              <p className="mt-1 text-[11px] text-muted">{[...a.regions].join(", ") || "no regions"}</p>
              <div className="mt-2 flex gap-2">
                {["green", "yellow", "orange", "red"].map((t) => a.counts[t] ? (
                  <span key={t} className="flex items-center gap-1 text-[11px]">
                    <span className="inline-block h-2 w-2 rounded-full" style={{ background: TONE[t] }} />{a.counts[t]}
                  </span>
                ) : null)}
              </div>
            </button>
          ))}
        </div>
      ) : (
        <AreaProjects area={areas.find((a) => a.id === area)} today={today} onBack={() => setArea(null)} />
      )}
    </div>
  );
}

function AreaProjects({ area, today, onBack }) {
  const [f, setF] = useState({ q: "", status: "", health: "", attention: false });
  const rows = (area?.sites || []).map((s) => ({ s, h: siteHealth(s, today) })).filter(({ s, h }) => {
    if (f.q && !`${s.label} ${s.code} ${s.location}`.toLowerCase().includes(f.q.toLowerCase())) return false;
    if (f.status && s.status !== f.status) return false;
    if (f.health && h.tone !== f.health) return false;
    if (f.attention && h.tone !== "red" && h.tone !== "orange") return false;
    return true;
  });
  const shorts = (s) => (s.dispatches || []).flatMap((d) => d.lines.filter((l) => l.status === "short"));

  return (
    <Card title={`📍 ${area?.name} — projects`}
      right={<Button size="sm" variant="ghost" onClick={onBack}>← Areas</Button>}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="w-48"><Input value={f.q} placeholder="search project…" onChange={(e) => setF({ ...f, q: e.target.value })} /></div>
        <Select value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}><option value="">any status</option>{["planning", "planned", "active", "completed"].map((s) => <option key={s} value={s}>{s}</option>)}</Select>
        <Select value={f.health} onChange={(e) => setF({ ...f, health: e.target.value })}><option value="">any health</option>{Object.keys(LABEL).map((t) => <option key={t} value={t}>{LABEL[t]}</option>)}</Select>
        <label className="flex items-center gap-1.5 text-xs text-muted"><input type="checkbox" checked={f.attention} onChange={(e) => setF({ ...f, attention: e.target.checked })} />needs attention</label>
      </div>
      <Table head={["Project", "Location", "Status", "Progress", "Current phase", "Health", "Alerts", ""]}>
        {rows.map(({ s, h }) => {
          const cur = (s.phases || []).find((p) => p.status === "in_progress");
          const done = (s.phases || []).filter((p) => p.status === "done").length;
          const sh = shorts(s);
          const awaitingAck = (s.dispatches || []).filter((d) => d.status === "dispatched").length;
          return (
            <tr key={s.id} className="border-b border-border/50">
              <Td>{s.label || s.code}</Td>
              <Td className="text-muted">{s.location || "-"}</Td>
              <Td><Badge tone={s.status === "completed" ? "ok" : s.status === "active" ? "accent" : "muted"}>{s.status}</Badge></Td>
              <Td mono>{done}/{TOTAL_PHASES}</Td>
              <Td className="text-muted">{cur ? `${cur.phase_seq}. ${PHASE_NAMES[cur.phase_seq]}` : "-"}</Td>
              <Td><span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: TONE[h.tone] }} /><span className="text-[11px] text-muted">{LABEL[h.tone]}</span></span></Td>
              <Td>
                <div className="flex flex-wrap gap-1">
                  {sh.length > 0 && <Badge tone="bad">{sh.length} short</Badge>}
                  {awaitingAck > 0 && <Badge tone="warn">{awaitingAck} awaiting ack</Badge>}
                  {sh.length === 0 && awaitingAck === 0 && <span className="text-muted">-</span>}
                </div>
              </Td>
              <Td><a className="text-accent hover:underline" href={`/projects/${s.id}`}>open →</a></Td>
            </tr>
          );
        })}
        {rows.length === 0 && <tr><Td className="text-muted">No projects match.</Td></tr>}
      </Table>
    </Card>
  );
}
