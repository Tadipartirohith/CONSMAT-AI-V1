import { useMemo, useState } from "react";
import { team, teams, site, TEAM_ROLES, ROLE_LABEL } from "../api.js";
import { getUser } from "../auth.js";
import { Card, Table, Td, Badge, Button, Field, Input, Select, Tabs, Notice, useAsync, PageSkeleton } from "../components/ui.jsx";

const FIELD_ROLES = ["spokesperson", "architect", "site_engineer", "finance"]; // roles that belong to a branch
const STAFF_ROLES = ["admin", "hub_manager", "hub_supervisor", "hr"];
const TEAM_TONE = { admin: "accent", member: "ok", viewer: "muted" };

const ALL_TABS = [
  { value: "members", label: "Members", staff: true },
  { value: "teams", label: "Teams", staff: false },
  { value: "branches", label: "Branches", staff: true },
];

export default function TeamAccess() {
  const me = getUser();
  const isStaff = STAFF_ROLES.includes(me?.role);
  const visible = ALL_TABS.filter((t) => isStaff || !t.staff);
  const [tab, setTab] = useState(isStaff ? "members" : "teams");

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <h1 className="font-head text-2xl font-extrabold text-ink">Team &amp; Access</h1>
        <span className="text-[11px] text-muted">Signed in as {ROLE_LABEL[me?.role] || me?.role}</span>
      </div>
      <Tabs tabs={visible} active={tab} onChange={setTab} />

      {tab === "members" && isStaff && <MembersPanel me={me} />}
      {tab === "teams" && <TeamsPanel me={me} isStaff={isStaff} />}
      {tab === "branches" && isStaff && <BranchesPanel me={me} />}
    </div>
  );
}

/* ---------------- Members: accounts, roles, status ---------------- */

