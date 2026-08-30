import { useState } from "react";
import { login } from "../auth.js";
import { publicApi } from "../api.js";

const field =
  "w-full rounded-xl bg-panel2 nm-inset px-3.5 py-2.5 text-sm text-white placeholder:text-muted/70 outline-none focus:ring-2 focus:ring-accent/50";
const label = "mb-1.5 block text-[11px] uppercase tracking-wider text-muted";
const primaryBtn =
  "w-full rounded-xl bg-accent py-2.5 text-sm font-semibold text-black nm-raised-sm nm-press hover:brightness-105 disabled:opacity-40";

export default function Login({ onDone }) {
  const [mode, setMode] = useState("signin"); // signin | enquire
  return (
    <div className="relative grid min-h-[100dvh] place-items-center overflow-hidden px-4">
      <div className="pointer-events-none absolute -top-40 left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-accent/10 blur-3xl" />
      <div className="relative w-full max-w-sm rounded-2xl bg-panel nm-raised p-7">
        <div className="mb-5 flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-xl bg-accent nm-raised-sm font-mono text-lg font-bold text-black">C</div>
          <div>
            <p className="font-head text-lg font-bold leading-tight text-white">Consmat</p>
            <p className="text-[11px] text-muted">You build, we provide</p>
          </div>
        </div>

        <div className="mb-5 grid grid-cols-2 gap-1 rounded-xl bg-panel2 nm-inset p-1">
          {[["signin", "Sign in"], ["enquire", "New enquiry"]].map(([m, lbl]) => (
            <button key={m} onClick={() => setMode(m)}
              className={`rounded-lg py-2 text-sm font-medium transition-all ${
                mode === m ? "bg-panel nm-raised-sm text-accent" : "text-muted hover:text-white"
              }`}>
              {lbl}
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
    <form onSubmit={submit} className="space-y-4">
      <label className="block"><span className={label}>Email</span>
        <input value={email} onChange={(e) => setEmail(e.target.value)} className={field} /></label>
      <label className="block"><span className={label}>Password</span>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className={field} /></label>
      <button type="submit" disabled={busy} className={primaryBtn}>{busy ? "Signing in..." : "Sign in"}</button>
      {err && <p className="text-xs text-red-300">{err}</p>}
      <p className="pt-1 text-center text-[11px] text-muted">Demo: <span className="text-accent">demo@consmat.com</span> / consmat123</p>
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
      <div className="space-y-2 rounded-xl bg-panel2 nm-inset p-4 text-sm">
        <p className="font-semibold text-emerald-300">Thank you, {fullName || "your enquiry is in"}.</p>
        <p className="text-white/80">
          {done.routed_to === "spoke"
            ? <>Your enquiry for <b className="text-white">{f.location}</b> has been sent to our <b className="text-white">{done.spoke}</b> team, who will contact you shortly.</>
            : <>We don't have a spoke covering <b className="text-white">{f.location}</b> yet, so your enquiry has gone to our head-office team, who will reach out about serving your area.</>}
        </p>
        <button onClick={() => { setDone(null); setF({ first: "", middle: "", last: "", phone: "", email: "", location: "", message: "" }); }}
          className="text-[11px] text-accent hover:underline">Submit another enquiry</button>
      </div>
    );
  }
  return (
    <form onSubmit={submit} className="space-y-3.5">
      <p className="text-[11px] text-muted">Tell us about your project. We'll route you to the team covering your area.</p>
      <div className="grid grid-cols-3 gap-2">
        <label className="block"><span className={label}>First</span>
          <input value={f.first} required onChange={(e) => setF({ ...f, first: e.target.value })} className={field} /></label>
        <label className="block"><span className={label}>Middle</span>
          <input value={f.middle} onChange={(e) => setF({ ...f, middle: e.target.value })} className={field} /></label>
        <label className="block"><span className={label}>Last</span>
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
      <button type="submit" disabled={busy} className={primaryBtn}>{busy ? "Sending..." : "Submit enquiry"}</button>
      {err && <p className="text-xs text-red-300">{err}</p>}
    </form>
  );
}
