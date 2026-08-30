import { useEffect, useRef, useState } from "react";
import { getUser, logout } from "../auth.js";
import { getThemePref, setThemePref } from "../theme.js";

const THEMES = [["light", "Light"], ["dark", "Dark"], ["system", "System"]];

function initials(name) {
  return (name || "?").split(" ").map((s) => s[0]).filter(Boolean).slice(0, 2).join("").toUpperCase();
}

// Profile menu: identity, appearance (light / dark / system), and sign out.
export default function ProfileMenu() {
  const u = getUser();
  const [open, setOpen] = useState(false);
  const [pref, setPref] = useState(getThemePref());
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [open]);

  const pick = (p) => { setPref(p); setThemePref(p); };

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen((v) => !v)}
        className="grid h-9 w-9 place-items-center rounded-full bg-accent/20 font-mono text-sm font-bold text-accent nm-press"
        aria-label="Profile and settings">
        {initials(u?.name)}
      </button>

      {open && (
        <div className="absolute right-0 z-40 mt-2 w-64 overflow-hidden rounded-2xl bg-panel nm-raised">
          <div className="flex items-center gap-3 border-b border-border/70 px-4 py-3.5">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-accent/20 font-mono text-sm font-bold text-accent">{initials(u?.name)}</span>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-ink">{u?.name}</p>
              <p className="truncate text-[11px] text-muted">{u?.id}</p>
            </div>
          </div>

          <div className="px-4 py-3.5">
            <p className="mb-2 text-[10px] font-medium uppercase tracking-[0.08em] text-muted">Appearance</p>
            <div className="grid grid-cols-3 gap-1 rounded-lg bg-panel2 nm-inset p-1">
              {THEMES.map(([v, l]) => (
                <button key={v} onClick={() => pick(v)}
                  className={`rounded-md py-1.5 text-xs font-medium transition-colors ${pref === v ? "bg-panel text-accent nm-raised-sm" : "text-muted hover:text-ink"}`}>{l}</button>
              ))}
            </div>
          </div>

          <button onClick={logout}
            className="w-full border-t border-border/70 px-4 py-3 text-left text-sm text-ink transition-colors hover:bg-muted/10">
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
