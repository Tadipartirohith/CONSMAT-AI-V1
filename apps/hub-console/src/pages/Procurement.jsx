import { useState } from "react";
import { proc, inv, MATERIALS, inr } from "../api.js";
import { Card, Table, Td, Badge, Button, Field, Input, Select, useAsync, PageSkeleton } from "../components/ui.jsx";

export default function Procurement() {
  const orders = useAsync(() => proc.orders());
  const products = useAsync(() => inv.products());
  const vendors = useAsync(() => proc.vendors());
  const [rows, setRows] = useState([]);
  const [result, setResult] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);


  const setRow = (i, k, v) => setRows(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  const delRow = (i) => setRows(rows.filter((_, j) => j !== i));
  const addRow = (prod, qty) => setRows([...rows, { product_id: prod.id, product_name: prod.name, material_id: prod.material_id, qty }]);
  const demand = () => rows.map((r) => ({ material_id: r.material_id, product_id: r.product_id, product_name: r.product_name, qty: Number(r.qty) }));

  const analyze = async () => {
    setBusy(true); setMsg(null);
    try { setResult(await proc.analyze({ demand: demand() })); }
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
    try { const o = await proc.receive(id); setMsg({ ok: true, text: `${o.code} to ${o.status}.` }); orders.reload(); }
    catch (e) { setMsg({ ok: false, text: e.message }); } finally { setBusy(false); }
  };

  const p = result?.profitability;
  if (orders.loading && !orders.data) return <PageSkeleton stats={0} rows={8} />;
  return (
    <div className="space-y-5">
      <h1 className="font-head text-2xl font-extrabold text-ink">Procurement</h1>
      {msg && <p className={`text-xs ${msg.ok === false ? "text-red-400" : msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text || msg}</p>}

      <SpokeOrderRequests vendors={vendors.data || []} onDone={orders.reload} />


      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Demand to cheapest-source plan">
          <div className="space-y-2">
            {rows.length === 0 && <p className="text-xs text-muted">Search and add products to procure.</p>}
            {rows.map((r, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="flex-1 truncate text-sm text-ink/80" title={r.product_name}>{r.product_name}</span>
                <div className="w-24"><Input type="number" step="any" value={r.qty} onChange={(e) => setRow(i, "qty", e.target.value)} /></div>
                <Button size="sm" variant="ghost" onClick={() => delRow(i)}>✕</Button>
              </div>
            ))}
            <AddDemandRow products={products.data || []} onAdd={addRow} onReload={products.reload} />
            <div className="flex pt-1">
              <Button onClick={analyze} disabled={busy || rows.length === 0}>Analyze</Button>
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
                    <Td>{l.brand ? <span>{l.brand}</span> : <span className="text-muted">{l.product_name || "-"}</span>}</Td>
                    <Td>{l.vendor_name}{l.is_hub_self && <Badge tone="accent">hub</Badge>}</Td>
                    <Td mono>{l.qty}</Td>
                    <Td mono>{inr(l.unit_cost)}</Td>
                    <Td mono>{inr(l.line_cost)}</Td>
                  </tr>
                ))}
              </Table>
              {result.plan.unavailable?.length > 0 && (
                <Unavailable items={result.plan.unavailable} vendors={vendors.data || []} onFixed={analyze} />
              )}
              <div className="mt-3 flex flex-wrap items-center gap-4 text-sm">
                <span>Buy total: <span className="font-mono text-ink">{inr(result.plan.total_cost)}</span></span>
                {p && <>
                  <span>Sell @ list: <span className="font-mono text-ink">{inr(p.sell_total)}</span></span>
                  <span>Margin: <span className={`font-mono ${p.profitable ? "text-emerald-400" : "text-red-400"}`}>{inr(p.margin_total)} ({p.margin_pct}%)</span></span>
                  <Badge tone={p.profitable ? "ok" : "bad"}>{p.profitable ? "profitable" : "loss"}</Badge>
                </>}
                <span className="text-[11px] text-muted">profitability vs {result.price_source || "-"}</span>
                <Button size="sm" onClick={createOrder} disabled={busy || !result.plan.lines.length}>Create order</Button>
              </div>
              {result.advice && <Advice advice={result.advice} />}
              {result.engine === "deterministic" && <p className="mt-2 text-[11px] text-muted">Hub LLM on stub, deterministic analysis. Configure AI_PROVIDER to enable advice.</p>}
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
              <Td className="text-muted">{o.lines.map((l) => `${l.product_name || l.material_id}×${l.qty}`).join(", ")}</Td>
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
      {advice.summary && <p className="text-ink/80">{advice.summary}</p>}
      {advice.profitability_note && <p className="mt-1 text-muted">{advice.profitability_note}</p>}
      {advice.alternatives?.length > 0 && (
        <div className="mt-2 border-l-2 border-[#22c55e]/50 pl-2">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-[#22c55e]">Cheaper alternatives</p>
          {advice.alternatives.map((a, i) => (
            <p key={i} className="mt-0.5 text-ink/80">↓ {typeof a === "string" ? a : a.suggestion}</p>
          ))}
        </div>
      )}
      {advice.recommendation && <p className="mt-2 text-ink/80"><b>Recommendation:</b> {advice.recommendation}</p>}
      {advice.flags?.length > 0 && <p className="mt-1 text-[#f59e0b]">⚑ {advice.flags.join(" · ")}</p>}
    </div>
  );
}

function Unavailable({ items, vendors, onFixed }) {
  return (
    <div className="mt-3 border border-[#f59e0b]/40 bg-[#f59e0b]/5 p-3">
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-[#f59e0b]">Not procurable</p>
      {items.map((u, i) => (
        <div key={i} className="mb-2 last:mb-0 text-sm">
          <p className="text-ink/80">{u.name}: <span className="text-muted">{u.reason}</span></p>
          {u.product_id && <SetPriceInline productId={u.product_id} vendors={vendors} onDone={onFixed} />}
        </div>
      ))}
      <p className="mt-1 text-[11px] text-muted">Add a vendor price to procure it, or pick a stocked brand instead.</p>
    </div>
  );
}

function SetPriceInline({ productId, vendors, onDone }) {
  const [vid, setVid] = useState("");
  const [price, setPrice] = useState("");
  const [msg, setMsg] = useState(null);
  const save = async (e) => {
    e.preventDefault(); setMsg(null);
    try { await proc.setPrice(vid, { product_id: productId, price: Number(price) }); onDone(); }
    catch (e) { setMsg(e.message); }
  };
  return (
    <form onSubmit={save} className="mt-1 flex items-center gap-2">
      <Select value={vid} required onChange={(e) => setVid(e.target.value)}>
        <option value="">vendor…</option>
        {vendors.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
      </Select>
      <div className="w-24"><Input type="number" step="any" value={price} placeholder="₹/unit" required onChange={(e) => setPrice(e.target.value)} /></div>
      <Button size="sm" type="submit">Set price &amp; retry</Button>
      {msg && <span className="text-[11px] text-red-400">{msg}</span>}
    </form>
  );
}

function AddDemandRow({ products, onAdd, onReload }) {
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState(null);
  const [qty, setQty] = useState(100);
  const [showNew, setShowNew] = useState(false);

  const ql = q.trim().toLowerCase();
  const matches = ql
    ? products.filter((p) =>
        p.name.toLowerCase().includes(ql) ||
        (p.brand || "").toLowerCase().includes(ql) ||
        (p.grade || "").toLowerCase().includes(ql)).slice(0, 8)
    : [];

  const pick = (p) => { setSelected(p); setQ(p.name); };
  const add = () => { if (selected) { onAdd(selected, Number(qty)); setSelected(null); setQ(""); } };

  return (
    <div className="border-t border-border/50 pt-2">
      <Input value={q} placeholder="search product by name or company… (e.g. ultratech, ppc, zuari)"
        onChange={(e) => { setQ(e.target.value); setSelected(null); setShowNew(false); }} />

      {/* live suggestions */}
      {ql && !selected && (
        <div className="mt-1 max-h-52 overflow-y-auto rounded-xl border border-border bg-panel2">
          {matches.length ? matches.map((p) => (
            <button key={p.id} type="button" onClick={() => pick(p)}
              className="block w-full px-2.5 py-1.5 text-left text-sm text-ink/80 hover:bg-muted/10">
              {p.name}{p.brand && <span className="text-muted"> · {p.brand}</span>}
            </button>
          )) : (
            <div className="px-2.5 py-2 text-sm">
              <span className="text-muted">No product found for “{q}”. </span>
              <button type="button" onClick={() => setShowNew(true)} className="text-accent hover:underline">Add a new product?</button>
            </div>
          )}
        </div>
      )}

      {selected && (
        <div className="mt-2 flex items-center gap-2">
          <span className="flex-1 truncate text-sm text-accent" title={selected.name}>{selected.name}</span>
          <div className="w-24"><Input type="number" step="any" value={qty} onChange={(e) => setQty(e.target.value)} /></div>
          <Button size="sm" onClick={add}>Add</Button>
        </div>
      )}

      {showNew && (
        <NewProduct initialName={q}
          onDone={(p) => { onReload(); setShowNew(false); if (p) pick(p); }} />
      )}
    </div>
  );
}

function NewProduct({ initialName = "", onDone }) {
  const [f, setF] = useState({ material_id: "cement", name: initialName, brand: "", grade: "" });
  const [msg, setMsg] = useState(null);
  const create = async (e) => {
    e.preventDefault(); setMsg(null);
    try { const p = await inv.createProduct(f); onDone(p); }
    catch (e) { setMsg(e.message); }
  };
  return (
    <form onSubmit={create} className="mt-2 space-y-2 border border-accent/30 bg-panel2 p-2.5">
      <p className="text-[11px] uppercase tracking-wider text-accent">New product</p>
      <div className="flex gap-2">
        <Select value={f.material_id} onChange={(e) => setF({ ...f, material_id: e.target.value })}>{MATERIALS.map((m) => <option key={m} value={m}>{m}</option>)}</Select>
        <Input value={f.brand} placeholder="brand / company" onChange={(e) => setF({ ...f, brand: e.target.value })} />
      </div>
      <Input value={f.name} placeholder="full product name" required onChange={(e) => setF({ ...f, name: e.target.value })} />
      <div className="flex gap-2">
        <Input value={f.grade} placeholder="grade (optional)" onChange={(e) => setF({ ...f, grade: e.target.value })} />
        <Button size="sm" type="submit">Create & select</Button>
      </div>
      {msg && <p className="text-[11px] text-red-400">{msg}</p>}
    </form>
  );
}

function SpokeOrderRequests({ vendors, onDone }) {
  const reqs = useAsync(() => proc.orderRequests("pending"));
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [state, setState] = useState({});
  const setV = (rid, vendor_id) => setState((s) => ({ ...s, [rid]: { ...(s[rid] || {}), vendor_id } }));
  const setP = (rid, pid, cost) => setState((s) => ({ ...s, [rid]: { ...(s[rid] || {}), prices: { ...((s[rid] || {}).prices || {}), [pid]: cost } } }));
  const decide = async (r, approve) => {
    setBusy(true); setMsg(null);
    try {
      const st = state[r.id] || {};
      const prices = Object.entries(st.prices || {}).map(([product_id, unit_cost]) => ({ product_id, unit_cost: Number(unit_cost) }));
      await proc.decideOrderRequest(r.id, { approve, vendor_id: st.vendor_id || "", prices });
      setMsg({ ok: true, text: approve ? `Approved ${r.code}, PO created.` : `Rejected ${r.code}.` });
      reqs.reload(); onDone?.();
    } catch (e) { setMsg({ ok: false, text: e.message }); } finally { setBusy(false); }
  };
  if ((reqs.data || []).length === 0) return null;
  return (
    <Card title={`Spoke order requests (${reqs.data.length})`} right={<Button size="sm" variant="ghost" onClick={reqs.reload}>Refresh</Button>}>
      {msg && <p className={`mb-2 text-xs ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>}
      <div className="space-y-3">
        {reqs.data.map((r) => {
          const st = state[r.id] || {};
          return (
            <div key={r.id} className="rounded-xl border border-border/60 bg-panel2 p-3">
              <div className="mb-2 flex flex-wrap items-center gap-2 text-sm">
                <span className="font-mono text-ink">{r.code}</span>
                {r.site_ref && <Badge tone="accent">{r.site_ref}</Badge>}
                <span className="text-muted">by {r.requested_by || r.requested_by_role}</span>
                {r.note && <span className="text-[11px] text-muted">"{r.note}"</span>}
              </div>
              <Table head={["Product", "Qty", "Rate (Rs/unit)"]}>
                {r.lines.map((l) => (
                  <tr key={l.product_id} className="border-b border-border/50">
                    <Td className="text-ink/80">{l.product_name}</Td>
                    <Td mono>{l.qty}</Td>
                    <Td><div className="w-28"><Input type="number" step="any" placeholder="rate" value={st.prices?.[l.product_id] ?? ""} onChange={(e) => setP(r.id, l.product_id, e.target.value)} /></div></Td>
                  </tr>
                ))}
              </Table>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <Select value={st.vendor_id || ""} onChange={(e) => setV(r.id, e.target.value)}>
                  <option value="">pick vendor…</option>
                  {vendors.filter((v) => !v.is_hub_self).map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
                </Select>
                <Button size="sm" onClick={() => decide(r, true)} disabled={busy || !st.vendor_id}>Approve &amp; create PO</Button>
                <Button size="sm" variant="ghost" onClick={() => decide(r, false)} disabled={busy}>Reject</Button>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
