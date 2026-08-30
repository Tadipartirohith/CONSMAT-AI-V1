import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { site, inv, proc, PHASE_NAMES, inr } from "../api.js";
import { Card, Table, Td, Badge, Button, Input, Select, useAsync, PageSkeleton } from "../components/ui.jsx";
import { getUser } from "../auth.js";
import { ArrowLeft, Compass, HardHat, Handshake, File, CheckCircle, Warning, X, Sparkle } from "@phosphor-icons/react";

// What each field role owns on a site. The architect is the design authority: the Bill of Materials
// (which products and how much) and the phase schedule come from the architect's drawings; the site
// engineer executes the build phase by phase; the spokesperson owns the customer relationship.
const ROLE_TASK = {
  architect: { icon: Compass, title: "Architect - design spec", text: "Enter and refine this site's Bill of Materials (products & quantities) from the drawings, and set each phase's planned dates. This is your design output; it stays editable until construction starts." },
  site_engineer: { icon: HardHat, title: "Site engineer - execution", text: "Run the build: start the site, complete phases in order (the hub auto-dispatches the next phase's materials), and confirm each delivery when it reaches site." },
  spokesperson: { icon: Handshake, title: "Spokesperson - coverage", text: "Own the customer relationship and coverage. Review and approve site-engineer phase-date changes; keep the plan and schedule aligned with the hub." },
};

