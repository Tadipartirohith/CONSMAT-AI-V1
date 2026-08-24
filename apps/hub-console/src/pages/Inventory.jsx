import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { inv, proc, inr } from "../api.js";
import { Card, Table, Td, Badge, Button, Field, Input, Select, useAsync } from "../components/ui.jsx";

const ICON = { cement: "🧱", steel: "🔩", sand: "🏖️", aggregate: "🪨", bricks: "🟥" };
const TONE = { green: "#22c55e", yellow: "#eab308", orange: "#f59e0b", red: "#ef4444" };

// ConSmat page-3 business verticals (segments), in display order.
const SEGMENTS = [
  { id: "S&F", name: "Structure & Foundation", tag: "S&F", icon: "🏗️" },
  { id: "B&B", name: "Bricks & Blocks", tag: "B&B", icon: "🧱" },
  { id: "S&S", name: "Sheets & Shades", tag: "S&S", icon: "🪵" },
  { id: "P&P", name: "Pipes & Plugs", tag: "P&P", icon: "🔌" },
  { id: "MixG&FixG", name: "Mortars, Adhesives & Coatings", tag: "MixG & FixG", icon: "🧴" },
  { id: "Interiors", name: "Interiors & Home", tag: "Interiors", icon: "🛋️" },
  { id: "Other", name: "Other", tag: "", icon: "📦" },
];

// Status from the 3x-reserved buffer: >=3x green, 1.5-3x yellow, 1-1.5x orange, <1x red.
function stockTone(s) {
  const rv = s ? Number(s.reserved) : 0;
  const av = s ? Number(s.available) : 0;
  if (rv <= 0) return "green";
  const r = av / rv;
  if (r < 1) return "red";
  if (r < 1.5) return "orange";
  if (r < 3) return "yellow";
  return "green";
}

