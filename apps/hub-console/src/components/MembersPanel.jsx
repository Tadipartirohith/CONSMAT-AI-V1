import { useMemo, useState } from "react";
import { team, site, ROLE_LABEL } from "../api.js";
import { getUser } from "../auth.js";
import { Card, Badge, Button, Field, Input, Select, Notice, useAsync, PageSkeleton } from "./ui.jsx";
import { Crown, Briefcase, IdentificationCard, ClipboardText, Handshake, Compass, HardHat, Wallet, MagnifyingGlass, Plus, UserPlus } from "@phosphor-icons/react";

const FIELD_ROLES = ["spokesperson", "architect", "site_engineer", "finance"];

// Role identity: one icon per role, one tier per role. Colour is carried only by the single
// accent + neutrals (no per-role rainbow); the hierarchy is shown by tier + rank order.
const ROLE_ICON = {
  admin: Crown, hub_manager: Briefcase, hr: IdentificationCard, hub_supervisor: ClipboardText,
  spokesperson: Handshake, architect: Compass, site_engineer: HardHat, finance: Wallet,
};
const TIERS = [
  { level: 1, label: "Leadership", roles: ["admin", "hub_manager"] },
  { level: 2, label: "People & Ops", roles: ["hr", "hub_supervisor"] },
  { level: 3, label: "Field team", roles: ["spokesperson", "architect", "site_engineer", "finance"] },
];
const ROLE_LEVEL = Object.fromEntries(TIERS.flatMap((t) => t.roles.map((r) => [r, t.level])));

function initials(name) {
  return (name || "?").split(" ").map((s) => s[0]).filter(Boolean).slice(0, 2).join("").toUpperCase();
}
function Avatar({ name }) {
  return <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-panel2 nm-inset font-mono text-xs font-semibold text-ink/75">{initials(name)}</div>;
}

