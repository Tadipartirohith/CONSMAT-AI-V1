import { useState } from "react";
import { Link } from "react-router-dom";
import { site } from "../api.js";
import { Card, Stat, Table, Td, Badge, Select, useAsync } from "../components/ui.jsx";

export default function Dashboard() {
  const spokes = useAsync(() => site.spokes());
  const [spokeId, setSpokeId] = useState(null);
  const id = spokeId || spokes.data?.[0]?.id;

  const dash = useAsync(() => (id ? site.dashboard(id) : Promise.resolve(null)), [id]);
  const territory = useAsync(() => (id ? site.territory(id) : Promise.resolve([])), [id]);

  const d = dash.data;
  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="font-head text-2xl font-extrabold text-white">Territory</h1>
          <p className="text-xs text-muted">Spokesperson view: consumers, sites, and deliveries needing attention.</p>
        </div>
        <Select value={id || ""} onChange={(e) => setSpokeId(e.target.value)}>
          {(spokes.data || []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </Select>
      </div>

      {d && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Consumers" value={d.consumers.total} sub={Object.entries(d.consumers.by_tier).map(([k, v]) => `${v} ${k}`).join(" · ") || "—"} />
          <Stat label="Sites" value={d.sites.total} sub={Object.entries(d.sites.by_status).map(([k, v]) => `${v} ${k}`).join(" · ") || "—"} />
          <Stat label="Coverage" value={d.spoke.areas.length} sub={d.spoke.areas.join(", ") || "no areas"} />
          <Stat label="Needs attention" value={d.attention.length} accent={d.attention.length > 0} sub="short deliveries" />
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Sites in territory" className="lg:col-span-2">
          {territory.error ? <p className="text-sm text-red-400">{territory.error}</p> : (
            <Table head={["Site", "Consumer", "Tier", "Status", "Phase", ""]}>
              {(territory.data || []).map((s) => (
                <tr key={s.site_id} className="border-b border-border/50">
                  <Td mono>{s.site}</Td>
                  <Td>{s.consumer}</Td>
                  <Td>{s.tier}</Td>
                  <Td><Badge tone={s.status === "completed" ? "ok" : s.status === "active" ? "accent" : "muted"}>{s.status}</Badge></Td>
                  <Td mono>{s.current_phase ?? "—"}</Td>
                  <Td><Link className="text-accent hover:underline" to={`/sites/${s.site_id}`}>open →</Link></Td>
                </tr>
              ))}
              {territory.data?.length === 0 && <tr><Td className="text-muted">No sites yet — create one from the Sites tab.</Td></tr>}
            </Table>
          )}
        </Card>

        <Card title="Deliveries needing attention">
          {!d ? <p className="text-sm text-muted">Loading…</p> : d.attention.length === 0 ? (
            <p className="text-sm text-emerald-400">All deliveries fulfilled.</p>
          ) : (
            <div className="space-y-2">
              {d.attention.map((a, i) => (
                <div key={i} className="border border-[#f59e0b]/30 bg-[#f59e0b]/5 p-2.5 text-sm">
                  <p className="flex items-center gap-2">
                    <Link className="font-mono text-accent hover:underline" to={`/sites/${a.site.replace("SITE-", "")}`}>{a.site}</Link>
                    <Badge tone="warn">{a.status}</Badge>
                    <span className="text-muted">phase {a.phase_seq}</span>
                  </p>
                  <p className="mt-1 text-[#f59e0b]">Short: {a.short_materials.join(", ") || "—"}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
