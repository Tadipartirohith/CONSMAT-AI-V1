import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { site, inv, proc, PHASE_NAMES, inr } from "../api.js";
import { Card, Table, Td, Badge, Button, Input, Select, useAsync, PageSkeleton } from "../components/ui.jsx";

const TABS = ["Overview", "Bill of materials", "Phase needs"];

export default function ProjectDetail() {
  const { id } = useParams();
  const detail = useAsync(() => site.siteDetail(id), [id]);
  const notifs = useAsync(() => site.notifications(), [id]);
  const needs = useAsync(() => site.phaseNeeds(id), [id]);
  const pstock = useAsync(() => inv.productStock(), [id]);
  const [tab, setTab] = useState("Overview");
  const s = detail.data;

  if (detail.error) return <p className="text-sm text-red-400">{detail.error}</p>;
  if (!s) return <PageSkeleton stats={0} rows={8} />;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <Link to="/projects" className="text-sm text-muted hover:text-ink">Back to Projects</Link>
        <h1 className="font-head text-2xl font-extrabold text-ink">{s.label || s.code}</h1>
        <Badge tone={s.status === "completed" ? "ok" : s.status === "active" ? "accent" : "muted"}>{s.status}</Badge>
        {s.project_type && <Badge tone={s.project_type === "captive" ? "accent" : "ok"}>{s.project_type}</Badge>}
        <span className="text-[11px] text-muted">{(s.stage || "onboarded").replace(/_/g, " ")}</span>
        {s.budget != null && <span className="text-[11px] text-accent">budget {inr(s.budget)}</span>}
        <span className="text-xs text-muted">{s.code} · {s.location} · {s.area_sqft} sqft × {s.floors} floor(s) · {s.construction_type}</span>
      </div>

      <ControlTower s={s} needs={needs.data || []} stock={pstock.data || []} />

      <BoqApprovalCard s={s} onChanged={detail.reload} />

      <div className="flex gap-1 border-b border-border">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm ${tab === t ? "border-b-2 border-accent text-accent" : "text-muted hover:text-ink"}`}>{t}</button>
        ))}
      </div>

      {tab === "Overview" && <Overview s={s} notifs={notifs} />}
      {tab === "Bill of materials" && <BomTab s={s} onSaved={detail.reload} />}
      {tab === "Phase needs" && <PhaseNeedsTab s={s} />}
    </div>
  );
}

function BoqApprovalCard({ s, onChanged }) {
  const boqs = useAsync(() => site.boqs(s.id), [s.id]);
  const stock = useAsync(() => site.boqStockCheck(s.id), [s.id, s.stage]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [note, setNote] = useState("");
  const [showChange, setShowChange] = useState(false);
  const latest = (boqs.data || []).find((b) => b.source === "final");
  const shortfalls = (stock.data || []).filter((r) => r.status !== "ok");
  const act = async (fn, ok) => {
    setBusy(true); setMsg(null);
    try { await fn(); setMsg({ ok: true, text: ok }); boqs.reload(); stock.reload(); onChanged?.(); }
    catch (e) { setMsg({ ok: false, text: e.message }); } finally { setBusy(false); }
  };

  return (
    <Card title="BOQ & approval" right={<Button size="sm" variant="ghost" onClick={() => { boqs.reload(); stock.reload(); }}>Refresh</Button>}>
      {msg && <p className={`mb-2 text-xs ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>}
      {!latest ? <p className="text-sm text-muted">No final BOQ submitted yet.</p> : (
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="font-mono text-ink">{latest.code}</span>
            <Badge tone={latest.status === "approved" ? "ok" : latest.status === "submitted" ? "warn" : "muted"}>{latest.status}</Badge>
            <Badge tone={latest.spoke_approved_by ? "ok" : "muted"}>spoke {latest.spoke_approved_by ? "✓" : "…"}</Badge>
            <Badge tone={latest.hub_approved_by ? "ok" : "muted"}>hub {latest.hub_approved_by ? "✓" : "…"}</Badge>
            {latest.diff_pct != null && <span className="text-[11px] text-muted">external diff {latest.diff_pct}%</span>}
            <span className="text-[11px] text-muted">{latest.lines.length} lines</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {latest.status === "submitted" && !latest.hub_approved_by &&
              <Button size="sm" onClick={() => act(() => site.approveBoq(latest.id), "Hub approval recorded.")} disabled={busy}>Approve (hub)</Button>}
            <Button size="sm" variant="ghost" onClick={() => setShowChange(!showChange)}>{showChange ? "Cancel" : "Request change"}</Button>
          </div>
          {showChange && (
            <div className="flex gap-2">
              <Input value={note} placeholder="what should change?" onChange={(e) => setNote(e.target.value)} />
              <Button size="sm" disabled={busy || !note.trim()}
                onClick={() => { act(() => site.requestBoqChange(s.id, note), "Change requested (needs spoke + SE ack)."); setShowChange(false); setNote(""); }}>Send</Button>
            </div>
          )}
        </div>
      )}
      {latest && latest.status === "approved" && (
        <>
          <div className="mt-3">
            <p className="mb-1 text-[11px] uppercase tracking-wider text-muted">Hub stock for this BOQ</p>
            {shortfalls.length === 0 ? <p className="text-sm text-emerald-400">All BOQ products are in stock.</p> : (
              <Table head={["Product", "Required", "Available", "Status"]}>
                {shortfalls.map((r) => (
                  <tr key={r.product_id} className="border-b border-border/50">
                    <Td className="text-ink/80">{r.product_name}</Td>
                    <Td mono>{r.required}</Td>
                    <Td mono>{r.available}</Td>
                    <Td><Badge tone={r.status === "out" ? "bad" : "warn"}>{r.status === "out" ? "out of stock" : "low"}</Badge></Td>
                  </tr>
                ))}
              </Table>
            )}
          </div>
          <BudgetFinance s={s} onChanged={onChanged} />
        </>
      )}
    </Card>
  );
}

