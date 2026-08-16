import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import Intake from "./pages/Intake.jsx";
import Sites from "./pages/Sites.jsx";
import SiteDetail from "./pages/SiteDetail.jsx";

const NAV = [
  { to: "/dashboard", label: "Territory" },
  { to: "/intake", label: "Intake" },
  { to: "/sites", label: "Sites" },
];

export default function App() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-56 shrink-0 border-r border-border bg-panel">
        <div className="flex items-center gap-2 border-b border-border px-4 py-4">
          <div className="grid h-7 w-7 place-items-center bg-accent font-mono text-sm font-bold text-black">S</div>
          <div>
            <p className="text-sm font-bold leading-tight text-white">Consmat Spoke</p>
            <p className="text-[10px] leading-tight text-muted">Field App</p>
          </div>
        </div>
        <nav className="p-2">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to}
              className={({ isActive }) =>
                `block px-3 py-2 text-sm transition-colors ${
                  isActive ? "bg-accent/10 text-accent" : "text-white/70 hover:bg-white/5"
                }`}>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <p className="px-4 pt-4 text-[10px] leading-relaxed text-muted">
          Spokesperson · architect · civil engineer
        </p>
      </aside>

      <main className="flex-1 overflow-x-hidden px-6 py-6">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/intake" element={<Intake />} />
          <Route path="/sites" element={<Sites />} />
          <Route path="/sites/:id" element={<SiteDetail />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
}
