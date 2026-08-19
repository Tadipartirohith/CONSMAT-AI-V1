import { useMemo, useState } from "react";
import { proc, MATERIALS, inr } from "../api.js";
import { Card, Table, Td, Badge, Button, Field, Input, Select, useAsync } from "../components/ui.jsx";

const OPS = { lt: "less than", lte: "≤", gt: "greater than", gte: "≥", eq: "equal to" };

export default function Market() {
  const drops = useAsync(() => proc.priceDrops());
  const alerts = useAsync(() => proc.alerts());
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [f, setF] = useState({ cat: "", brand: "", name: "", maxPrice: "" });

  const scan = async (category) => {
    setBusy(true); setMsg(null);
    try { const r = await proc.marketScan(category); setMsg(`Scanned ${r.scanned.length} categor(ies) — ${r.offers} offers via ${r.provider}.`); drops.reload(); alerts.reload(); }
    catch (e) { setMsg(e.message); } finally { setBusy(false); }
  };

  const rows = useMemo(() => (drops.data || []).filter((d) => {
    if (f.cat && d.material_id !== f.cat) return false;
    if (f.brand && !`${d.brand}`.toLowerCase().includes(f.brand.toLowerCase())) return false;
    if (f.name && !`${d.product_name}`.toLowerCase().includes(f.name.toLowerCase())) return false;
    if (f.maxPrice && d.offer_price > Number(f.maxPrice)) return false;
    return true;
  }), [drops.data, f]);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-head text-2xl font-extrabold text-white">Open-market watch</h1>
          <p className="text-xs text-muted">Products where an open-market offer beats your current avg cost. Auto-scans every 4 hours.</p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" onClick={() => scan("")} disabled={busy}>{busy ? "Scanning…" : "Refresh now"}</Button>
        </div>
      </div>
      {msg && <p className="text-xs text-muted">{msg}</p>}

      <Card title="Below-cost open-market offers"
        right={<div className="flex flex-wrap items-center gap-2">
          <Select value={f.cat} onChange={(e) => setF({ ...f, cat: e.target.value })}>
            <option value="">all categories</option>{MATERIALS.map((m) => <option key={m} value={m}>{m}</option>)}
          </Select>
          <div className="w-28"><Input value={f.brand} placeholder="brand" onChange={(e) => setF({ ...f, brand: e.target.value })} /></div>
          <div className="w-32"><Input value={f.name} placeholder="name" onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
          <div className="w-24"><Input type="number" value={f.maxPrice} placeholder="max ₹" onChange={(e) => setF({ ...f, maxPrice: e.target.value })} /></div>
        </div>}>
        {drops.error ? <p className="text-sm text-red-400">{drops.error}</p> : rows.length === 0 ? (
          <p className="text-sm text-muted">No below-cost offers right now. Hit “Refresh now” to scan the market.</p>
        ) : (
          <Table head={["Category", "Product", "Brand", "Your avg", "Market offer", "Seller", "Saving", ""]}>
            {rows.map((d, i) => (
              <tr key={`${d.product_id}-${i}`} className="border-b border-border/50">
                <Td className="text-muted">{d.material_id}</Td>
                <Td>{d.product_name}</Td>
                <Td className="text-muted">{d.brand || "-"}</Td>
                <Td mono>{inr(d.avg_cost)}</Td>
                <Td mono className="text-accent">{inr(d.offer_price)}</Td>
                <Td className="text-muted">{d.seller} <Badge tone={d.confidence === "firm" ? "ok" : "warn"}>{d.source}</Badge></Td>
                <Td mono className="text-emerald-400">−{d.saving_pct}%</Td>
                <Td>{d.url ? <a href={d.url} target="_blank" rel="noreferrer"><Button size="sm">Buy now →</Button></a> : <span className="text-muted">-</span>}</Td>
              </tr>
            ))}
          </Table>
        )}
        <p className="mt-2 text-[11px] text-[#f59e0b]">Advisory — indicative internet prices, verify before purchase.</p>
      </Card>

      <Alerts alerts={alerts} />
    </div>
  );
}

function Alerts({ alerts }) {
  const [f, setF] = useState({ material_id: "", query: "", op: "lt", value: "", seller: "", location: "" });
  const [msg, setMsg] = useState(null);
  const add = async (e) => {
    e.preventDefault(); setMsg(null);
    try { await proc.createAlert({ ...f, value: Number(f.value) }); setF({ ...f, value: "", seller: "", location: "", query: "" }); alerts.reload(); }
    catch (e) { setMsg(e.message); }
  };
  const del = async (id) => { await proc.deleteAlert(id); alerts.reload(); };

  return (
    <Card title="Price alerts">
      <form onSubmit={add} className="mb-3 flex flex-wrap items-end gap-2">
        <Field label="Category">
          <Select value={f.material_id} onChange={(e) => setF({ ...f, material_id: e.target.value })}>
            <option value="">any</option>{MATERIALS.map((m) => <option key={m} value={m}>{m}</option>)}
          </Select>
        </Field>
        <Field label="Name/brand contains"><Input value={f.query} placeholder="e.g. ultratech" onChange={(e) => setF({ ...f, query: e.target.value })} /></Field>
        <Field label="Price is">
          <Select value={f.op} onChange={(e) => setF({ ...f, op: e.target.value })}>
            {Object.entries(OPS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </Select>
        </Field>
        <div className="w-24"><Field label="₹ value"><Input type="number" value={f.value} required onChange={(e) => setF({ ...f, value: e.target.value })} /></Field></div>
        <Field label="Trader contains"><Input value={f.seller} placeholder="optional" onChange={(e) => setF({ ...f, seller: e.target.value })} /></Field>
        <Field label="Location contains"><Input value={f.location} placeholder="optional" onChange={(e) => setF({ ...f, location: e.target.value })} /></Field>
        <Button type="submit">Add alert</Button>
      </form>
      {msg && <p className="mb-2 text-xs text-red-400">{msg}</p>}

      {(alerts.data || []).length === 0 ? <p className="text-sm text-muted">No alerts yet.</p> : (
        <div className="space-y-3">
          {(alerts.data || []).map(({ alert: a, matches }) => (
            <div key={a.id} className="border border-border/60 bg-panel2 p-3">
              <div className="flex items-center gap-2 text-sm">
                <Badge tone={matches.length ? "ok" : "muted"}>{matches.length} match{matches.length === 1 ? "" : "es"}</Badge>
                <span className="text-white/80">{a.material_id || "any"} · {a.query || "any"} · price {OPS[a.op]} {inr(a.value)}{a.seller ? ` · ${a.seller}` : ""}{a.location ? ` · ${a.location}` : ""}</span>
                <button onClick={() => del(a.id)} className="ml-auto text-[11px] text-red-400 hover:underline">delete</button>
              </div>
              {matches.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {matches.slice(0, 8).map((m, i) => (
                    <a key={i} href={m.url || "#"} target="_blank" rel="noreferrer" className="border border-emerald-500/30 px-2 py-0.5 font-mono text-xs text-emerald-400 hover:bg-emerald-500/10">
                      {m.seller}: {inr(m.price)} <span className="text-muted">({m.material_id})</span>
                    </a>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
