import { useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Home from "./pages/Home.jsx";
import Project from "./pages/Project.jsx";
import Login from "./pages/Login.jsx";
import { getUser } from "./auth.js";
import ProfileMenu from "./components/ProfileMenu.jsx";

export default function App() {
  const [user, setUser] = useState(getUser());
  if (!user) return <Login onDone={() => setUser(getUser())} />;

  const me = user.org_ref; // consumer id

  return (
    <div className="min-h-[100dvh] bg-bg">
      <div className="mx-auto max-w-4xl px-4 pt-4">
        <header className="flex items-center gap-3 rounded-2xl bg-panel nm-raised px-5 py-3.5">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-accent nm-raised-sm font-mono text-base font-bold text-onAccent">C</div>
          <div className="mr-auto">
            <p className="font-head text-sm font-bold leading-tight text-ink">Consmat</p>
            <p className="text-[10px] leading-tight text-muted">My Project</p>
          </div>
          <ProfileMenu />
        </header>
      </div>

      <main className="mx-auto max-w-4xl px-4 py-6">
        <Routes>
          <Route path="/" element={<Home me={me} meName={user.name} />} />
          <Route path="/projects/:id" element={<Project me={me} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
