import { useState } from "react";
import { Link } from "react-router-dom";
import { site } from "../api.js";
import { Card, Table, Td, Badge, Button, Field, Input, Select, useAsync } from "../components/ui.jsx";

const FIN_STATUS = ["pending", "in_progress", "approved", "rejected"];

export default function Finance() {
  const sites = useAsync(() => site.sites());
  const partners = useAsync(() => site.financePartners());
  const [msg, setMsg] = useState(null);

  // Finance handles captive projects (client projects are funded by the customer's own payment).
  const captive = (sites.data || []).filter((s) => s.project_type === "captive");

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-head text-2xl font-extrabold text-ink">Finance</h1>
        <p className="text-xs text-muted">Secure funding for captive projects from a preferred partner, and track status.</p>
      </div>
      {msg && <p className={`text-xs ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>}

      <Card title="Captive projects" right={<Button size="sm" variant="ghost" onClick={sites.reload}>Refresh</Button>}>
        {captive.length === 0 ? <p className="text-sm text-muted">No captive projects yet.</p> : (
          <div className="space-y-2">
            {captive.map((s) => (
              <FinanceRow key={s.id} s={s} partners={partners.data || []} onMsg={setMsg} />
            ))}
          </div>
        )}
      </Card>

      <PartnersCard partners={partners} onMsg={setMsg} />
    </div>
  );
}

function FinanceRow({ s, partners, onMsg }) {
  const fin = useAsync(() => site.projectFinance(s.id), [s.id]);
  const budget = useAsync(() => site.previewBudget(s.id).catch(() => null), [s.id]);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState(null);
  const f = fin.data;
  const state = form || { status: f?.status || "pending", eligibility: f?.eligibility || "pending", partner_id: f?.partner_id || "", amount: f?.amount ?? "", remarks: f?.remarks || "" };

  const save = async () => {
    setBusy(true);
    try {
      await site.updateFinance(s.id, {
        status: state.status, eligibility: state.eligibility,
        partner_id: state.partner_id ? Number(state.partner_id) : 0,
        amount: state.amount === "" ? undefined : Number(state.amount), remarks: state.remarks,
      });
      onMsg?.({ ok: true, text: `${s.code} finance updated.` }); setForm(null); fin.reload();
    } catch (e) { onMsg?.({ ok: false, text: e.message }); } finally { setBusy(false); }
  };

  return (
    <div className="border border-border/60 bg-panel2 p-3">
      <div className="mb-2 flex flex-wrap items-center gap-2 text-sm">
        <Link to={`/sites/${s.id}`} className="font-mono text-accent hover:underline">{s.code}</Link>
        <span className="text-ink/80">{s.label || "-"}</span>
        <span className="text-[11px] text-muted">{(s.stage || "").replace(/_/g, " ")}</span>
        {f && <Badge tone={f.status === "approved" ? "ok" : f.status === "rejected" ? "bad" : "warn"}>{f.status.replace("_", " ")}</Badge>}
        {f?.eligibility && f.eligibility !== "pending" && <Badge tone={f.eligibility === "eligible" ? "ok" : f.eligibility === "not_eligible" ? "bad" : "accent"}>{f.eligibility.replace("_", " ")}</Badge>}
        <span className="ml-auto text-[11px] text-muted">budget {budget.data?.total != null ? `Rs ${Math.round(budget.data.total)}` : (s.budget != null ? `Rs ${Math.round(s.budget)}` : "not issued")}</span>
      </div>
      <div className="flex flex-wrap items-end gap-2">
        <Field label="Eligibility">
          <Select value={state.eligibility} onChange={(e) => setForm({ ...state, eligibility: e.target.value })}>
            {["pending", "review", "eligible", "not_eligible"].map((x) => <option key={x} value={x}>{x.replace("_", " ")}</option>)}
          </Select>
        </Field>
        <Field label="Status">
          <Select value={state.status} onChange={(e) => setForm({ ...state, status: e.target.value })}>
            {FIN_STATUS.map((x) => <option key={x} value={x}>{x.replace("_", " ")}</option>)}
          </Select>
        </Field>
        <Field label="Partner">
          <Select value={state.partner_id} onChange={(e) => setForm({ ...state, partner_id: e.target.value })}>
            <option value="">- none -</option>
            {partners.filter((p) => p.active).map((p) => <option key={p.id} value={p.id}>{p.name} ({p.kind})</option>)}
          </Select>
        </Field>
        <Field label="Amount (Rs)"><Input type="number" step="any" value={state.amount} onChange={(e) => setForm({ ...state, amount: e.target.value })} /></Field>
        <div className="flex-1"><Field label="Remarks"><Input value={state.remarks} onChange={(e) => setForm({ ...state, remarks: e.target.value })} /></Field></div>
        <Button size="sm" onClick={save} disabled={busy}>Save</Button>
      </div>
    </div>
  );
}

function PartnersCard({ partners, onMsg }) {
  const [f, setF] = useState({ name: "", kind: "bank", note: "" });
  const [busy, setBusy] = useState(false);
  const add = async (e) => {
    e.preventDefault(); setBusy(true);
    try { await site.createFinancePartner(f); setF({ name: "", kind: "bank", note: "" }); partners.reload(); onMsg?.({ ok: true, text: "Partner added." }); }
    catch (e) { onMsg?.({ ok: false, text: e.message }); } finally { setBusy(false); }
  };
  return (
    <Card title="Preferred finance partners" right={<Button size="sm" variant="ghost" onClick={partners.reload}>Refresh</Button>}>
      <form onSubmit={add} className="mb-3 flex flex-wrap items-end gap-2 border-b border-border/60 pb-3">
        <Field label="Name"><Input value={f.name} required placeholder="e.g. ICICI Bank" onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
        <Field label="Kind">
          <Select value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}>
            {["bank", "nbfc", "internal"].map((k) => <option key={k} value={k}>{k}</option>)}
          </Select>
        </Field>
        <div className="flex-1"><Field label="Note"><Input value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} /></Field></div>
        <Button size="sm" type="submit" disabled={busy || !f.name.trim()}>Add partner</Button>
      </form>
      <Table head={["Name", "Kind", "Status", "Note"]}>
        {(partners.data || []).map((p) => (
          <tr key={p.id} className="border-b border-border/50">
            <Td className="text-ink/85">{p.name}</Td>
            <Td><Badge tone={p.kind === "internal" ? "accent" : "muted"}>{p.kind}</Badge></Td>
            <Td>{p.active ? <Badge tone="ok">active</Badge> : <Badge tone="muted">inactive</Badge>}</Td>
            <Td className="text-muted">{p.note || "-"}</Td>
          </tr>
        ))}
        {partners.data?.length === 0 && <tr><Td className="text-muted">No partners yet.</Td></tr>}
      </Table>
    </Card>
  );
}
