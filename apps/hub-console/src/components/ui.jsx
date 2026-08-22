import { useEffect, useState, useCallback } from "react";

export function Card({ title, right, children, className = "" }) {
  return (
    <div className={`border border-border bg-panel ${className}`}>
      {(title || right) && (
        <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
          <h3 className="text-sm font-semibold text-white">{title}</h3>
          {right}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}

export function Stat({ label, value, sub, accent }) {
  return (
    <div className="border border-border bg-panel p-4">
      <p className="text-[10px] uppercase tracking-wider text-muted">{label}</p>
      <p className={`mt-1 font-mono text-2xl font-bold ${accent ? "text-accent" : "text-white"}`}>{value}</p>
      {sub && <p className="mt-0.5 text-xs text-muted">{sub}</p>}
    </div>
  );
}

export function Button({ children, onClick, type = "button", variant = "primary", disabled, size = "md" }) {
  const styles = {
    primary: "bg-accent text-black hover:bg-accentHover font-semibold",
    ghost: "border border-border text-white/80 hover:bg-white/5",
    danger: "border border-red-500/40 text-red-400 hover:bg-red-500/10",
  };
  const sizes = { md: "px-3 py-1.5 text-sm", sm: "px-2 py-1 text-xs" };
  return (
    <button type={type} onClick={onClick} disabled={disabled}
      className={`inline-flex items-center gap-1.5 transition-colors disabled:opacity-40 ${styles[variant]} ${sizes[size]}`}>
      {children}
    </button>
  );
}

export function Field({ label, children }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] uppercase tracking-wider text-muted">{label}</span>
      {children}
    </label>
  );
}

const inputCls =
  "w-full border border-border bg-panel2 px-2.5 py-1.5 text-sm text-white outline-none focus:border-accent";

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
            {head.map((h) => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export function Td({ children, mono, className = "" }) {
  return <td className={`px-3 py-2 ${mono ? "font-mono" : ""} ${className}`}>{children}</td>;
}

export function Badge({ children, tone = "muted", className = "" }) {
  const tones = {
    muted: "bg-white/5 text-muted",
    ok: "bg-emerald-500/15 text-emerald-400",
    warn: "bg-[#f59e0b]/15 text-[#f59e0b]",
    bad: "bg-red-500/15 text-red-400",
    accent: "bg-accent/15 text-accent",
  };
  return <span className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${tones[tone]} ${className}`}>{children}</span>;
}

// tiny data hook
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
