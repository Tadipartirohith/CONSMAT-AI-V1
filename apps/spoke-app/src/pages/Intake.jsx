import { useState } from "react";
import { site, TIERS } from "../api.js";
import { Card, Table, Td, Badge, Button, Field, Input, Select, useAsync } from "../components/ui.jsx";

export default function Intake() {
  const spokes = useAsync(() => site.spokes());
  const consumers = useAsync(() => site.consumers());
  const [result, setResult] = useState(null);
  const [err, setErr] = useState(null);

  const [form, setForm] = useState({ name: "", tier: "individual", location: "", phone: "" });
  const submit = async (e) => {
    e.preventDefault(); setErr(null); setResult(null);
    try {
      const r = await site.intake(form);
      setResult(r);
      setForm({ name: "", tier: "individual", location: "", phone: "" });
      consumers.reload();
    } catch (e) { setErr(e.message); }
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-head text-2xl font-extrabold text-white">Consumer Intake</h1>
        <p className="text-xs text-muted">Classify the consumer and auto-assign the serving spoke by location (geofence).</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="New intake">
          <form onSubmit={submit} className="space-y-3">
            <Field label="Name"><Input value={form.name} required onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <Field label="Consumer tier">
              <Select value={form.tier} onChange={(e) => setForm({ ...form, tier: e.target.value })}>
                {TIERS.map((t) => <option key={t} value={t}>{t}</option>)}
              </Select>
            </Field>
            <Field label="Location (site area)"><Input value={form.location} required placeholder="e.g. Medchal" onChange={(e) => setForm({ ...form, location: e.target.value })} /></Field>
            <Field label="Phone"><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
            <Button type="submit">Intake & assign</Button>
            {err && <p className="text-xs text-red-400">{err}</p>}
            {result && (
              <div className="border border-emerald-500/30 bg-emerald-500/5 p-2.5 text-sm">
                <p className="text-emerald-400">✓ {result.consumer.name} ({result.consumer.tier})</p>
                <p className="text-muted">assigned to <span className="text-white">{result.assigned_spoke.name}</span></p>
              </div>
            )}
          </form>
        </Card>

        <Card title="Consumers" className="lg:col-span-2" right={<Button size="sm" variant="ghost" onClick={consumers.reload}>Refresh</Button>}>
          <Table head={["ID", "Name", "Tier", "Spoke", "Phone"]}>
            {(consumers.data || []).map((c) => (
              <tr key={c.id} className="border-b border-border/50">
                <Td mono className="text-muted">{c.id}</Td>
                <Td>{c.name}</Td>
                <Td><Badge tone="accent">{c.tier}</Badge></Td>
                <Td mono className="text-muted">{c.spoke_id}</Td>
                <Td>{c.phone || "—"}</Td>
              </tr>
            ))}
          </Table>
        </Card>
      </div>

      <SpokeCoverage spokes={spokes} />
    </div>
  );
}

function SpokeCoverage({ spokes }) {
  const [msg, setMsg] = useState(null);
  const [form, setForm] = useState({ spoke_id: "", area: "" });
  const addArea = async (e) => {
    e.preventDefault(); setMsg(null);
    try { await site.addArea(form.spoke_id, form.area); setForm({ ...form, area: "" }); spokes.reload(); setMsg("Coverage added."); }
    catch (e) { setMsg(e.message); }
  };
  return (
    <Card title="Spoke coverage (geofence)">
      <div className="grid gap-4 md:grid-cols-2">
        <Table head={["Spoke", "Areas covered"]}>
          {(spokes.data || []).map((s) => (
            <tr key={s.id} className="border-b border-border/50">
              <Td>{s.name}</Td>
              <Td className="text-muted">{s.geofence || "—"}</Td>
            </tr>
          ))}
        </Table>
        <form onSubmit={addArea} className="flex items-end gap-2">
          <Field label="Spoke">
            <Select value={form.spoke_id} required onChange={(e) => setForm({ ...form, spoke_id: e.target.value })}>
              <option value="">select…</option>
              {(spokes.data || []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </Select>
          </Field>
          <Field label="Area keyword"><Input value={form.area} required placeholder="e.g. Kompally" onChange={(e) => setForm({ ...form, area: e.target.value })} /></Field>
          <Button type="submit">Add</Button>
        </form>
      </div>
      {msg && <p className="mt-2 text-xs text-muted">{msg}</p>}
    </Card>
  );
}
