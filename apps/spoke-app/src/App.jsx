import { useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import Intake from "./pages/Intake.jsx";
import Sites from "./pages/Sites.jsx";
import SiteDetail from "./pages/SiteDetail.jsx";
import Finance from "./pages/Finance.jsx";
import Inventory from "./pages/Inventory.jsx";
import Enquiries from "./pages/Enquiries.jsx";
import Login from "./pages/Login.jsx";
import { getUser, logout } from "./auth.js";

const NAV = [
  { to: "/dashboard", label: "Coverage", icon: "🗺️" },
  { to: "/enquiries", label: "Enquiries", icon: "📨" },
  { to: "/intake", label: "Onboarding", icon: "🤝" },
  { to: "/sites", label: "Sites", icon: "🏗️" },
  { to: "/finance", label: "Finance", icon: "💰", roles: ["finance", "spokesperson", "hub_manager", "hub_supervisor"] },
  { to: "/inventory", label: "Hub stock", icon: "📦" },
];

export default function App() {
  const [user, setUser] = useState(getUser());
  if (!user) return <Login onDone={() => setUser(getUser())} />;
  return (
    <div className="flex min-h-screen">
      <aside className="w-56 shrink-0 border-r border-border bg-panel">
        <div className="flex items-center gap-2 border-b border-border px-4 py-4">
          <div className="grid h-8 w-8 place-items-center rounded bg-accent font-mono text-sm font-bold text-black">C</div>
          <div>
            <p className="text-sm font-bold leading-tight text-white">Consmat Field</p>
            <p className="text-[10px] leading-tight text-muted">Spoke workspace</p>
          </div>
        </div>
        <nav className="p-2">
          {NAV.filter((n) => !n.roles || n.roles.includes(user.role)).map((n) => (
            <NavLink key={n.to} to={n.to}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded px-3 py-2 text-sm transition-colors ${
                  isActive ? "bg-accent/10 text-accent" : "text-white/70 hover:bg-white/5"
                }`}>
              <span className="text-base">{n.icon}</span>{n.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-4 border-t border-border px-4 pt-3">
          <p className="text-xs font-medium text-white">{user.name}</p>
          <p className="text-[10px] text-muted">{user.role}</p>
          <button onClick={logout} className="mt-2 text-[11px] text-accent hover:underline">Sign out</button>
        </div>
      </aside>

      <main className="flex-1 overflow-x-hidden px-6 py-6">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/intake" element={<Intake />} />
          <Route path="/sites" element={<Sites />} />
          <Route path="/sites/:id" element={<SiteDetail />} />
          <Route path="/finance" element={<Finance />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/enquiries" element={<Enquiries />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
}
