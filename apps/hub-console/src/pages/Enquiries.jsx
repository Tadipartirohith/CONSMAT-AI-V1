import { useState } from "react";
import { site } from "../api.js";
import { Card, Table, Td, Badge, Button, Select, useAsync, PageSkeleton } from "../components/ui.jsx";

const NEXT = { new: "contacted", contacted: "converted" };
const TONE = { new: "warn", contacted: "accent", converted: "ok", closed: "muted" };

export default function Enquiries() {
  // Default to hub-routed leads (locations no spoke covers yet - the supervisor's queue).
  const [scope, setScope] = useState("hub");
  const enquiries = useAsync(() => site.enquiries(scope === "all" ? "" : scope), [scope]);
  const spokes = useAsync(() => site.spokes());
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  const spokeName = (id) => (spokes.data || []).find((s) => s.id === id)?.name || id;
  const setStatus = async (id, status) => {
    setBusy(true); setMsg(null);
    try { await site.updateEnquiry(id, status); enquiries.reload(); }
    catch (e) { setMsg(e.message); } finally { setBusy(false); }
  };
  const rows = enquiries.data || [];

  if (enquiries.loading && !enquiries.data) return <PageSkeleton stats={0} rows={8} />;
  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-head text-2xl font-extrabold text-ink">Enquiries</h1>
          <p className="text-xs text-muted">Customer enquiries. Hub-routed ones are for locations no spoke covers yet - grow coverage or handle directly.</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={scope} onChange={(e) => setScope(e.target.value)}>
            <option value="hub">Hub-routed (unserved)</option>
            <option value="spoke">Spoke-routed</option>
            <option value="all">All</option>
          </Select>
          <Button size="sm" variant="ghost" onClick={enquiries.reload}>Refresh</Button>
        </div>
      </div>
      {msg && <p className="text-xs text-red-400">{msg}</p>}

      <Card title={scope === "hub" ? "Unserved-location enquiries" : scope === "spoke" ? "Spoke-routed enquiries" : "All enquiries"}>
        {rows.length === 0 ? <p className="text-sm text-muted">No enquiries in this view.</p> : (
          <Table head={["Name", "Contact", "Location", "Routed to", "Need", "Status", ""]}>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-border/50">
                <Td className="text-ink/85">{r.name}</Td>
                <Td className="text-muted">{[r.phone, r.email].filter(Boolean).join(" · ") || "-"}</Td>
                <Td>{r.location}</Td>
                <Td>{r.routed_to === "spoke" ? <Badge tone="accent">{spokeName(r.spoke_id)}</Badge> : <Badge tone="bad">hub (unserved)</Badge>}</Td>
                <Td className="text-muted">{r.message || "-"}</Td>
                <Td><Badge tone={TONE[r.status]}>{r.status}</Badge></Td>
                <Td>
                  <div className="flex gap-1">
                    {NEXT[r.status] && <Button size="sm" onClick={() => setStatus(r.id, NEXT[r.status])} disabled={busy}>Mark {NEXT[r.status]}</Button>}
                    {r.status !== "closed" && r.status !== "converted" && <Button size="sm" variant="ghost" onClick={() => setStatus(r.id, "closed")} disabled={busy}>Close</Button>}
                  </div>
                </Td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </div>
  );
}
