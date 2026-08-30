import { useEffect, useState, useCallback } from "react";

// Soft-UI shape scale (locked): containers rounded-2xl, controls rounded-xl, pills rounded-full.

export function Card({ title, right, children, className = "" }) {
  return (
    <div className={`rounded-2xl bg-panel nm-raised ${className}`}>
      {(title || right) && (
        <div className="flex items-center justify-between border-b border-border/50 px-5 py-3">
          <h3 className="font-head text-sm font-semibold text-ink">{title}</h3>
          {right}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

export function Badge({ children, tone = "muted", className = "" }) {
  const tones = {
    muted: "bg-muted/10 text-muted",
    ok: "bg-emerald-500/15 text-emerald-300",
    warn: "bg-[#f59e0b]/15 text-[#fbbf24]",
    bad: "bg-red-500/15 text-red-300",
    accent: "bg-accent/15 text-accent",
  };
  return <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${tones[tone]} ${className}`}>{children}</span>;
}

export function Progress({ pct }) {
  return (
    <div className="h-2.5 w-full overflow-hidden rounded-full bg-panel2 nm-inset">
      <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${pct}%` }} />
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
export function Skeleton({ className = "" }) {
  return <div className={`animate-pulse rounded-lg bg-muted/15 ${className}`} />;
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
