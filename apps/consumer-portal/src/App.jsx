import { useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Home from "./pages/Home.jsx";
import Project from "./pages/Project.jsx";
import Login from "./pages/Login.jsx";
import { getUser, logout } from "./auth.js";

export default function App() {
  const [user, setUser] = useState(getUser());
  if (!user) return <Login onDone={() => setUser(getUser())} />;

  const me = user.org_ref; // consumer id

  return (
    <div className="min-h-screen">
      <header className="flex items-center gap-3 border-b border-border bg-panel px-6 py-3">
        <div className="grid h-7 w-7 place-items-center bg-accent font-mono text-sm font-bold text-black">C</div>
        <div className="mr-auto">
          <p className="text-sm font-bold leading-tight text-white">Consmat</p>
          <p className="text-[10px] leading-tight text-muted">My Project</p>
        </div>
        <div className="text-right">
          <p className="text-xs font-medium text-white">{user.name}</p>
          <button onClick={logout} className="text-[11px] text-accent hover:underline">Sign out</button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-6">
        <Routes>
          <Route path="/" element={<Home me={me} meName={user.name} />} />
          <Route path="/projects/:id" element={<Project me={me} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
