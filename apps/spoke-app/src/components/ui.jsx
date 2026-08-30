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

export function Stat({ label, value, sub, accent }) {
  return (
    <div className="rounded-2xl bg-panel nm-raised p-5">
      <p className="text-[10px] uppercase tracking-wider text-muted">{label}</p>
      <p className={`mt-1 font-mono text-2xl font-bold ${accent ? "text-accent" : "text-ink"}`}>{value}</p>
      {sub && <p className="mt-0.5 text-xs text-muted">{sub}</p>}
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
      <span className="mb-1.5 block text-[11px] uppercase tracking-wider text-muted">{label}</span>
      {children}
    </label>
  );
}

const inputCls =
  "w-full rounded-xl bg-panel2 nm-inset px-3.5 py-2 text-sm text-ink placeholder:text-muted/70 outline-none focus:ring-2 focus:ring-accent/50";

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
          <tr className="border-b border-border text-left text-[11px] uppercase tracking-wider text-muted">
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
    muted: "bg-muted/10 text-muted",
    ok: "bg-emerald-500/15 text-emerald-300",
    warn: "bg-[#f59e0b]/15 text-[#fbbf24]",
    bad: "bg-red-500/15 text-red-300",
    accent: "bg-accent/15 text-accent",
  };
  return <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${tones[tone]} ${className}`}>{children}</span>;
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
