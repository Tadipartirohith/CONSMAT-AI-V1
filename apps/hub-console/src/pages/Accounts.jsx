import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { pay, proc, inv, site, inr } from "../api.js";
import { Card, Stat, Table, Td, Badge, Button, useAsync } from "../components/ui.jsx";

const C = { rev: "#22c55e", escrow: "#38bdf8", spend: "#f59e0b", overdue: "#ef4444", muted: "#3f4655" };
const TABS = ["Overview", "Receivables", "Payables", "Ledger"];
const daysSince = (d) => (d ? Math.max(0, Math.round((Date.now() - new Date(d)) / 86400000)) : 0);
const bucketOf = (age) => (age <= 30 ? "0-30" : age <= 60 ? "31-60" : "60+");

export default function Accounts() {
  const payments = useAsync(() => pay.list());
  const orders = useAsync(() => proc.orders());
  const stock = useAsync(() => inv.stock());
  const sites = useAsync(() => site.sites());
  const consumers = useAsync(() => site.consumers());
  const [tab, setTab] = useState("Overview");

  const a = useMemo(() => compute(payments.data, orders.data, stock.data, sites.data, consumers.data),
    [payments.data, orders.data, stock.data, sites.data, consumers.data]);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="font-head text-2xl font-extrabold text-ink">Accounts &amp; Management</h1>
          <p className="text-xs text-muted">Receivables, payables, escrow and cash position across the hub. All-time.</p>
        </div>
        <Button size="sm" variant="ghost" onClick={() => { payments.reload(); orders.reload(); stock.reload(); sites.reload(); }}>Refresh</Button>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Kpi label="Revenue collected" value={inr(a.captured)} sub={`${a.paymentsCount} payments`} bar={a.captured} max={a.captured} color={C.rev} />
        <Kpi label="Released to hub" value={inr(a.released)} sub={a.captured ? `${pct(a.released, a.captured)}% of collected` : "-"} bar={a.released} max={a.captured} color={C.rev} />
        <Kpi label="Held in escrow" value={inr(a.escrow)} sub="awaiting delivery" bar={a.escrow} max={a.captured} color={C.escrow} />
        <Kpi label="Procurement spend" value={inr(a.apTotal)} sub={`${a.ordersCount} POs`} bar={a.apTotal} max={a.apTotal} color={C.spend} />
        <Kpi label="Payables outstanding" value={inr(a.apPayable)} sub="approved, not received" bar={a.apPayable} max={a.apTotal} color={C.overdue} />
        <Kpi label="Gross margin" value={inr(a.margin)} sub={`${a.marginPct}% vs collected`} bar={Math.abs(a.margin)} max={a.captured} color={a.margin >= 0 ? C.rev : C.overdue} />
      </div>

      <div className="flex gap-1 border-b border-border">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm ${tab === t ? "border-b-2 border-accent text-accent" : "text-muted hover:text-ink"}`}>{t}</button>
        ))}
      </div>

      {tab === "Overview" && <Overview a={a} />}
      {tab === "Receivables" && <Receivables a={a} />}
      {tab === "Payables" && <Payables a={a} />}
      {tab === "Ledger" && <Ledger a={a} />}
    </div>
  );
}

/* ---------- KPI card with a mini fill bar ---------- */
function Kpi({ label, value, sub, bar, max, color }) {
  const w = max > 0 ? Math.min(100, Math.max(3, (bar / max) * 100)) : 0;
  return (
    <div className="border border-border bg-panel p-4">
      <p className="text-[10px] uppercase tracking-wider text-muted">{label}</p>
      <p className="mt-1 font-head text-xl font-extrabold text-ink">{value}</p>
      <div className="mt-2 h-1 w-full overflow-hidden rounded bg-panel2">
        <div className="h-full rounded" style={{ width: `${w}%`, background: color }} />
      </div>
      <p className="mt-1 text-[11px] text-muted">{sub}</p>
    </div>
  );
}

/* ---------- Overview: cash position + AR/AP aging + top parties ---------- */
function Overview({ a }) {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Cash position">
          <StackBar segments={[
            { label: "Released", value: a.released, color: C.rev },
            { label: "In escrow", value: a.escrow, color: C.escrow },
          ]} total={a.captured} empty="No customer payments yet." />
          <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <Line label="Receivable outstanding" value={inr(a.receivable)} tone={a.receivable > 0 ? "warn" : "ok"} />
            <Line label="Payables outstanding" value={inr(a.apPayable)} tone={a.apPayable > 0 ? "warn" : "ok"} />
            <Line label="Inventory value" value={inr(a.invValue)} />
            <Line label="Net position" value={inr(a.released - a.apPaid)} tone={(a.released - a.apPaid) >= 0 ? "ok" : "bad"} />
          </div>
        </Card>

        <Card title="Aging">
          <div className="grid grid-cols-2 gap-4">
            <Aging title="Receivable (escrow)" buckets={a.arAging} color={C.escrow} />
            <Aging title="Payable (POs)" buckets={a.apAging} color={C.spend} />
          </div>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Top customers by revenue">
          <RankList rows={a.topCustomers} color={C.rev} empty="No revenue yet." />
        </Card>
        <Card title="Top vendors by spend">
          <RankList rows={a.topVendors} color={C.spend} empty="No procurement yet." />
        </Card>
      </div>
    </div>
  );
}

function Line({ label, value, tone }) {
  const col = tone === "bad" ? "text-red-400" : tone === "warn" ? "text-[#f59e0b]" : tone === "ok" ? "text-emerald-400" : "text-ink";
  return (
    <div className="flex items-center justify-between border-b border-border/50 py-1">
      <span className="text-muted">{label}</span>
      <span className={`font-mono ${col}`}>{value}</span>
    </div>
  );
}

function StackBar({ segments, total, empty }) {
  if (!total) return <p className="text-sm text-muted">{empty}</p>;
  return (
    <>
      <div className="flex h-4 w-full overflow-hidden rounded bg-panel2">
        {segments.filter((s) => s.value > 0).map((s) => (
          <div key={s.label} title={`${s.label} ${inr(s.value)}`} style={{ width: `${(s.value / total) * 100}%`, background: s.color }} />
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-4 text-xs">
        {segments.map((s) => (
          <span key={s.label} className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: s.color }} />
            <span className="text-ink/80">{inr(s.value)}</span><span className="text-muted">{s.label}</span>
          </span>
        ))}
      </div>
    </>
  );
}

function Aging({ title, buckets, color }) {
  const max = Math.max(1, ...Object.values(buckets));
  return (
    <div>
      <p className="mb-2 text-[11px] uppercase tracking-wider text-muted">{title}</p>
      <div className="space-y-1.5">
        {["0-30", "31-60", "60+"].map((b) => (
          <div key={b} className="flex items-center gap-2 text-xs">
            <span className="w-12 shrink-0 text-muted">{b}d</span>
            <div className="h-2.5 flex-1 overflow-hidden rounded bg-panel2">
              <div className="h-full rounded" style={{ width: `${(buckets[b] / max) * 100}%`, background: b === "60+" ? C.overdue : color }} />
            </div>
            <span className="w-20 shrink-0 text-right font-mono text-ink/70">{inr(buckets[b])}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function RankList({ rows, color, empty }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  if (rows.length === 0) return <p className="text-sm text-muted">{empty}</p>;
  return (
    <div className="space-y-1.5">
      {rows.slice(0, 6).map((r) => (
        <div key={r.name} className="text-sm">
          <div className="flex items-center justify-between">
            <span className="truncate text-ink/85">{r.name}</span>
            <span className="ml-2 shrink-0 font-mono text-ink/70">{inr(r.value)}</span>
          </div>
          <div className="mt-0.5 h-1.5 w-full overflow-hidden rounded bg-panel2">
            <div className="h-full rounded" style={{ width: `${(r.value / max) * 100}%`, background: color }} />
          </div>
        </div>
      ))}
    </div>
  );
}

/* ---------- Receivables ---------- */
function Receivables({ a }) {
  return (
    <Card title={`Receivables - ${a.ar.length} payment(s), ${inr(a.escrow)} in escrow`}>
      <Table head={["Payment", "Project", "Customer", "Amount", "Released", "In escrow", "Status", "Age"]}>
        {a.ar.map((r) => (
          <tr key={r.id} className="border-b border-border/50">
            <Td mono>{r.code}</Td>
            <Td>{r.ref ? <Link to={`/projects/${r.ref.replace("SITE-", "")}`} className="text-accent hover:underline">{r.ref}</Link> : "-"}</Td>
            <Td className="text-muted">{r.customer}</Td>
            <Td mono>{inr(r.amount)}</Td>
            <Td mono className="text-emerald-400">{inr(r.released)}</Td>
            <Td mono className="text-[#38bdf8]">{inr(r.escrow)}</Td>
            <Td><Badge tone={r.status === "released" || r.status === "paid" ? "ok" : r.status === "held" ? "accent" : "warn"}>{r.status}</Badge></Td>
            <Td className="text-muted">{r.age}d</Td>
          </tr>
        ))}
        {a.ar.length === 0 && <tr><Td className="text-muted">No customer payments yet.</Td></tr>}
      </Table>
    </Card>
  );
}

/* ---------- Payables ---------- */
function Payables({ a }) {
  return (
    <Card title={`Payables - ${a.ap.length} PO(s), ${inr(a.apPayable)} outstanding`}>
      <Table head={["PO", "Vendors", "Lines", "Total", "Status", "Age"]}>
        {a.ap.map((o) => (
          <tr key={o.id} className="border-b border-border/50">
            <Td mono>{o.code}</Td>
            <Td className="text-muted">{o.vendors}</Td>
            <Td className="text-muted">{o.lineCount}</Td>
            <Td mono>{inr(o.total)}</Td>
            <Td><Badge tone={o.status === "received" ? "ok" : "warn"}>{o.status === "received" ? "paid" : "payable"}</Badge></Td>
            <Td className="text-muted">{o.age}d</Td>
          </tr>
        ))}
        {a.ap.length === 0 && <tr><Td className="text-muted">No procurement orders yet.</Td></tr>}
      </Table>
    </Card>
  );
}

/* ---------- Ledger ---------- */
function Ledger({ a }) {
  return (
    <Card title="Ledger (unified transactions)">
      <Table head={["Date", "Ref", "Description", "In", "Out"]}>
        {a.ledger.map((t, i) => (
          <tr key={i} className="border-b border-border/50">
            <Td className="text-muted">{t.date ? new Date(t.date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "2-digit" }) : "-"}</Td>
            <Td mono>{t.code}</Td>
            <Td className="text-ink/80">{t.desc}</Td>
            <Td mono className="text-emerald-400">{t.in ? inr(t.in) : ""}</Td>
            <Td mono className="text-[#f59e0b]">{t.out ? inr(t.out) : ""}</Td>
          </tr>
        ))}
        {a.ledger.length === 0 && <tr><Td className="text-muted">No transactions yet.</Td></tr>}
      </Table>
    </Card>
  );
}

const pct = (x, y) => (y > 0 ? Math.round((x / y) * 100) : 0);

/* ---------- aggregation ---------- */
function compute(payments, orders, stock, sites, consumers) {
  payments = payments || []; orders = orders || []; stock = stock || []; sites = sites || []; consumers = consumers || [];
  const cName = Object.fromEntries(consumers.map((c) => [c.id, c.name]));
  const CAPTURED = new Set(["held", "released", "paid"]);

  // Receivables (customer payments)
  const ar = [], byRef = {}, byConsumer = {}, arAging = { "0-30": 0, "31-60": 0, "60+": 0 };
  let captured = 0, released = 0;
  for (const p of payments) {
    if (!CAPTURED.has(p.status)) continue;
    const rel = p.status === "paid" ? p.amount : (p.released_amount || 0);
    const esc = Math.max(0, p.amount - rel);
    const age = daysSince(p.created_at);
    captured += p.amount; released += rel;
    byRef[p.ref] = (byRef[p.ref] || 0) + p.amount;
    byConsumer[p.consumer_id] = (byConsumer[p.consumer_id] || 0) + p.amount;
    if (esc > 0) arAging[bucketOf(age)] += esc;
    ar.push({ id: p.id, code: p.code, ref: p.ref, customer: cName[p.consumer_id] || p.consumer_id || "-",
              amount: p.amount, released: rel, escrow: esc, status: p.status, age });
  }
  const escrow = captured - released;

  // Payables (procurement orders)
  const ap = [], vendorSpend = {}, apAging = { "0-30": 0, "31-60": 0, "60+": 0 };
  let apTotal = 0, apPaid = 0;
  for (const o of orders) {
    const total = o.total_cost || 0;
    const age = daysSince(o.created_at);
    apTotal += total;
    if (o.status === "received") apPaid += total; else apAging[bucketOf(age)] += total;
    const vs = [...new Set((o.lines || []).map((l) => l.vendor_name).filter(Boolean))];
    for (const l of o.lines || []) {
      const key = l.vendor_name || "vendor";
      vendorSpend[key] = (vendorSpend[key] || 0) + (l.qty || 0) * (l.unit_cost || 0);
    }
    ap.push({ id: o.id, code: o.code, vendors: vs.join(", ") || "-", lineCount: (o.lines || []).length,
              total, status: o.status, age });
  }
  const apPayable = apTotal - apPaid;

  // Receivable outstanding = issued project budgets not yet collected
  let receivable = 0;
  for (const s of sites) {
    if (s.budget && s.budget > 0) receivable += Math.max(0, s.budget - (byRef[s.code] || 0));
  }

  const invValue = stock.reduce((t, r) => t + (r.on_hand || 0) * (r.avg_cost || 0), 0);
  const margin = captured - apTotal;

  const topCustomers = Object.entries(byConsumer).map(([id, value]) => ({ name: cName[id] || id, value })).sort((x, y) => y.value - x.value);
  const topVendors = Object.entries(vendorSpend).map(([name, value]) => ({ name, value })).sort((x, y) => y.value - x.value);

  const ledger = [
    ...payments.filter((p) => CAPTURED.has(p.status)).map((p) => ({ date: p.created_at, code: p.code, desc: `Payment received${p.ref ? ` for ${p.ref}` : ""}`, in: p.amount, out: 0 })),
    ...orders.map((o) => ({ date: o.created_at, code: o.code, desc: `Procurement${o.note ? ` - ${o.note}` : ""}`, in: 0, out: o.total_cost || 0 })),
  ].sort((x, y) => new Date(y.date || 0) - new Date(x.date || 0)).slice(0, 40);

  return {
    captured, released, escrow, apTotal, apPaid, apPayable, receivable, invValue, margin,
    marginPct: pct(margin, captured), paymentsCount: ar.length, ordersCount: orders.length,
    ar, ap, arAging, apAging, topCustomers, topVendors, ledger,
  };
}
