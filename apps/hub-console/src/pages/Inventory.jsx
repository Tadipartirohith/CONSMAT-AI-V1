import { useState } from "react";
import { inv, inr } from "../api.js";
import { Card, Table, Td, Badge, Button, Field, Input, Select, useAsync } from "../components/ui.jsx";

export default function Inventory() {
  const materials = useAsync(() => inv.materials());
  const products = useAsync(() => inv.products());
  const pstock = useAsync(() => inv.productStock());
  const low = useAsync(() => inv.lowStock());
  const [ledgerFor, setLedgerFor] = useState(null);
  const [msg, setMsg] = useState(null);
  const [form, setForm] = useState({ product_id: "", qty: "", unit_cost: "" });

  const reload = () => { pstock.reload(); low.reload(); };
  const stockOf = (pid) => (pstock.data || []).find((s) => s.product_id === pid);
  const lowByProduct = Object.fromEntries((low.data || []).map((l) => [l.product_id, l]));

  const submitInbound = async (e) => {
    e.preventDefault();
    setMsg(null);
    if (!form.product_id) { setMsg({ ok: false, text: "Pick a product." }); return; }
    try {
      await inv.productInbound({ product_id: form.product_id, qty: Number(form.qty), unit_cost: Number(form.unit_cost), ref_type: "manual" });
      setForm({ ...form, qty: "", unit_cost: "" });
      setMsg({ ok: true, text: "Inbound recorded." });
      reload();
    } catch (e) { setMsg({ ok: false, text: e.message }); }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="font-head text-2xl font-extrabold text-white">Inventory</h1>
        <Button size="sm" variant="ghost" onClick={reload}>Refresh</Button>
      </div>

      {low.data?.length > 0 && (
        <Card title="Low / no stock (below 3x committed demand)">
          <Table head={["Product", "On hand", "Reserved", "3x target", "Shortfall", ""]}>
            {low.data.map((l) => (
              <tr key={l.product_id} className="border-b border-border/50">
                <Td>{l.product_id}</Td>
                <Td mono>{l.on_hand}</Td>
                <Td mono>{l.reserved}</Td>
                <Td mono>{l.buffer_target}</Td>
                <Td mono>{l.shortfall}</Td>
                <Td><Badge tone={l.status === "no_stock" ? "bad" : "warn"}>{l.status === "no_stock" ? "no stock" : "low"}</Badge></Td>
              </tr>
            ))}
          </Table>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          {(materials.data || []).map((m) => {
            const prods = (products.data || []).filter((p) => p.material_id === m.id);
            return (
              <Card key={m.id} title={`${m.name} (${m.category || m.id})`}>
                <Table head={["Product", "Brand", "On hand", "Reserved", "Available", "Avg cost", ""]}>
                  {prods.map((p) => {
                    const s = stockOf(p.id);
                    const lowRow = lowByProduct[p.id];
                    return (
                      <tr key={p.id} className="border-b border-border/50">
                        <Td>{p.name}</Td>
                        <Td className="text-muted">{p.brand || "-"}</Td>
                        <Td mono>{s ? s.on_hand : 0}</Td>
                        <Td mono>{s ? s.reserved : 0}</Td>
                        <Td mono>{s ? s.available : 0} {lowRow && <Badge tone={lowRow.status === "no_stock" ? "bad" : "warn"}>{lowRow.status === "no_stock" ? "no stock" : "low"}</Badge>}</Td>
                        <Td mono>{s ? inr(s.avg_cost) : "-"}</Td>
                        <Td><Button size="sm" variant="ghost" onClick={() => setLedgerFor(m.id)}>Ledger</Button></Td>
                      </tr>
                    );
                  })}
                  {prods.length === 0 && <tr><Td className="text-muted">No products in this category.</Td></tr>}
                </Table>
              </Card>
            );
          })}
        </div>

        <Card title="Receive stock (inbound)">
          <form onSubmit={submitInbound} className="space-y-3">
            <Field label="Product (brand)">
              <Select value={form.product_id} required onChange={(e) => setForm({ ...form, product_id: e.target.value })}>
                <option value="">select a product…</option>
                {(products.data || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </Select>
            </Field>
            <Field label="Quantity"><Input type="number" step="any" value={form.qty} required onChange={(e) => setForm({ ...form, qty: e.target.value })} /></Field>
            <Field label="Unit cost (₹)"><Input type="number" step="any" value={form.unit_cost} required onChange={(e) => setForm({ ...form, unit_cost: e.target.value })} /></Field>
            <Button type="submit">Record inbound</Button>
            {msg && <p className={`text-xs ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>}
          </form>
        </Card>
      </div>

      {ledgerFor && <LedgerCard material={ledgerFor} onClose={() => setLedgerFor(null)} />}
    </div>
  );
}

function LedgerCard({ material, onClose }) {
  const ledger = useAsync(() => inv.ledger(material), [material]);
  return (
    <Card title={`Ledger, ${material}`} right={<Button size="sm" variant="ghost" onClick={onClose}>Close</Button>}>
      {ledger.error ? <p className="text-sm text-red-400">{ledger.error}</p> : (
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
        </Table>
      )}
    </Card>
  );
}
