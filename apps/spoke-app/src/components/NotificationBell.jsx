import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell } from "@phosphor-icons/react";
import { site } from "../api.js";
import { getUser } from "../auth.js";

// Top-right bell: shows all unread notifications for this spoke, with a live count.
export default function NotificationBell() {
  const me = getUser();
  const spoke = me?.org_ref;
  const base = spoke ? `spoke_id=${spoke}${me?.role === "finance" ? "&audience=finance" : ""}` : "";
  const query = `${base}${base ? "&" : ""}unread_only=true`;
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const nav = useNavigate();
  const ref = useRef(null);

  const load = () => site.notifications(query).then(setItems).catch(() => {});
  useEffect(() => {
    load();
    const t = setInterval(load, 60000);   // keep the unread count fresh
    return () => clearInterval(t);
  }, [query]); // eslint-disable-line

  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const count = items.length;
  const openRow = async (n) => {
    try { await site.markNotifRead(n.id); } catch { /* ignore */ }
    setOpen(false);
    if (n.site_id) nav(`/sites/${n.site_id}`);
    load();
  };
  const markAll = async () => {
    try { if (spoke) await site.markAllReadSpoke(spoke); } catch { /* ignore */ }
    load();
  };

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => { setOpen((v) => !v); if (!open) load(); }}
        className="relative grid h-10 w-10 place-items-center rounded-xl bg-panel text-white/80 nm-raised-sm nm-press hover:text-white"
        aria-label={`Notifications${count ? `, ${count} unread` : ""}`}>
        <Bell size={19} weight={count ? "fill" : "regular"} />
        {count > 0 && (
          <span className="absolute -right-1 -top-1 grid h-5 min-w-[20px] place-items-center rounded-full bg-accent px-1 text-[10px] font-bold text-black">
            {count > 99 ? "99+" : count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-30 mt-2 w-[360px] max-w-[calc(100vw-2rem)] overflow-hidden rounded-2xl bg-panel nm-raised">
          <div className="flex items-center justify-between border-b border-border/50 px-4 py-2.5">
            <p className="text-sm font-semibold text-white">Notifications{count ? ` (${count})` : ""}</p>
            {count > 0 && <button onClick={markAll} className="text-[11px] text-accent hover:underline">Mark all read</button>}
          </div>
          <div className="max-h-96 overflow-auto">
            {count === 0 ? (
              <p className="px-4 py-6 text-center text-sm text-muted">You are all caught up.</p>
            ) : items.map((n) => (
              <button key={n.id} onClick={() => openRow(n)}
                className="flex w-full items-start gap-2.5 border-b border-border/40 px-4 py-2.5 text-left transition-colors hover:bg-white/[0.03]">
                <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-accent" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-white/90">{n.message}</p>
                  <p className="mt-0.5 text-[11px] text-muted">
                    {n.site_id ? `SITE-${n.site_id}` : "General"}
                    {n.created_at ? ` · ${new Date(n.created_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}` : ""}
                  </p>
                </div>
              </button>
            ))}
          </div>
          <button onClick={() => { setOpen(false); nav("/notifications"); }}
            className="w-full border-t border-border/50 px-4 py-2.5 text-center text-xs text-accent hover:bg-white/[0.03]">
            View all notifications
          </button>
        </div>
      )}
    </div>
  );
}
