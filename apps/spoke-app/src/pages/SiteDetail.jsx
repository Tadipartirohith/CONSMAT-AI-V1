import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { site, inv, proc, PHASE_NAMES } from "../api.js";
import { Card, Table, Td, Badge, Button, Input, Select, useAsync } from "../components/ui.jsx";
import { getUser } from "../auth.js";

// What each field role owns on a site. The architect is the design authority: the Bill of Materials
// (which products and how much) and the phase schedule come from the architect's drawings; the civil
// engineer executes the build phase by phase; the spokesperson owns the customer relationship.
const ROLE_TASK = {
  architect: { icon: "📐", title: "Architect - design spec", text: "Enter and refine this site's Bill of Materials (products & quantities) from the drawings, and set each phase's planned dates. This is your design output; it stays editable until construction starts." },
  civil_engineer: { icon: "🏗️", title: "Civil engineer - execution", text: "Run the build: start the site, complete phases in order (the hub auto-dispatches the next phase's materials), and confirm each delivery when it reaches site." },
  spokesperson: { icon: "🤝", title: "Spokesperson - coverage", text: "Own the customer relationship and coverage. Review and approve civil-engineer phase-date changes; keep the plan and schedule aligned with the hub." },
};

function RoleGuide() {
  const role = getUser()?.role;
  const t = ROLE_TASK[role];
  if (!t) return null;
  return (
    <div className="flex items-start gap-2.5 border border-accent/30 bg-accent/5 px-3 py-2">
      <span className="text-lg">{t.icon}</span>
      <div>
        <p className="text-xs font-semibold text-accent">{t.title}</p>
        <p className="text-[11px] text-white/70">{t.text}</p>
      </div>
    </div>
  );
}