function MembersPanel({ me }) {
  const users = useAsync(() => team.users());
  const roles = useAsync(() => team.roles());
  const spokes = useAsync(() => site.spokes());
  const [msg, setMsg] = useState(null);

  const ranks = roles.data?.ranks || {};
  const assignable = roles.data?.assignable || [];
  const spokeMap = Object.fromEntries((spokes.data || []).map((s) => [s.id, s.name]));
  const canManage = (targetRole) => me?.role === "admin" || (ranks[me?.role] || 0) > (ranks[targetRole] || 0);
  const flash = (ok, text) => setMsg({ ok, text });

  const grouped = useMemo(() => {
    const order = roles.data?.manageable || ["admin", "hub_manager", "hub_supervisor", "hr", "spokesperson", "architect", "site_engineer", "finance"];
    const g = {};
    for (const u of users.data || []) (g[u.role] ||= []).push(u);
    return order.filter((r) => g[r]).map((r) => ({ role: r, list: g[r] }));
  }, [users.data, roles.data]);

  if (users.loading && !users.data) return <PageSkeleton stats={0} rows={8} />;
  return (
    <div className="space-y-4">
      <Notice msg={msg} />
      <AddMemberForm assignable={assignable} spokes={spokes.data || []} onFlash={flash} onDone={users.reload} />

      {grouped.length === 0 ? (
        <Card title="Members"><p className="text-sm text-muted">No members to show for your access level.</p></Card>
      ) : (
        <Card title="Members" right={<span className="text-[11px] text-muted">{(users.data || []).length} accounts</span>}>
          {grouped.map(({ role, list }) => (
            <div key={role} className="mb-4 last:mb-0">
              <div className="mb-1.5 flex items-center gap-2">
                <h3 className="text-sm font-semibold text-ink">{ROLE_LABEL[role] || role}</h3>
                <span className="text-[11px] text-muted">{list.length}</span>
              </div>
              <Table head={["Name", "Email", "Branch", "Role", "Status", ""]}>
                {list.map((u) => (
                  <MemberRow key={u.id} u={u} me={me} canManage={canManage(u.role)} assignable={assignable}
                    branchName={spokeMap[u.org_ref]} isField={FIELD_ROLES.includes(u.role)}
                    onFlash={flash} onDone={users.reload} />
                ))}
              </Table>
            </div>
          ))}
        </Card>
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

  if (assignable.length === 0) return null;
  return (
    <Card title="Add member">
      <form onSubmit={save} className="flex flex-wrap items-end gap-3">
        <div className="min-w-[180px] flex-1"><Field label="Email"><Input type="email" value={f.email} required placeholder="name@consmat.com" onChange={(e) => setF({ ...f, email: e.target.value })} /></Field></div>
        <div className="min-w-[140px] flex-1"><Field label="Name"><Input value={f.name} placeholder="Full name" onChange={(e) => setF({ ...f, name: e.target.value })} /></Field></div>
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
        <Button type="submit" disabled={busy || !f.role || !f.email.trim()}>Add member</Button>
      </form>
      <p className="mt-2 text-[11px] text-muted">You can assign roles below your own. The member signs in with the temporary password.</p>
    </Card>
  );
}

function MemberRow({ u, me, canManage, assignable, branchName, isField, onFlash, onDone }) {
  const [busy, setBusy] = useState(false);
  const isSelf = u.id === me?.sub || u.id === me?.id;
  const roleOptions = [...new Set([u.role, ...assignable])];

  const patch = async (b, ok) => {
    setBusy(true);
    try { await team.updateUser(u.id, b); onFlash(true, ok); onDone(); }
    catch (e) { onFlash(false, e.message); } finally { setBusy(false); }
  };

  return (
    <tr className="border-b border-border/50">
      <Td className="text-ink/90">{u.name}</Td>
      <Td mono className="text-muted">{u.id}</Td>
      <Td className="text-muted">{isField ? (branchName || u.org_ref || "-") : "-"}</Td>
      <Td>
        {canManage ? (
          <Select value={u.role} disabled={busy} onChange={(e) => patch({ role: e.target.value }, `${u.name} is now ${ROLE_LABEL[e.target.value] || e.target.value}.`)}>
            {roleOptions.map((r) => <option key={r} value={r}>{ROLE_LABEL[r] || r}</option>)}
          </Select>
        ) : <Badge tone="muted">{ROLE_LABEL[u.role] || u.role}</Badge>}
      </Td>
      <Td><Badge tone={u.active ? "ok" : "bad"}>{u.active ? "active" : "disabled"}</Badge></Td>
      <Td>
        {canManage && !isSelf ? (
          <Button size="sm" variant="ghost" disabled={busy}
            onClick={() => patch({ active: !u.active }, `${u.name} ${u.active ? "deactivated" : "reactivated"}.`)}>
            {u.active ? "Deactivate" : "Reactivate"}
          </Button>
        ) : <span className="text-[11px] text-muted">{isSelf ? "You" : "-"}</span>}
      </Td>
    </tr>
  );
}

/* ---------------- Teams: group people into teams ---------------- */

function TeamsPanel({ me, isStaff }) {
  const teamsA = useAsync(() => teams.list());
  const usersA = useAsync(() => team.users().catch(() => []));
  const [sel, setSel] = useState(null);
  const [msg, setMsg] = useState(null);
  const [nt, setNt] = useState({ name: "", description: "", spoke_id: "" });

  const detail = useAsync(() => (sel ? teams.get(sel) : Promise.resolve(null)), [sel]);
  const t = detail.data;
  const canManage = t && (isStaff || t.members.some((m) => m.user_id === me?.id && m.role === "admin"));

  const createTeam = async (e) => {
    e.preventDefault(); setMsg(null);
    try {
      const created = await teams.create({ name: nt.name, description: nt.description, spoke_id: nt.spoke_id });
      setNt({ name: "", description: "", spoke_id: "" }); teamsA.reload(); setSel(created.id);
      setMsg({ ok: true, text: `Team "${created.name}" created.` });
    } catch (e) { setMsg({ ok: false, text: e.message }); }
  };
  const afterMember = (text) => { setMsg({ ok: true, text }); detail.reload(); teamsA.reload(); };
  const err = (e) => setMsg({ ok: false, text: e.message });

  if (teamsA.loading && !teamsA.data) return <PageSkeleton stats={0} rows={6} />;
  return (
    <div className="space-y-4">
      <Notice msg={msg} />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,340px)_1fr]">
        <div className="space-y-4">
          <Card title="Teams" right={<Button size="sm" variant="ghost" onClick={teamsA.reload}>Refresh</Button>}>
            <div className="space-y-1.5">
              {(teamsA.data || []).map((tm) => (
                <button key={tm.id} onClick={() => setSel(tm.id)}
                  className={`w-full rounded-lg border px-3 py-2 text-left transition-colors ${sel === tm.id ? "border-accent/50 bg-accent/10" : "border-border bg-panel2 hover:bg-muted/10"}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-ink">{tm.name}</span>
                    <span className="text-[11px] text-muted">{tm.member_count} member{tm.member_count === 1 ? "" : "s"}</span>
                  </div>
                  <div className="mt-0.5 flex items-center gap-2">
                    {tm.spoke_id && <span className="text-[10px] uppercase tracking-wider text-muted">{tm.spoke_id}</span>}
                    {!tm.active && <Badge tone="muted">archived</Badge>}
                  </div>
                </button>
              ))}
              {teamsA.data?.length === 0 && <p className="text-sm text-muted">No teams yet.</p>}
            </div>
          </Card>

          {isStaff && (
            <Card title="Create a team">
              <form onSubmit={createTeam} className="space-y-3">
                <Field label="Name"><Input value={nt.name} required placeholder="e.g. Kompally Design" onChange={(e) => setNt({ ...nt, name: e.target.value })} /></Field>
                <Field label="Description"><Input value={nt.description} onChange={(e) => setNt({ ...nt, description: e.target.value })} /></Field>
                <Field label="Branch (optional)"><Input value={nt.spoke_id} placeholder="branch id, e.g. s_kompally" onChange={(e) => setNt({ ...nt, spoke_id: e.target.value })} /></Field>
                <Button type="submit">Create team</Button>
              </form>
            </Card>
          )}
        </div>

        <Card title={t ? t.name : "Select a team"} right={t && canManage && <Badge tone="accent">Manager</Badge>}>
          {!t ? <p className="text-sm text-muted">Select a team to view its members.</p> : (
            <div className="space-y-4">
              {t.description && <p className="text-sm text-muted">{t.description}</p>}
              <Table head={["Member", "Email", "Role", "Granted by", canManage ? "" : null].filter((x) => x !== null)}>
                {t.members.map((m) => (
                  <tr key={m.user_id} className="border-b border-border/50">
                    <Td className="text-ink/90">{m.name}</Td>
                    <Td mono className="text-muted">{m.user_id}</Td>
                    <Td>
                      {canManage ? (
                        <Select value={m.role} onChange={async (e) => { try { await teams.setMemberRole(t.id, m.user_id, e.target.value); afterMember(`${m.name} is now ${e.target.value}.`); } catch (ex) { err(ex); } }}>
                          {TEAM_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                        </Select>
                      ) : <Badge tone={TEAM_TONE[m.role]}>{m.role}</Badge>}
                    </Td>
                    <Td className="text-muted">{m.granted_by || "-"}</Td>
                    {canManage && <Td><Button size="sm" variant="ghost" onClick={async () => { try { await teams.removeMember(t.id, m.user_id); afterMember(`${m.name} removed from ${t.name}.`); } catch (ex) { err(ex); } }}>Remove</Button></Td>}
                  </tr>
                ))}
                {t.members.length === 0 && <tr><Td className="text-muted">No members yet.</Td></tr>}
              </Table>

              {canManage && <AddTeamMember team={t} users={usersA.data || []} onDone={afterMember} onErr={err} />}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function AddTeamMember({ team: t, users, onDone, onErr }) {
  const [uid, setUid] = useState("");
  const [role, setRole] = useState("member");
  const [busy, setBusy] = useState(false);
  const memberEmails = new Set(t.members.map((m) => m.user_id));
  const assignable = users.filter((u) => !["consumer", "vendor", "service"].includes(u.role) && !memberEmails.has(u.id));

  const add = async (e) => {
    e.preventDefault(); if (!uid) return; setBusy(true);
    try { await teams.addMember(t.id, { user_id: uid, role }); setUid(""); setRole("member"); onDone(`Added to ${t.name}.`); }
    catch (ex) { onErr(ex); } finally { setBusy(false); }
  };

  return (
    <form onSubmit={add} className="flex flex-wrap items-end gap-2 border-t border-border/60 pt-3">
      <div className="min-w-[220px] flex-1">
        <Field label="Add a member">
          <Select value={uid} onChange={(e) => setUid(e.target.value)}>
            <option value="">Select a person</option>
            {assignable.map((u) => <option key={u.id} value={u.id}>{u.name} - {ROLE_LABEL[u.role] || u.role}</option>)}
          </Select>
        </Field>
      </div>
      <Field label="Role">
        <Select value={role} onChange={(e) => setRole(e.target.value)}>
          {TEAM_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
        </Select>
      </Field>
      <Button type="submit" disabled={busy || !uid}>Add</Button>
    </form>
  );
}

/* ---------------- Branches: regions and coverage ---------------- */

function BranchesPanel({ me }) {
  const spokes = useAsync(() => site.spokes());
  const [msg, setMsg] = useState(null);
  const [f, setF] = useState({ name: "", geo: "" });
  const [busy, setBusy] = useState(false);
  const [regionFor, setRegionFor] = useState("");
  const [region, setRegion] = useState("");
  const canAdd = ["admin", "hub_manager", "hub_supervisor"].includes(me?.role);
  const flash = (ok, text) => setMsg({ ok, text });

  const addBranch = async (e) => {
    e.preventDefault(); setBusy(true);
    try { await site.createSpoke({ name: f.name, geofence: f.geo }); flash(true, `Branch "${f.name}" created.`); setF({ name: "", geo: "" }); spokes.reload(); }
    catch (e) { flash(false, e.message); } finally { setBusy(false); }
  };
  const addRegion = async (id) => {
    if (!region.trim()) return; setBusy(true);
    try { await site.changeArea(id, region.trim(), "add"); flash(true, `Region "${region.trim()}" added.`); setRegion(""); setRegionFor(""); spokes.reload(); }
    catch (e) { flash(false, e.message); } finally { setBusy(false); }
  };

  if (spokes.loading && !spokes.data) return <PageSkeleton stats={0} rows={6} />;
  return (
    <div className="space-y-4">
      <Notice msg={msg} />
      {canAdd && (
        <Card title="Add a branch">
          <form onSubmit={addBranch} className="flex flex-wrap items-end gap-3">
            <div className="min-w-[180px] flex-1"><Field label="Branch name"><Input value={f.name} required placeholder="e.g. Whitefield" onChange={(e) => setF({ ...f, name: e.target.value })} /></Field></div>
            <div className="min-w-[160px] flex-1"><Field label="Geofence (optional)"><Input value={f.geo} placeholder="e.g. east zone" onChange={(e) => setF({ ...f, geo: e.target.value })} /></Field></div>
            <Button type="submit" disabled={busy || !f.name.trim()}>Add branch</Button>
          </form>
        </Card>
      )}
      <Card title="Branches" right={<span className="text-[11px] text-muted">{(spokes.data || []).length} branches</span>}>
        {(spokes.data || []).length === 0 ? <p className="text-sm text-muted">No branches yet.</p> : (
          <div className="space-y-2">
            {(spokes.data || []).map((s) => (
              <div key={s.id} className="rounded-xl border border-border/50 bg-panel2 px-3.5 py-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-ink">{s.name} <span className="text-[11px] text-muted">({s.id})</span></span>
                  {canAdd && <button className="text-[11px] text-accent hover:underline" onClick={() => setRegionFor(regionFor === s.id ? "" : s.id)}>{regionFor === s.id ? "Cancel" : "Add region"}</button>}
                </div>
                <p className="mt-0.5 text-[11px] text-muted">Regions: {(s.areas || []).map((a) => a.area || a).join(", ") || "none"}</p>
                {regionFor === s.id && (
                  <div className="mt-2 flex gap-2">
                    <Input value={region} placeholder="Region keyword" onChange={(e) => setRegion(e.target.value)} />
                    <Button size="sm" onClick={() => addRegion(s.id)} disabled={busy || !region.trim()}>Add</Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
