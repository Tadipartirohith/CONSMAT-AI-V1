import { useMemo, useState } from "react";
import { inv, proc, price, site, inr } from "../api.js";
import { Card, Stat, Table, Td, Badge, Button, Field, Input, Select, useAsync, PageSkeleton } from "../components/ui.jsx";
import { MagnifyingGlass, PaperPlaneTilt, Plus, Minus, X, Package } from "@phosphor-icons/react";

// The hub's live inventory (read-only). The field sees quantities and the hub's SELLING price, never
// cost/avg. Type quantities to raise an order request; a product the hub does not stock yet can be
// requested by name. Every request routes to the hub's procurement supervisor, who approves -> a PO.

function stockLevel(s) {
  const rv = Number(s.reserved) || 0, av = Number(s.available) || 0;
  if (av <= 0) return "short";
  if (rv <= 0) return "ok";
  const r = av / rv;
  if (r < 1) return "short";
  if (r < 1.5) return "low";
  return "ok";
}
const LEVEL = { ok: { tone: "ok", label: "In stock" }, low: { tone: "warn", label: "Low" }, short: { tone: "bad", label: "Short" } };

export default function Inventory() {
  const load = useAsync(async () => {
    const [ps, products, materials, requests, sites] = await Promise.all([
      inv.productStock(), inv.products(), inv.materials(), proc.orderRequests(), site.sites(),
    ]);
    const ids = ps.map((s) => s.product_id).filter(Boolean);
    let priceMap = {};
    try { priceMap = ids.length ? await price.sellingPricesProducts(ids) : {}; } catch { priceMap = {}; }
    return { ps, products, materials, requests, sites, priceMap };
  });
  const d = load.data || {};
  const [q, setQ] = useState("");
  const [mat, setMat] = useState("");
  const [cart, setCart] = useState([]);
  const [siteRef, setSiteRef] = useState("");
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  const [showNew, setShowNew] = useState(false);

  const nameMap = useMemo(() => Object.fromEntries((d.products || []).map((p) => [p.id, p])), [d.products]);
  const all = useMemo(() => (d.ps || []).map((s) => ({ ...s, p: nameMap[s.product_id] || {}, level: stockLevel(s) })), [d.ps, nameMap]);
  const rows = all.filter((s) => {
    if (mat && s.material_id !== mat) return false;
    if (q) return `${s.p.name || ""} ${s.p.brand || ""} ${s.material_id}`.toLowerCase().includes(q.toLowerCase());
    return true;
  });
  const shortN = all.filter((s) => s.level === "short").length;
  const lowN = all.filter((s) => s.level === "low").length;
  const openReq = (d.requests || []).filter((r) => r.status !== "approved" && r.status !== "rejected").length;

  const addStocked = (s) => {
    if (cart.find((c) => c.key === s.product_id)) return;
    setCart([...cart, { key: s.product_id, product_id: s.product_id, product_name: s.p.name || s.product_id, qty: 1, source: "inventory" }]);
  };
  const addNew = (item) => setCart([...cart, { key: `new-${Date.now()}`, product_id: "", product_name: item.name, material_id: item.material_id, note: item.note, qty: Number(item.qty) || 1, source: "new" }]);
  const setQty = (key, v) => setCart(cart.map((c) => c.key === key ? { ...c, qty: v } : c));
  const bump = (key, delta) => setCart(cart.map((c) => c.key === key ? { ...c, qty: Math.max(1, (Number(c.qty) || 0) + delta) } : c));
  const removeItem = (key) => setCart(cart.filter((c) => c.key !== key));
  const submit = async () => {
    setBusy(true); setMsg(null);
    try {
      const r = await proc.createOrderRequest({
        site_ref: siteRef, note,
        lines: cart.map((c) => ({ product_id: c.product_id, product_name: c.product_name, material_id: c.material_id || "", source: c.source, note: c.note || "", qty: Number(c.qty) })),
      });
      setMsg({ ok: true, text: `Request ${r.code} sent to the procurement supervisor for approval.` });
      setCart([]); setSiteRef(""); setNote(""); load.reload();
    } catch (e) { setMsg({ ok: false, text: e.message }); } finally { setBusy(false); }
  };

  if (load.loading && !load.data) return <PageSkeleton stats={4} rows={6} />;
  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-head text-2xl font-extrabold text-ink">Inventory</h1>
        <p className="mt-1 text-xs text-muted">The hub's live inventory. Type the quantities you need and place a request; a product not stocked yet can be requested by name. Every request routes to the hub's procurement supervisor, who approves it and sets the vendor and rate.</p>
      </div>
      {msg && <div className={`rounded-xl px-4 py-2.5 text-sm ${msg.ok ? "bg-emerald-500/10 text-emerald-300" : "bg-red-500/10 text-red-300"}`}>{msg.text}</div>}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Products in stock" value={all.length} />
        <Stat label="Running low" value={lowN} accent={lowN > 0} />
        <Stat label="Short" value={shortN} />
        <Stat label="Open requests" value={openReq} />
      </div>

      {cart.length > 0 && (
        <Card title={`Order request (${cart.length} item${cart.length > 1 ? "s" : ""})`}>
          <div className="space-y-2">
            {cart.map((c) => (
              <div key={c.key} className="flex items-center gap-3 rounded-xl bg-panel2 nm-inset px-3 py-2 text-sm">
                <span className="flex-1 truncate text-ink/90">{c.product_name}</span>
                {c.source === "new" && <Badge tone="accent">new</Badge>}
                <div className="flex items-center gap-1.5">
                  <button onClick={() => bump(c.key, -1)} className="grid h-7 w-7 place-items-center rounded-lg bg-panel text-muted nm-raised-sm nm-press hover:text-ink"><Minus size={13} weight="bold" /></button>
                  <input type="number" step="any" value={c.qty} onChange={(e) => setQty(c.key, e.target.value)}
                    className="w-16 rounded-lg bg-bg px-2 py-1 text-center font-mono text-sm text-ink outline-none focus:ring-2 focus:ring-accent/50" />
                  <button onClick={() => bump(c.key, 1)} className="grid h-7 w-7 place-items-center rounded-lg bg-panel text-muted nm-raised-sm nm-press hover:text-ink"><Plus size={13} weight="bold" /></button>
                </div>
                <button onClick={() => removeItem(c.key)} className="grid h-7 w-7 place-items-center rounded-lg text-muted transition-colors hover:text-red-300"><X size={14} /></button>
              </div>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap items-end gap-3">
            <Field label="For project (optional)">
              <Select value={siteRef} onChange={(e) => setSiteRef(e.target.value)}>
                <option value="">not project-specific</option>
                {(d.sites || []).map((s) => <option key={s.id} value={s.code}>{s.code}{s.label ? ` - ${s.label}` : ""}{s.location ? ` (${s.location})` : ""}</option>)}
              </Select>
            </Field>
            <div className="min-w-[180px] flex-1"><Field label="Note"><Input value={note} placeholder="reason / urgency" onChange={(e) => setNote(e.target.value)} /></Field></div>
            <Button onClick={submit} disabled={busy}><PaperPlaneTilt size={15} weight="fill" />{busy ? "Sending..." : "Send to procurement"}</Button>
          </div>
        </Card>
      )}

      {showNew && <NewProductForm materials={d.materials || []} onAdd={(item) => { addNew(item); setShowNew(false); }} onClose={() => setShowNew(false)} />}

      <Card title="Product stock" right={
        <div className="flex items-center gap-2">
          <Button size="sm" variant="ghost" onClick={() => setShowNew(true)}><Plus size={13} weight="bold" />Request a product</Button>
          <div className="relative">
            <MagnifyingGlass size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input value={q} placeholder="search product / brand" onChange={(e) => setQ(e.target.value)}
              className="w-48 rounded-xl bg-panel2 nm-inset py-2 pl-9 pr-3 text-sm text-ink placeholder:text-muted/70 outline-none focus:ring-2 focus:ring-accent/50" />
          </div>
          <Select value={mat} onChange={(e) => setMat(e.target.value)}>
            <option value="">all categories</option>
            {(d.materials || []).map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </Select>
        </div>}>
        <Table head={["Product", "Brand", "Category", "On hand", "Available", "Hub price", "Status", ""]}>
          {rows.map((s) => {
            const lv = LEVEL[s.level];
            const inCart = cart.some((c) => c.key === s.product_id);
            const hp = d.priceMap ? d.priceMap[s.product_id] : undefined;
            return (
              <tr key={s.product_id} className="border-b border-border/50">
                <Td className="text-ink/90">{s.p.name || s.product_id}</Td>
                <Td className="text-muted">{s.p.brand || "-"}</Td>
                <Td className="text-muted">{s.material_id}</Td>
                <Td mono>{s.on_hand}</Td>
                <Td mono>{Math.max(0, s.available)}</Td>
                <Td mono className="text-ink/90">{hp != null ? inr(hp) : "-"}</Td>
                <Td><Badge tone={lv.tone}>{lv.label}</Badge></Td>
                <Td>
                  <Button size="sm" variant="ghost" disabled={inCart} onClick={() => addStocked(s)}>
                    {inCart ? "Added" : <><Plus size={13} weight="bold" />Request</>}
                  </Button>
                </Td>
              </tr>
            );
          })}
          {rows.length === 0 && (
            <tr><Td className="text-muted">
              No stock rows{q || mat ? " match the filter" : " yet"}.{" "}
              <button onClick={() => setShowNew(true)} className="text-accent hover:underline">Request this as a new product</button>.
            </Td></tr>
          )}
        </Table>
      </Card>

      <Card title="My order requests" right={<Button size="sm" variant="ghost" onClick={load.reload}>Refresh</Button>}>
        {(d.requests || []).length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-8 text-center">
            <div className="grid h-11 w-11 place-items-center rounded-xl bg-panel2 nm-inset text-muted"><Package size={20} /></div>
            <p className="text-sm text-muted">No requests yet. Add products above and send them to procurement.</p>
          </div>
        ) : (
          <Table head={["Request", "For", "Items", "Status", "PO"]}>
            {(d.requests || []).map((r) => (
              <tr key={r.id} className="border-b border-border/50">
                <Td mono>{r.code}</Td>
                <Td className="text-muted">{r.site_ref || "-"}</Td>
                <Td className="text-muted">{r.lines.map((l) => `${l.product_name} x${l.qty}`).join(", ")}</Td>
                <Td><Badge tone={r.status === "approved" ? "ok" : r.status === "rejected" ? "bad" : "warn"}>{r.status}</Badge></Td>
                <Td className="text-muted">{r.order_id ? `PO-${r.order_id}` : "-"}</Td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </div>
  );
}

function NewProductForm({ materials, onAdd, onClose }) {
  const [f, setF] = useState({ name: "", material_id: "", qty: "1", note: "" });
  const submit = (e) => {
    e.preventDefault();
    if (!f.name.trim() || !(Number(f.qty) > 0)) return;
    onAdd({ name: f.name.trim(), material_id: f.material_id, qty: f.qty, note: f.note.trim() });
  };
  return (
    <Card title="Request a product not in stock">
      <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
        <div className="min-w-[220px] flex-1"><Field label="Product name"><Input value={f.name} required placeholder="e.g. Dr. Fixit waterproofing 20kg" onChange={(e) => setF({ ...f, name: e.target.value })} /></Field></div>
        <Field label="Category (optional)">
          <Select value={f.material_id} onChange={(e) => setF({ ...f, material_id: e.target.value })}>
            <option value="">unspecified</option>
            {materials.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </Select>
        </Field>
        <div className="w-24"><Field label="Qty"><Input type="number" step="any" value={f.qty} onChange={(e) => setF({ ...f, qty: e.target.value })} /></Field></div>
        <div className="min-w-[160px] flex-1"><Field label="Note (optional)"><Input value={f.note} placeholder="where you saw it / why" onChange={(e) => setF({ ...f, note: e.target.value })} /></Field></div>
        <Button type="submit">Add to request</Button>
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
      </form>
      <p className="mt-2 text-[11px] text-muted">The hub does not price unstocked or open-market items for the field. Add it here and the procurement supervisor will price and order it on approval.</p>
    </Card>
  );
}
