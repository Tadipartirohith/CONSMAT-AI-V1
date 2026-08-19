import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { site, inv, proc, PHASE_NAMES, inr } from "../api.js";
import { Card, Table, Td, Badge, Button, Input, Select, useAsync } from "../components/ui.jsx";

const TABS = ["Overview", "Bill of materials", "Phase needs"];

export default function ProjectDetail() {
  const { id } = useParams();
  const detail = useAsync(() => site.siteDetail(id), [id]);
  const notifs = useAsync(() => site.notifications(), [id]);
  const [tab, setTab] = useState("Overview");
  const s = detail.data;

  if (detail.error) return <p className="text-sm text-red-400">{detail.error}</p>;
  if (!s) return <p className="text-sm text-muted">Loading…</p>;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <Link to="/projects" className="text-sm text-muted hover:text-white">← Projects</Link>
        <h1 className="font-head text-2xl font-extrabold text-white">{s.label || s.code}</h1>
        <Badge tone={s.status === "completed" ? "ok" : s.status === "active" ? "accent" : "muted"}>{s.status}</Badge>
        <span className="text-xs text-muted">{s.code} · {s.location} · {s.area_sqft} sqft × {s.floors} floor(s) · {s.construction_type}</span>
      </div>

      <div className="flex gap-1 border-b border-border">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm ${tab === t ? "border-b-2 border-accent text-accent" : "text-muted hover:text-white"}`}>{t}</button>
        ))}
      </div>

      {tab === "Overview" && <Overview s={s} notifs={notifs} />}
      {tab === "Bill of materials" && <BomTab s={s} onSaved={detail.reload} />}
      {tab === "Phase needs" && <PhaseNeedsTab s={s} />}
    </div>
  );
}

function Overview({ s, notifs }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Construction phases (CE / spoke)">
        <Table head={["#", "Phase", "Status", "Start", "End"]}>
          {s.phases.slice().sort((a, b) => a.phase_seq - b.phase_seq).map((p) => (
            <tr key={p.phase_seq} className="border-b border-border/50">
              <Td mono className="text-muted">{p.phase_seq}</Td>
              <Td>{PHASE_NAMES[p.phase_seq]}</Td>
              <Td><Badge tone={p.status === "done" ? "ok" : p.status === "in_progress" ? "accent" : "muted"}>{p.status}</Badge></Td>
              <Td className="text-muted">{p.planned_start || "-"}</Td>
              <Td className="text-muted">{p.planned_end || "-"}</Td>
            </tr>
          ))}
        </Table>
      </Card>
      <Card title="Dispatches">
        {s.dispatches.length === 0 ? <p className="text-sm text-muted">No dispatches yet.</p> : (
          <div className="space-y-2">
            {s.dispatches.slice().sort((a, b) => a.phase_seq - b.phase_seq).map((d) => (
              <div key={d.id} className="border border-border/60 bg-panel2 p-2.5 text-sm">
                <div className="mb-1 flex items-center gap-2">
                  <span className="font-mono text-white">{d.code}</span>
                  <span className="text-muted">phase {d.phase_seq}</span>
                  <Badge tone={d.status === "dispatched" ? "ok" : d.status === "partial" ? "warn" : "bad"}>{d.status}</Badge>
                </div>
                <div className="flex flex-wrap gap-2">
                  {d.lines.map((l, i) => <span key={i} className={`font-mono text-xs ${l.status === "short" ? "text-red-400" : "text-white/70"}`}>{l.product_name || l.material_id} ×{l.qty}{l.status === "short" && " (short)"}</span>)}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
      <Card title="Notifications" className="lg:col-span-2">
        {(notifs.data || []).filter((n) => n.site_id === Number(s.id)).slice(0, 8).map((n) => (
          <div key={n.id} className="border-b border-border/50 py-1.5 text-sm"><Badge tone={n.kind === "dispatched" ? "ok" : "warn"}>{n.kind}</Badge> <span className="ml-2 text-white/80">{n.message}</span></div>
        ))}
        {(notifs.data || []).filter((n) => n.site_id === Number(s.id)).length === 0 && <p className="text-sm text-muted">No notifications.</p>}
      </Card>
    </div>
  );
}

function BomTab({ s, onSaved }) {
  const products = useAsync(() => inv.products());
  const [rows, setRows] = useState(() => s.bom_lines.map((b) => ({ product_id: b.product_id, material_id: b.material_id, product_name: b.product_name || b.material_id, total_qty: b.total_qty })));
  const [pid, setPid] = useState("");
  const [qty, setQty] = useState("");
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  const editable = s.status === "planning" || s.status === "planned";

  // LLM
  const [prompt, setPrompt] = useState("");
  const [sug, setSug] = useState(null);
  const [llmBusy, setLlmBusy] = useState(false);

  const add = () => {
    const p = (products.data || []).find((x) => x.id === pid);
    if (!p || !qty) return;
    setRows([...rows, { product_id: p.id, material_id: p.material_id, product_name: p.name, total_qty: Number(qty) }]);
    setPid(""); setQty("");
  };
  const save = async () => {
    setBusy(true); setMsg(null);
    try { await site.setBom(s.id, rows.map((r) => ({ material_id: r.material_id, product_id: r.product_id, product_name: r.product_name, total_qty: Number(r.total_qty) }))); setMsg({ ok: true, text: "BOM saved." }); onSaved(); }
    catch (e) { setMsg({ ok: false, text: e.message }); } finally { setBusy(false); }
  };
  const optimize = async () => {
    setLlmBusy(true); setSug(null);
    try {
      const catalog = (products.data || []).map((p) => ({ id: p.id, name: p.name, brand: p.brand, material_id: p.material_id, grade: p.grade }));
      const r = await proc.bomOptimize({ prompt, current_bom: rows, catalog });
      setSug(r);
    } catch (e) { setMsg({ ok: false, text: e.message }); } finally { setLlmBusy(false); }
  };
  const applySuggestion = () => {
    if (!sug?.lines) return;
    setRows(sug.lines.map((l) => ({ product_id: l.product_id, material_id: l.material_id, product_name: l.product_name, total_qty: l.total_qty })));
    setSug(null);
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title={editable ? "Bill of materials (hub can edit)" : "Bill of materials (locked after start)"}>
        {msg && <p className={`mb-2 text-xs ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>}
        <div className="space-y-2">
          {rows.map((r, i) => (
            <div key={i} className="flex items-center gap-2 text-sm">
              <span className="flex-1 truncate text-white/80" title={r.product_name}>{r.product_name}</span>
              <div className="w-24"><Input type="number" step="any" value={r.total_qty} disabled={!editable} onChange={(e) => setRows(rows.map((x, j) => j === i ? { ...x, total_qty: e.target.value } : x))} /></div>
              {editable && <Button size="sm" variant="ghost" onClick={() => setRows(rows.filter((_, j) => j !== i))}>✕</Button>}
            </div>
          ))}
          {rows.length === 0 && <p className="text-xs text-muted">No BOM yet.</p>}
          {editable && (
            <>
              <div className="flex items-center gap-2 pt-1">
                <Select value={pid} onChange={(e) => setPid(e.target.value)}>
                  <option value="">select product…</option>
                  {(products.data || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </Select>
                <div className="w-24"><Input type="number" step="any" placeholder="qty" value={qty} onChange={(e) => setQty(e.target.value)} /></div>
                <Button size="sm" onClick={add}>Add</Button>
              </div>
              <Button onClick={save} disabled={busy || rows.length === 0}>Save BOM</Button>
            </>
          )}
        </div>
      </Card>

      <Card title="LLM optimize (you are the boss — review before applying)">
        <div className="space-y-2">
          <div className="flex gap-2">
            <Input value={prompt} placeholder="e.g. optimize for cost / use premium brands / cut cement 10%" onChange={(e) => setPrompt(e.target.value)} />
            <Button onClick={optimize} disabled={llmBusy}>{llmBusy ? "Thinking…" : "Ask LLM"}</Button>
          </div>
          {sug && (
            <div className="border border-accent/30 bg-accent/5 p-3 text-sm">
              <p className="text-white/80">{sug.summary}</p>
              {sug.lines?.length > 0 && (
                <Table head={["Product", "Qty", "Why"]}>
                  {sug.lines.map((l, i) => (
                    <tr key={i} className="border-b border-border/50">
                      <Td>{l.product_name}</Td>
                      <Td mono>{l.total_qty}</Td>
                      <Td className="text-muted">{l.reason}</Td>
                    </tr>
                  ))}
                </Table>
              )}
              {editable && sug.lines?.length > 0 && <Button size="sm" className="mt-2" onClick={applySuggestion}>Apply to editor →</Button>}
            </div>
          )}
          <p className="text-[11px] text-muted">The LLM only suggests. You review, edit, and Save — nothing changes until you do.</p>
        </div>
      </Card>
    </div>
  );
}

