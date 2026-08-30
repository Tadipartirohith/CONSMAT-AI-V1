import { useEffect, useState, useCallback } from "react";

// Consmat premium component kit. Quiet elevation (hairline + soft shadow), Signal Amber accent,
// Geist type, one radius scale (controls rounded-lg, cards rounded-2xl, pills rounded-full).

export function Card({ title, right, children, className = "" }) {
  return (
    <div className={`rounded-2xl bg-panel nm-raised ${className}`}>
      {(title || right) && (
        <div className="flex items-center justify-between gap-3 border-b border-border/70 px-5 py-3.5">
          <h3 className="font-head text-sm font-semibold text-ink">{title}</h3>
          {right}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

export function Stat({ label, value, sub, accent }) {
  return (
    <div className="rounded-2xl bg-panel nm-raised p-5">
      <p className="text-[10px] font-medium uppercase tracking-[0.08em] text-muted">{label}</p>
      <p className={`mt-1.5 font-mono text-2xl font-semibold tracking-tight ${accent ? "text-accent" : "text-ink"}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-muted">{sub}</p>}
    </div>
  );
}

export function Button({ children, onClick, type = "button", variant = "primary", disabled, size = "md" }) {
  const styles = {
    primary: "bg-accent text-onAccent font-semibold nm-press hover:bg-accentHover",
    ghost: "bg-panel text-ink/85 nm-raised-sm nm-press hover:text-ink hover:bg-panel2",
    danger: "bg-panel text-red-400 nm-raised-sm nm-press hover:text-red-300",
  };
  const sizes = { md: "px-4 py-2 text-sm", sm: "px-3 py-1.5 text-xs" };
  return (
    <button type={type} onClick={onClick} disabled={disabled}
      className={`inline-flex items-center justify-center gap-1.5 rounded-lg disabled:opacity-40 disabled:pointer-events-none ${styles[variant]} ${sizes[size]}`}>
      {children}
    </button>
  );
}

export function Field({ label, children }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-[0.08em] text-muted">{label}</span>
      {children}
    </label>
  );
}

const inputCls =
  "w-full rounded-lg bg-panel2 nm-inset px-3 py-2 text-sm text-ink placeholder:text-muted/60 outline-none focus:ring-2 focus:ring-accent/45";

export function Input(props) {
  return <input {...props} className={inputCls} />;
}

export function Select({ children, ...props }) {
  return <select {...props} className={inputCls}>{children}</select>;
}

export function Table({ head, children }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-[11px] font-medium uppercase tracking-[0.06em] text-muted">
            {head.map((h) => <th key={h} className="px-3 py-2.5 font-medium">{h}</th>)}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export function Td({ children, mono, className = "" }) {
  return <td className={`px-3 py-2.5 ${mono ? "font-mono" : ""} ${className}`}>{children}</td>;
}

export function Badge({ children, tone = "muted", className = "" }) {
  const tones = {
    muted: "bg-muted/[0.12] text-muted",
    ok: "bg-emerald-500/15 text-emerald-300",
    warn: "bg-amber-400/15 text-amber-300",
    bad: "bg-red-500/15 text-red-300",
    accent: "bg-accent/15 text-accent",
  };
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${tones[tone]} ${className}`}>{children}</span>;
}

// ---- polish primitives ----
export function Skeleton({ className = "" }) {
  return <div className={`animate-pulse rounded-lg bg-muted/[0.12] ${className}`} />;
}

export function Empty({ icon, title, hint }) {
  return (
    <div className="flex flex-col items-center gap-2 py-10 text-center">
      {icon && <div className="grid h-11 w-11 place-items-center rounded-xl bg-panel2 nm-inset text-muted">{icon}</div>}
      <p className="text-sm font-medium text-ink/90">{title}</p>
      {hint && <p className="max-w-xs text-xs text-muted">{hint}</p>}
    </div>
  );
}

export function useAsync(fn, deps = []) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const run = useCallback(() => {
    setLoading(true);
    fn().then((d) => { setData(d); setError(null); }).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, deps); // eslint-disable-line
  useEffect(() => { run(); }, [run]);
  return { data, error, loading, reload: run };
}
export function PageSkeleton({ stats = 0, rows = 6 }) {
  return (
    <div className="space-y-5">
      <Skeleton className="h-7 w-56" />
      {stats > 0 && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {Array.from({ length: stats }).map((_, i) => (
            <div key={i} className="space-y-2.5 rounded-2xl bg-panel nm-raised p-5">
              <Skeleton className="h-2.5 w-20" /><Skeleton className="h-6 w-16" />
            </div>
          ))}
        </div>
      )}
      <div className="space-y-3 rounded-2xl bg-panel nm-raised p-5">
        {Array.from({ length: rows }).map((_, i) => <Skeleton key={i} className="h-4 w-full" />)}
      </div>
    </div>
  );
}
