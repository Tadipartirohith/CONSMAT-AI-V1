import { useMemo, useState } from "react";
import { inv, proc, site } from "../api.js";
import { Card, Stat, Table, Td, Badge, Button, Field, Input, Select, useAsync } from "../components/ui.jsx";
import { MagnifyingGlass, PaperPlaneTilt, Plus, Minus, X, Package } from "@phosphor-icons/react";

// Live hub stock (read-only). The spoke types quantities into an order request; sending it
// routes the request to the hub's procurement supervisor, who approves and sets vendor + rate.

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
  const pstock = useAsync(() => inv.productStock());
  const products = useAsync(() => inv.products());
  const materials = useAsync(() => inv.materials());
  const requests = useAsync(() => proc.orderRequests());
  const sites = useAsync(() => site.sites());
  const [q, setQ] = useState("");
  const [mat, setMat] = useState("");
  const [cart, setCart] = useState([]);
  const [siteRef, setSiteRef] = useState("");
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const nameMap = useMemo(() => Object.fromEntries((products.data || []).map((p) => [p.id, p])), [products.data]);
  const all = useMemo(() => (pstock.data || []).map((s) => ({ ...s, p: nameMap[s.product_id] || {}, level: stockLevel(s) })), [pstock.data, nameMap]);
  const rows = all.filter((s) => {
    if (mat && s.material_id !== mat) return false;
    if (q) return `${s.p.name || ""} ${s.p.brand || ""} ${s.material_id}`.toLowerCase().includes(q.toLowerCase());
    return true;
  });
  const shortN = all.filter((s) => s.level === "short").length;
  const lowN = all.filter((s) => s.level === "low").length;
  const openReq = (requests.data || []).filter((r) => r.status !== "approved" && r.status !== "rejected").length;

  const addToCart = (s) => {
    if (cart.find((c) => c.product_id === s.product_id)) return;
    setCart([...cart, { product_id: s.product_id, product_name: s.p.name || s.product_id, qty: 1 }]);
  };
  const setQty = (pid, v) => setCart(cart.map((c) => c.product_id === pid ? { ...c, qty: v } : c));
  const bump = (pid, d) => setCart(cart.map((c) => c.product_id === pid ? { ...c, qty: Math.max(1, (Number(c.qty) || 0) + d) } : c));
  const removeItem = (pid) => setCart(cart.filter((c) => c.product_id !== pid));
  const submit = async () => {
    setBusy(true); setMsg(null);
    try {
      const r = await proc.createOrderRequest({ site_ref: siteRef, note, lines: cart.map((c) => ({ product_id: c.product_id, qty: Number(c.qty) })) });
      setMsg({ ok: true, text: `Request ${r.code} sent to the procurement supervisor for approval.` });
      setCart([]); setSiteRef(""); setNote(""); requests.reload();
    } catch (e) { setMsg({ ok: false, text: e.message }); } finally { setBusy(false); }
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-head text-2xl font-extrabold text-white">Hub stock &amp; orders</h1>
        <p className="mt-1 text-xs text-muted">Live hub inventory. Type the quantities you need and place a request; it routes to the hub's procurement supervisor, who approves it and sets the vendor and rate.</p>
      </div>
      {msg && (
        <div className={`rounded-xl px-4 py-2.5 text-sm ${msg.ok ? "bg-emerald-500/10 text-emerald-300" : "bg-red-500/10 text-red-300"}`}>{msg.text}</div>
      )}

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
              <div key={c.product_id} className="flex items-center gap-3 rounded-xl bg-panel2 nm-inset px-3 py-2 text-sm">
                <span className="flex-1 truncate text-white/90">{c.product_name}</span>
                <div className="flex items-center gap-1.5">
                  <button onClick={() => bump(c.product_id, -1)} className="grid h-7 w-7 place-items-center rounded-lg bg-panel text-muted nm-raised-sm nm-press hover:text-white"><Minus size={13} weight="bold" /></button>
                  <input type="number" step="any" value={c.qty} onChange={(e) => setQty(c.product_id, e.target.value)}
                    className="w-16 rounded-lg bg-bg px-2 py-1 text-center font-mono text-sm text-white outline-none focus:ring-2 focus:ring-accent/50" />
                  <button onClick={() => bump(c.product_id, 1)} className="grid h-7 w-7 place-items-center rounded-lg bg-panel text-muted nm-raised-sm nm-press hover:text-white"><Plus size={13} weight="bold" /></button>
                </div>
                <button onClick={() => removeItem(c.product_id)} className="grid h-7 w-7 place-items-center rounded-lg text-muted transition-colors hover:text-red-300"><X size={14} /></button>
              </div>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap items-end gap-3">
            <Field label="For project (optional)">
              <Select value={siteRef} onChange={(e) => setSiteRef(e.target.value)}>
                <option value="">not project-specific</option>
                {(sites.data || []).map((s) => <option key={s.id} value={s.code}>{s.code}{s.label ? ` - ${s.label}` : ""}{s.location ? ` (${s.location})` : ""}</option>)}
              </Select>
            </Field>
            <div className="min-w-[180px] flex-1"><Field label="Note"><Input value={note} placeholder="reason / urgency" onChange={(e) => setNote(e.target.value)} /></Field></div>
            <Button onClick={submit} disabled={busy}><PaperPlaneTilt size={15} weight="fill" />{busy ? "Sending..." : "Send to procurement"}</Button>
          </div>
        </Card>
      )}

      <Card title="Product stock" right={
        <div className="flex items-center gap-2">
          <div className="relative">
            <MagnifyingGlass size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input value={q} placeholder="search product / brand" onChange={(e) => setQ(e.target.value)}
              className="w-52 rounded-xl bg-panel2 nm-inset py-2 pl-9 pr-3 text-sm text-white placeholder:text-muted/70 outline-none focus:ring-2 focus:ring-accent/50" />
          </div>
          <Select value={mat} onChange={(e) => setMat(e.target.value)}>
            <option value="">all categories</option>
            {(materials.data || []).map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </Select>
        </div>}>
        <Table head={["Product", "Brand", "Category", "On hand", "Available", "Status", ""]}>
          {rows.map((s) => {
            const lv = LEVEL[s.level];
            const inCart = cart.some((c) => c.product_id === s.product_id);
            return (
              <tr key={s.product_id} className="border-b border-border/50">
                <Td className="text-white/90">{s.p.name || s.product_id}</Td>
                <Td className="text-muted">{s.p.brand || "-"}</Td>
                <Td className="text-muted">{s.material_id}</Td>
                <Td mono>{s.on_hand}</Td>
                <Td mono>{Math.max(0, s.available)}</Td>
                <Td><Badge tone={lv.tone}>{lv.label}</Badge></Td>
                <Td>
                  <Button size="sm" variant="ghost" disabled={inCart} onClick={() => addToCart(s)}>
                    {inCart ? "Added" : <><Plus size={13} weight="bold" />Request</>}
                  </Button>
                </Td>
              </tr>
            );
          })}
          {rows.length === 0 && <tr><Td className="text-muted">No stock rows{q || mat ? " match the filter" : " yet"}.</Td></tr>}
        </Table>
      </Card>

      <Card title="My order requests" right={<Button size="sm" variant="ghost" onClick={requests.reload}>Refresh</Button>}>
        {(requests.data || []).length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-8 text-center">
            <div className="grid h-11 w-11 place-items-center rounded-xl bg-panel2 nm-inset text-muted"><Package size={20} /></div>
            <p className="text-sm text-muted">No requests yet. Add products above and send them to procurement.</p>
          </div>
        ) : (
          <Table head={["Request", "For", "Items", "Status", "PO"]}>
            {(requests.data || []).map((r) => (
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
