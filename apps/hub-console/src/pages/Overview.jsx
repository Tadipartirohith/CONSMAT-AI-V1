import { Fragment, useMemo, useState } from "react";
import { inv, proc, site, inr, PHASE_NAMES } from "../api.js";
import { Card, Stat, Table, Td, Badge, Button, useAsync } from "../components/ui.jsx";

const TONE = {
  green: { dot: "#22c55e", label: "on track" },
  yellow: { dot: "#eab308", label: "watch" },
  orange: { dot: "#f59e0b", label: "delayed" },
  red: { dot: "#ef4444", label: "blocked" },
};

const daysBetween = (a, b) => Math.round((a - b) / 86400000);

// RAG health from delays (phase vs planned end) and delivery (material shortfalls).
function siteHealth(s, today) {
  if (s.status === "completed") return { tone: "green", reason: "completed" };
  const shorts = (s.dispatches || []).flatMap((d) => d.lines.filter((l) => l.status === "short"));
  const cur = (s.phases || []).find((p) => p.status === "in_progress");
  const end = cur?.planned_end ? new Date(cur.planned_end) : null;
  const overdue = end ? daysBetween(today, end) : null; // >0 = past end date
  if (shorts.length || (overdue != null && overdue > 3)) return { tone: "red", reason: shorts.length ? `${shorts.length} material(s) short` : `${overdue}d overdue` };
  if (overdue != null && overdue >= 0) return { tone: "orange", reason: `phase ${cur.phase_seq} past due` };
  if (s.status === "active" && (end == null)) return { tone: "yellow", reason: "no phase dates set" };
  if (overdue != null && overdue >= -3) return { tone: "yellow", reason: `phase ends in ${-overdue}d` };
  return { tone: "green", reason: "on schedule" };
}

export default function Overview() {
  const stock = useAsync(() => inv.stock());
  const vendors = useAsync(() => proc.vendors());
  const orders = useAsync(() => proc.orders());
  const sites = useAsync(() => site.sites());
  const consumers = useAsync(() => site.consumers());
  const spokes = useAsync(() => site.spokes());

  const stockRows = stock.data || [];
  const stockValue = stockRows.reduce((s, r) => s + r.on_hand * r.avg_cost, 0);

  const today = useMemo(() => new Date(), []);
  const health = useMemo(() => (sites.data || []).map((s) => ({ s, h: siteHealth(s, today) })), [sites.data, today]);
  const counts = health.reduce((m, x) => { m[x.h.tone] = (m[x.h.tone] || 0) + 1; return m; }, {});
  const total = health.length;
  const active = (sites.data || []).filter((s) => s.status === "active").length;
  const attention = (counts.yellow || 0) + (counts.orange || 0) + (counts.red || 0);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-head text-2xl font-extrabold text-white">Hub Overview</h1>
        <p className="text-xs text-muted">Live snapshot across projects, inventory, vendors and procurement.</p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Projects" value={total} accent sub={`${active} active`} />
        <Stat label="Needs attention" value={attention} sub="watch / delayed / blocked" />
        <Stat label="Stock value" value={inr(stockValue)} sub={`${stockRows.length} materials`} />
        <Stat label="Procurement orders" value={orders.data?.length ?? "n/a"} sub={`${vendors.data?.length ?? 0} vendors`} />
      </div>

      <Card title="Project health" right={<Button size="sm" variant="ghost" onClick={sites.reload}>Refresh</Button>}>
        {total === 0 ? <p className="text-sm text-muted">No projects yet.</p> : (
          <>
            <div className="mb-3 flex h-2.5 w-full overflow-hidden rounded">
              {["green", "yellow", "orange", "red"].map((t) => counts[t] ? (
                <div key={t} title={`${counts[t]} ${TONE[t].label}`} style={{ width: `${(counts[t] / total) * 100}%`, background: TONE[t].dot }} />
              ) : null)}
            </div>
            <div className="mb-3 flex flex-wrap gap-4 text-xs">
              {["green", "yellow", "orange", "red"].map((t) => (
                <span key={t} className="flex items-center gap-1.5">
                  <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: TONE[t].dot }} />
                  <span className="text-white/80">{counts[t] || 0}</span>
                  <span className="text-muted">{TONE[t].label}</span>
                </span>
              ))}
            </div>
            <Table head={["Project", "Status", "Phase", "Health"]}>
              {health.map(({ s, h }) => {
                const cur = (s.phases || []).find((p) => p.status === "in_progress");
                return (
                  <tr key={s.id} className="border-b border-border/50">
                    <Td><a className="text-accent hover:underline" href={`/projects/${s.id}`}>{s.label || s.code}</a></Td>
                    <Td><Badge tone={s.status === "completed" ? "ok" : s.status === "active" ? "accent" : "muted"}>{s.status}</Badge></Td>
                    <Td className="text-muted">{cur ? `${cur.phase_seq}. ${PHASE_NAMES[cur.phase_seq]}` : "-"}</Td>
                    <Td>
                      <span className="flex items-center gap-1.5">
                        <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: TONE[h.tone].dot }} />
                        <span className="text-white/80">{TONE[h.tone].label}</span>
                        <span className="text-[11px] text-muted">· {h.reason}</span>
                      </span>
                    </Td>
                  </tr>
                );
              })}
            </Table>
          </>
        )}
      </Card>

      <NetworkShortfalls sites={sites} consumers={consumers.data || []} spokes={spokes.data || []} />
    </div>
  );
}

