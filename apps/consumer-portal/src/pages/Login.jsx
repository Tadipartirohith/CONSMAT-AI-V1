import { useState } from "react";
import { login } from "../auth.js";
import { publicApi } from "../api.js";

const field = "w-full border border-border bg-panel2 px-2.5 py-1.5 text-sm text-white outline-none focus:border-accent";
const label = "mb-1 block text-[11px] uppercase tracking-wider text-muted";

export default function Login({ onDone }) {
  const [mode, setMode] = useState("signin");   // signin | enquire
  return (
    <div className="grid min-h-screen place-items-center px-4">
      <div className="w-full max-w-sm border border-border bg-panel p-6">
        <div className="mb-4 flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center bg-accent font-mono text-sm font-bold text-black">C</div>
          <div>
            <p className="font-bold text-white">Consmat</p>
            <p className="text-[10px] text-muted">You Build, We Provide</p>
          </div>
        </div>

        <div className="mb-4 flex gap-1 border-b border-border">
          {["signin", "enquire"].map((m) => (
            <button key={m} onClick={() => setMode(m)}
              className={`px-3 py-2 text-sm ${mode === m ? "border-b-2 border-accent text-accent" : "text-muted hover:text-white"}`}>
              {m === "signin" ? "Sign in" : "New enquiry"}
            </button>
          ))}
        </div>

        {mode === "signin" ? <SignIn onDone={onDone} /> : <Enquire />}
      </div>
    </div>
  );
}

function SignIn({ onDone }) {
  const [email, setEmail] = useState("demo@consmat.com");
  const [password, setPassword] = useState("consmat123");
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try { await login(email, password); onDone(); }
    catch (e) { setErr(e.message); setBusy(false); }
  };
  return (
    <form onSubmit={submit} className="space-y-3">
      <label className="block"><span className={label}>Email</span>
        <input value={email} onChange={(e) => setEmail(e.target.value)} className={field} /></label>
      <label className="block"><span className={label}>Password</span>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className={field} /></label>
      <button type="submit" disabled={busy} className="w-full bg-accent px-3 py-2 text-sm font-semibold text-black hover:bg-accentHover disabled:opacity-40">
        {busy ? "Signing in…" : "Sign in"}
      </button>
      {err && <p className="text-xs text-red-400">{err}</p>}
      <p className="border-t border-border pt-3 text-[11px] text-muted">Demo: <span className="text-accent">demo@consmat.com</span> · consmat123</p>
    </form>
  );
}

function Enquire() {
  const [f, setF] = useState({ first: "", middle: "", last: "", phone: "", email: "", location: "", message: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [done, setDone] = useState(null);
  const fullName = [f.first, f.middle, f.last].map((s) => s.trim()).filter(Boolean).join(" ");
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try { setDone(await publicApi.enquire({ name: fullName, phone: f.phone, email: f.email, location: f.location, message: f.message })); }
    catch (e) { setErr(e.message); } finally { setBusy(false); }
  };
  if (done) {
    return (
      <div className="space-y-2 rounded border border-emerald-500/30 bg-emerald-500/5 p-3 text-sm">
        <p className="text-emerald-400">✓ Thank you, {fullName || "your enquiry is in"}!</p>
        <p className="text-white/80">
          {done.routed_to === "spoke"
            ? <>Your enquiry for <b>{f.location}</b> has been sent to our <b>{done.spoke}</b> team, who will contact you shortly.</>
            : <>We don't have a spoke covering <b>{f.location}</b> yet, so your enquiry has gone to our head-office team, who will reach out about serving your area.</>}
        </p>
        <button onClick={() => { setDone(null); setF({ first: "", middle: "", last: "", phone: "", email: "", location: "", message: "" }); }}
          className="text-[11px] text-accent hover:underline">Submit another enquiry</button>
      </div>
    );
  }
  return (
    <form onSubmit={submit} className="space-y-3">
      <p className="text-[11px] text-muted">Tell us about your project. We'll route you to the team covering your area.</p>
      <div className="grid grid-cols-3 gap-2">
        <label className="block"><span className={label}>First name</span>
          <input value={f.first} required onChange={(e) => setF({ ...f, first: e.target.value })} className={field} /></label>
        <label className="block"><span className={label}>Middle name</span>
          <input value={f.middle} onChange={(e) => setF({ ...f, middle: e.target.value })} className={field} /></label>
        <label className="block"><span className={label}>Last name</span>
          <input value={f.last} required onChange={(e) => setF({ ...f, last: e.target.value })} className={field} /></label>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <label className="block"><span className={label}>Phone</span>
          <input value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} className={field} /></label>
        <label className="block"><span className={label}>Email</span>
          <input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} className={field} /></label>
      </div>
      <label className="block"><span className={label}>Site location</span>
        <input value={f.location} required placeholder="e.g. Kompally, Hyderabad" onChange={(e) => setF({ ...f, location: e.target.value })} className={field} /></label>
      <label className="block"><span className={label}>Please share your requirement</span>
        <textarea value={f.message} rows={2} onChange={(e) => setF({ ...f, message: e.target.value })} className={field} /></label>
      <button type="submit" disabled={busy} className="w-full bg-accent px-3 py-2 text-sm font-semibold text-black hover:bg-accentHover disabled:opacity-40">
        {busy ? "Sending…" : "Submit enquiry"}
      </button>
      {err && <p className="text-xs text-red-400">{err}</p>}
    </form>
  );
}
