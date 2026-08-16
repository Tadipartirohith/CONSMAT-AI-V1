import { useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import Home from "./pages/Home.jsx";
import Project from "./pages/Project.jsx";
import { site, store } from "./api.js";
import { useAsync } from "./components/ui.jsx";

export default function App() {
  const consumers = useAsync(() => site.consumers());
  const [me, setMe] = useState(store.get());
  const navigate = useNavigate();

  const pick = (id) => { setMe(id); store.set(id); navigate("/"); };
  const meName = consumers.data?.find((c) => c.id === me)?.name;

  return (
    <div className="min-h-screen">
      <header className="flex items-center gap-3 border-b border-border bg-panel px-6 py-3">
        <div className="grid h-7 w-7 place-items-center bg-accent font-mono text-sm font-bold text-black">C</div>
        <div className="mr-auto">
          <p className="text-sm font-bold leading-tight text-white">Consmat</p>
          <p className="text-[10px] leading-tight text-muted">My Project</p>
        </div>
        <span className="text-[11px] uppercase tracking-wider text-muted">Signed in as</span>
        <select value={me} onChange={(e) => pick(e.target.value)}
          className="border border-border bg-panel2 px-2.5 py-1.5 text-sm text-white outline-none focus:border-accent">
          <option value="">select…</option>
          {(consumers.data || []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-6">
        <Routes>
          <Route path="/" element={<Home me={me} meName={meName} />} />
          <Route path="/projects/:id" element={<Project me={me} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