function NetworkShortfalls({ sites, consumers, spokes }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [open, setOpen] = useState(null);

  const consumerMap = Object.fromEntries(consumers.map((c) => [c.id, c]));
  const spokeMap = Object.fromEntries(spokes.map((s) => [s.id, s]));

  // group short lines by site
  const bySite = [];
  for (const s of sites.data || []) {
    const shorts = (s.dispatches || []).flatMap((d) => d.lines.filter((l) => l.status === "short").map((l) => ({ ...l, phase_seq: d.phase_seq })));
    if (!shorts.length) continue;
    const c = consumerMap[s.consumer_id];
    const spoke = c ? spokeMap[c.spoke_id] : null;
    const cur = (s.phases || []).find((p) => p.status === "in_progress");
    bySite.push({ site: s, shorts, spoke, phaseSeq: cur?.phase_seq });
  }
  const totalShort = bySite.reduce((n, x) => n + x.shorts.length, 0);

  const redispatch = async () => {
    setBusy(true); setMsg(null);
    try {
      const res = await site.backfillAll();
      const done = res.sites.reduce((n, s) => n + s.backfilled.length, 0);
      const left = res.sites.reduce((n, s) => n + s.still_short.length, 0);
      setMsg({ ok: true, text: `Re-dispatched ${done} line(s)${left ? `, ${left} still short (need more stock)` : ""}.` });
      sites.reload();
    } catch (e) { setMsg({ ok: false, text: e.message }); } finally { setBusy(false); }
  };

  return (
    <Card title="Deliveries awaiting materials"
      right={<Button size="sm" onClick={redispatch} disabled={busy || totalShort === 0}>Re-dispatch shortfalls</Button>}>
      {msg && <p className={`mb-3 text-xs ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>}
      {totalShort === 0 ? (
        <p className="text-sm text-emerald-400">No outstanding shortfalls, every dispatch is fulfilled.</p>
      ) : (
        <>
          <p className="mb-2 text-xs text-[#f59e0b]">{totalShort} awaiting line(s) across {bySite.length} project(s). Replenish stock, then re-dispatch.</p>
          <Table head={["Project", "Spoke", "Location", "Phase", "Materials"]}>
            {bySite.map(({ site: s, shorts, spoke, phaseSeq }) => (
              <Fragment key={s.id}>
                <tr className="border-b border-border/50">
                  <Td><a className="text-accent hover:underline" href={`/projects/${s.id}`}>{s.label || s.code}</a></Td>
                  <Td className="text-muted">{spoke?.name || "-"}</Td>
                  <Td className="text-muted">{s.location || "-"}</Td>
                  <Td className="text-muted">{phaseSeq ? `${phaseSeq}. ${PHASE_NAMES[phaseSeq]}` : "-"}</Td>
                  <Td>
                    <Button size="sm" variant="ghost" onClick={() => setOpen(open === s.id ? null : s.id)}>
                      {open === s.id ? "Hide" : `View list (${shorts.length})`}
                    </Button>
                  </Td>
                </tr>
                {open === s.id && (
                  <tr className="border-b border-border/50 bg-panel2">
                    <td className="px-3 py-2 text-muted" colSpan={5}>
                      <div className="flex flex-wrap gap-2 py-1">
                        {shorts.map((l, i) => (
                          <span key={i} className="border border-[#f59e0b]/40 px-2 py-0.5 font-mono text-xs text-[#f59e0b]">
                            {l.product_name || l.material_id} ×{l.qty} <span className="text-muted">(P{l.phase_seq})</span>
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </Table>
        </>
      )}
    </Card>
  );
}
