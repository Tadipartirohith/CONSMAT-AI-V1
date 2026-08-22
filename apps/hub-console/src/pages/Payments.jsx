import { useState } from "react";
import { pay, inr } from "../api.js";
import { Card, Table, Td, Badge, Button, Field, Input, useAsync } from "../components/ui.jsx";

export default function Payments() {
  const cfg = useAsync(() => pay.config());
  const list = useAsync(() => pay.list());
  const [msg, setMsg] = useState(null);

  const [form, setForm] = useState({ ref: "SITE-1", consumer_id: "c_demo", amount: "" });
  const record = async (e) => {
    e.preventDefault();
    setMsg(null);
    try {
      const p = await pay.create({ ref: form.ref, consumer_id: form.consumer_id, amount: Number(form.amount) });
      setForm({ ...form, amount: "" });
      setMsg({ ok: true, text: `${p.code} ${p.status} (${p.provider}).` });
      list.reload();
    } catch (e) { setMsg({ ok: false, text: e.message }); }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="font-head text-2xl font-extrabold text-white">Payments</h1>
          <p className="text-xs text-muted">Config-driven gateway; provider set in payment-service config.yaml.</p>
        </div>
        {cfg.data && <Badge tone="accent">{cfg.data.provider} · {cfg.data.currency}</Badge>}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Payments" className="lg:col-span-2" right={<Button size="sm" variant="ghost" onClick={list.reload}>Refresh</Button>}>
          {list.error ? <p className="text-sm text-red-400">{list.error}</p> : (
            <Table head={["Payment", "For", "Payer", "Amount", "Escrow released", "Provider", "Status"]}>
              {(list.data || []).map((p) => {
                const tone = p.status === "paid" || p.status === "released" ? "ok"
                  : p.status === "held" ? "accent" : p.status === "pending" ? "warn" : "bad";
                const relPct = p.amount ? Math.round(((p.released_amount || 0) / p.amount) * 100) : 0;
                const escrow = p.status === "held" || p.status === "released";
                return (
                <tr key={p.id} className="border-b border-border/50">
                  <Td mono>{p.code}</Td>
                  <Td>{p.ref || "-"}</Td>
                  <Td className="text-muted">{p.consumer_id || "-"}</Td>
                  <Td mono>{inr(p.amount)}</Td>
                  <Td mono className="text-muted">{escrow ? `${inr(p.released_amount || 0)} · ${relPct}%` : "-"}</Td>
                  <Td>{p.provider}</Td>
                  <Td><Badge tone={tone}>{p.status}</Badge></Td>
                </tr>
                );
              })}
              {list.data?.length === 0 && <tr><Td className="text-muted">No payments yet.</Td></tr>}
            </Table>
          )}
        </Card>

        <Card title="Record a payment">
          <form onSubmit={record} className="space-y-3">
            <Field label="For (ref)"><Input value={form.ref} onChange={(e) => setForm({ ...form, ref: e.target.value })} /></Field>
            <Field label="Payer (consumer id)"><Input value={form.consumer_id} onChange={(e) => setForm({ ...form, consumer_id: e.target.value })} /></Field>
            <Field label="Amount (₹)"><Input type="number" step="any" value={form.amount} required onChange={(e) => setForm({ ...form, amount: e.target.value })} /></Field>
            <Button type="submit">Take payment</Button>
            {msg && <p className={`text-xs ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>}
          </form>
        </Card>
      </div>
    </div>
  );
}
