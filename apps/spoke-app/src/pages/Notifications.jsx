import { useState } from "react";
import { Link } from "react-router-dom";
import { site } from "../api.js";
import { getUser } from "../auth.js";
import { Card, Badge, Button, useAsync } from "../components/ui.jsx";

const ICON = {
  design_uploaded: "📐", design_updated: "📐", boq_submitted: "📋", boq_diff_flagged: "⚠️",
  boq_final_submitted: "📋", boq_spoke_approved: "✅", boq_hub_approved: "✅", boq_approved: "✅",
  boq_change_requested: "✏️", boq_change_ack: "✏️", boq_changed: "✏️", boq_updated: "📋",
  out_of_stock: "⛔", low_stock: "⚠️", budget_issued: "💰", budget_updated: "💰",
  finance_submitted: "🏦", finance_approved: "🏦", finance_rejected: "🚫", finance_eligibility: "🏦",
  started: "🏗️", dispatched: "🚚", dispatch_pending: "⏳", received: "📦", phase_done: "✅",
  project_done: "🎉", confirm_reminder: "🔔",
};

export default function Notifications() {
  const me = getUser();
  const spoke = me?.org_ref;
  const q = spoke ? `spoke_id=${spoke}${me?.role === "finance" ? "&audience=finance" : ""}` : "";
  const notifs = useAsync(() => site.notifications(q), [q]);
  const [busy, setBusy] = useState(false);
  const rows = notifs.data || [];
  const unread = rows.filter((n) => !n.read).length;
  const markAll = async () => {
    setBusy(true);
    try { await site.markAllReadSpoke(spoke); notifs.reload(); } finally { setBusy(false); }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-head text-2xl font-extrabold text-white">Notifications</h1>
          <p className="text-xs text-muted">{me?.role === "finance" ? "Finance updates for your captive projects." : "Live end-to-end updates across your spoke's projects."}</p>
        </div>
        <div className="flex items-center gap-2">
          {unread > 0 && <Badge tone="warn">{unread} new</Badge>}
          {unread > 0 && <Button size="sm" variant="ghost" onClick={markAll} disabled={busy}>Mark all read</Button>}
          <Button size="sm" variant="ghost" onClick={notifs.reload}>Refresh</Button>
        </div>
      </div>
      <Card title="Recent">
        {rows.length === 0 ? <p className="text-sm text-muted">No notifications yet.</p> : (
          <div className="space-y-1.5">
            {rows.map((n) => (
              <div key={n.id} className={`flex items-start gap-2 border-b border-border/50 pb-1.5 text-sm ${n.read ? "" : "bg-accent/5"}`}>
                <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.read ? "bg-transparent" : "bg-accent"}`} />
                <span className="text-base">{ICON[n.kind] || "🔔"}</span>
                <div className="min-w-0 flex-1">
                  <span className={n.read ? "text-white/70" : "text-white/90"}>{n.message}</span>
                  {n.site_id ? <Link to={`/sites/${n.site_id}`} className="ml-2 text-[11px] text-accent hover:underline">SITE-{n.site_id}</Link> : null}
                </div>
                {n.created_at && <span className="shrink-0 text-[11px] text-muted">{new Date(n.created_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</span>}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
