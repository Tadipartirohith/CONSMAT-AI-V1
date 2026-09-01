import { useState } from "react";
import { site, TIERS, SEGMENTS } from "../api.js";
import { getUser } from "../auth.js";
import { Card, Table, Td, Badge, Button, Field, Input, Select, useAsync, PageSkeleton } from "../components/ui.jsx";
import LocationField from "../components/LocationField.jsx";

export default function Intake() {
  const spokes = useAsync(() => site.spokes());
  const consumers = useAsync(() => site.consumers());
  const [result, setResult] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);

  const [form, setForm] = useState({ name: "", tier: "individual", location: "", phone: "", email: "", fund_type: "captive", segment: "homeowner" });
  const submit = async (e) => {
    e.preventDefault(); setErr(null); setResult(null); setBusy(true);
    try {
      const r = await site.intake(form);
      setResult(r);
      setForm({ name: "", tier: "individual", location: "", phone: "", email: "", fund_type: "captive", segment: "homeowner" });
      consumers.reload();
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  if (spokes.loading && !spokes.data) return <PageSkeleton stats={0} rows={6} />;
  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-head text-2xl font-extrabold text-ink">Onboarding</h1>
        <p className="text-xs text-muted">Register a customer, auto-assign the serving spoke by location, and create their tracking login.</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="New client">
          <form onSubmit={submit} className="space-y-3">
            <Field label="Customer name"><Input value={form.name} required onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label="Customer tier">
                <Select value={form.tier} onChange={(e) => setForm({ ...form, tier: e.target.value })}>
                  {TIERS.map((t) => <option key={t} value={t}>{t}</option>)}
                </Select>
              </Field>
              <Field label="Segment (B2B / B2C)">
                <Select value={form.segment} onChange={(e) => setForm({ ...form, segment: e.target.value })}>
                  {SEGMENTS.map((s) => <option key={s} value={s} className="capitalize">{s}</option>)}
                </Select>
              </Field>
            </div>
            <Field label="Location (site area)"><LocationField value={form.location} onChange={(v) => setForm({ ...form, location: v })} /></Field>
            <Field label="Email (customer login)"><Input type="email" value={form.email} placeholder="customer@email.com - blank = auto id" onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
            <Field label="Phone"><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
            <Field label="Fund type">
              <Select value={form.fund_type} onChange={(e) => setForm({ ...form, fund_type: e.target.value })}>
                <option value="captive">Captive (financed in-house)</option>
                <option value="client">Client (customer pays)</option>
              </Select>
            </Field>
            <p className="text-[11px] text-muted">Each project defaults to this fund type; you can still change it per project.</p>
            <Button type="submit" disabled={busy}>{busy ? "Onboarding…" : "Onboard customer"}</Button>
            {err && <p className="text-xs text-red-400">{err}</p>}
            {result && (
              <div className="space-y-1 rounded border border-emerald-500/30 bg-emerald-500/5 p-3 text-sm">
                <p className="text-emerald-400">✓ {result.consumer.name} onboarded ({result.consumer.tier})</p>
                <p className="text-muted">Builder ID <span className="font-mono text-ink">{result.consumer.id}</span> · spoke <span className="text-ink">{result.assigned_spoke.name}</span></p>
                {result.login?.created ? (
                  <p className="text-muted">Login <span className="font-mono text-ink">{result.login.email}</span> · temp password <span className="font-mono text-ink">{result.login.temp_password}</span></p>
                ) : result.login ? (
                  <p className="text-[#f59e0b]">Login {result.login.email} could not be created ({result.login.error || "already exists"}).</p>
                ) : null}
              </div>
            )}
          </form>
        </Card>

        <Card title="Customers" className="lg:col-span-2" right={<Button size="sm" variant="ghost" onClick={consumers.reload}>Refresh</Button>}>
          <Table head={["Builder ID", "Name", "Tier", "Segment", "Fund type", "Login", "Phone"]}>
            {(consumers.data || []).map((c) => (
              <tr key={c.id} className="border-b border-border/50">
                <Td mono className="text-muted">{c.id}</Td>
                <Td>{c.name}</Td>
                <Td><Badge tone="accent">{c.tier}</Badge></Td>
                <Td>{c.segment ? <span className="text-[11px] capitalize text-ink/80">{c.segment}</span> : <span className="text-[11px] text-muted">-</span>}</Td>
                <Td>{c.fund_type ? <Badge tone={c.fund_type === "captive" ? "accent" : "ok"}>{c.fund_type}</Badge> : <span className="text-[11px] text-muted">-</span>}</Td>
                <Td mono className="text-muted">{c.email || `${c.id}@consmat.com`}</Td>
                <Td>{c.phone || "-"}</Td>
              </tr>
            ))}
            {consumers.data?.length === 0 && <tr><Td className="text-muted">No customers yet.</Td></tr>}
          </Table>
        </Card>
      </div>

      <SpokeCoverage spokes={spokes} />
    </div>
  );
}

function SpokeCoverage({ spokes }) {
  const me = getUser();
  const mySpokeId = me?.org_ref || spokes.data?.[0]?.id;
  const [msg, setMsg] = useState(null);
  const [area, setArea] = useState("");
  const detail = useAsync(() => (mySpokeId ? site.spoke(mySpokeId) : Promise.resolve(null)), [mySpokeId]);
  const areas = detail.data?.areas || [];

  const addArea = async (e) => {
    e.preventDefault(); setMsg(null);
    try {
      const r = await site.addArea(mySpokeId, area);
      setArea(""); detail.reload();
      setMsg(r?.applied ? "Region added." : "Request sent to supervisor/manager for approval.");
    } catch (e) { setMsg(e.message); }
  };
  return (
    <Card title="My coverage (geofenced regions)">
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <p className="mb-2 text-[11px] uppercase tracking-wider text-muted">Regions served by {detail.data?.name || "your spoke"}</p>
          <p className="text-sm text-ink/90">{areas.length ? areas.join(", ") : "no regions yet - add one"}</p>
        </div>
        <form onSubmit={addArea} className="flex items-end gap-2">
          <Field label="Add a region keyword"><Input value={area} required placeholder="e.g. Kompally" onChange={(e) => setArea(e.target.value)} /></Field>
          <Button type="submit">Add</Button>
        </form>
      </div>
      {msg && <p className="mt-2 text-xs text-muted">{msg}</p>}
    </Card>
  );
}
