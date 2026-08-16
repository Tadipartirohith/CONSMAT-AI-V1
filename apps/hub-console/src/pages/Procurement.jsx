import { useState } from "react";
import { proc, MATERIALS, TIERS, inr } from "../api.js";
import { Card, Table, Td, Badge, Button, Field, Input, Select, useAsync } from "../components/ui.jsx";

export default function Procurement() {
  const orders = useAsync(() => proc.orders());
  const [rows, setRows] = useState([{ material_id: "cement", qty: 200 }, { material_id: "steel", qty: 4 }]);
  const [tier, setTier] = useState("individual");
  const [result, setResult] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const setRow = (i, k, v) => setRows(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  const addRow = () => setRows([...rows, { material_id: "sand", qty: 10 }]);
  const delRow = (i) => setRows(rows.filter((_, j) => j !== i));
  const demand = () => rows.map((r) => ({ material_id: r.material_id, qty: Number(r.qty) }));

  const analyze = async () => {
    setBusy(true); setMsg(null);
    try { setResult(await proc.analyze({ demand: demand(), tier })); }
    catch (e) { setMsg(e.message); } finally { setBusy(false); }
  };

  const createOrder = async () => {
    if (!result?.plan?.lines?.length) return;
    setBusy(true); setMsg(null);
    try {
      const lines = result.plan.lines.map((l) => ({ material_id: l.material_id, product_id: l.product_id, product_name: l.product_name, vendor_id: l.vendor_id, qty: l.qty, unit_cost: l.unit_cost }));
      const o = await proc.createOrder({ lines, note: "from hub-console" });
      setMsg({ ok: true, text: `Created ${o.code} (${inr(o.total_cost)}).` });
      orders.reload();
    } catch (e) { setMsg({ ok: false, text: e.message }); } finally { setBusy(false); }
  };

  const receive = async (id) => {
    setBusy(true); setMsg(null);
    try { const o = await proc.receive(id); setMsg({ ok: true, text: `${o.code} → ${o.status}.` }); orders.reload(); }
    catch (e) { setMsg({ ok: false, text: e.message }); } finally { setBusy(false); }
  };

  const p = result?.profitability;
  return (
    <div className="space-y-5">
      <h1 className="font-head text-2xl font-extrabold text-white">Procurement</h1>
      {msg && <p className={`text-xs ${msg.ok === false ? "text-red-400" : msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text || msg}</p>}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Demand → cheapest-source plan">
          <div className="space-y-2">
            {rows.map((r, i) => (
              <div key={i} className="flex items-center gap-2">
                <Select value={r.material_id} onChange={(e) => setRow(i, "material_id", e.target.value)}>
                  {MATERIALS.map((m) => <option key={m} value={m}>{m}</option>)}
                </Select>
                <Input type="number" step="any" value={r.qty} onChange={(e) => setRow(i, "qty", e.target.value)} />
                <Button size="sm" variant="ghost" onClick={() => delRow(i)}>✕</Button>
              </div>
            ))}
            <div className="flex items-center gap-2 pt-1">
              <Button size="sm" variant="ghost" onClick={addRow}>+ material</Button>
              <div className="ml-auto flex items-center gap-2">
                <span className="text-[11px] uppercase text-muted">tier</span>
                <Select value={tier} onChange={(e) => setTier(e.target.value)}>{TIERS.map((t) => <option key={t} value={t}>{t}</option>)}</Select>
                <Button onClick={analyze} disabled={busy}>Analyze</Button>
              </div>
            </div>
          </div>
        </Card>

        <Card title="Plan & profitability">
          {!result ? <p className="text-sm text-muted">Run an analysis to see the plan.</p> : (
            <>
              <Table head={["Material", "Product", "Vendor", "Qty", "Unit", "Line"]}>
                {result.plan.lines.map((l) => (
                  <tr key={l.material_id} className="border-b border-border/50">
                    <Td>{l.material_id}</Td>
                    <Td>{l.brand ? <span>{l.brand}</span> : <span className="text-muted">{l.product_name || "—"}</span>}</Td>
                    <Td>{l.vendor_name}{l.is_hub_self && <Badge tone="accent">hub</Badge>}</Td>
                    <Td mono>{l.qty}</Td>
                    <Td mono>{inr(l.unit_cost)}</Td>
                    <Td mono>{inr(l.line_cost)}</Td>
                  </tr>
                ))}
              </Table>
              <div className="mt-3 flex flex-wrap items-center gap-4 text-sm">
                <span>Buy total: <span className="font-mono text-white">{inr(result.plan.total_cost)}</span></span>
                {p && <>
                  <span>Sell: <span className="font-mono text-white">{inr(p.sell_total)}</span></span>
                  <span>Margin: <span className={`font-mono ${p.profitable ? "text-emerald-400" : "text-red-400"}`}>{inr(p.margin_total)} ({p.margin_pct}%)</span></span>
                  <Badge tone={p.profitable ? "ok" : "bad"}>{p.profitable ? "profitable" : "loss"}</Badge>
                </>}
                <span className="text-[11px] text-muted">prices: {result.price_source || "—"}</span>
                <Button size="sm" onClick={createOrder} disabled={busy || !result.plan.lines.length}>Create order</Button>
              </div>
              {result.advice && <Advice advice={result.advice} />}
              {result.engine === "deterministic" && <p className="mt-2 text-[11px] text-muted">Hub LLM on stub — deterministic analysis. Configure AI_PROVIDER to enable advice.</p>}
            </>
          )}
        </Card>
      </div>

      <Card title="Procurement orders" right={<Button size="sm" variant="ghost" onClick={orders.reload}>Refresh</Button>}>
        <Table head={["Order", "Status", "Total", "Lines", ""]}>
          {(orders.data || []).map((o) => (
            <tr key={o.id} className="border-b border-border/50">
              <Td mono>{o.code}</Td>
              <Td><Badge tone={o.status === "received" ? "ok" : "warn"}>{o.status}</Badge></Td>
              <Td mono>{inr(o.total_cost)}</Td>
              <Td className="text-muted">{o.lines.map((l) => `${l.material_id}×${l.qty}`).join(", ")}</Td>
              <Td>{o.status !== "received" && <Button size="sm" onClick={() => receive(o.id)} disabled={busy}>Receive</Button>}</Td>
            </tr>
          ))}
          {orders.data?.length === 0 && <tr><Td className="text-muted">No orders yet.</Td></tr>}
        </Table>
      </Card>
    </div>
  );
}

function Advice({ advice }) {
  return (
    <div className="mt-3 border border-accent/30 bg-accent/5 p-3 text-sm">
      <p className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-accent">Hub LLM advice</p>
      {advice.summary && <p className="text-white/80">{advice.summary}</p>}
      {advice.recommendation && <p className="mt-1 text-white/80"><b>Recommendation:</b> {advice.recommendation}</p>}
      {advice.flags?.length > 0 && <p className="mt-1 text-[#f59e0b]">⚑ {advice.flags.join(" · ")}</p>}
    </div>
  );
}