function BudgetFinance({ s, onChanged }) {
  const fin = useAsync(() => site.projectFinance(s.id), [s.id]);
  const partners = useAsync(() => site.financePartners(), []);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const issue = async () => {
    setBusy(true); setMsg(null);
    try { const r = await site.issueBudget(s.id); setMsg({ ok: true, text: `Budget issued: ${inr(r.budget)}` }); onChanged?.(); }
    catch (e) { setMsg({ ok: false, text: e.message }); } finally { setBusy(false); }
  };
  const f = fin.data;
  const partnerName = f?.partner_id ? (partners.data || []).find((p) => p.id === f.partner_id)?.name : null;
  return (
    <div className="mt-3 border-t border-border/60 pt-3">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-[11px] uppercase tracking-wider text-muted">Budget</span>
        {s.budget != null ? <span className="font-mono text-accent">{inr(s.budget)}</span> : <span className="text-muted">not issued</span>}
        <Button size="sm" variant="ghost" onClick={issue} disabled={busy}>{s.budget != null ? "Re-issue" : "Issue budget"}</Button>
        {s.project_type === "captive" && f && (
          <>
            <span className="ml-3 text-[11px] uppercase tracking-wider text-muted">Finance</span>
            <Badge tone={f.status === "approved" ? "ok" : f.status === "rejected" ? "bad" : "warn"}>{f.status.replace("_", " ")}</Badge>
            {partnerName && <span className="text-[11px] text-muted">{partnerName}</span>}
            {f.amount != null && <span className="font-mono text-[11px] text-muted">{inr(f.amount)}</span>}
          </>
        )}
      </div>
      {msg && <p className={`mt-1 text-xs ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>}
    </div>
  );
}

function ControlTower({ s, needs, stock }) {
  const phases = s.phases.slice().sort((a, b) => a.phase_seq - b.phase_seq);
  const cur = phases.find((p) => p.status === "in_progress");
  const done = phases.filter((p) => p.status === "done").length;
  const dispatched = new Set((s.dispatches || []).map((d) => d.phase_seq));
  const nextPhase = phases.find((p) => !dispatched.has(p.phase_seq) && p.status !== "done");

  let eta = null;
  if (cur?.planned_end) { const d = new Date(cur.planned_end); d.setDate(d.getDate() - 2); eta = d.toISOString().slice(0, 10); }

  const avail = Object.fromEntries((stock || []).map((x) => [x.product_id, Number(x.available)]));
  const nextNeeds = (needs.find((n) => nextPhase && n.phase_seq === nextPhase.phase_seq)?.lines) || [];
  const shortItems = nextNeeds.filter((l) => (avail[l.product_id] || 0) < l.qty);
  const covered = nextNeeds.length > 0 && shortItems.length === 0;

  // Delivery acknowledgement: fully-delivered shipments confirmed by the customer vs still awaiting.
  const delivered = (s.dispatches || []).filter((d) => d.status === "dispatched" || d.status === "received");
  const confirmed = delivered.filter((d) => d.status === "received").length;
  const awaiting = delivered.filter((d) => d.status === "dispatched").length;

  const Tile = ({ label, value, sub, tone }) => (
    <div className="border border-border bg-panel p-3">
      <p className="text-[10px] uppercase tracking-wider text-muted">{label}</p>
      <p className={`mt-0.5 font-head text-lg font-bold ${tone || "text-ink"}`}>{value}</p>
      {sub && <p className="text-[11px] text-muted">{sub}</p>}
    </div>
  );

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
      <Tile label="Current phase" value={cur ? `${cur.phase_seq}. ${PHASE_NAMES[cur.phase_seq]}` : (s.status === "completed" ? "Completed" : "Not started")} sub={cur?.planned_end ? `ends ${cur.planned_end}` : "no end date"} />
      <Tile label="Progress" value={`${done}/9 phases`} sub={`${Math.round(done / 9 * 100)}% done`} />
      <Tile label="Next shipment" value={nextPhase ? `Phase ${nextPhase.phase_seq}` : "-"} sub={nextPhase ? (eta ? `~${eta}` : "set phase dates") : "all dispatched"} tone="text-accent" />
      <Tile label="Stock for next phase" value={nextNeeds.length === 0 ? "-" : covered ? "Covered" : `${shortItems.length} short`} sub={shortItems.length ? shortItems.map((l) => l.product_name || l.material_id).join(", ") : (nextNeeds.length ? "hub has stock" : "nothing needed")} tone={nextNeeds.length === 0 ? "text-ink" : covered ? "text-emerald-400" : "text-[#f59e0b]"} />
      <Tile label="Deliveries confirmed" value={delivered.length === 0 ? "-" : `${confirmed}/${delivered.length}`} sub={awaiting > 0 ? `${awaiting} awaiting confirmation` : (delivered.length ? "all confirmed" : "none delivered")} tone={delivered.length === 0 ? "text-ink" : awaiting > 0 ? "text-[#f59e0b]" : "text-emerald-400"} />
    </div>
  );
}

function Overview({ s, notifs }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Construction phases (SE / spoke)">
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
                  <span className="font-mono text-ink">{d.code}</span>
                  <span className="text-muted">phase {d.phase_seq}</span>
                  <Badge tone={d.status === "dispatched" ? "ok" : d.status === "partial" ? "warn" : "bad"}>{d.status}</Badge>
                </div>
                <div className="flex flex-wrap gap-2">
                  {d.lines.map((l, i) => <span key={i} className={`font-mono text-xs ${l.status === "short" ? "text-red-400" : "text-ink/70"}`}>{l.product_name || l.material_id} ×{l.qty}{l.status === "short" && " (short)"}</span>)}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
      <Card title="Notifications" className="lg:col-span-2">
        {(notifs.data || []).filter((n) => n.site_id === Number(s.id)).slice(0, 8).map((n) => (
          <div key={n.id} className="border-b border-border/50 py-1.5 text-sm"><Badge tone={n.kind === "dispatched" ? "ok" : "warn"}>{n.kind}</Badge> <span className="ml-2 text-ink/80">{n.message}</span></div>
        ))}
        {(notifs.data || []).filter((n) => n.site_id === Number(s.id)).length === 0 && <p className="text-sm text-muted">No notifications.</p>}
      </Card>
    </div>
  );
}

function BomTab({ s, onSaved }) {
  const products = useAsync(() => inv.products());
  const [rows, setRows] = useState(() => s.bom_lines.map((b) => ({ product_id: b.product_id, material_id: b.material_id, product_name: b.product_name || b.material_id, phase_seq: b.phase_seq || 0, total_qty: b.total_qty })));
  const [pid, setPid] = useState("");
  const [qty, setQty] = useState("");
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  const editable = s.status === "planning" || s.status === "planned";

  // LLM
  const [prompt, setPrompt] = useState("");
  const [sug, setSug] = useState(null);
  const [llmBusy, setLlmBusy] = useState(false);
  const [extractMsg, setExtractMsg] = useState(null);

  const add = () => {
    const p = (products.data || []).find((x) => x.id === pid);
    if (!p || !qty) return;
    setRows([...rows, { product_id: p.id, material_id: p.material_id, product_name: p.name, phase_seq: 0, total_qty: Number(qty) }]);
    setPid(""); setQty("");
  };
  const save = async () => {
    setBusy(true); setMsg(null);
    try { await site.setBom(s.id, rows.filter((r) => r.product_id).map((r) => ({ material_id: r.material_id, product_id: r.product_id, product_name: r.product_name, phase_seq: Number(r.phase_seq) || 0, total_qty: Number(r.total_qty) }))); setMsg({ ok: true, text: "BOM saved." }); onSaved(); }
    catch (e) { setMsg({ ok: false, text: e.message }); } finally { setBusy(false); }
  };
  const uploadDoc = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    setBusy(true); setExtractMsg("Reading document…");
    try {
      const r = await proc.bomExtract(file);
      const extracted = (r.lines || []).map((l) => ({ product_id: l.product_id || "", material_id: l.material_id || "", product_name: l.product_name || l.raw || "", phase_seq: l.phase_seq || 0, total_qty: l.total_qty || 0, matched: l.matched }));
      setRows(extracted);
      setExtractMsg(`${r.summary} (${extracted.filter((x) => x.product_id).length}/${extracted.length} mapped - review, fix unmatched, then Save)`);
    } catch (e) { setExtractMsg(e.message); } finally { setBusy(false); e.target.value = ""; }
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
    setRows(sug.lines.map((l) => ({ product_id: l.product_id, material_id: l.material_id, product_name: l.product_name, phase_seq: l.phase_seq || 0, total_qty: l.total_qty })));
    setSug(null);
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title={editable ? "Bill of materials - enter, upload or optimize" : "Bill of materials (locked after start)"}
        right={editable && <label className="cursor-pointer text-[11px] text-accent hover:underline">Upload doc (pdf/docx)<input type="file" accept=".pdf,.docx,.txt,.csv" className="hidden" onChange={uploadDoc} /></label>}>
        {msg && <p className={`mb-2 text-xs ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>}
        {extractMsg && <p className="mb-2 text-xs text-[#f59e0b]">{extractMsg}</p>}
        <div className="space-y-2">
          {rows.map((r, i) => (
            <div key={i} className="flex items-center gap-2 text-sm">
              {r.product_id
                ? <span className="flex-1 truncate text-ink/80" title={r.product_name}>{r.product_name}</span>
                : editable
                  ? <Select value="" onChange={(e) => { const p = (products.data || []).find((x) => x.id === e.target.value); if (p) setRows(rows.map((x, j) => j === i ? { ...x, product_id: p.id, material_id: p.material_id, product_name: p.name } : x)); }}>
                      <option value="">map “{r.product_name}”…</option>
                      {(products.data || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                    </Select>
                  : <span className="flex-1 truncate text-[#f59e0b]">{r.product_name} (unmatched)</span>}
              <Select value={r.phase_seq} disabled={!editable} onChange={(e) => setRows(rows.map((x, j) => j === i ? { ...x, phase_seq: Number(e.target.value) } : x))}>
                <option value={0}>auto (all phases)</option>
                {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => <option key={n} value={n}>P{n}. {PHASE_NAMES[n]}</option>)}
              </Select>
              <div className="w-20"><Input type="number" step="any" value={r.total_qty} disabled={!editable} onChange={(e) => setRows(rows.map((x, j) => j === i ? { ...x, total_qty: e.target.value } : x))} /></div>
              {editable && <Button size="sm" variant="ghost" onClick={() => setRows(rows.filter((_, j) => j !== i))}>✕</Button>}
            </div>
          ))}
          {rows.length === 0 && <p className="text-xs text-muted">No BOM yet - add products, upload a doc, or ask the LLM.</p>}
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
              <Button onClick={save} disabled={busy || rows.filter((r) => r.product_id).length === 0}>Save BOM</Button>
              <p className="text-[11px] text-muted">Set a phase per line (or “auto” to let the weight matrix slice it across phases).</p>
            </>
          )}
        </div>
      </Card>

      <Card title="LLM optimize (you are the boss - review before applying)">
        <div className="space-y-2">
          <div className="flex gap-2">
            <Input value={prompt} placeholder="e.g. optimize for cost / use premium brands / cut cement 10%" onChange={(e) => setPrompt(e.target.value)} />
            <Button onClick={optimize} disabled={llmBusy}>{llmBusy ? "Thinking…" : "Ask LLM"}</Button>
          </div>
          {sug && (
            <div className="border border-accent/30 bg-accent/5 p-3 text-sm">
              <p className="text-ink/80">{sug.summary}</p>
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
              {editable && sug.lines?.length > 0 && <Button size="sm" className="mt-2" onClick={applySuggestion}>Apply to editor </Button>}
            </div>
          )}
          <p className="text-[11px] text-muted">The LLM only suggests. You review, edit, and Save - nothing changes until you do.</p>
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
                <span className="text-ink/80">{PHASE_NAMES[p.phase_seq]}</span>
                <Badge tone={p.status === "done" ? "ok" : p.status === "in_progress" ? "accent" : "muted"}>{p.status}</Badge>
              </div>
              {p.lines.length === 0 ? <p className="text-[11px] text-muted">nothing required this phase</p> : (
                <div className="flex flex-wrap gap-2">
                  {p.lines.map((l, i) => <span key={i} className="border border-border px-2 py-0.5 font-mono text-xs text-ink/70">{l.product_name || l.material_id} ×{l.qty}</span>)}
                </div>
              )}
            </div>
          ))}
          {(needs.data || []).length === 0 && <p className="text-sm text-muted">Enter a BOM first (Bill of materials tab).</p>}
        </div>
      )}
      <p className="mt-2 text-[11px] text-muted">To change what a phase needs, edit the BOM - the hub can optimize it with the LLM on the Bill-of-materials tab.</p>
    </Card>
  );
}
