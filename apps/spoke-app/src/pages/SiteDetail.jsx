import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { site } from "../api.js";
import { Card, Table, Td, Badge, Button, useAsync } from "../components/ui.jsx";

const PHASE_NAMES = {
  1: "Excavation & footing", 2: "Foundation & plinth", 3: "RCC superstructure",
  4: "Masonry / brickwork", 5: "Roofing / slab", 6: "Internal plastering",
  7: "External plastering", 8: "Flooring & tiling", 9: "MEP & finishing",
};

export default function SiteDetail() {
  const { id } = useParams();
  const detail = useAsync(() => site.siteDetail(id), [id]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  const s = detail.data;
  const act = async (fn, label) => {
    setBusy(true); setMsg(null);
    try { await fn(); setMsg({ ok: true, text: `${label} done.` }); detail.reload(); }
    catch (e) { setMsg({ ok: false, text: e.message }); } finally { setBusy(false); }
  };

  if (detail.error) return <p className="text-sm text-red-400">{detail.error}</p>;
  if (!s) return <p className="text-sm text-muted">Loading…</p>;

  const planned = s.bom_lines.length > 0;
  const phase1 = s.phases.find((p) => p.phase_seq === 1);
  const inProgress = s.phases.find((p) => p.status === "in_progress");
  const notStarted = planned && phase1 && phase1.status === "pending";
  const hasShorts = s.dispatches.some((d) => d.lines.some((l) => l.status === "short"));

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Link to="/sites" className="text-sm text-muted hover:text-white">← Sites</Link>
        <h1 className="font-head text-2xl font-extrabold text-white">{s.code}</h1>
        <Badge tone={s.status === "completed" ? "ok" : s.status === "active" ? "accent" : "muted"}>{s.status}</Badge>
      </div>
      {msg && <p className={`text-xs ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>}

      <div className="flex flex-wrap gap-4 border border-border bg-panel p-4 text-sm">
        <Info label="Label" value={s.label || "-"} />
        <Info label="Location" value={s.location || "-"} />
        <Info label="Area" value={`${s.area_sqft} sqft × ${s.floors} floor(s)`} />
        <Info label="Type" value={s.construction_type} />
        <Info label="Built-up" value={`${s.total_area} sqft`} />
        <div className="ml-auto flex items-center gap-2">
          {!planned && <Button onClick={() => act(() => site.plan(id), "Plan generated")} disabled={busy}>Generate plan (architect)</Button>}
          {notStarted && <Button onClick={() => act(() => site.start(id), "Started")} disabled={busy}>Start construction</Button>}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Bill of materials">
          {!planned ? <p className="text-sm text-muted">No plan yet, the architect must generate the BOM.</p> : (
            <Table head={["Material", "Total qty"]}>
              {s.bom_lines.map((b) => (
                <tr key={b.material_id} className="border-b border-border/50">
                  <Td>{b.material_id}</Td>
                  <Td mono>{b.total_qty}</Td>
                </tr>
              ))}
            </Table>
          )}
        </Card>

        <Card title="Construction phases">
          <div className="space-y-1.5">
            {s.phases.sort((a, b) => a.phase_seq - b.phase_seq).map((p) => (
              <div key={p.phase_seq} className="flex items-center gap-3 border border-border/60 bg-panel2 px-3 py-2">
                <span className="w-5 font-mono text-xs text-muted">{p.phase_seq}</span>
                <span className="flex-1 text-sm text-white/80">{PHASE_NAMES[p.phase_seq]}</span>
                <Badge tone={p.status === "done" ? "ok" : p.status === "in_progress" ? "accent" : "muted"}>{p.status}</Badge>
                {p.status === "in_progress" && (
                  <Button size="sm" onClick={() => act(() => site.completePhase(id, p.phase_seq), `Phase ${p.phase_seq} completed`)} disabled={busy}>
                    Complete (civil eng.)
                  </Button>
                )}
              </div>
            ))}
          </div>
          {inProgress && <p className="mt-2 text-[11px] text-muted">Completing a phase triggers hub dispatch of the next phase's materials.</p>}
        </Card>
      </div>

      <Card title="Dispatches (hub → site)"
        right={hasShorts && (
          <Button size="sm" onClick={() => act(() => site.backfill(id), "Backfill")} disabled={busy}>
            Backfill shortfalls
          </Button>
        )}>
        {s.dispatches.length === 0 ? <p className="text-sm text-muted">No dispatches yet.</p> : (
          <div className="space-y-2">
            {s.dispatches.sort((a, b) => a.phase_seq - b.phase_seq).map((d) => (
              <div key={d.id} className="border border-border/60 bg-panel2 p-3">
                <div className="mb-1.5 flex items-center gap-2 text-sm">
                  <span className="font-mono text-white">{d.code}</span>
                  <span className="text-muted">phase {d.phase_seq}, {PHASE_NAMES[d.phase_seq]}</span>
                  <Badge tone={d.status === "dispatched" ? "ok" : d.status === "partial" ? "warn" : "bad"}>{d.status}</Badge>
                </div>
                <div className="flex flex-wrap gap-2">
                  {d.lines.map((l, i) => (
                    <span key={i} className={`font-mono text-xs ${l.status === "short" ? "text-red-400" : "text-white/70"}`}>
                      {l.material_id} ×{l.qty}{l.status === "short" && " (short)"}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

function Info({ label, value }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-muted">{label}</p>
      <p className="text-white">{value}</p>
    </div>
  );
}
