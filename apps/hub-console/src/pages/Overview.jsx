import { useState } from "react";
import { inv, proc, price, site, inr } from "../api.js";
import { Card, Stat, Table, Td, Badge, Button, useAsync } from "../components/ui.jsx";

export default function Overview() {
  const stock = useAsync(() => inv.stock());
  const vendors = useAsync(() => proc.vendors());
  const orders = useAsync(() => proc.orders());
  const margins = useAsync(() => price.margins());

  const stockRows = stock.data || [];
  const stockValue = stockRows.reduce((s, r) => s + r.on_hand * r.avg_cost, 0);
  const lowCount = stockRows.filter((r) => r.available <= 0).length;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-head text-2xl font-extrabold text-white">Hub Overview</h1>
        <p className="text-xs text-muted">Live snapshot across inventory, vendors, procurement and pricing.</p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Stat label="Stock value" value={inr(stockValue)} accent sub={`${stockRows.length} materials`} />
        <Stat label="Vendors" value={vendors.data?.length ?? "n/a"} sub="registry" />
        <Stat label="Procurement orders" value={orders.data?.length ?? "n/a"} sub="all-time" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Inventory position">
          {stock.error ? <Err msg={stock.error} /> : (
            <Table head={["Material", "On hand", "Reserved", "Avg cost"]}>
              {stockRows.map((r) => (
                <tr key={r.material_id} className="border-b border-border/50">
                  <Td>{r.material_id}</Td>
                  <Td mono>{r.on_hand}{r.available <= 0 && <span className="ml-2"><Badge tone="bad">out</Badge></span>}</Td>
                  <Td mono>{r.reserved}</Td>
                  <Td mono>{inr(r.avg_cost)}</Td>
                </tr>
              ))}
            </Table>
          )}
          {lowCount > 0 && <p className="mt-3 text-xs text-[#f59e0b]">{lowCount} material(s) out of stock, procurement needed.</p>}
        </Card>

        <Card title="Margin rules">
          {margins.error ? <Err msg={margins.error} /> : (
            <Table head={["Material", "Tier", "Margin %"]}>
              {(margins.data || []).map((m) => (
                <tr key={m.id} className="border-b border-border/50">
                  <Td>{m.material_id || <span className="text-muted">any</span>}</Td>
                  <Td>{m.tier || <span className="text-muted">any</span>}</Td>
                  <Td mono>{m.margin_pct}%</Td>
                </tr>
              ))}
            </Table>
          )}
        </Card>
      </div>

      <NetworkShortfalls />
    </div>
  );
}

function NetworkShortfalls() {
  const sites = useAsync(() => site.sites());
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  const shorts = [];
  for (const s of sites.data || []) {
    for (const d of s.dispatches || []) {
      for (const l of d.lines || []) {
        if (l.status === "short") shorts.push({ site: s.code, phase: d.phase_seq, material: l.material_id, qty: l.qty });
      }
    }
  }

  const redispatch = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const res = await site.backfillAll();
      const done = res.sites.reduce((n, s) => n + s.backfilled.length, 0);
      const left = res.sites.reduce((n, s) => n + s.still_short.length, 0);
      setMsg({ ok: true, text: `Re-dispatched ${done} line(s)${left ? `, ${left} still short (need more stock)` : ""}.` });
      sites.reload();
    } catch (e) {
      setMsg({ ok: false, text: e.message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="Deliveries awaiting materials"
      right={<Button size="sm" onClick={redispatch} disabled={busy || shorts.length === 0}>Re-dispatch shortfalls</Button>}>
      {msg && <p className={`mb-3 text-xs ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>}
      {shorts.length === 0 ? (
        <p className="text-sm text-emerald-400">No outstanding shortfalls, every dispatch is fulfilled.</p>
      ) : (
        <>
          <p className="mb-2 text-xs text-[#f59e0b]">{shorts.length} short line(s) across sites. Replenish stock, then re-dispatch.</p>
          <Table head={["Site", "Phase", "Material", "Qty"]}>
            {shorts.map((s, i) => (
              <tr key={i} className="border-b border-border/50">
                <Td mono>{s.site}</Td>
                <Td mono>{s.phase}</Td>
                <Td>{s.material}</Td>
                <Td mono className="text-[#f59e0b]">{s.qty}</Td>
              </tr>
            ))}
          </Table>
        </>
      )}
    </Card>
  );
}

function Err({ msg }) {
  return <p className="text-sm text-red-400">Failed to load: {msg}</p>;
}
