import { useState } from "react";
import { site, PHASE_NAMES } from "../api.js";
import { Card, Table, Td, Badge, Button, useAsync } from "../components/ui.jsx";

const TOTAL_PHASES = 9;

export default function Projects() {
  const sites = useAsync(() => site.sites());
  const changes = useAsync(() => site.phaseChanges("pending"));
  const notifs = useAsync(() => site.notifications());
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const decide = async (id, approve) => {
    setBusy(true); setMsg(null);
    try { await site.decideChange(id, approve); setMsg({ ok: true, text: approve ? "Approved." : "Rejected." }); changes.reload(); sites.reload(); }
    catch (e) { setMsg({ ok: false, text: e.message }); } finally { setBusy(false); }
  };
  const tick = async () => {
    setBusy(true); setMsg(null);
    try { const r = await site.schedulerTick(); setMsg({ ok: true, text: `Scheduler ran: ${r.actions.length} action(s).` }); notifs.reload(); sites.reload(); }
    catch (e) { setMsg({ ok: false, text: e.message }); } finally { setBusy(false); }
  };

  const currentPhase = (s) => (s.phases || []).find((p) => p.status === "in_progress")?.phase_seq;
  const donePhases = (s) => (s.phases || []).filter((p) => p.status === "done").length;
  const shorts = (s) => (s.dispatches || []).flatMap((d) => d.lines.filter((l) => l.status === "short").map((l) => l.product_name || l.material_id));

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-head text-2xl font-extrabold text-white">Projects</h1>
          <p className="text-xs text-muted">Every construction site across the network (manager oversight).</p>
        </div>
        <Button size="sm" variant="ghost" onClick={tick} disabled={busy}>Run scheduler</Button>
      </div>
      {msg && <p className={`text-xs ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>}

      {changes.data?.length > 0 && (
        <Card title="Phase date changes awaiting approval">
          <Table head={["Site", "Phase", "Old end", "New end", "Requested by", ""]}>
            {changes.data.map((c) => (
              <tr key={c.id} className="border-b border-border/50">
                <Td mono>SITE-{c.site_id}</Td>
                <Td>{c.phase_seq}. {PHASE_NAMES[c.phase_seq]}</Td>
                <Td className="text-muted">{c.old_end || "-"}</Td>
                <Td>{c.new_end}</Td>
                <Td className="text-muted">{c.requested_by || c.requested_by_role}</Td>
                <Td>
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => decide(c.id, true)} disabled={busy}>Approve</Button>
                    <Button size="sm" variant="ghost" onClick={() => decide(c.id, false)} disabled={busy}>Reject</Button>
                  </div>
                </Td>
              </tr>
            ))}
          </Table>
        </Card>
      )}

      <Card title="Sites" right={<Button size="sm" variant="ghost" onClick={sites.reload}>Refresh</Button>}>
        {sites.error ? <p className="text-sm text-red-400">{sites.error}</p> : (
          <Table head={["Site", "Label", "Status", "Progress", "Current phase", "Alerts"]}>
            {(sites.data || []).map((s) => {
              const sh = shorts(s);
              return (
                <tr key={s.id} className="border-b border-border/50">
                  <Td mono>{s.code}</Td>
                  <Td>{s.label || "-"}</Td>
                  <Td><Badge tone={s.status === "completed" ? "ok" : s.status === "active" ? "accent" : "muted"}>{s.status}</Badge></Td>
                  <Td mono>{donePhases(s)}/{TOTAL_PHASES}</Td>
                  <Td className="text-muted">{currentPhase(s) ? `${currentPhase(s)}. ${PHASE_NAMES[currentPhase(s)]}` : "-"}</Td>
                  <Td>{sh.length > 0 ? <Badge tone="bad">{sh.length} short</Badge> : <span className="text-muted">-</span>}</Td>
                </tr>
              );
            })}
            {sites.data?.length === 0 && <tr><Td className="text-muted">No sites yet.</Td></tr>}
          </Table>
        )}
      </Card>

      <Card title="Recent notifications" right={<Button size="sm" variant="ghost" onClick={notifs.reload}>Refresh</Button>}>
        {(notifs.data || []).slice(0, 12).map((n) => (
          <div key={n.id} className="border-b border-border/50 py-1.5 text-sm">
            <span className="mr-2 font-mono text-[11px] text-muted">SITE-{n.site_id}</span>
            <Badge tone={n.kind === "dispatched" ? "ok" : "warn"}>{n.kind}</Badge>
            <span className="ml-2 text-white/80">{n.message}</span>
          </div>
        ))}
        {notifs.data?.length === 0 && <p className="text-sm text-muted">No notifications yet.</p>}
      </Card>
    </div>
  );
}
