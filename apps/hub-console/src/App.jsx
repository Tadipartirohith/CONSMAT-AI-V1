import { useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import {
  Gauge, EnvelopeSimple, Buildings, Package, Storefront, TrendUp, ShoppingCart,
  Tag, CreditCard, ChartLineUp, IdentificationBadge, UsersThree, MagnifyingGlass, SignOut,
} from "@phosphor-icons/react";
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
import Teams from "./pages/Teams.jsx";
import Enquiries from "./pages/Enquiries.jsx";
import Login from "./pages/Login.jsx";
import { getUser, logout } from "./auth.js";

const NAV = [
  { to: "/overview", label: "Overview", icon: Gauge },
  { to: "/enquiries", label: "Enquiries", icon: EnvelopeSimple, roles: ["admin", "hub_manager", "hub_supervisor"] },
  { to: "/projects", label: "Projects", icon: Buildings },
  { to: "/inventory", label: "Inventory", icon: Package },
  { to: "/vendors", label: "Vendors", icon: Storefront },
  { to: "/market", label: "Market", icon: TrendUp },
  { to: "/procurement", label: "Procurement", icon: ShoppingCart },
  { to: "/pricing", label: "Pricing", icon: Tag },
  { to: "/payments", label: "Payments", icon: CreditCard },
  { to: "/accounts", label: "Accounts", icon: ChartLineUp, roles: ["admin", "hub_manager", "hub_supervisor"] },
  { to: "/team", label: "Team & access", icon: IdentificationBadge, roles: ["admin", "hub_manager", "hub_supervisor", "hr"] },
  { to: "/teams", label: "Teams", icon: UsersThree, roles: ["admin", "hub_manager", "hub_supervisor", "hr", "spokesperson", "architect", "site_engineer", "finance"] },
];

function TopBar({ title }) {
  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border/70 bg-bg/85 px-6 backdrop-blur">
      <h1 className="font-head text-[15px] font-semibold text-white">{title}</h1>
      <div className="ml-auto flex items-center gap-2">
        <div className="hidden items-center gap-2 rounded-lg border border-border/80 bg-panel px-3 py-1.5 text-xs text-muted sm:flex">
          <MagnifyingGlass size={14} />
          <span>Search</span>
          <span className="ml-6 rounded border border-border px-1.5 py-px font-mono text-[10px] text-muted/80">Cmd K</span>
        </div>
      </div>
    </header>
  );
}

export default function App() {
  const [user, setUser] = useState(getUser());
  const location = useLocation();
  if (!user) return <Login onDone={() => setUser(getUser())} />;

  const nav = NAV.filter((n) => !n.roles || n.roles.includes(user.role));
  const active = nav.find((n) => location.pathname.startsWith(n.to));
  const title = active ? active.label : "Consmat Hub";

  return (
    <div className="flex min-h-screen bg-bg">
      <aside className="flex w-60 shrink-0 flex-col border-r border-border/70 bg-panel px-3 py-4">
        <div className="mb-5 flex items-center gap-2.5 px-2">
          <div className="grid h-9 w-9 place-items-center rounded-lg bg-accent font-mono text-base font-bold text-black nm-raised-sm">C</div>
          <div>
            <p className="font-head text-sm font-bold leading-tight text-white">Consmat Hub</p>
            <p className="text-[10px] leading-tight text-muted">Operations console</p>
          </div>
        </div>

        <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto">
          {nav.map((n) => {
            const Icon = n.icon;
            return (
              <NavLink key={n.to} to={n.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                    isActive ? "bg-accent/[0.12] font-medium text-accent" : "text-white/70 hover:bg-white/[0.05] hover:text-white"
                  }`}>
                {({ isActive }) => (<><Icon size={18} weight={isActive ? "fill" : "regular"} />{n.label}</>)}
              </NavLink>
            );
          })}
        </nav>

        <div className="mt-3 flex items-center gap-2.5 rounded-xl bg-panel2 nm-inset px-3 py-2.5">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-accent/20 font-mono text-xs font-bold text-accent">
            {(user.name || "?").slice(0, 1).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-semibold text-white">{user.name}</p>
            <p className="text-[10px] capitalize text-muted">{(user.role || "").replace(/_/g, " ")}</p>
          </div>
          <button onClick={logout} title="Sign out"
            className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-muted transition-colors hover:text-accent">
            <SignOut size={16} />
          </button>
        </div>
      </aside>

      <main className="flex min-h-screen flex-1 flex-col overflow-x-hidden">
        <TopBar title={title} />
        <div className="mx-auto w-full max-w-6xl flex-1 px-6 py-6">
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
            <Route path="/teams" element={<Teams />} />
            <Route path="/enquiries" element={<Enquiries />} />
            <Route path="*" element={<Navigate to="/overview" replace />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
