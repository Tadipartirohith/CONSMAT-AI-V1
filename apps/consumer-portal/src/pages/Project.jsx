import { Link, useParams } from "react-router-dom";
import { site, progressOf, PHASE_NAMES } from "../api.js";
import { Card, Badge, Progress, useAsync } from "../components/ui.jsx";

export default function Project({ me }) {
  const { id } = useParams();
  const detail = useAsync(() => site.siteDetail(id), [id]);
  const s = detail.data;

  if (detail.error) return <p className="text-sm text-red-400">{detail.error}</p>;
  if (!s) return <p className="text-sm text-muted">Loading…</p>;
  if (me && s.consumer_id !== me) {
    return <p className="text-sm text-muted">This project belongs to another account.</p>;
  }

  const pr = progressOf(s);
  const phases = [...s.phases].sort((a, b) => a.phase_seq - b.phase_seq);
  const dispatchByPhase = {};
  for (const d of s.dispatches) dispatchByPhase[d.phase_seq] = d;

  return (
    <div className="space-y-5">
      <Link to="/" className="text-sm text-muted hover:text-white">← My projects</Link>

      <div className="border border-border bg-panel p-5">
        <div className="flex items-center justify-between">
          <h1 className="font-head text-2xl font-extrabold text-white">{s.label || s.code}</h1>
          <Badge tone={s.status === "completed" ? "ok" : s.status === "active" ? "accent" : "muted"}>{s.status}</Badge>
        </div>
        <p className="mt-1 text-sm text-muted">{s.location} · {s.area_sqft} sqft · {s.floors} floor(s) · {s.construction_type}</p>
        <div className="mt-4">
          <div className="mb-1 flex justify-between text-sm">
            <span className="text-white">{pr.currentSeq ? `In progress: ${PHASE_NAMES[pr.currentSeq]}` : s.status === "completed" ? "Project complete" : "Awaiting start"}</span>
            <span className="font-mono text-accent">{pr.done}/{pr.total} phases · {pr.pct}%</span>
          </div>
          <Progress pct={pr.pct} />
        </div>
      </div>

      <Card title="Construction timeline">
        <ol className="space-y-2">
          {phases.map((p) => {
            const d = dispatchByPhase[p.phase_seq];
            const delivered = d?.lines.filter((l) => l.status !== "short").map((l) => l.material_id) || [];
            const awaiting = d?.lines.filter((l) => l.status === "short").map((l) => l.material_id) || [];
            const dot = p.status === "done" ? "bg-accent" : p.status === "in_progress" ? "bg-[#f59e0b] animate-pulse" : "bg-border";
            return (
              <li key={p.phase_seq} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <span className={`mt-1.5 h-3 w-3 rounded-full ${dot}`} />
                  {p.phase_seq < 9 && <span className="w-px flex-1 bg-border" />}
                </div>
                <div className="flex-1 pb-3">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm ${p.status === "pending" ? "text-muted" : "text-white"}`}>
                      {p.phase_seq}. {PHASE_NAMES[p.phase_seq]}
                    </span>
                    <Badge tone={p.status === "done" ? "ok" : p.status === "in_progress" ? "warn" : "muted"}>{p.status.replace("_", " ")}</Badge>
                  </div>
                  {delivered.length > 0 && <p className="mt-0.5 text-xs text-emerald-400">✓ Materials delivered: {delivered.join(", ")}</p>}
                  {awaiting.length > 0 && <p className="mt-0.5 text-xs text-[#f59e0b]">⏳ Awaiting stock: {awaiting.join(", ")}</p>}
                </div>
              </li>
            );
          })}
        </ol>
      </Card>
    </div>
  );
}