function RoleGuide() {
  const role = getUser()?.role;
  const t = ROLE_TASK[role];
  if (!t) return null;
  const Icon = t.icon;
  return (
    <div className="flex items-start gap-3 rounded-xl border border-accent/25 bg-accent/[0.06] px-4 py-3">
      <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-accent/15 text-accent"><Icon size={18} weight="fill" /></div>
      <div>
        <p className="text-xs font-semibold text-accent">{t.title}</p>
        <p className="mt-0.5 text-[11px] leading-relaxed text-ink/70">{t.text}</p>
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

  if (detail.error) return <p className="text-sm text-red-300">{detail.error}</p>;
  if (!s) return <PageSkeleton stats={0} rows={8} />;

  const planned = s.bom_lines.length > 0;
  const editable = s.status === "planning" || s.status === "planned";
  const phase1 = s.phases.find((p) => p.phase_seq === 1);
  const notStarted = planned && phase1 && phase1.status === "pending";
  const hasShorts = s.dispatches.some((d) => d.lines.some((l) => l.status === "short"));
  const pending = (changes.data || []).filter((c) => c.status === "pending");

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <Link to="/sites" className="flex items-center gap-1 text-sm text-muted transition-colors hover:text-ink"><ArrowLeft size={15} />Sites</Link>
        <h1 className="font-head text-2xl font-extrabold text-ink">{s.code}</h1>
        <Badge tone={s.status === "completed" ? "ok" : s.status === "active" ? "accent" : "muted"}>{s.status}</Badge>
        {s.project_type && <Badge tone={s.project_type === "captive" ? "accent" : "ok"}>{s.project_type}</Badge>}
        <span className="text-[11px] capitalize text-muted">{(s.stage || "onboarded").replace(/_/g, " ")}</span>
        <div className="ml-auto flex items-center gap-2">
          {!s.project_type && (
            <Select value="" onChange={(e) => e.target.value && act(() => site.updateSite(id, { project_type: e.target.value }), "Project type set")}>
              <option value="">set project type...</option>
              <option value="captive">captive</option>
              <option value="client">client</option>
            </Select>
          )}
          {notStarted && <Button onClick={() => act(() => site.start(id), "Started")} disabled={busy}>Start construction</Button>}
        </div>
      </div>
      {msg && <div className={`rounded-xl px-4 py-2.5 text-sm ${msg.ok ? "bg-emerald-500/10 text-emerald-300" : "bg-red-500/10 text-red-300"}`}>{msg.text}</div>}

      <RoleGuide />

      <div className="grid grid-cols-2 gap-4 rounded-2xl bg-panel nm-raised p-5 text-sm md:grid-cols-4">
        <Info label="Label" value={s.label || "-"} />
        <Info label="Location" value={s.location || "-"} />
        <Info label="Area" value={`${s.area_sqft} sqft x ${s.floors} floor(s)`} />
        <Info label="Type" value={s.construction_type} />
      </div>

      <DesignFilesCard siteId={id} />

      <BoqStatusCard siteId={id} onMsg={setMsg} reload={reloadAll} />

      {pending.length > 0 && (
        <Card title="Phase date changes awaiting your approval">
          {pending.map((c) => (
            <div key={c.id} className="flex flex-wrap items-center gap-3 border-b border-border/50 py-2 text-sm last:border-0">
              <span className="text-ink/80">Phase {c.phase_seq} ({PHASE_NAMES[c.phase_seq]}): end {c.old_end || "?"} to <b className="text-ink">{c.new_end}</b></span>
              {c.escalated && <Badge tone="bad">escalated, needs hub</Badge>}
              {c.remarks && <span className="text-[11px] text-[#fbbf24]">"{c.remarks}"</span>}
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
          <div className="space-y-2">
            {s.phases.slice().sort((a, b) => a.phase_seq - b.phase_seq).map((p) => (
              <PhaseRow key={p.phase_seq} siteId={id} phase={p} busy={busy}
                onComplete={() => act(() => site.completePhase(id, p.phase_seq), `Phase ${p.phase_seq} completed`)}
                onDates={(b) => act(() => site.setPhaseDates(id, p.phase_seq, b), `Phase ${p.phase_seq} dates`)} />
            ))}
          </div>
          <p className="mt-3 text-[11px] leading-relaxed text-muted">A site engineer's change to a phase end date needs spoke or manager approval. The hub auto-dispatches the next phase about a day before the current one ends.</p>
        </Card>
      </div>

      <Card title="Dispatches (hub to site)"
        right={hasShorts && <Button size="sm" onClick={() => act(() => site.backfill(id), "Backfill")} disabled={busy}>Backfill shortfalls</Button>}>
        {s.dispatches.length === 0 ? <p className="text-sm text-muted">No dispatches yet.</p> : (
          <div className="space-y-2.5">
            {s.dispatches.slice().sort((a, b) => a.phase_seq - b.phase_seq).map((d) => (
              <div key={d.id} className="rounded-xl border border-border/40 bg-panel2 p-3.5">
                <div className="mb-2 flex flex-wrap items-center gap-2 text-sm">
                  <span className="font-mono text-ink">{d.code}</span>
                  <span className="text-muted">phase {d.phase_seq}, {PHASE_NAMES[d.phase_seq]}</span>
                  <Badge tone={d.status === "received" ? "accent" : d.status === "dispatched" ? "ok" : d.status === "partial" ? "warn" : "bad"}>{d.status}</Badge>
                  {d.status === "dispatched" && <Button size="sm" onClick={() => act(() => site.confirmDelivery(d.id), "Delivery confirmed")} disabled={busy}>Confirm delivery</Button>}
                  {d.status === "received" && <span className="flex items-center gap-1 text-[11px] text-accent"><CheckCircle size={13} weight="fill" />confirmed</span>}
                </div>
                <div className="flex flex-wrap gap-x-3 gap-y-1">
                  {d.lines.map((l, i) => (
                    <span key={i} className={`font-mono text-xs ${l.status === "short" ? "text-red-300" : "text-ink/70"}`}>
                      {l.product_name || l.material_id} x{l.qty}{l.status === "short" && " (short)"}
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
          <div key={n.id} className="flex items-center gap-2 border-b border-border/50 py-2 text-sm last:border-0">
            <Badge tone={n.kind === "dispatched" ? "ok" : "warn"}>{n.kind}</Badge>
            <span className="text-ink/80">{n.message}</span>
          </div>
        ))}
        {(notifs.data || []).filter((n) => n.site_id === Number(id)).length === 0 && <p className="text-sm text-muted">No notifications for this site yet.</p>}
      </Card>
    </div>
  );
}

function BoqStatusCard({ siteId, onMsg, reload }) {
  const boqs = useAsync(() => site.boqs(siteId), [siteId]);
  const changes = useAsync(() => site.boqChanges(siteId), [siteId]);
  const [busy, setBusy] = useState(false);
  const latest = (boqs.data || []).find((b) => b.source === "final");
  const pendingChanges = (changes.data || []).filter((c) => c.status === "pending");
  const ack = async (cid) => {
    setBusy(true);
    try { await site.ackBoqChange(cid); changes.reload(); boqs.reload(); reload?.(); }
    catch (e) { onMsg?.({ ok: false, text: e.message }); } finally { setBusy(false); }
  };
  if (!latest && pendingChanges.length === 0) return null;
  return (
    <Card title="BOQ status" right={<Button size="sm" variant="ghost" onClick={() => { boqs.reload(); changes.reload(); }}>Refresh</Button>}>
      {latest ? (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="font-mono text-ink">{latest.code}</span>
          <Badge tone={latest.status === "approved" ? "ok" : latest.status === "submitted" ? "warn" : "muted"}>{latest.status}</Badge>
          <Badge tone={latest.spoke_approved_by ? "ok" : "muted"}>spoke {latest.spoke_approved_by ? "ok" : "pending"}</Badge>
          <Badge tone={latest.hub_approved_by ? "ok" : "muted"}>hub {latest.hub_approved_by ? "ok" : "pending"}</Badge>
          {latest.diff_pct != null && <span className="text-[11px] text-muted">external diff {latest.diff_pct}%</span>}
        </div>
      ) : <p className="text-sm text-muted">No final BOQ submitted yet.</p>}
      {pendingChanges.length > 0 && (
        <div className="mt-3 space-y-1.5">
          <p className="text-[11px] uppercase tracking-wider text-[#fbbf24]">Hub change requests (need spoke + SE acknowledgement)</p>
          {pendingChanges.map((c) => (
            <div key={c.id} className="flex flex-wrap items-center gap-2 rounded-xl border border-[#f59e0b]/30 bg-panel2 px-3 py-2 text-sm">
              <span className="flex-1 text-ink/80">{c.note}</span>
              <Badge tone={c.spoke_acked ? "ok" : "muted"}>spoke</Badge>
              <Badge tone={c.ce_acked ? "ok" : "muted"}>SE</Badge>
              <Button size="sm" onClick={() => ack(c.id)} disabled={busy}>Acknowledge</Button>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function DesignFilesCard({ siteId }) {
  const docs = useAsync(() => site.documents(siteId, "design"), [siteId]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const canUpload = ["architect", "admin"].includes(getUser()?.role);   // design is the architect's
  const upload = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    setBusy(true); setErr(null);
    try { await site.uploadDocument(siteId, file, "design"); docs.reload(); }
    catch (e) { setErr(e.message); } finally { setBusy(false); e.target.value = ""; }
  };
  return (
    <Card title="Design files (architect)" right={canUpload &&
      <label className="cursor-pointer text-[11px] text-accent hover:underline">
        {busy ? "Uploading..." : "Upload design"}
        <input type="file" className="hidden" onChange={upload} accept=".pdf,.dwg,.dxf,.png,.jpg,.jpeg,.zip" />
      </label>}>
      {err && <p className="mb-1 text-xs text-red-300">{err}</p>}
      {(docs.data || []).length === 0 ? (
        <p className="text-sm text-muted">{canUpload ? "No design uploaded yet. Upload the CAD/design here; the SE builds the BOQ from it." : "No design uploaded yet. The architect uploads it here; you can view and download it to build the BOQ."}</p>
      ) : (
        <div className="space-y-1.5">
          {(docs.data || []).map((d) => (
            <div key={d.id} className="flex items-center gap-2.5 rounded-xl bg-panel2 px-3 py-2 text-sm">
              <File size={17} className="text-accent" weight="fill" />
              <button onClick={() => site.downloadDocument(d.id, d.filename)} className="text-accent hover:underline">{d.filename}</button>
              <span className="ml-auto text-[11px] text-muted">{(d.size / 1024).toFixed(0)} KB, {d.uploaded_by || d.uploaded_by_role}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
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
  const [cmp, setCmp] = useState(null);
  const [sugg, setSugg] = useState(null);
  const [reqMsg, setReqMsg] = useState(null);

  const orderMarket = async (mid, offer) => {
    setReqMsg(null);
    try {
      const qty = cleanRows().filter((r) => r.material_id === mid).reduce((t, r) => t + Number(r.total_qty || 0), 0) || 1;
      const r = await proc.createOrderRequest({
        site_ref: `SITE-${siteId}`, note: `BOQ open-market alternative for ${mid}`,
        lines: [{ product_id: "", product_name: offer.product || mid, material_id: mid, source: "market", note: offer.seller || "", qty }],
      });
      setReqMsg({ ok: true, text: `Request ${r.code} sent to procurement for "${offer.product || mid}". The hub will price and order it.` });
    } catch (e) { setReqMsg({ ok: false, text: e.message }); }
  };

  const add = () => {
    const p = (products.data || []).find((x) => x.id === pid);
    if (!p || !qty) return;
    setRows([...rows, { product_id: p.id, material_id: p.material_id, product_name: p.name, phase_seq: 0, total_qty: Number(qty) }]);
    setPid(""); setQty("");
  };
  const del = (i) => setRows(rows.filter((_, j) => j !== i));
  const setField = (i, k, v) => setRows(rows.map((x, j) => j === i ? { ...x, [k]: v } : x));
  const cleanRows = () => rows.filter((r) => r.product_id).map((r) => ({ material_id: r.material_id, product_id: r.product_id, product_name: r.product_name, phase_seq: Number(r.phase_seq) || 0, total_qty: Number(r.total_qty) }));
  const submit = async () => {
    setBusy(true); setErr(null);
    try { const r = await site.submitBoq(siteId, cleanRows()); setCmp(r); setInfo(null); }
    catch (e) { setErr(e.message); } finally { setBusy(false); }
  };
  const submitFinal = async () => {
    setBusy(true); setErr(null);
    try { await site.submitFinalBoq(siteId, cleanRows()); setCmp(null); onSaved("Final BOQ submitted for spoke + hub approval."); }
    catch (e) { setErr(e.message); } finally { setBusy(false); }
  };
  const findAlternatives = async () => {
    setBusy(true); setErr(null); setSugg(null);
    try {
      const catalog = (products.data || []).map((p) => ({ id: p.id, name: p.name, brand: p.brand, material_id: p.material_id, grade: p.grade }));
      const current_bom = cleanRows().map((r) => ({ product_id: r.product_id, product_name: r.product_name, material_id: r.material_id, total_qty: r.total_qty }));
      const r = await proc.bomOptimize({ prompt: "Suggest cheaper or better alternative branded products for these BOM lines. Keep each material's quantity close to the current BOM.", current_bom, catalog });
      setSugg(r);
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };
  const applySuggestions = () => {
    if (!sugg?.lines?.length) return;
    setRows(sugg.lines.map((l) => ({ product_id: l.product_id || "", material_id: l.material_id || "", product_name: l.product_name || "", phase_seq: 0, total_qty: l.total_qty || 0 })));
    setSugg(null);
  };
  const uploadDoc = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    setBusy(true); setInfo("Reading document..."); setErr(null);
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
    <Card title="Bill of Quantities (BOQ)"
      right={<label className="cursor-pointer text-[11px] text-accent hover:underline">Upload doc<input type="file" accept=".pdf,.docx,.txt,.csv" className="hidden" onChange={uploadDoc} /></label>}>
      <div className="space-y-2">
        {info && <p className="text-[11px] text-[#fbbf24]">{info}</p>}
        {rows.map((r, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            {r.product_id
              ? <span className="flex-1 truncate text-ink/80" title={r.product_name}>{r.product_name}</span>
              : <Select value="" onChange={(e) => { const p = (products.data || []).find((x) => x.id === e.target.value); if (p) setRows(rows.map((x, j) => j === i ? { ...x, product_id: p.id, material_id: p.material_id, product_name: p.name } : x)); }}>
                  <option value="">map "{r.product_name}"...</option>
                  {(products.data || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </Select>}
            <Select value={r.phase_seq} onChange={(e) => setField(i, "phase_seq", Number(e.target.value))}>
              <option value={0}>auto</option>
              {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => <option key={n} value={n}>P{n}</option>)}
            </Select>
            <div className="w-20"><Input type="number" step="any" value={r.total_qty} onChange={(e) => setField(i, "total_qty", e.target.value)} /></div>
            <button onClick={() => del(i)} className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-muted transition-colors hover:text-red-300"><X size={15} /></button>
          </div>
        ))}
        {rows.length === 0 && <p className="text-xs text-muted">Add products, or upload a BOM doc; the LLM extracts and maps it.</p>}
        <div className="flex items-center gap-2 pt-1">
          <Select value={pid} onChange={(e) => setPid(e.target.value)}>
            <option value="">select product...</option>
            {(products.data || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </Select>
          <div className="w-24"><Input type="number" step="any" placeholder="qty" value={qty} onChange={(e) => setQty(e.target.value)} /></div>
          <Button size="sm" onClick={add}>Add</Button>
        </div>
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <Button onClick={submit} disabled={busy || cleanRows().length === 0}>Submit BOQ &amp; compare</Button>
          <Button variant="ghost" onClick={submitFinal} disabled={busy || cleanRows().length === 0}>Submit as final BOQ</Button>
          <Button variant="ghost" onClick={findAlternatives} disabled={busy || cleanRows().length === 0}><Sparkle size={14} weight="fill" />Find alternatives</Button>
          {err && <span className="text-xs text-red-300">{err}</span>}
        </div>
        {sugg && <SuggestPanel sugg={sugg} onApply={applySuggestions} onClose={() => setSugg(null)} onOrderMarket={orderMarket} reqMsg={reqMsg} />}
        {cmp && <ComparePanel cmp={cmp} onFinal={submitFinal} busy={busy} />}
        <p className="text-[11px] leading-relaxed text-muted">The SE builds the BOQ from the architect's design. Submitting compares it against the external app's BOQ; a difference over 5% needs a reconciled final BOQ. The final BOQ needs spoke + hub approval.</p>
      </div>
    </Card>
  );
}

function SuggestPanel({ sugg, onApply, onClose, onOrderMarket, reqMsg }) {
  return (
    <div className="mt-2 rounded-xl border border-accent/25 bg-accent/[0.06] p-3.5">
      <div className="mb-1.5 flex items-center justify-between">
        <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-accent"><Sparkle size={13} weight="fill" />AI alternatives</p>
        <button onClick={onClose} className="text-[11px] text-muted hover:text-ink">dismiss</button>
      </div>
      {sugg.summary && <p className="mb-2 text-sm text-ink/80">{sugg.summary}</p>}
      {reqMsg && <p className={`mb-2 text-xs ${reqMsg.ok ? "text-emerald-300" : "text-red-300"}`}>{reqMsg.text}</p>}
      {(sugg.lines || []).length > 0 && (
        <>
          <p className="mb-1 text-[10px] uppercase tracking-wider text-muted">In-catalog alternatives (hub selling price)</p>
          <div className="max-h-44 overflow-auto">
            <Table head={["Suggested product", "Qty", "Hub price", "Why"]}>
              {sugg.lines.map((l, i) => (
                <tr key={i} className="border-b border-border/50">
                  <Td className="text-ink/80">{l.product_name || l.product_id}</Td>
                  <Td mono>{l.total_qty}</Td>
                  <Td mono className="text-ink/90">{l.hub_price != null ? inr(l.hub_price) : "-"}</Td>
                  <Td className="text-[11px] text-muted">{l.reason || "-"}</Td>
                </tr>
              ))}
            </Table>
          </div>
          <div className="mt-2"><Button size="sm" onClick={onApply}>Apply to BOQ</Button></div>
        </>
      )}
      {sugg.market && Object.keys(sugg.market).length > 0 && (
        <div className="mt-3 border-t border-border/60 pt-2">
          <p className="mb-1 text-[10px] uppercase tracking-wider text-muted">Open-market finds</p>
          <p className="mb-1.5 text-[11px] text-muted">Market prices are set by the hub. Request one and the procurement supervisor prices and orders it into your BOQ.</p>
          {Object.entries(sugg.market).map(([mid, offers]) => (
            <div key={mid} className="mb-2">
              <p className="mb-1 text-[11px] text-ink/60">{mid}</p>
              <div className="space-y-1">
                {offers.map((o, i) => (
                  <div key={i} className="flex items-center justify-between gap-2 rounded-lg bg-panel2 px-2.5 py-1.5 text-xs">
                    <span className="min-w-0 flex-1 truncate text-ink/80">{o.product}{o.seller ? ` - ${o.seller}` : ""}</span>
                    {o.price != null
                      ? <span className="shrink-0 font-mono text-ink/70">{inr(o.price)}</span>
                      : <Button size="sm" variant="ghost" onClick={() => onOrderMarket(mid, o)}>Request / order</Button>}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
      {(sugg.lines || []).length === 0 && (!sugg.market || Object.keys(sugg.market).length === 0) && (
        <p className="text-xs text-muted">No alternatives found for these items.</p>
      )}
    </div>
  );
}

function ComparePanel({ cmp, onFinal, busy }) {
  const extMap = Object.fromEntries((cmp.external || []).map((l) => [l.product_id || l.material_id, l.total_qty]));
  const over = cmp.needs_final;
  return (
    <div className={`mt-2 rounded-xl border p-3.5 ${over ? "border-red-500/40 bg-red-500/[0.07]" : "border-emerald-500/30 bg-emerald-500/[0.07]"}`}>
      <p className={`flex items-start gap-1.5 text-sm font-semibold ${over ? "text-red-300" : "text-emerald-300"}`}>
        {over ? <Warning size={16} weight="fill" className="mt-0.5 shrink-0" /> : <CheckCircle size={16} weight="fill" className="mt-0.5 shrink-0" />}
        {over ? `SE vs external BOQ differ by ${cmp.diff_pct}% (over ${cmp.threshold}%). Reconcile the quantities, then submit the final BOQ.`
              : `SE and external BOQ agree within ${cmp.threshold}% (max ${cmp.diff_pct}%). You can submit the final BOQ.`}
      </p>
      <p className="mb-1 mt-2 text-[10px] uppercase tracking-wider text-muted">SE vs external ({cmp.external_provider})</p>
      <div className="max-h-40 overflow-auto">
        <Table head={["Product", "SE qty", "External qty", "Diff %"]}>
          {(cmp.ce_lines || []).map((l, i) => {
            const key = l.product_id || l.material_id;
            const ce = Number(l.total_qty), ext = Number(extMap[key] ?? 0);
            const d = Math.max(ce, ext) ? Math.abs(ce - ext) / Math.max(ce, ext) * 100 : 0;
            return (
              <tr key={i} className="border-b border-border/50">
                <Td className="text-ink/80">{l.product_name || key}</Td>
                <Td mono>{ce}</Td>
                <Td mono>{ext}</Td>
                <Td mono className={d > cmp.threshold ? "text-red-300" : "text-muted"}>{d.toFixed(1)}%</Td>
              </tr>
            );
          })}
        </Table>
      </div>
      <div className="mt-2"><Button size="sm" onClick={onFinal} disabled={busy}>Submit final BOQ</Button></div>
    </div>
  );
}

function PhaseRow({ phase: p, busy, onComplete, onDates }) {
  const [start, setStart] = useState(p.planned_start || "");
  const [end, setEnd] = useState(p.planned_end || "");
  const [remarks, setRemarks] = useState("");
  const [editing, setEditing] = useState(false);

  return (
    <div className="rounded-xl border border-border/40 bg-panel2 px-3.5 py-2.5">
      <div className="flex items-center gap-3">
        <span className="grid h-6 w-6 shrink-0 place-items-center rounded-lg bg-bg font-mono text-[11px] text-muted">{p.phase_seq}</span>
        <span className="flex-1 text-sm text-ink/85">{PHASE_NAMES[p.phase_seq]}</span>
        <Badge tone={p.status === "done" ? "ok" : p.status === "in_progress" ? "accent" : "muted"}>{p.status.replace("_", " ")}</Badge>
        <Button size="sm" variant="ghost" onClick={() => setEditing(!editing)}>{editing ? "Cancel" : "Dates"}</Button>
        {p.status === "in_progress" && <Button size="sm" onClick={onComplete} disabled={busy}>Complete</Button>}
      </div>
      <div className="mt-1 pl-9 text-[11px] text-muted">
        {p.planned_start || "no start"} to {p.planned_end || "no end"}
      </div>
      {editing && (
        <div className="mt-2 flex flex-wrap items-center gap-2 pl-9">
          <label className="text-[11px] text-muted">Start <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} /></label>
          <label className="text-[11px] text-muted">End <Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} /></label>
          <Input value={remarks} placeholder="remarks (needed if compressing to under 1 week)" onChange={(e) => setRemarks(e.target.value)} />
          <Button size="sm" onClick={() => { onDates({ start: start || null, end: end || null, remarks }); setEditing(false); }} disabled={busy}>Save</Button>
        </div>
      )}
    </div>
  );
}

function Info({ label, value }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-muted">{label}</p>
      <p className="mt-0.5 text-ink">{value}</p>
    </div>
  );
}
