import { Link } from "react-router-dom";
import { site, progressOf, PHASE_NAMES } from "../api.js";
import { Card, Badge, Progress, useAsync } from "../components/ui.jsx";

export default function Home({ me, meName }) {
  const sites = useAsync(() => site.sites());

  if (!me) {
    return (
      <div className="mt-16 text-center">
        <h1 className="font-head text-2xl font-extrabold text-ink">Welcome to Consmat</h1>
        <p className="mt-2 text-sm text-muted">Select your name in the top-right to see your construction projects.</p>
      </div>
    );
  }

  const mine = (sites.data || []).filter((s) => s.consumer_id === me);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-head text-2xl font-extrabold text-ink">Hi{meName ? `, ${meName}` : ""}</h1>
        <p className="text-xs text-muted">Track your construction projects and material deliveries.</p>
      </div>

      {sites.error ? <p className="text-sm text-red-400">{sites.error}</p>
        : mine.length === 0 ? (
          <Card><p className="text-sm text-muted">No projects yet. Your spoke will set one up after intake.</p></Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {mine.map((s) => {
              const pr = progressOf(s);
              return (
                <Link key={s.id} to={`/projects/${s.id}`}
                  className="block border border-border bg-panel p-4 transition-colors hover:border-accent/50">
                  <div className="flex items-center justify-between">
                    <p className="font-semibold text-ink">{s.label || s.code}</p>
                    <Badge tone={s.status === "completed" ? "ok" : s.status === "active" ? "accent" : "muted"}>{s.status}</Badge>
                  </div>
                  <p className="mt-0.5 text-xs text-muted">{s.location} · {s.area_sqft} sqft · {s.floors} floor(s)</p>
                  <div className="mt-3">
                    <div className="mb-1 flex justify-between text-xs">
                      <span className="text-muted">{pr.currentSeq ? PHASE_NAMES[pr.currentSeq] : s.status === "completed" ? "Completed" : "Not started"}</span>
                      <span className="font-mono text-accent">{pr.pct}%</span>
                    </div>
                    <Progress pct={pr.pct} />
                  </div>
                </Link>
              );
            })}
          </div>
        )}
    </div>
  );
}
