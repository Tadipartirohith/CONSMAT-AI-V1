import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import Overview from "./pages/Overview.jsx";
import Inventory from "./pages/Inventory.jsx";
import Vendors from "./pages/Vendors.jsx";
import Procurement from "./pages/Procurement.jsx";
import Pricing from "./pages/Pricing.jsx";

const NAV = [
  { to: "/overview", label: "Overview" },
  { to: "/inventory", label: "Inventory" },
  { to: "/vendors", label: "Vendors" },
  { to: "/procurement", label: "Procurement" },
  { to: "/pricing", label: "Pricing" },
];

export default function App() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-56 shrink-0 border-r border-border bg-panel">
        <div className="flex items-center gap-2 border-b border-border px-4 py-4">
          <div className="grid h-7 w-7 place-items-center bg-accent font-mono text-sm font-bold text-black">C</div>
          <div>
            <p className="text-sm font-bold leading-tight text-white">Consmat Hub</p>
            <p className="text-[10px] leading-tight text-muted">Operations Console</p>
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
          Hub-and-spoke V1 · supervisor + manager operations
        </p>
      </aside>

      <main className="flex-1 overflow-x-hidden px-6 py-6">
        <Routes>
          <Route path="/" element={<Navigate to="/overview" replace />} />
          <Route path="/overview" element={<Overview />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/vendors" element={<Vendors />} />
          <Route path="/procurement" element={<Procurement />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="*" element={<Navigate to="/overview" replace />} />
        </Routes>
      </main>
    </div>
  );
}
