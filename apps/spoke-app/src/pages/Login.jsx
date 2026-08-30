import { useState } from "react";
import { login } from "../auth.js";

const DEMO = [
  ["spoke@consmat.com", "Spokesperson"],
  ["architect@consmat.com", "Architect"],
  ["site@consmat.com", "Site engineer"],
];

const inputCls =
  "w-full rounded-xl bg-panel2 nm-inset px-3.5 py-2.5 text-sm text-ink outline-none focus:ring-2 focus:ring-accent/50";
const labelCls = "mb-1.5 block text-[11px] uppercase tracking-wider text-muted";

export default function Login({ onDone }) {
  const [email, setEmail] = useState("spoke@consmat.com");
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
    <div className="relative grid min-h-[100dvh] place-items-center overflow-hidden px-4">
      <div className="pointer-events-none absolute -top-40 left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-accent/10 blur-3xl" />
      <div className="relative w-full max-w-sm rounded-2xl bg-panel nm-raised p-7">
        <div className="mb-6 flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-xl bg-accent nm-raised-sm font-mono text-lg font-bold text-onAccent">C</div>
          <div>
            <p className="font-head text-lg font-bold leading-tight text-ink">Consmat Field</p>
            <p className="text-[11px] text-muted">Spoke workspace</p>
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
            className="w-full rounded-xl bg-accent py-2.5 text-sm font-semibold text-onAccent nm-press hover:bg-accentHover disabled:opacity-40">
            {busy ? "Signing in..." : "Sign in"}
          </button>
          {err && <p className="text-xs text-red-300">{err}</p>}
        </form>

        <div className="mt-6">
          <p className="mb-2 text-[10px] uppercase tracking-wider text-muted">Demo accounts (password: consmat123)</p>
          <div className="flex flex-wrap gap-2">
            {DEMO.map(([em, label]) => (
              <button key={em} onClick={() => setEmail(em)}
                className={`rounded-lg px-2.5 py-1 text-[11px] transition-colors ${
                  email === em ? "bg-panel2 nm-inset text-accent" : "bg-panel nm-raised-sm text-ink/70 hover:text-ink"
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
