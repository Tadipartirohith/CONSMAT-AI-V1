import { useState } from "react";
import { inv, MATERIALS, inr } from "../api.js";
import { Card, Table, Td, Badge, Button, Field, Input, Select, useAsync } from "../components/ui.jsx";

export default function Inventory() {
  const stock = useAsync(() => inv.stock());
  const [ledgerFor, setLedgerFor] = useState(null);
  const [msg, setMsg] = useState(null);

  const [form, setForm] = useState({ material_id: "cement", qty: "", unit_cost: "" });
  const submitInbound = async (e) => {
    e.preventDefault();
    setMsg(null);
    try {
      await inv.inbound({ material_id: form.material_id, qty: Number(form.qty), unit_cost: Number(form.unit_cost), ref_type: "manual" });
      setForm({ ...form, qty: "", unit_cost: "" });
      setMsg({ ok: true, text: "Inbound recorded." });
      stock.reload();
    } catch (e) { setMsg({ ok: false, text: e.message }); }
  };

  return (
    <div className="space-y-5">
      <h1 className="font-head text-2xl font-extrabold text-white">Inventory</h1>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Stock positions" className="lg:col-span-2" right={<Button size="sm" variant="ghost" onClick={stock.reload}>Refresh</Button>}>
          {stock.error ? <p className="text-sm text-red-400">{stock.error}</p> : (
            <Table head={["Material", "On hand", "Reserved", "Available", "Avg cost", ""]}>
              {(stock.data || []).map((r) => (
                <tr key={r.material_id} className="border-b border-border/50">
                  <Td>{r.material_id}</Td>
                  <Td mono>{r.on_hand}</Td>
                  <Td mono>{r.reserved}</Td>
                  <Td mono>{r.available} {r.available <= 0 && <Badge tone="bad">out</Badge>}</Td>
                  <Td mono>{inr(r.avg_cost)}</Td>
                  <Td><Button size="sm" variant="ghost" onClick={() => setLedgerFor(r.material_id)}>Ledger</Button></Td>
                </tr>
              ))}
            </Table>
          )}
        </Card>

        <Card title="Receive stock (inbound)">
          <form onSubmit={submitInbound} className="space-y-3">
            <Field label="Material">
              <Select value={form.material_id} onChange={(e) => setForm({ ...form, material_id: e.target.value })}>
                {MATERIALS.map((m) => <option key={m} value={m}>{m}</option>)}
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
        <Table head={["Dir", "Qty", "Unit cost", "Balance", "Ref"]}>
          {(ledger.data || []).map((e) => (
            <tr key={e.id} className="border-b border-border/50">
              <Td><Badge tone={e.direction === "inbound" ? "ok" : e.direction === "outbound" ? "warn" : "muted"}>{e.direction}</Badge></Td>
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
