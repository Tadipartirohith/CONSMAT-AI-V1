import { useState } from "react";
import { login } from "../auth.js";

const DEMO = [
  ["manager@consmat.com", "Hub Manager"],
  ["supervisor@consmat.com", "Hub Supervisor"],
  ["hr@consmat.com", "HR"],
  ["ops@consmat.com", "Operations"],
];

const inputCls =
  "w-full rounded-lg bg-panel2 nm-inset px-3.5 py-2.5 text-sm text-white outline-none focus:ring-2 focus:ring-accent/45";
const labelCls = "mb-1.5 block text-[11px] font-medium uppercase tracking-[0.08em] text-muted";

export default function Login({ onDone }) {
  const [email, setEmail] = useState("manager@consmat.com");
  const [password, setPassword] = useState("consmat123");
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await login(email, password);
      onDone();
    } catch (e) {
      setErr(e.message);
      setBusy(false);
    }
  };

  return (
    <div className="relative grid min-h-[100dvh] place-items-center overflow-hidden bg-bg px-4">
      <div className="pointer-events-none absolute -top-40 left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-accent/10 blur-3xl" />
      <div className="relative w-full max-w-sm rounded-2xl bg-panel nm-raised p-7">
        <div className="mb-6 flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-lg bg-accent font-mono text-lg font-bold text-black nm-raised-sm">C</div>
          <div>
            <p className="font-head text-lg font-bold leading-tight text-white">Consmat Hub</p>
            <p className="text-[11px] text-muted">Operations console</p>
          </div>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <label className="block">
            <span className={labelCls}>Email</span>
            <input value={email} onChange={(e) => setEmail(e.target.value)} className={inputCls} />
          </label>
          <label className="block">
            <span className={labelCls}>Password</span>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className={inputCls} />
          </label>
          <button type="submit" disabled={busy}
            className="w-full rounded-lg bg-accent py-2.5 text-sm font-semibold text-black nm-press hover:bg-accentHover disabled:opacity-40">
            {busy ? "Signing in..." : "Sign in"}
          </button>
          {err && <p className="text-xs text-red-300">{err}</p>}
        </form>

        <div className="mt-6">
          <p className="mb-2 text-[10px] font-medium uppercase tracking-[0.08em] text-muted">Demo accounts (password: consmat123)</p>
          <div className="flex flex-wrap gap-2">
            {DEMO.map(([em, label]) => (
              <button key={em} onClick={() => setEmail(em)}
                className={`rounded-lg px-2.5 py-1 text-[11px] transition-colors ${
                  email === em ? "bg-panel2 nm-inset text-accent" : "bg-panel nm-raised-sm text-white/70 hover:text-white"
                }`}>
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
