import { Link } from "react-router-dom";
import { site } from "../api.js";
import { getUser } from "../auth.js";
import { Card, Stat, Table, Td, Badge, useAsync } from "../components/ui.jsx";

export default function Dashboard() {
  const spokes = useAsync(() => site.spokes());
  // A spokesperson is tied to one spoke (org_ref); no picker needed.
  const me = getUser();
  const id = me?.org_ref || spokes.data?.[0]?.id;

  const dash = useAsync(() => (id ? site.dashboard(id) : Promise.resolve(null)), [id]);
  const territory = useAsync(() => (id ? site.territory(id) : Promise.resolve([])), [id]);

  const d = dash.data;
  const regions = d?.spoke?.areas || [];

  return (
    <div className="space-y-5">
      <div className="rounded-lg border border-border bg-gradient-to-br from-panel to-panel2 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[11px] uppercase tracking-wider text-accent">Coverage · geofenced service area</p>
            <h1 className="font-head text-2xl font-extrabold text-white">{d?.spoke?.name || "My coverage"}</h1>
            <p className="mt-0.5 text-xs text-muted">Hi {me?.name || "there"} - your consumers, sites and deliveries needing attention.</p>
          </div>
          <div className="text-right">
            <p className="text-[10px] uppercase tracking-wider text-muted">Regions served</p>
            <p className="mt-1 max-w-xs text-sm text-white/90">{regions.length ? regions.join(", ") : "no regions yet"}</p>
          </div>
        </div>
      </div>

      {d && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Consumers" value={d.consumers.total} accent sub={Object.entries(d.consumers.by_tier).map(([k, v]) => `${v} ${k}`).join(" · ") || "-"} />
          <Stat label="Sites" value={d.sites.total} sub={Object.entries(d.sites.by_status).map(([k, v]) => `${v} ${k}`).join(" · ") || "-"} />
          <Stat label="Regions" value={regions.length} sub="geofence keywords" />
          <Stat label="Needs attention" value={d.attention.length} sub="short deliveries" />
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Sites in coverage" className="lg:col-span-2">
          {territory.error ? <p className="text-sm text-red-400">{territory.error}</p> : (
            <Table head={["Site", "Consumer", "Tier", "Status", "Phase", ""]}>
              {(territory.data || []).map((s) => (
                <tr key={s.site_id} className="border-b border-border/50">
                  <Td mono>{s.site}</Td>
                  <Td>{s.consumer}</Td>
                  <Td><Badge tone="accent">{s.tier}</Badge></Td>
                  <Td><Badge tone={s.status === "completed" ? "ok" : s.status === "active" ? "accent" : "muted"}>{s.status}</Badge></Td>
                  <Td mono>{s.current_phase ?? "-"}</Td>
                  <Td><Link className="text-accent hover:underline" to={`/sites/${s.site_id}`}>open </Link></Td>
                </tr>
              ))}
              {territory.data?.length === 0 && <tr><Td className="text-muted">No sites yet - onboard a consumer, then create a site.</Td></tr>}
            </Table>
          )}
        </Card>

        <Card title="Deliveries needing attention">
          {!d ? <p className="text-sm text-muted">Loading…</p> : d.attention.length === 0 ? (
            <p className="text-sm text-emerald-400">All deliveries fulfilled.</p>
          ) : (
            <div className="space-y-2">
              {d.attention.map((a, i) => (
                <div key={i} className="rounded border border-[#f59e0b]/30 bg-[#f59e0b]/5 p-2.5 text-sm">
                  <p className="flex items-center gap-2">
                    <Link className="font-mono text-accent hover:underline" to={`/sites/${a.site.replace("SITE-", "")}`}>{a.site}</Link>
                    <Badge tone="warn">{a.status}</Badge>
                    <span className="text-muted">phase {a.phase_seq}</span>
                  </p>
                  <p className="mt-1 text-[#f59e0b]">Short: {a.short_materials.join(", ") || "-"}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
