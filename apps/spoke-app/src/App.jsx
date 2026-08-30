import { useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { MapTrifold, Bell, EnvelopeSimple, Handshake, Buildings, Wallet, Package, SignOut } from "@phosphor-icons/react";
import NotificationBell from "./components/NotificationBell.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Intake from "./pages/Intake.jsx";
import Sites from "./pages/Sites.jsx";
import SiteDetail from "./pages/SiteDetail.jsx";
import Finance from "./pages/Finance.jsx";
import Inventory from "./pages/Inventory.jsx";
import Enquiries from "./pages/Enquiries.jsx";
import Notifications from "./pages/Notifications.jsx";
import Login from "./pages/Login.jsx";
import { getUser, logout } from "./auth.js";

const NAV = [
  { to: "/dashboard", label: "Coverage", icon: MapTrifold },
  { to: "/notifications", label: "Notifications", icon: Bell },
  { to: "/enquiries", label: "Enquiries", icon: EnvelopeSimple },
  { to: "/intake", label: "Onboarding", icon: Handshake },
  { to: "/sites", label: "Sites", icon: Buildings },
  { to: "/finance", label: "Finance", icon: Wallet, roles: ["finance", "spokesperson", "hub_manager", "hub_supervisor"] },
  { to: "/inventory", label: "Inventory", icon: Package },
];

export default function App() {
  const [user, setUser] = useState(getUser());
  if (!user) return <Login onDone={() => setUser(getUser())} />;
  return (
    <div className="flex min-h-[100dvh] bg-bg">
      <aside className="flex w-60 shrink-0 flex-col px-3 py-4">
        <div className="mb-6 flex items-center gap-3 px-2">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-accent nm-raised-sm font-mono text-base font-bold text-black">C</div>
          <div>
            <p className="font-head text-sm font-bold leading-tight text-white">Consmat Field</p>
            <p className="text-[10px] leading-tight text-muted">Spoke workspace</p>
          </div>
        </div>

        <nav className="flex flex-col gap-1.5">
          {NAV.filter((n) => !n.roles || n.roles.includes(user.role)).map((n) => {
            const Icon = n.icon;
            return (
              <NavLink key={n.to} to={n.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm transition-all ${
                    isActive
                      ? "bg-panel2 nm-inset font-semibold text-accent"
                      : "text-white/70 hover:bg-white/[0.04] hover:text-white"
                  }`}>
                {({ isActive }) => (<><Icon size={19} weight={isActive ? "fill" : "regular"} />{n.label}</>)}
              </NavLink>
            );
          })}
        </nav>

        <div className="mt-auto flex items-center gap-3 rounded-xl bg-panel nm-raised-sm px-3.5 py-3">
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-semibold text-white">{user.name}</p>
            <p className="text-[10px] capitalize text-muted">{(user.role || "").replace(/_/g, " ")}</p>
          </div>
          <button onClick={logout} title="Sign out"
            className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-muted transition-colors hover:text-accent">
            <SignOut size={17} />
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-x-hidden px-6 py-6">
        <div className="mx-auto max-w-6xl">
          <div className="mb-5 flex items-center justify-end">
            <NotificationBell />
          </div>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/intake" element={<Intake />} />
            <Route path="/sites" element={<Sites />} />
            <Route path="/sites/:id" element={<SiteDetail />} />
            <Route path="/finance" element={<Finance />} />
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/enquiries" element={<Enquiries />} />
            <Route path="/notifications" element={<Notifications />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