function PhaseNeedsTab({ s }) {
  const needs = useAsync(() => site.phaseNeeds(s.id), [s.id]);
  return (
    <Card title="What each phase needs (BOM sliced across the 9 phases)">
      {needs.error ? <p className="text-sm text-red-400">{needs.error}</p> : (
        <div className="space-y-2">
          {(needs.data || []).map((p) => (
            <div key={p.phase_seq} className="border border-border/60 bg-panel2 p-2.5">
              <div className="mb-1 flex items-center gap-2 text-sm">
                <span className="font-mono text-muted">{p.phase_seq}</span>
                <span className="text-white/80">{PHASE_NAMES[p.phase_seq]}</span>
                <Badge tone={p.status === "done" ? "ok" : p.status === "in_progress" ? "accent" : "muted"}>{p.status}</Badge>
              </div>
              {p.lines.length === 0 ? <p className="text-[11px] text-muted">nothing required this phase</p> : (
                <div className="flex flex-wrap gap-2">
                  {p.lines.map((l, i) => <span key={i} className="border border-border px-2 py-0.5 font-mono text-xs text-white/70">{l.product_name || l.material_id} ×{l.qty}</span>)}
                </div>
              )}
            </div>
          ))}
          {(needs.data || []).length === 0 && <p className="text-sm text-muted">Enter a BOM first (Bill of materials tab).</p>}
        </div>
      )}
      <p className="mt-2 text-[11px] text-muted">To change what a phase needs, edit the BOM — the hub can optimize it with the LLM on the Bill-of-materials tab.</p>
    </Card>
  );
}