export default function SiteDetail() {
  const { id } = useParams();
  const detail = useAsync(() => site.siteDetail(id), [id]);
  const changes = useAsync(() => site.phaseChanges(id), [id]);
  const notifs = useAsync(() => site.notifications(), [id]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  const s = detail.data;
  const reloadAll = () => { detail.reload(); changes.reload(); notifs.reload(); };
  const act = async (fn, label) => {
    setBusy(true); setMsg(null);
    try { await fn(); setMsg({ ok: true, text: `${label} done.` }); reloadAll(); }
    catch (e) { setMsg({ ok: false, text: e.message }); } finally { setBusy(false); }
  };

  if (detail.error) return <p className="text-sm text-red-400">{detail.error}</p>;
  if (!s) return <p className="text-sm text-muted">Loading…</p>;

  const planned = s.bom_lines.length > 0;
  const editable = s.status === "planning" || s.status === "planned";
  const phase1 = s.phases.find((p) => p.phase_seq === 1);
  const notStarted = planned && phase1 && phase1.status === "pending";
  const hasShorts = s.dispatches.some((d) => d.lines.some((l) => l.status === "short"));
  const pending = (changes.data || []).filter((c) => c.status === "pending");

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Link to="/sites" className="text-sm text-muted hover:text-white">Back to Sites</Link>
        <h1 className="font-head text-2xl font-extrabold text-white">{s.code}</h1>
        <Badge tone={s.status === "completed" ? "ok" : s.status === "active" ? "accent" : "muted"}>{s.status}</Badge>
        {s.project_type && <Badge tone={s.project_type === "captive" ? "accent" : "ok"}>{s.project_type}</Badge>}
        <span className="text-[11px] text-muted">{(s.stage || "onboarded").replace(/_/g, " ")}</span>
        <div className="ml-auto flex items-center gap-2">
          {!s.project_type && (
            <Select value="" onChange={(e) => e.target.value && act(() => site.updateSite(id, { project_type: e.target.value }), "Project type set")}>
              <option value="">set project type…</option>
              <option value="captive">captive</option>
              <option value="client">client</option>
            </Select>
          )}
          {notStarted && <Button onClick={() => act(() => site.start(id), "Started")} disabled={busy}>Start construction</Button>}
        </div>
      </div>
      {msg && <p className={`text-xs ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>}

      <RoleGuide />

      <div className="flex flex-wrap gap-4 border border-border bg-panel p-4 text-sm">
        <Info label="Label" value={s.label || "-"} />
        <Info label="Location" value={s.location || "-"} />
        <Info label="Area" value={`${s.area_sqft} sqft × ${s.floors} floor(s)`} />
        <Info label="Type" value={s.construction_type} />
      </div>

      {pending.length > 0 && (
        <Card title="Phase date changes awaiting your approval">
          {pending.map((c) => (
            <div key={c.id} className="flex flex-wrap items-center gap-3 border-b border-border/50 py-2 text-sm">
              <span className="text-white/80">Phase {c.phase_seq} ({PHASE_NAMES[c.phase_seq]}): end {c.old_end || "?"} to <b>{c.new_end}</b></span>
              <span className="text-muted">by {c.requested_by || c.requested_by_role}</span>
              <div className="ml-auto flex gap-2">
                <Button size="sm" onClick={() => act(() => site.decideChange(c.id, true), "Approved")} disabled={busy}>Approve</Button>
                <Button size="sm" variant="ghost" onClick={() => act(() => site.decideChange(c.id, false), "Rejected")} disabled={busy}>Reject</Button>
              </div>
            </div>
          ))}
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <BomCard siteId={id} lines={s.bom_lines} editable={editable} onSaved={(t) => { setMsg({ ok: true, text: t }); reloadAll(); }} />

        <Card title="Construction phases">
          <div className="space-y-1.5">
            {s.phases.slice().sort((a, b) => a.phase_seq - b.phase_seq).map((p) => (
              <PhaseRow key={p.phase_seq} siteId={id} phase={p} busy={busy}
                onComplete={() => act(() => site.completePhase(id, p.phase_seq), `Phase ${p.phase_seq} completed`)}
                onDates={(b) => act(() => site.setPhaseDates(id, p.phase_seq, b), `Phase ${p.phase_seq} dates`)} />
            ))}
          </div>
          <p className="mt-2 text-[11px] text-muted">A civil engineer's change to a phase end date needs spoke or manager approval. The hub auto-dispatches the next phase ~1 day before the current one ends.</p>
        </Card>
      </div>

      <Card title="Dispatches (hub to site)"
        right={hasShorts && <Button size="sm" onClick={() => act(() => site.backfill(id), "Backfill")} disabled={busy}>Backfill shortfalls</Button>}>
        {s.dispatches.length === 0 ? <p className="text-sm text-muted">No dispatches yet.</p> : (
          <div className="space-y-2">
            {s.dispatches.slice().sort((a, b) => a.phase_seq - b.phase_seq).map((d) => (
              <div key={d.id} className="border border-border/60 bg-panel2 p-3">
                <div className="mb-1.5 flex items-center gap-2 text-sm">
                  <span className="font-mono text-white">{d.code}</span>
                  <span className="text-muted">phase {d.phase_seq}, {PHASE_NAMES[d.phase_seq]}</span>
                  <Badge tone={d.status === "received" ? "accent" : d.status === "dispatched" ? "ok" : d.status === "partial" ? "warn" : "bad"}>{d.status}</Badge>
                  {d.status === "dispatched" && <Button size="sm" onClick={() => act(() => site.confirmDelivery(d.id), "Delivery confirmed")} disabled={busy}>Confirm delivery</Button>}
                  {d.status === "received" && <span className="text-[11px] text-accent">✓ confirmed</span>}
                </div>
                <div className="flex flex-wrap gap-2">
                  {d.lines.map((l, i) => (
                    <span key={i} className={`font-mono text-xs ${l.status === "short" ? "text-red-400" : "text-white/70"}`}>
                      {l.product_name || l.material_id} ×{l.qty}{l.status === "short" && " (short)"}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card title="Notifications" right={<Button size="sm" variant="ghost" onClick={notifs.reload}>Refresh</Button>}>
        {(notifs.data || []).filter((n) => n.site_id === Number(id)).slice(0, 8).map((n) => (
          <div key={n.id} className="border-b border-border/50 py-1.5 text-sm">
            <Badge tone={n.kind === "dispatched" ? "ok" : "warn"}>{n.kind}</Badge>
            <span className="ml-2 text-white/80">{n.message}</span>
          </div>
        ))}
        {(notifs.data || []).filter((n) => n.site_id === Number(id)).length === 0 && <p className="text-sm text-muted">No notifications for this site yet.</p>}
      </Card>
    </div>
  );
}

function BomCard({ siteId, lines, editable, onSaved }) {
  const products = useAsync(() => inv.products());
  const [rows, setRows] = useState(() => lines.map((b) => ({ product_id: b.product_id, material_id: b.material_id, product_name: b.product_name || b.material_id, phase_seq: b.phase_seq || 0, total_qty: b.total_qty })));
  const [pid, setPid] = useState("");
  const [qty, setQty] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [info, setInfo] = useState(null);

  const add = () => {
    const p = (products.data || []).find((x) => x.id === pid);
    if (!p || !qty) return;
    setRows([...rows, { product_id: p.id, material_id: p.material_id, product_name: p.name, phase_seq: 0, total_qty: Number(qty) }]);
    setPid(""); setQty("");
  };
  const del = (i) => setRows(rows.filter((_, j) => j !== i));
  const setField = (i, k, v) => setRows(rows.map((x, j) => j === i ? { ...x, [k]: v } : x));
  const save = async () => {
    setBusy(true); setErr(null);
    try { await site.setBom(siteId, rows.filter((r) => r.product_id).map((r) => ({ material_id: r.material_id, product_id: r.product_id, product_name: r.product_name, phase_seq: Number(r.phase_seq) || 0, total_qty: Number(r.total_qty) }))); onSaved("Bill of materials saved."); }
    catch (e) { setErr(e.message); } finally { setBusy(false); }
  };
  const uploadDoc = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    setBusy(true); setInfo("Reading document…"); setErr(null);
    try {
      const r = await proc.bomExtract(file);
      setRows((r.lines || []).map((l) => ({ product_id: l.product_id || "", material_id: l.material_id || "", product_name: l.product_name || l.raw || "", phase_seq: l.phase_seq || 0, total_qty: l.total_qty || 0 })));
      setInfo(`${r.summary} - review & map any unmatched, set phases, then Save.`);
    } catch (e) { setErr(e.message); } finally { setBusy(false); e.target.value = ""; }
  };

  if (!editable) {
    return (
      <Card title="Bill of materials">
        {rows.length === 0 ? <p className="text-sm text-muted">No BOM entered.</p> : (
          <Table head={["Product", "Phase", "Total qty"]}>
            {rows.map((r, i) => (
              <tr key={i} className="border-b border-border/50"><Td>{r.product_name}</Td><Td className="text-muted">{r.phase_seq ? `P${r.phase_seq}` : "auto"}</Td><Td mono>{r.total_qty}</Td></tr>
            ))}
          </Table>
        )}
      </Card>
    );
  }

  return (
    <Card title="Bill of materials · design spec (architect)"
      right={<label className="cursor-pointer text-[11px] text-accent hover:underline">Upload doc<input type="file" accept=".pdf,.docx,.txt,.csv" className="hidden" onChange={uploadDoc} /></label>}>
      <div className="space-y-2">
        {info && <p className="text-[11px] text-[#f59e0b]">{info}</p>}
        {rows.map((r, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            {r.product_id
              ? <span className="flex-1 truncate text-white/80" title={r.product_name}>{r.product_name}</span>
              : <Select value="" onChange={(e) => { const p = (products.data || []).find((x) => x.id === e.target.value); if (p) setRows(rows.map((x, j) => j === i ? { ...x, product_id: p.id, material_id: p.material_id, product_name: p.name } : x)); }}>
                  <option value="">map “{r.product_name}”…</option>
                  {(products.data || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </Select>}
            <Select value={r.phase_seq} onChange={(e) => setField(i, "phase_seq", Number(e.target.value))}>
              <option value={0}>auto</option>
              {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => <option key={n} value={n}>P{n}</option>)}
            </Select>
            <div className="w-20"><Input type="number" step="any" value={r.total_qty} onChange={(e) => setField(i, "total_qty", e.target.value)} /></div>
            <Button size="sm" variant="ghost" onClick={() => del(i)}>✕</Button>
          </div>
        ))}
        {rows.length === 0 && <p className="text-xs text-muted">Add products, or upload a BOM doc - the LLM extracts and maps it.</p>}
        <div className="flex items-center gap-2 pt-1">
          <Select value={pid} onChange={(e) => setPid(e.target.value)}>
            <option value="">select product…</option>
            {(products.data || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </Select>
          <div className="w-24"><Input type="number" step="any" placeholder="qty" value={qty} onChange={(e) => setQty(e.target.value)} /></div>
          <Button size="sm" onClick={add}>Add</Button>
        </div>
        <div className="flex items-center gap-2 pt-1">
          <Button onClick={save} disabled={busy || rows.filter((r) => r.product_id).length === 0}>Save BOM</Button>
          {err && <span className="text-xs text-red-400">{err}</span>}
        </div>
        <p className="text-[11px] text-muted">Set a phase per line (“auto” lets the hub slice it across phases). Editable until construction starts.</p>
      </div>
    </Card>
  );
}

function PhaseRow({ phase: p, busy, onComplete, onDates }) {
  const [start, setStart] = useState(p.planned_start || "");
  const [end, setEnd] = useState(p.planned_end || "");
  const [editing, setEditing] = useState(false);

  return (
    <div className="border border-border/60 bg-panel2 px-3 py-2">
      <div className="flex items-center gap-3">
        <span className="w-5 font-mono text-xs text-muted">{p.phase_seq}</span>
        <span className="flex-1 text-sm text-white/80">{PHASE_NAMES[p.phase_seq]}</span>
        <Badge tone={p.status === "done" ? "ok" : p.status === "in_progress" ? "accent" : "muted"}>{p.status}</Badge>
        <Button size="sm" variant="ghost" onClick={() => setEditing(!editing)}>{editing ? "Cancel" : "Dates"}</Button>
        {p.status === "in_progress" && <Button size="sm" onClick={onComplete} disabled={busy}>Complete</Button>}
      </div>
      <div className="mt-1 pl-8 text-[11px] text-muted">
        {p.planned_start || "no start"} to {p.planned_end || "no end"}
      </div>
      {editing && (
        <div className="mt-2 flex flex-wrap items-center gap-2 pl-8">
          <label className="text-[11px] text-muted">Start <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} /></label>
          <label className="text-[11px] text-muted">End <Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} /></label>
          <Button size="sm" onClick={() => { onDates({ start: start || null, end: end || null }); setEditing(false); }} disabled={busy}>Save</Button>
        </div>
      )}
    </div>
  );
}

function Info({ label, value }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-muted">{label}</p>
      <p className="text-white">{value}</p>
    </div>
  );
}
