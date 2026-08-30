import { useState } from "react";
import { Link } from "react-router-dom";
import { site, CTYPES } from "../api.js";
import { Card, Table, Td, Badge, Button, Field, Input, Select, useAsync } from "../components/ui.jsx";
import LocationField from "../components/LocationField.jsx";

export default function Sites() {
  const sites = useAsync(() => site.sites());
  const consumers = useAsync(() => site.consumers());
  const [err, setErr] = useState(null);

  // Fund type is chosen at onboarding; the site inherits it (overridable later on the site page).
  const [f, setF] = useState({ consumer_id: "", label: "", location: "", area_sqft: "", floors: 1, construction_type: "standard" });
  const submit = async (e) => {
    e.preventDefault(); setErr(null);
    try {
      await site.createSite({
        consumer_id: f.consumer_id, label: f.label, location: f.location,
        area_sqft: Number(f.area_sqft), floors: Number(f.floors), construction_type: f.construction_type,
      });
      setF({ ...f, label: "", location: "", area_sqft: "" });
      sites.reload();
    } catch (e) { setErr(e.message); }
  };

  return (
    <div className="space-y-5">
      <h1 className="font-head text-2xl font-extrabold text-ink">Sites</h1>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Sites" className="lg:col-span-2" right={<Button size="sm" variant="ghost" onClick={sites.reload}>Refresh</Button>}>
          <Table head={["Site", "Label", "Location", "Area", "Type", "Stage", ""]}>
            {(sites.data || []).map((s) => (
              <tr key={s.id} className="border-b border-border/50">
                <Td><Link className="font-medium text-accent hover:underline" to={`/sites/${s.id}`}>{s.code}</Link></Td>
                <Td>{s.label || "-"}</Td>
                <Td>{s.location || "-"}</Td>
                <Td mono>{s.area_sqft} × {s.floors}f</Td>
                <Td>{s.project_type ? <Badge tone={s.project_type === "captive" ? "accent" : "ok"}>{s.project_type}</Badge> : <span className="text-[11px] text-muted">-</span>}</Td>
                <Td className="text-muted text-[11px]">{(s.stage || "onboarded").replace(/_/g, " ")}</Td>
                <Td><Link className="text-accent hover:underline" to={`/sites/${s.id}`}>open</Link></Td>
              </tr>
            ))}
            {sites.data?.length === 0 && <tr><Td className="text-muted">No sites yet.</Td></tr>}
          </Table>
        </Card>

        <Card title="New site">
          <form onSubmit={submit} className="space-y-3">
            <Field label="Consumer">
              <Select value={f.consumer_id} required onChange={(e) => setF({ ...f, consumer_id: e.target.value })}>
                <option value="">select…</option>
                {(consumers.data || []).map((c) => <option key={c.id} value={c.id}>{c.name} ({c.tier})</option>)}
              </Select>
            </Field>
            <Field label="Label"><Input value={f.label} placeholder="e.g. Villa A" onChange={(e) => setF({ ...f, label: e.target.value })} /></Field>
            <Field label="Location"><LocationField value={f.location} onChange={(v) => setF({ ...f, location: v })} /></Field>
            <div className="flex gap-2">
              <Field label="Area (sqft)"><Input type="number" step="any" value={f.area_sqft} required onChange={(e) => setF({ ...f, area_sqft: e.target.value })} /></Field>
              <Field label="Floors"><Input type="number" min="1" value={f.floors} onChange={(e) => setF({ ...f, floors: e.target.value })} /></Field>
            </div>
            <Field label="Construction type">
              <Select value={f.construction_type} onChange={(e) => setF({ ...f, construction_type: e.target.value })}>
                {CTYPES.map((c) => <option key={c} value={c}>{c}</option>)}
              </Select>
            </Field>
            <p className="text-[11px] text-muted">Fund type is inherited from the customer (set at onboarding); change it on the site page if needed.</p>
            <Button type="submit">Create site</Button>
            {err && <p className="text-xs text-red-400">{err}</p>}
          </form>
        </Card>
      </div>
    </div>
  );
}
