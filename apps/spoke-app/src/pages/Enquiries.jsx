import { useState } from "react";
import { site } from "../api.js";
import { getUser } from "../auth.js";
import { Card, Table, Td, Badge, Button, useAsync, PageSkeleton } from "../components/ui.jsx";

const NEXT = { new: "contacted", contacted: "converted" };
const TONE = { new: "warn", contacted: "accent", converted: "ok", closed: "muted" };

export default function Enquiries() {
  const me = getUser();
  const mySpoke = me?.org_ref;
  const enquiries = useAsync(() => site.enquiries(mySpoke), [mySpoke]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  const setStatus = async (id, status) => {
    setBusy(true); setMsg(null);
    try { await site.updateEnquiry(id, status); enquiries.reload(); }
    catch (e) { setMsg(e.message); } finally { setBusy(false); }
  };

  const rows = enquiries.data || [];
  const open = rows.filter((r) => r.status === "new").length;

  if (enquiries.loading && !enquiries.data) return <PageSkeleton stats={0} rows={8} />;
  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-head text-2xl font-extrabold text-ink">Enquiries</h1>
          <p className="text-xs text-muted">Leads routed to your spoke by location. Contact them, then convert to an onboarded customer.</p>
        </div>
        <div className="flex items-center gap-2">
          {open > 0 && <Badge tone="warn">{open} new</Badge>}
          <Button size="sm" variant="ghost" onClick={enquiries.reload}>Refresh</Button>
        </div>
      </div>
      {msg && <p className="text-xs text-red-400">{msg}</p>}

      <Card title="Incoming enquiries">
        {rows.length === 0 ? <p className="text-sm text-muted">No enquiries for your area yet.</p> : (
          <Table head={["Name", "Contact", "Location", "Need", "Status", ""]}>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-border/50">
                <Td className="text-ink/85">{r.name}</Td>
                <Td className="text-muted">{[r.phone, r.email].filter(Boolean).join(" · ") || "-"}</Td>
                <Td>{r.location}</Td>
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
