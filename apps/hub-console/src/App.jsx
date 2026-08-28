import { useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import Overview from "./pages/Overview.jsx";
import Projects from "./pages/Projects.jsx";
import ProjectDetail from "./pages/ProjectDetail.jsx";
import Inventory from "./pages/Inventory.jsx";
import Vendors from "./pages/Vendors.jsx";
import Market from "./pages/Market.jsx";
import Procurement from "./pages/Procurement.jsx";
import Pricing from "./pages/Pricing.jsx";
import Payments from "./pages/Payments.jsx";
import Accounts from "./pages/Accounts.jsx";
import Team from "./pages/Team.jsx";
import Enquiries from "./pages/Enquiries.jsx";
import Login from "./pages/Login.jsx";
import { getUser, logout } from "./auth.js";

const NAV = [
  { to: "/overview", label: "Overview" },
  { to: "/enquiries", label: "Enquiries", roles: ["admin", "hub_manager", "hub_supervisor"] },
  { to: "/projects", label: "Projects" },
  { to: "/inventory", label: "Inventory" },
  { to: "/vendors", label: "Vendors" },
  { to: "/market", label: "Market" },
  { to: "/procurement", label: "Procurement" },
  { to: "/pricing", label: "Pricing" },
  { to: "/payments", label: "Payments" },
  { to: "/accounts", label: "Accounts", roles: ["admin", "hub_manager", "hub_supervisor"] },
  { to: "/team", label: "Team & access", roles: ["admin", "hub_manager", "hub_supervisor"] },
];

export default function App() {
  const [user, setUser] = useState(getUser());
  if (!user) return <Login onDone={() => setUser(getUser())} />;

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
          {NAV.filter((n) => !n.roles || n.roles.includes(user.role)).map((n) => (
            <NavLink key={n.to} to={n.to}
              className={({ isActive }) =>
                `block px-3 py-2 text-sm transition-colors ${
                  isActive ? "bg-accent/10 text-accent" : "text-white/70 hover:bg-white/5"
                }`}>
              {n.label}
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
          <Route path="/" element={<Navigate to="/overview" replace />} />
          <Route path="/overview" element={<Overview />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/projects/:id" element={<ProjectDetail />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/vendors" element={<Vendors />} />
          <Route path="/market" element={<Market />} />
          <Route path="/procurement" element={<Procurement />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/payments" element={<Payments />} />
          <Route path="/accounts" element={<Accounts />} />
          <Route path="/team" element={<Team />} />
          <Route path="/enquiries" element={<Enquiries />} />
          <Route path="*" element={<Navigate to="/overview" replace />} />
        </Routes>
      </main>
    </div>
  );
}
