import { useState } from "react";
import { login } from "../auth.js";

const DEMO = [
  ["manager@consmat.com", "Hub Manager"],
  ["supervisor@consmat.com", "Hub Supervisor"],
  ["ops@consmat.com", "Operations"],
];

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
    <div className="grid min-h-screen place-items-center px-4">
      <div className="w-full max-w-sm border border-border bg-panel p-6">
        <div className="mb-5 flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center bg-accent font-mono text-sm font-bold text-black">C</div>
          <div>
            <p className="font-bold text-white">Consmat Hub Console</p>
            <p className="text-[10px] text-muted">Manager · Supervisor · Operations</p>
          </div>
        </div>
        <form onSubmit={submit} className="space-y-3">
          <label className="block">
            <span className="mb-1 block text-[11px] uppercase tracking-wider text-muted">Email</span>
            <input value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-border bg-panel2 px-2.5 py-1.5 text-sm text-white outline-none focus:border-accent" />
          </label>
          <label className="block">
            <span className="mb-1 block text-[11px] uppercase tracking-wider text-muted">Password</span>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-border bg-panel2 px-2.5 py-1.5 text-sm text-white outline-none focus:border-accent" />
          </label>
          <button type="submit" disabled={busy}
            className="w-full bg-accent px-3 py-2 text-sm font-semibold text-black hover:bg-accentHover disabled:opacity-40">
            {busy ? "Signing in…" : "Sign in"}
          </button>
          {err && <p className="text-xs text-red-400">{err}</p>}
        </form>
        <div className="mt-4 border-t border-border pt-3">
          <p className="mb-1 text-[10px] uppercase tracking-wider text-muted">Demo accounts (password: consmat123)</p>
          {DEMO.map(([em, label]) => (
            <button key={em} onClick={() => setEmail(em)} className="mr-2 text-[11px] text-accent hover:underline">{label}</button>
          ))}
        </div>
      </div>
    </div>
  );
}
