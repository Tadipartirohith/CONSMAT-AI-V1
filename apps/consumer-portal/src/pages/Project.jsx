import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { site, price, pay, progressOf, PHASE_NAMES, inr } from "../api.js";
import { Card, Badge, Progress, useAsync } from "../components/ui.jsx";

const EVENT = {
  started: { icon: "🏗️" }, dispatched: { icon: "🚚" }, phase_done: { icon: "✅" },
  project_done: { icon: "🎉" }, received: { icon: "📦" },
};

export default function Project({ me }) {
  const { id } = useParams();
  const detail = useAsync(() => site.siteDetail(id), [id]);
  const events = useAsync(() => (me ? site.notifications(me) : Promise.resolve([])), [me]);
  const s = detail.data;

  if (detail.error) return <p className="text-sm text-red-400">{detail.error}</p>;
  if (!s) return <p className="text-sm text-muted">Loading…</p>;
  if (me && s.consumer_id !== me) {
    return <p className="text-sm text-muted">This project belongs to another account.</p>;
  }

  const pr = progressOf(s);
  const phases = [...s.phases].sort((a, b) => a.phase_seq - b.phase_seq);
  const dispatchByPhase = {};
  for (const d of s.dispatches) dispatchByPhase[d.phase_seq] = d;

  // Next material delivery (ETA) - the hub pre-dispatches ~2 days before the current phase ends.
  const fmt = (d) => d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  const dispatchedSeqs = new Set(s.dispatches.map((x) => x.phase_seq));
  const cur = phases.find((p) => p.status === "in_progress");
  const nextPhase = phases.find((p) => !dispatchedSeqs.has(p.phase_seq) && p.status !== "done");
  let etaDate = null;
  if (cur?.planned_end) { const d = new Date(cur.planned_end); d.setDate(d.getDate() - 2); etaDate = d; }
  const nextDelivery = s.status === "completed" ? "All deliveries completed 🎉"
    : !cur ? "Deliveries begin once construction starts."
      : nextPhase ? `${PHASE_NAMES[nextPhase.phase_seq]} materials${etaDate ? ` - expected around ${fmt(etaDate)}` : " - date being scheduled"}`
        : "All materials for the current plan are on their way.";

  return (
    <div className="space-y-5">
      <Link to="/" className="text-sm text-muted hover:text-ink">Back to My projects</Link>

      <div className="border border-border bg-panel p-5">
        <div className="flex items-center justify-between">
          <h1 className="font-head text-2xl font-extrabold text-ink">{s.label || s.code}</h1>
          <Badge tone={s.status === "completed" ? "ok" : s.status === "active" ? "accent" : "muted"}>{s.status}</Badge>
        </div>
        <p className="mt-1 text-sm text-muted">{s.location} · {s.area_sqft} sqft · {s.floors} floor(s) · {s.construction_type}</p>
        <div className="mt-4">
          <div className="mb-1 flex justify-between text-sm">
            <span className="text-ink">{pr.currentSeq ? `Currently in Phase ${pr.currentSeq} of ${pr.total}: ${PHASE_NAMES[pr.currentSeq]}` : s.status === "completed" ? "Project complete 🎉" : "Awaiting start"}</span>
            <span className="font-mono text-accent">{pr.done}/{pr.total} phases · {pr.pct}%</span>
          </div>
          <Progress pct={pr.pct} />
        </div>
        <div className="mt-4 flex items-center gap-2 rounded border border-accent/30 bg-accent/5 px-3 py-2 text-sm">
          <span className="text-lg">🚚</span>
          <span className="text-[10px] uppercase tracking-wider text-accent">Next delivery</span>
          <span className="text-ink/90">{nextDelivery}</span>
        </div>
      </div>

      <BuildingPlans siteId={id} />

      {s.bom_lines.length > 0 && <PayPanel site={s} me={me} />}

      <UpdatesFeed events={events} siteId={Number(id)} me={me} />

      <Card title="Construction timeline">
        <ol className="space-y-2">
          {phases.map((p) => {
            const d = dispatchByPhase[p.phase_seq];
            const delivered = d?.lines.filter((l) => l.status !== "short").map((l) => l.product_name || l.material_id) || [];
            const awaiting = d?.lines.filter((l) => l.status === "short").map((l) => l.product_name || l.material_id) || [];
            const dot = p.status === "done" ? "bg-accent" : p.status === "in_progress" ? "bg-[#f59e0b] animate-pulse" : "bg-border";
            return (
              <li key={p.phase_seq} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <span className={`mt-1.5 h-3 w-3 rounded-full ${dot}`} />
                  {p.phase_seq < 9 && <span className="w-px flex-1 bg-border" />}
                </div>
                <div className="flex-1 pb-3">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm ${p.status === "pending" ? "text-muted" : "text-ink"}`}>
                      {p.phase_seq}. {PHASE_NAMES[p.phase_seq]}
                    </span>
                    <Badge tone={p.status === "done" ? "ok" : p.status === "in_progress" ? "warn" : "muted"}>{p.status.replace("_", " ")}</Badge>
                  </div>
                  {(p.planned_start || p.planned_end) && <p className="mt-0.5 text-[11px] text-muted">Scheduled: {p.planned_start || "?"} to {p.planned_end || "?"}</p>}
                  {delivered.length > 0 && <p className="mt-0.5 text-xs text-emerald-400">✓ Materials delivered: {delivered.join(", ")}</p>}
                  {awaiting.length > 0 && <p className="mt-0.5 text-xs text-[#f59e0b]">⏳ Awaiting stock: {awaiting.join(", ")}</p>}
                  {nextPhase && p.phase_seq === nextPhase.phase_seq && delivered.length === 0 && (
                    <p className="mt-0.5 text-xs text-accent">🚚 Materials expected {etaDate ? `around ${fmt(etaDate)}` : "soon"}</p>
                  )}
                  {d && d.status === "received" && <p className="mt-0.5 text-xs text-emerald-400">📦 Delivered &amp; confirmed{d.received_at ? ` · ${fmt(new Date(d.received_at))}` : ""}</p>}
                </div>
              </li>
            );
          })}
        </ol>
      </Card>
    </div>
  );
}

function BuildingPlans({ siteId }) {
  const docs = useAsync(() => site.documents(siteId, "design"), [siteId]);
  const list = docs.data || [];
  return (
    <Card title="Building plans">
      {list.length === 0 ? (
        <p className="text-sm text-muted">Your architect's design and building plans will appear here once uploaded.</p>
      ) : (
        <div className="space-y-1.5">
          {list.map((d) => (
            <div key={d.id} className="flex items-center gap-2 border-b border-border/50 py-1.5 text-sm">
              <span className="text-base">📐</span>
              <button onClick={() => site.downloadDocument(d.id, d.filename)} className="text-accent hover:underline">{d.filename}</button>
              <span className="text-[11px] text-muted">{(d.size / 1024).toFixed(0)} KB</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function UpdatesFeed({ events, siteId, me }) {
  const [busy, setBusy] = useState(false);
  const mine = (events.data || []).filter((n) => n.site_id === siteId);
  const unread = mine.filter((n) => !n.read).length;
  const markAll = async () => { setBusy(true); try { await site.markAllRead(me); events.reload(); } finally { setBusy(false); } };
  return (
    <Card title={`Updates${unread ? ` · ${unread} new` : ""}`}
      right={unread > 0 && <button onClick={markAll} disabled={busy} className="text-[11px] text-accent hover:underline">Mark all read</button>}>
      {mine.length === 0 ? <p className="text-sm text-muted">No updates yet. You'll see delivery and phase updates here.</p> : (
        <div className="space-y-1.5">
          {mine.slice(0, 15).map((n) => {
            const e = EVENT[n.kind] || { icon: "🔔" };
            return (
              <div key={n.id} className={`flex items-start gap-2 rounded border-b border-border/50 pb-1.5 pl-1 text-sm ${n.read ? "" : "bg-accent/5"}`}>
                <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.read ? "bg-transparent" : "bg-accent"}`} />
                <span className="text-base">{e.icon}</span>
                <div>
                  <span className={n.read ? "text-ink/70" : "text-ink/90"}>{n.message}</span>
                  {n.created_at && <span className="ml-2 text-[11px] text-muted">{new Date(n.created_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

function PayPanel({ site: s, me }) {
  const consumers = useAsync(() => site.consumers());
  const tier = consumers.data?.find((c) => c.id === me)?.tier;
  const items = s.bom_lines.map((b) => ({ material_id: b.material_id, qty: b.total_qty }));
  const quote = useAsync(() => (tier ? price.quote({ tier, items }) : Promise.resolve(null)), [tier]);
  const payments = useAsync(() => pay.forRef(s.code, me), [s.code]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const total = quote.data?.total;
  const payment = (payments.data || []).find((p) => ["held", "released", "paid"].includes(p.status));
  const released = payment?.status === "released";
  const relPct = payment && payment.amount ? Math.round((payment.released_amount / payment.amount) * 100) : 0;

  const doPay = async () => {
    setBusy(true);
    setErr(null);
    try {
      await pay.create({ ref: s.code, consumer_id: me, amount: total });
      payments.reload();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="Project payment">
      <div className="flex flex-wrap items-center gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-wider text-muted">Estimate ({tier || "…"} pricing)</p>
          <p className="font-mono text-xl font-bold text-ink">{total != null ? inr(total) : "…"}</p>
        </div>
        <div className="ml-auto">
          {payment ? (
            <span className="inline-flex items-center gap-2 text-sm text-emerald-400">
              {released ? "✓ Released" : "🔒 In escrow"} <Badge tone={released ? "ok" : "accent"}>{payment.code}</Badge>
            </span>
          ) : (
            <button onClick={doPay} disabled={busy || total == null}
              className="bg-accent px-4 py-2 text-sm font-semibold text-onAccent hover:bg-accentHover disabled:opacity-40">
              {busy ? "Processing…" : `Pay ${total != null ? inr(total) : ""}`}
            </button>
          )}
        </div>
      </div>
      {payment && !released && (
        <div className="mt-3">
          <div className="mb-1 flex justify-between text-[11px] text-muted">
            <span>Funds held safely in escrow, released to the supplier only as deliveries are confirmed.</span>
            <span className="font-mono">{relPct}% released</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded bg-muted/15">
            <div className="h-full rounded bg-accent" style={{ width: `${relPct}%` }} />
          </div>
        </div>
      )}
      {quote.error && <p className="mt-2 text-xs text-red-400">Could not price project: {quote.error}</p>}
      {err && <p className="mt-2 text-xs text-red-400">{err}</p>}
      {released && <p className="mt-2 text-xs text-muted">All deliveries confirmed - your escrow has been fully released.</p>}
    </Card>
  );
}
