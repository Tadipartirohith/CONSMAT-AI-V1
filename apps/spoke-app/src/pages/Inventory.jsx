import { useMemo, useState } from "react";
import { inv, proc } from "../api.js";
import { Card, Table, Td, Badge, Button, Field, Input, Select, useAsync } from "../components/ui.jsx";

// Read hub stock + raise a stock-order request to the hub (the hub approves and sets vendor/rate).
function tone(s) {
  const rv = Number(s.reserved) || 0, av = Number(s.available) || 0;
  if (rv <= 0) return "green";
  const r = av / rv;
  if (r < 1) return "red";
  if (r < 1.5) return "orange";
  if (r < 3) return "yellow";
  return "green";
}
const TONE = { green: "#22c55e", yellow: "#eab308", orange: "#f59e0b", red: "#ef4444" };

export default function Inventory() {
  const pstock = useAsync(() => inv.productStock());
  const products = useAsync(() => inv.products());
  const materials = useAsync(() => inv.materials());
  const requests = useAsync(() => proc.orderRequests());
  const [q, setQ] = useState("");
  const [mat, setMat] = useState("");
  const [cart, setCart] = useState([]);
  const [siteRef, setSiteRef] = useState("");
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const nameMap = useMemo(() => Object.fromEntries((products.data || []).map((p) => [p.id, p])), [products.data]);
  const rows = (pstock.data || []).map((s) => ({ ...s, p: nameMap[s.product_id] || {} })).filter((s) => {
    if (mat && s.material_id !== mat) return false;
    if (q) {
      const hay = `${s.p.name || ""} ${s.p.brand || ""} ${s.material_id}`.toLowerCase();
      if (!hay.includes(q.toLowerCase())) return false;
    }
    return true;
  });

  const addToCart = (s) => {
    if (cart.find((c) => c.product_id === s.product_id)) return;
    setCart([...cart, { product_id: s.product_id, product_name: s.p.name || s.product_id, qty: 1 }]);
  };
  const setQty = (pid, v) => setCart(cart.map((c) => c.product_id === pid ? { ...c, qty: v } : c));
  const removeItem = (pid) => setCart(cart.filter((c) => c.product_id !== pid));
  const submit = async () => {
    setBusy(true); setMsg(null);
    try {
      const r = await proc.createOrderRequest({ site_ref: siteRef, note, lines: cart.map((c) => ({ product_id: c.product_id, qty: Number(c.qty) })) });
      setMsg({ ok: true, text: `Request ${r.code} sent to hub for approval.` });
      setCart([]); setSiteRef(""); setNote(""); requests.reload();
    } catch (e) { setMsg({ ok: false, text: e.message }); } finally { setBusy(false); }
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-head text-2xl font-extrabold text-white">Hub stock & orders</h1>
        <p className="text-xs text-muted">Live hub stock (read-only). Add items to a stock-order request; the hub approves it and sets the vendor + rate.</p>
      </div>
      {msg && <p className={`text-xs ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>}

      {cart.length > 0 && (
        <Card title={`Order request (${cart.length})`}>
          <div className="space-y-1.5">
            {cart.map((c) => (
              <div key={c.product_id} className="flex items-center gap-2 text-sm">
                <span className="flex-1 truncate text-white/85">{c.product_name}</span>
                <div className="w-24"><Input type="number" step="any" value={c.qty} onChange={(e) => setQty(c.product_id, e.target.value)} /></div>
                <Button size="sm" variant="ghost" onClick={() => removeItem(c.product_id)}>✕</Button>
              </div>
            ))}
          </div>
          <div className="mt-2 flex flex-wrap items-end gap-2">
            <Field label="For project (optional)"><Input value={siteRef} placeholder="e.g. SITE-3" onChange={(e) => setSiteRef(e.target.value)} /></Field>
            <div className="flex-1"><Field label="Note"><Input value={note} placeholder="reason / urgency" onChange={(e) => setNote(e.target.value)} /></Field></div>
            <Button onClick={submit} disabled={busy}>Send request to hub</Button>
          </div>
        </Card>
      )}

      <Card title="Product stock" right={
        <div className="flex items-center gap-2">
          <div className="w-48"><Input value={q} placeholder="search product / brand" onChange={(e) => setQ(e.target.value)} /></div>
          <Select value={mat} onChange={(e) => setMat(e.target.value)}>
            <option value="">all categories</option>
            {(materials.data || []).map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </Select>
        </div>}>
        <Table head={["Product", "Brand", "Category", "On hand", "Available", "Status", ""]}>
          {rows.map((s) => (
            <tr key={s.product_id} className="border-b border-border/50">
              <Td className="text-white/85">{s.p.name || s.product_id}</Td>
              <Td className="text-muted">{s.p.brand || "-"}</Td>
              <Td className="text-muted">{s.material_id}</Td>
              <Td mono>{s.on_hand}</Td>
              <Td mono>{Math.max(0, s.available)}</Td>
              <Td><span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: TONE[tone(s)] }} /></Td>
              <Td><Button size="sm" variant="ghost" onClick={() => addToCart(s)}>Request</Button></Td>
            </tr>
          ))}
          {rows.length === 0 && <tr><Td className="text-muted">No stock rows{q || mat ? " match the filter" : " yet"}.</Td></tr>}
        </Table>
      </Card>

      <Card title="My order requests" right={<Button size="sm" variant="ghost" onClick={requests.reload}>Refresh</Button>}>
        {(requests.data || []).length === 0 ? <p className="text-sm text-muted">No requests yet.</p> : (
          <Table head={["Request", "For", "Items", "Status", "PO"]}>
            {(requests.data || []).map((r) => (
              <tr key={r.id} className="border-b border-border/50">
                <Td mono>{r.code}</Td>
                <Td className="text-muted">{r.site_ref || "-"}</Td>
                <Td className="text-muted">{r.lines.map((l) => `${l.product_name} ×${l.qty}`).join(", ")}</Td>
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