export default function Inventory() {
  const materials = useAsync(() => inv.materials());
  const products = useAsync(() => inv.products());
  const pstock = useAsync(() => inv.productStock());
  const [sp, setSp] = useSearchParams();
  const cat = sp.get("material") || null;          // drill-down via URL: nav "Inventory" resets it
  const setCat = (id) => setSp(id ? { material: id } : {});
  const [adding, setAdding] = useState(false);
  const [receiving, setReceiving] = useState(false);
  const [procure, setProcure] = useState(null);    // product being procured

  const reload = () => { products.reload(); pstock.reload(); };
  const stockOf = (pid) => (pstock.data || []).find((s) => s.product_id === pid);
  const countByMat = useMemo(() => {
    const m = {};
    (products.data || []).forEach((p) => { m[p.material_id] = (m[p.material_id] || 0) + 1; });
    return m;
  }, [products.data]);
  const lowByMat = useMemo(() => {
    const m = {};
    (pstock.data || []).forEach((s) => { if (stockTone(s) !== "green") m[s.material_id] = (m[s.material_id] || 0) + 1; });
    return m;
  }, [pstock.data]);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="font-head text-2xl font-extrabold text-white">Inventory</h1>
        <div className="flex gap-2">
          <Button size="sm" onClick={() => setReceiving(true)}>Receive stock</Button>
          <Button size="sm" variant="ghost" onClick={() => setAdding(true)}>Add product</Button>
          <Button size="sm" variant="ghost" onClick={reload}>Refresh</Button>
        </div>
      </div>

      {!cat ? (
        <>
          <p className="text-xs text-muted">Materials grouped by business vertical (ConSmat classification). Pick a category to see its brands, stock and status.</p>
          {SEGMENTS.map((seg) => {
            const mats = (materials.data || []).filter((m) => (m.segment || "Other") === seg.id);
            if (mats.length === 0) return null;
            return (
              <div key={seg.id}>
                <h2 className="mb-2 mt-1 flex items-center gap-2 text-sm font-bold text-white">
                  <span>{seg.icon}</span>{seg.name}<span className="text-[11px] font-normal text-muted">{seg.tag}</span>
                </h2>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
                  {mats.map((m) => (
                    <button key={m.id} onClick={() => setCat(m.id)}
                      className="flex flex-col items-start gap-1 border border-border bg-panel p-4 text-left hover:border-accent">
                      <span className="text-2xl">{ICON[m.id] || seg.icon}</span>
                      <span className="text-sm font-semibold text-white">{m.name}</span>
                      <span className="text-[11px] text-muted">{countByMat[m.id] || 0} brands</span>
                      {lowByMat[m.id] > 0 && <Badge tone="warn">{lowByMat[m.id]} low</Badge>}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </>
      ) : (
        <CategoryView material={(materials.data || []).find((m) => m.id === cat)} products={products.data || []}
          stockOf={stockOf} onBack={() => setCat(null)} onProcure={setProcure} />
      )}

      {adding && (
        <AddProduct materials={materials.data || []} products={products.data || []} lockedCat={cat}
          onClose={() => setAdding(false)} onDone={() => { setAdding(false); reload(); }} />
      )}
      {receiving && (
        <ReceiveStock products={products.data || []}
          onClose={() => setReceiving(false)} onDone={() => { setReceiving(false); reload(); }} />
      )}
      {procure && (
        <ProcureStock product={procure} onClose={() => setProcure(null)} onDone={() => { setProcure(null); reload(); }} />
      )}
    </div>
  );
}

function ReceiveStock({ products, onClose, onDone }) {
  const vendors = useAsync(() => proc.vendors());
  const [q, setQ] = useState("");
  const [pid, setPid] = useState("");
  const [vendorId, setVendorId] = useState("");
  const [qty, setQty] = useState("");
  const [rate, setRate] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const matches = q.trim()
    ? products.filter((p) => `${p.name} ${p.brand}`.toLowerCase().includes(q.toLowerCase())).slice(0, 8)
    : [];
  const chosen = products.find((p) => p.id === pid);

  const save = async (e) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try {
      await inv.productInbound({ product_id: pid, qty: Number(qty), unit_cost: Number(rate), ref_type: "manual" });
      if (vendorId) { try { await proc.setPrice(vendorId, { product_id: pid, price: Number(rate) }); } catch { /* price is best-effort */ } }
      onDone();
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4" onClick={onClose}>
      <div className="w-full max-w-md border border-border bg-panel p-5" onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-head text-lg font-bold text-white">Receive stock (inbound)</h3>
          <button onClick={onClose} className="text-muted hover:text-white">✕</button>
        </div>
        <form onSubmit={save} className="space-y-3">
          <Field label="Product - search by name or brand">
            {chosen ? (
              <div className="flex items-center gap-2 border border-border bg-panel2 px-2.5 py-1.5 text-sm">
                <span className="flex-1 text-white/80">{chosen.name} <span className="text-muted">({chosen.brand || "no brand"})</span></span>
                <button type="button" className="text-[11px] text-accent hover:underline" onClick={() => { setPid(""); setQ(""); }}>change</button>
              </div>
            ) : (
              <>
                <Input value={q} placeholder="e.g. bharathi / ultratech 53 / red clay" onChange={(e) => setQ(e.target.value)} />
                {matches.length > 0 && (
                  <div className="mt-1 max-h-44 overflow-auto border border-border bg-panel2">
                    {matches.map((p) => (
                      <button type="button" key={p.id} onClick={() => { setPid(p.id); setQ(p.name); }}
                        className="block w-full px-2.5 py-1.5 text-left text-sm text-white/80 hover:bg-white/5">
                        {p.name} <span className="text-muted">· {p.brand || "no brand"} · {p.material_id}</span>
                      </button>
                    ))}
                  </div>
                )}
                {q.trim() && matches.length === 0 && <p className="mt-1 text-[11px] text-muted">No product matches - add it first via Add product.</p>}
              </>
            )}
          </Field>
          <Field label="Vendor (records this rate as their price)">
            <Select value={vendorId} onChange={(e) => setVendorId(e.target.value)}>
              <option value="">- optional -</option>
              {(vendors.data || []).map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
            </Select>
          </Field>
          <Field label="Quantity"><Input type="number" step="any" value={qty} required onChange={(e) => setQty(e.target.value)} /></Field>
          <Field label="Rate (₹/unit)"><Input type="number" step="any" value={rate} required onChange={(e) => setRate(e.target.value)} /></Field>
          <Button type="submit" disabled={busy || !pid}>Record inbound</Button>
          {err && <p className="text-xs text-red-400">{err}</p>}
        </form>
      </div>
    </div>
  );
}

function CategoryView({ material, products, stockOf, onBack, onProcure }) {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [ledgerFor] = useState(material?.id);
  const list = products.filter((p) => p.material_id === material?.id);
  const filtered = list.filter((p) => {
    const hay = `${p.name} ${p.brand} ${p.grade}`.toLowerCase();
    if (q && !hay.includes(q.toLowerCase())) return false;
    if (status && stockTone(stockOf(p.id)) !== status) return false;
    return true;
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" variant="ghost" onClick={onBack}>Back to Categories</Button>
        <span className="text-xl">{ICON[material?.id] || "📦"}</span>
        <h2 className="font-head text-lg font-bold text-white">{material?.name}</h2>
        <span className="text-[11px] text-muted">{list.length} brands</span>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          <div className="w-56"><Input value={q} placeholder="search name or brand…" onChange={(e) => setQ(e.target.value)} /></div>
          <Select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">all status</option>
            <option value="green">green</option>
            <option value="yellow">yellow</option>
            <option value="orange">orange</option>
            <option value="red">red</option>
          </Select>
        </div>
      </div>

      <Card title={`${material?.name} brands`}>
        <Table head={["Name", "Brand", "Stock", "Reserved", "Available", "Avg cost", "Status", ""]}>
          {filtered.map((p) => {
            const s = stockOf(p.id);
            const tone = stockTone(s);
            const oh = s ? s.on_hand : 0, rv = s ? s.reserved : 0;
            const avRaw = s ? s.available : 0;
            const av = Math.max(0, avRaw);              // never show a negative available (0 when stocked out)
            const overCommit = avRaw < 0;
            return (
              <tr key={p.id} className="border-b border-border/50">
                <Td>{p.name}</Td>
                <Td className="text-muted">{p.brand || "-"}</Td>
                <Td mono>{oh}</Td>
                <Td mono>{rv}</Td>
                <Td mono>
                  {av}
                  {overCommit && <span className="ml-1 text-[10px] text-red-400">over-committed</span>}
                </Td>
                <Td mono>{s ? inr(s.avg_cost) : "-"}</Td>
                <Td>
                  <span className="flex items-center gap-1.5">
                    <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: TONE[tone] }} />
                    <span className="text-[11px] text-muted">{tone}</span>
                  </span>
                </Td>
                <Td><Button size="sm" variant="ghost" onClick={() => onProcure({ ...p, material_name: material?.name })}>Procure</Button></Td>
              </tr>
            );
          })}
          {filtered.length === 0 && (
            <tr><td colSpan={8} className="px-3 py-3 text-sm text-muted">
              No {material?.name?.toLowerCase()} match{q ? ` "${q}"` : ""}. Use <b>Add product</b> above to create one.
            </td></tr>
          )}
        </Table>
        <p className="mt-2 text-[11px] text-muted">Status by the hub's 3x buffer: available &ge; 3x reserved = green, 1.5-3x = yellow, 1-1.5x = orange, &lt; 1x = red. Available never shows below 0; an over-committed product is flagged in red.</p>
      </Card>

      {ledgerFor && <LedgerCard material={ledgerFor} />}
    </div>
  );
}

/* Procure stock: compare hub vendor rates against live open-market rates, then place a purchase order. */
function ProcureStock({ product, onClose, onDone }) {
  const vendorPrices = useAsync(() => proc.market(product.material_id));
  const [offers, setOffers] = useState(null);
  const [scanBusy, setScanBusy] = useState(false);
  const [vendorId, setVendorId] = useState("");
  const [rate, setRate] = useState("");
  const [qty, setQty] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  // Vendor rates offered for this exact product (cheapest first).
  const rows = (vendorPrices.data || []).filter((r) => r.product_id === product.id && !r.is_hub_self)
    .sort((a, b) => a.price - b.price);

  const loadOffers = async () => {
    setScanBusy(true);
    try {
      let list = await proc.externalOffers(product.material_id);
      if (!list || list.length === 0) { await proc.scout(product.material_id); list = await proc.externalOffers(product.material_id); }
      setOffers(list || []);
    } catch (e) { setMsg({ ok: false, text: e.message }); } finally { setScanBusy(false); }
  };

  const place = async (e) => {
    e.preventDefault(); setBusy(true); setMsg(null);
    try {
      await proc.createOrder({ lines: [{ material_id: product.material_id, product_id: product.id,
        product_name: product.name, vendor_id: vendorId, qty: Number(qty), unit_cost: Number(rate) }],
        note: `Procured from Inventory for ${product.name}` });
      setMsg({ ok: true, text: "Purchase order created. Receive it under Procurement to add stock." });
      setTimeout(onDone, 900);
    } catch (e) { setMsg({ ok: false, text: e.message }); } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4" onClick={onClose}>
      <div className="max-h-[90vh] w-full max-w-lg overflow-auto border border-border bg-panel p-5" onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h3 className="font-head text-lg font-bold text-white">Procure {product.name}</h3>
            <p className="text-[11px] text-muted">{product.brand || "no brand"} · {product.material_name || product.material_id}</p>
          </div>
          <button onClick={onClose} className="text-muted hover:text-white">✕</button>
        </div>

        <div className="mb-3">
          <p className="mb-1 text-[11px] uppercase tracking-wider text-muted">Hub vendor rates</p>
          {vendorPrices.loading ? <p className="text-sm text-muted">Loading…</p>
            : rows.length === 0 ? <p className="text-sm text-muted">No vendor rate on file for this product yet.</p>
            : (
            <div className="space-y-1">
              {rows.map((r) => (
                <button key={r.vendor_id} type="button" onClick={() => { setVendorId(r.vendor_id); setRate(String(r.price)); }}
                  className={`flex w-full items-center justify-between border px-2.5 py-1.5 text-left text-sm ${vendorId === r.vendor_id ? "border-accent bg-accent/5" : "border-border bg-panel2"}`}>
                  <span className="text-white/85">{r.vendor_name}{r.city ? <span className="text-muted"> · {r.city}</span> : null}</span>
                  <span className="font-mono text-accent">{inr(r.price)}<span className="text-[10px] text-muted">/unit</span></span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="mb-3">
          <div className="mb-1 flex items-center justify-between">
            <p className="text-[11px] uppercase tracking-wider text-muted">Open-market rates</p>
            <button type="button" onClick={loadOffers} disabled={scanBusy} className="text-[11px] text-accent hover:underline">{scanBusy ? "scanning…" : "Check market"}</button>
          </div>
          {offers == null ? <p className="text-[11px] text-muted">Check live open-market rates for a reference price.</p>
            : offers.length === 0 ? <p className="text-[11px] text-muted">No market offers found.</p>
            : (
            <div className="space-y-1">
              {offers.slice(0, 6).map((o) => (
                <div key={o.id} className="flex items-center justify-between border border-border/60 bg-panel2 px-2.5 py-1.5 text-sm">
                  <span className="min-w-0 truncate text-white/80">{o.seller} <span className="text-muted">· {o.product_name}</span></span>
                  <span className="ml-2 shrink-0 font-mono text-white/70">{inr(o.price)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <form onSubmit={place} className="space-y-3 border-t border-border pt-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Quantity"><Input type="number" step="any" value={qty} required onChange={(e) => setQty(e.target.value)} /></Field>
            <Field label="Rate (₹/unit)"><Input type="number" step="any" value={rate} required onChange={(e) => setRate(e.target.value)} /></Field>
          </div>
          {!vendorId && <p className="text-[11px] text-[#f59e0b]">Pick a vendor rate above to place the order.</p>}
          <Button type="submit" disabled={busy || !vendorId || !qty}>Place purchase order</Button>
          {msg && <p className={`text-xs ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>}
        </form>
      </div>
    </div>
  );
}

function AddProduct({ materials, products, lockedCat, onClose, onDone }) {
  const [f, setF] = useState({ material_id: lockedCat || "cement", name: "", brand: "", grade: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const brandsInCat = [...new Set(products.filter((p) => p.material_id === f.material_id && p.brand).map((p) => p.brand))];
  const isNewBrand = f.brand.trim() && !brandsInCat.some((b) => b.toLowerCase() === f.brand.trim().toLowerCase());

  const save = async (e) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try { await inv.createProduct({ material_id: f.material_id, name: f.name, brand: f.brand.trim(), grade: f.grade }); onDone(); }
    catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4" onClick={onClose}>
      <div className="w-full max-w-md border border-border bg-panel p-5" onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-head text-lg font-bold text-white">Add new product</h3>
          <button onClick={onClose} className="text-muted hover:text-white">✕</button>
        </div>
        <form onSubmit={save} className="space-y-3">
          <Field label="Category">
            <Select value={f.material_id} disabled={!!lockedCat} onChange={(e) => setF({ ...f, material_id: e.target.value, brand: "" })}>
              {materials.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </Select>
          </Field>
          <Field label="Product name"><Input value={f.name} required placeholder="e.g. UltraTech Super PPC Cement 50kg" onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
          <Field label="Brand">
            <Input list="brand-suggestions" value={f.brand} placeholder="start typing…" onChange={(e) => setF({ ...f, brand: e.target.value })} />
            <datalist id="brand-suggestions">{brandsInCat.map((b) => <option key={b} value={b} />)}</datalist>
            {isNewBrand && <p className="mt-1 text-[11px] text-[#f59e0b]">New brand "{f.brand.trim()}" - it will be created with this product.</p>}
          </Field>
          <Field label="Grade (optional)"><Input value={f.grade} placeholder="e.g. OPC 53 / Fe 550D" onChange={(e) => setF({ ...f, grade: e.target.value })} /></Field>
          <div className="flex items-center gap-2">
            <Button type="submit" disabled={busy}>Create product</Button>
            <span className="text-[11px] text-muted">Price &amp; stock are recorded at Inbound.</span>
          </div>
          {err && <p className="text-xs text-red-400">{err}</p>}
        </form>
      </div>
    </div>
  );
}

function LedgerCard({ material }) {
  const [open, setOpen] = useState(false);
  const ledger = useAsync(() => (open ? inv.ledger(material) : Promise.resolve([])), [material, open]);
  return (
    <Card title={`Ledger - ${material}`} right={<Button size="sm" variant="ghost" onClick={() => setOpen(!open)}>{open ? "Hide" : "Show"}</Button>}>
      {!open ? <p className="text-sm text-muted">Movement history for this category.</p> : (
        <Table head={["Dir", "Product", "Qty", "Unit cost", "Balance", "Ref"]}>
          {(ledger.data || []).map((e) => (
            <tr key={e.id} className="border-b border-border/50">
              <Td><Badge tone={e.direction === "inbound" ? "ok" : e.direction === "outbound" ? "warn" : "muted"}>{e.direction}</Badge></Td>
              <Td className="text-muted">{e.product_id || "-"}</Td>
              <Td mono>{e.qty}</Td>
              <Td mono>{inr(e.unit_cost)}</Td>
              <Td mono>{e.balance_after}</Td>
              <Td className="text-muted">{e.ref_type}{e.ref_id ? `:${e.ref_id}` : ""}</Td>
            </tr>
          ))}
          {ledger.data?.length === 0 && <tr><Td className="text-muted">No movements yet.</Td></tr>}
        </Table>
      )}
    </Card>
  );
}
