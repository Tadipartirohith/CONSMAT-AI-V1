import { Fragment, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { inv, proc, site, inr, PHASE_NAMES } from "../api.js";
import { Card, Stat, Table, Td, Badge, Button, useAsync } from "../components/ui.jsx";
import { siteHealth } from "./Projects.jsx";

const TONE = {
  green: { dot: "#22c55e", label: "on track" },
  yellow: { dot: "#eab308", label: "watch" },
  orange: { dot: "#f59e0b", label: "delayed" },
  red: { dot: "#ef4444", label: "blocked" },
};
const ORDER = ["green", "yellow", "orange", "red"];

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

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Project health" right={<Button size="sm" variant="ghost" onClick={sites.reload}>Refresh</Button>}>
          <HealthDonut counts={counts} total={total} />
        </Card>
        <Card title="Stock buffer watch" right={<Button size="sm" variant="ghost" onClick={() => window.location.reload()}>Refresh</Button>}>
          <StockBuffer />
        </Card>
      </div>

      <MarketRow />

      <NetworkShortfalls sites={sites} consumers={consumers.data || []} spokes={spokes.data || []} />

      <EventsFeed />
    </div>
  );
}

/* ---- Project-health donut: hover a segment to read its count, click to open those projects ---- */
function HealthDonut({ counts, total }) {
  const nav = useNavigate();
  const [hover, setHover] = useState(null);
  if (total === 0) return <p className="text-sm text-muted">No projects yet.</p>;

  const segs = ORDER.filter((t) => counts[t]).map((t) => ({ key: t, value: counts[t], color: TONE[t].dot, label: TONE[t].label }));
  const R = 62, SW = 22, C = 2 * Math.PI * R;
  let acc = 0;
  const center = hover ? { big: `${hover.value}/${total}`, small: hover.label } : { big: total, small: total === 1 ? "project" : "projects" };

  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-center sm:gap-6">
      <div className="relative h-[168px] w-[168px] shrink-0">
        <svg viewBox="0 0 168 168" className="h-full w-full">
          <g transform="rotate(-90 84 84)">
            <circle cx="84" cy="84" r={R} fill="none" stroke="#1f2937" strokeWidth={SW} />
            {segs.map((seg) => {
              const len = (seg.value / total) * C;
              const el = (
                <circle key={seg.key} cx="84" cy="84" r={R} fill="none" stroke={seg.color} strokeWidth={SW}
                  strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-acc}
                  opacity={hover && hover.key !== seg.key ? 0.28 : 1}
                  className="cursor-pointer transition-opacity"
                  onMouseEnter={() => setHover(seg)} onMouseLeave={() => setHover(null)}
                  onClick={() => nav(`/projects?health=${seg.key}`)} />
              );
              acc += len;
              return el;
            })}
          </g>
        </svg>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-head text-3xl font-extrabold text-white">{center.big}</span>
          <span className="text-[11px] text-muted">{center.small}</span>
        </div>
      </div>
      <div className="flex-1 space-y-1.5">
        {ORDER.map((t) => (
          <button key={t} onClick={() => counts[t] && nav(`/projects?health=${t}`)}
            onMouseEnter={() => counts[t] && setHover({ key: t, value: counts[t], label: TONE[t].label })}
            onMouseLeave={() => setHover(null)}
            className={`flex w-full items-center gap-2 rounded px-2 py-1 text-left text-sm ${counts[t] ? "hover:bg-white/5" : "opacity-40"}`}>
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: TONE[t].dot }} />
            <span className="text-white/80">{counts[t] || 0}</span>
            <span className="text-muted">{TONE[t].label}</span>
            {counts[t] > 0 && <span className="ml-auto text-[11px] text-accent">view</span>}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ---- Stock buffer watch: out / low / future-need against the 3x-reserved buffer ---- */
const RATIO_BAND = (onHand, reserved) => {
  if (reserved <= 0) return "ok";
  const r = onHand / reserved;
  if (r < 1) return "out";        // can't even cover committed demand
  if (r < 1.5) return "low";      // under 1.5x
  if (r < 3) return "watch";      // under the 3x target
  return "ok";
};
const BAND = {
  out: { color: "#ef4444", label: "Out of stock" },
  low: { color: "#f59e0b", label: "Low buffer" },
  watch: { color: "#eab308", label: "Below 3x target" },
};

function StockBuffer() {
  const low = useAsync(() => inv.lowStock());
  const products = useAsync(() => inv.products());
  const nav = useNavigate();
  const [pick, setPick] = useState(null);

  const nameMap = Object.fromEntries((products.data || []).map((p) => [p.id, p.name]));
  const items = (low.data || []).map((r) => {
    const band = RATIO_BAND(r.on_hand, r.reserved);
    const target = r.reserved * 3;
    return { ...r, band, target, pct: target > 0 ? Math.min(100, (r.on_hand / target) * 100) : 0,
             name: nameMap[r.product_id] || r.product_id };
  }).sort((a, b) => (a.on_hand / (a.reserved || 1)) - (b.on_hand / (b.reserved || 1)));

  const groups = { out: [], low: [], watch: [] };
  for (const it of items) (groups[it.band] || groups.watch).push(it);
  const shown = pick ? groups[pick] : items;

  if (low.loading) return <p className="text-sm text-muted">Loading…</p>;
  if (items.length === 0) return <p className="text-sm text-emerald-400">Every product holds a healthy buffer (3x committed demand).</p>;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2">
        {["out", "low", "watch"].map((b) => (
          <button key={b} onClick={() => setPick(pick === b ? null : b)}
            className={`border px-2 py-2 text-left ${pick === b ? "border-accent bg-accent/5" : "border-border bg-panel2"}`}>
            <div className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: BAND[b].color }} />
              <span className="font-head text-xl font-bold text-white">{groups[b].length}</span>
            </div>
            <p className="mt-0.5 text-[11px] text-muted">{BAND[b].label}</p>
          </button>
        ))}
      </div>
      {pick && <p className="text-[11px] text-muted">Showing {BAND[pick].label.toLowerCase()} - click the tile again to show all.</p>}
      <div className="space-y-2">
        {shown.map((it) => (
          <button key={it.product_id} onClick={() => nav(`/inventory?material=${it.material_id}`)}
            className="block w-full text-left">
            <div className="flex items-center justify-between text-xs">
              <span className="truncate text-white/85">{it.name}</span>
              <span className="ml-2 shrink-0 font-mono text-muted">{it.on_hand} / {it.target} <span className="text-[10px]">(3x)</span></span>
            </div>
            <div className="mt-1 h-2 w-full overflow-hidden rounded bg-panel2">
              <div className="h-full rounded" style={{ width: `${Math.max(4, it.pct)}%`, background: BAND[it.band]?.color || "#eab308" }} />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

/* ---- Market watch (daily per-material movement) + price outlook per segment ---- */
const SEG_LABEL = {
  "S&F": "Structure & Foundation", "B&B": "Bricks & Blocks", "S&S": "Sheets & Shades",
  "P&P": "Pipes & Plugs", "MixG&FixG": "Mortars & Coatings", "Interiors": "Interiors & Home",
};

function Spark({ series, up }) {
  if (!series || series.length < 2) return <span className="inline-block w-12" />;
  const w = 48, h = 16, min = Math.min(...series), max = Math.max(...series), rng = (max - min) || 1;
  const pts = series.map((v, i) => `${(i / (series.length - 1)) * w},${h - ((v - min) / rng) * h}`).join(" ");
  return <svg width={w} height={h} className="shrink-0"><polyline points={pts} fill="none" stroke={up ? "#ef4444" : "#22c55e"} strokeWidth="1.5" /></svg>;
}

function MarketRow() {
  const market = useAsync(() => proc.marketIndex());
  const data = (market.data || []).filter((d) => d.current > 0);
  const bySeg = {};
  data.forEach((d) => (bySeg[d.segment || "Other"] ||= []).push(d));
  const outlook = Object.entries(bySeg).map(([seg, items]) => {
    const avg = Math.round((items.reduce((s, d) => s + d.change_pct, 0) / items.length) * 100) / 100;
    return { seg, avg, dir: avg > 0.3 ? "up" : avg < -0.3 ? "down" : "stable", n: items.length };
  }).sort((a, b) => b.avg - a.avg);

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Market watch (daily)" right={<Button size="sm" variant="ghost" onClick={market.reload}>Refresh</Button>}>
        {market.loading ? <p className="text-sm text-muted">Loading…</p> : data.length === 0 ? (
          <p className="text-sm text-muted">No market prices yet. Run an open-market scan under Market.</p>
        ) : (
          <div className="max-h-80 space-y-3 overflow-auto">
            {Object.entries(bySeg).map(([seg, items]) => (
              <div key={seg}>
                <p className="mb-1 text-[10px] uppercase tracking-wider text-muted">{SEG_LABEL[seg] || seg}</p>
                <div className="space-y-1">
                  {items.map((d) => (
                    <div key={d.material_id} className="flex items-center gap-2 text-sm">
                      <span className="min-w-0 flex-1 truncate text-white/80">{d.name}</span>
                      <Spark series={d.series} up={d.change_pct >= 0} />
                      <span className="w-16 text-right font-mono text-white/70">{inr(d.current)}</span>
                      <span className={`w-14 text-right font-mono text-xs ${d.change_pct > 0 ? "text-red-400" : d.change_pct < 0 ? "text-emerald-400" : "text-muted"}`}>
                        {d.change_pct > 0 ? "▲" : d.change_pct < 0 ? "▼" : ""}{Math.abs(d.change_pct)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card title="Price outlook">
        <p className="mb-2 text-[11px] text-muted">Will our materials go up or down? Recent open-market trend per vertical (rising = costlier for us).</p>
        {outlook.length === 0 ? <p className="text-sm text-muted">No market data yet.</p> : (
          <div className="space-y-1.5">
            {outlook.map((r) => (
              <div key={r.seg} className="flex items-center gap-2 text-sm">
                <span className="flex-1 text-white/80">{SEG_LABEL[r.seg] || r.seg}</span>
                <span className="text-[11px] text-muted">{r.n} items</span>
                <Badge tone={r.dir === "up" ? "bad" : r.dir === "down" ? "ok" : "muted"}>
                  {r.dir === "up" ? "▲ rising" : r.dir === "down" ? "▼ falling" : "stable"}
                </Badge>
                <span className={`w-16 text-right font-mono text-xs ${r.avg > 0 ? "text-red-400" : r.avg < 0 ? "text-emerald-400" : "text-muted"}`}>
                  {r.avg > 0 ? "+" : ""}{r.avg}%
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

/* ---- Network events feed (dispatch, phase, delivery notifications across all sites) ---- */
function EventsFeed() {
  const events = useAsync(() => site.notifications());
  const [kind, setKind] = useState("");
  const rows = (events.data || []).filter((n) => !kind || n.kind === kind).slice(0, 20);
  const kinds = [...new Set((events.data || []).map((n) => n.kind))];
  const ICON = { dispatched: "🚚", dispatch_pending: "⏳", received: "📦", started: "🏗️",
                 phase_done: "✅", project_done: "🎉", confirm_reminder: "🔔", low_stock: "⚠️" };

  return (
    <Card title="Network events" right={<Button size="sm" variant="ghost" onClick={events.reload}>Refresh</Button>}>
      {kinds.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1.5">
          <button onClick={() => setKind("")} className={`rounded px-2 py-0.5 text-[11px] ${!kind ? "bg-accent/15 text-accent" : "bg-panel2 text-muted"}`}>all</button>
          {kinds.map((k) => (
            <button key={k} onClick={() => setKind(k)} className={`rounded px-2 py-0.5 text-[11px] ${kind === k ? "bg-accent/15 text-accent" : "bg-panel2 text-muted"}`}>{k}</button>
          ))}
        </div>
      )}
      {rows.length === 0 ? <p className="text-sm text-muted">No events yet.</p> : (
        <div className="space-y-1.5">
          {rows.map((n) => (
            <div key={n.id} className="flex items-start gap-2 border-b border-border/50 pb-1.5 text-sm">
              <span className="text-base">{ICON[n.kind] || "🔔"}</span>
              <div className="min-w-0 flex-1">
                <span className="text-white/85">{n.message}</span>
                {n.site_id ? <Link to={`/projects/${n.site_id}`} className="ml-2 text-[11px] text-accent hover:underline">SITE-{n.site_id}</Link> : null}
              </div>
              {n.created_at && <span className="shrink-0 text-[11px] text-muted">{new Date(n.created_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</span>}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function NetworkShortfalls({ sites, consumers, spokes }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [open, setOpen] = useState(null);

  const consumerMap = Object.fromEntries(consumers.map((c) => [c.id, c]));
  const spokeMap = Object.fromEntries(spokes.map((s) => [s.id, s]));

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
      // Still-short is a warning (need more stock), so surface it in red, not green.
      setMsg({ ok: left === 0, text: `Re-dispatched ${done} line(s)${left ? `, ${left} still short (need more stock)` : ""}.` });
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
                  <Td><Link className="text-accent hover:underline" to={`/projects/${s.id}`}>{s.label || s.code}</Link></Td>
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
