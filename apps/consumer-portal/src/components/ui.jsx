import { useEffect, useState, useCallback } from "react";

export function Card({ title, right, children, className = "" }) {
  return (
    <div className={`border border-border bg-panel ${className}`}>
      {title && <div className="flex items-center justify-between border-b border-border px-4 py-2.5"><h3 className="text-sm font-semibold text-white">{title}</h3>{right}</div>}
      <div className="p-4">{children}</div>
    </div>
  );
}

export function Badge({ children, tone = "muted" }) {
  const tones = {
    muted: "bg-white/5 text-muted",
    ok: "bg-emerald-500/15 text-emerald-400",
    warn: "bg-[#f59e0b]/15 text-[#f59e0b]",
    bad: "bg-red-500/15 text-red-400",
    accent: "bg-accent/15 text-accent",
  };
  return <span className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${tones[tone]}`}>{children}</span>;
}

export function Progress({ pct }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-panel2">
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