export default function MembersPanel({ me }) {
  const users = useAsync(() => team.users());
  const roles = useAsync(() => team.roles());
  const spokes = useAsync(() => site.spokes());
  const [msg, setMsg] = useState(null);
  const [q, setQ] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [showAdd, setShowAdd] = useState(false);

  const ranks = roles.data?.ranks || {};
  const assignable = roles.data?.assignable || [];
  const spokeMap = Object.fromEntries((spokes.data || []).map((s) => [s.id, s.name]));
  const canManage = (targetRole) => me?.role === "admin" || (ranks[me?.role] || 0) > (ranks[targetRole] || 0);
  const flash = (ok, text) => setMsg({ ok, text });

  const all = users.data || [];
  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return all.filter((u) => {
      if (roleFilter && u.role !== roleFilter) return false;
      if (statusFilter === "active" && !u.active) return false;
      if (statusFilter === "disabled" && u.active) return false;
      if (needle && !`${u.name} ${u.id}`.toLowerCase().includes(needle)) return false;
      return true;
    });
  }, [all, q, roleFilter, statusFilter]);

  // Group filtered members by role, ordered by rank (highest first).
  const groups = useMemo(() => {
    const order = (roles.data?.manageable || Object.keys(ROLE_LEVEL)).slice()
      .sort((a, b) => (ranks[b] || 0) - (ranks[a] || 0));
    const g = {};
    for (const u of filtered) (g[u.role] ||= []).push(u);
    return order.filter((r) => g[r]).map((r) => ({ role: r, list: g[r] }));
  }, [filtered, roles.data, ranks]);

  const tierCounts = useMemo(() => {
    const byRole = {};
    for (const u of all) byRole[u.role] = (byRole[u.role] || 0) + 1;
    return TIERS.map((t) => ({ ...t, count: t.roles.reduce((n, r) => n + (byRole[r] || 0), 0) }));
  }, [all]);

  if (users.loading && !users.data) return <PageSkeleton stats={3} rows={8} />;

  const roleOptions = (roles.data?.manageable || Object.keys(ROLE_LEVEL));
  return (
    <div className="space-y-4">
      <Notice msg={msg} />

      {/* Hierarchy overview */}
      <div className="grid gap-3 sm:grid-cols-3">
        {tierCounts.map((t) => (
          <div key={t.level} className="rounded-xl bg-panel nm-raised p-4">
            <div className="flex items-center justify-between">
              <p className="text-[10px] font-medium uppercase tracking-[0.08em] text-muted">L{t.level} &middot; {t.label}</p>
              <span className="font-mono text-sm font-semibold text-ink">{t.count}</span>
            </div>
            <div className="mt-2.5 flex gap-1.5">
              {t.roles.map((r) => {
                const Icon = ROLE_ICON[r];
                return <span key={r} title={ROLE_LABEL[r] || r} className="grid h-7 w-7 place-items-center rounded-lg bg-panel2 text-muted">{Icon ? <Icon size={15} /> : null}</span>;
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-52 flex-1">
          <MagnifyingGlass size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name or email"
            className="w-full rounded-lg bg-panel2 nm-inset py-2 pl-9 pr-3 text-sm text-ink placeholder:text-muted/60 outline-none focus:ring-2 focus:ring-accent/45" />
        </div>
        <Select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)}>
          <option value="">All roles</option>
          {roleOptions.map((r) => <option key={r} value={r}>{ROLE_LABEL[r] || r}</option>)}
        </Select>
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="disabled">Disabled</option>
        </Select>
        {assignable.length > 0 && (
          <Button variant={showAdd ? "ghost" : "primary"} onClick={() => setShowAdd((v) => !v)}>
            <UserPlus size={15} weight="fill" />{showAdd ? "Close" : "Add member"}
          </Button>
        )}
      </div>

      {showAdd && <AddMemberForm assignable={assignable} spokes={spokes.data || []} onFlash={flash}
        onDone={() => { users.reload(); setShowAdd(false); }} />}

      {/* Members grouped by role, ranked */}
      {groups.length === 0 ? (
        <Card><p className="py-6 text-center text-sm text-muted">{all.length === 0 ? "No members to show for your access level." : "No members match these filters."}</p></Card>
      ) : (
        <div className="overflow-hidden rounded-2xl bg-panel nm-raised">
          {groups.map(({ role, list }, gi) => {
            const Icon = ROLE_ICON[role];
            return (
              <div key={role} className={gi > 0 ? "border-t border-border" : ""}>
                <div className="flex items-center gap-2.5 bg-panel2/40 px-4 py-2.5">
                  <span className="grid h-7 w-7 place-items-center rounded-lg bg-panel2 text-muted">{Icon ? <Icon size={15} weight="fill" /> : null}</span>
                  <h3 className="text-sm font-semibold text-ink">{ROLE_LABEL[role] || role}</h3>
                  <span className="rounded-full bg-panel px-2 py-0.5 font-mono text-[10px] text-muted">L{ROLE_LEVEL[role] || "-"}</span>
                  <span className="ml-auto text-[11px] text-muted">{list.length}</span>
                </div>
                {list.map((u) => (
                  <MemberRow key={u.id} u={u} me={me} canManage={canManage(u.role)} assignable={assignable}
                    branchName={spokeMap[u.org_ref]} isField={FIELD_ROLES.includes(u.role)}
                    onFlash={flash} onDone={users.reload} />
                ))}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function AddMemberForm({ assignable, spokes, onFlash, onDone }) {
  const [f, setF] = useState({ email: "", name: "", password: "", role: "", org_ref: "" });
  const [busy, setBusy] = useState(false);
  const isField = FIELD_ROLES.includes(f.role);

  const save = async (e) => {
    e.preventDefault(); setBusy(true);
    try {
      await team.createUser({ email: f.email.trim().toLowerCase(), name: f.name, password: f.password,
        role: f.role, org_ref: isField ? f.org_ref : "" });
      onFlash(true, `${f.email} added as ${ROLE_LABEL[f.role] || f.role}.`);
      setF({ email: "", name: "", password: "", role: "", org_ref: "" }); onDone();
    } catch (e) { onFlash(false, e.message); } finally { setBusy(false); }
  };

  return (
    <Card title="Add member">
      <form onSubmit={save} className="flex flex-wrap items-end gap-3">
        <div className="min-w-44 flex-1"><Field label="Email"><Input type="email" value={f.email} required placeholder="name@consmat.com" onChange={(e) => setF({ ...f, email: e.target.value })} /></Field></div>
        <div className="min-w-36 flex-1"><Field label="Name"><Input value={f.name} placeholder="Full name" onChange={(e) => setF({ ...f, name: e.target.value })} /></Field></div>
        <Field label="Role">
          <Select value={f.role} required onChange={(e) => setF({ ...f, role: e.target.value })}>
            <option value="">Select role</option>
            {assignable.map((r) => <option key={r} value={r}>{ROLE_LABEL[r] || r}</option>)}
          </Select>
        </Field>
        {isField && (
          <Field label="Branch">
            <Select value={f.org_ref} onChange={(e) => setF({ ...f, org_ref: e.target.value })}>
              <option value="">Unassigned</option>
              {spokes.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </Select>
          </Field>
        )}
        <Field label="Temp password"><Input value={f.password} required placeholder="min 4 chars" onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
        <Button type="submit" disabled={busy || !f.role || !f.email.trim()}><Plus size={14} weight="bold" />Add</Button>
      </form>
      <p className="mt-2 text-[11px] text-muted">You can assign roles below your own. The member signs in with the temporary password.</p>
    </Card>
  );
}

function MemberRow({ u, me, canManage, assignable, branchName, isField, onFlash, onDone }) {
  const [busy, setBusy] = useState(false);
  const [confirmDel, setConfirmDel] = useState(false);
  const isSelf = u.id === me?.sub || u.id === me?.id;
  const isAdmin = u.role === "admin";
  const roleOptions = [...new Set([u.role, ...assignable])];

  const patch = async (b, ok) => {
    setBusy(true);
    try { await team.updateUser(u.id, b); onFlash(true, ok); onDone(); }
    catch (e) { onFlash(false, e.message); } finally { setBusy(false); }
  };
  const del = async () => {
    setBusy(true);
    try { await team.deleteUser(u.id); onFlash(true, `${u.name} deleted.`); onDone(); }
    catch (e) { onFlash(false, e.message); } finally { setBusy(false); setConfirmDel(false); }
  };

  return (
    <div className="flex items-center gap-3 border-t border-border/50 px-4 py-2.5">
      <Avatar name={u.name} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-ink">{u.name}</p>
        <p className="truncate font-mono text-[11px] text-muted">{u.id}</p>
      </div>
      <span className="hidden w-28 shrink-0 truncate text-xs text-muted md:block">{isField ? (branchName || u.org_ref || "-") : "-"}</span>
      <div className="hidden w-40 shrink-0 sm:block">
        {canManage && !isAdmin
          ? <Select value={u.role} disabled={busy} onChange={(e) => patch({ role: e.target.value }, `${u.name} is now ${ROLE_LABEL[e.target.value] || e.target.value}.`)}>
              {roleOptions.map((r) => <option key={r} value={r}>{ROLE_LABEL[r] || r}</option>)}
            </Select>
          : <Badge tone={isAdmin ? "accent" : "muted"}>{ROLE_LABEL[u.role] || u.role}</Badge>}
      </div>
      <Badge tone={u.active ? "ok" : "bad"}>{u.active ? "active" : "disabled"}</Badge>
      <div className="flex w-44 shrink-0 items-center justify-end gap-1.5">
        {isAdmin ? <span className="text-[11px] text-muted">Permanent</span>
          : isSelf ? <span className="text-[11px] text-muted">You</span>
          : canManage ? (
            <>
              <Button size="sm" variant="ghost" disabled={busy}
                onClick={() => patch({ active: !u.active }, `${u.name} ${u.active ? "deactivated" : "reactivated"}.`)}>
                {u.active ? "Deactivate" : "Reactivate"}
              </Button>
              {confirmDel ? (
                <>
                  <Button size="sm" variant="danger" disabled={busy} onClick={del}>Confirm</Button>
                  <button onClick={() => setConfirmDel(false)} className="text-[11px] text-muted hover:text-ink">cancel</button>
                </>
              ) : <Button size="sm" variant="danger" onClick={() => setConfirmDel(true)}>Delete</Button>}
            </>
          ) : <span className="text-[11px] text-muted">-</span>}
      </div>
    </div>
  );
}
