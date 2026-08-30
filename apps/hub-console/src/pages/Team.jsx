import { useMemo, useState } from "react";
import { team, site, ROLE_LABEL } from "../api.js";
import { getUser } from "../auth.js";
import { Card, Table, Td, Badge, Button, Field, Input, Select, useAsync, PageSkeleton } from "../components/ui.jsx";

const FIELD_ROLES = ["spokesperson", "architect", "site_engineer", "finance"];  // roles that belong to a spoke team

export default function Team() {
  const me = getUser();
  const users = useAsync(() => team.users());
  const roles = useAsync(() => team.roles());
  const spokes = useAsync(() => site.spokes());
  const [msg, setMsg] = useState(null);

  const ranks = roles.data?.ranks || {};
  const assignable = roles.data?.assignable || [];
  const spokeMap = Object.fromEntries((spokes.data || []).map((s) => [s.id, s.name]));
  const canManage = (targetRole) => me?.role === "admin" || (ranks[me?.role] || 0) > (ranks[targetRole] || 0);

  const flash = (ok, text) => setMsg({ ok, text });
  const reload = () => { users.reload(); spokes.reload(); };

  // group users by role (highest rank first), managed roles only
  const grouped = useMemo(() => {
    const order = (roles.data?.manageable || ["admin", "hub_manager", "hub_supervisor", "spokesperson", "architect", "site_engineer"]);
    const g = {};
    for (const u of users.data || []) (g[u.role] ||= []).push(u);
    return order.filter((r) => g[r]).map((r) => ({ role: r, list: g[r] }));
  }, [users.data, roles.data]);

  if (users.loading && !users.data) return <PageSkeleton stats={0} rows={8} />;
  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-head text-2xl font-extrabold text-ink">Team &amp; access</h1>
          <p className="text-xs text-muted">Manage regions, spokes and who can do what. You are signed in as <b className="text-ink/80">{ROLE_LABEL[me?.role] || me?.role}</b>.</p>
        </div>
        <Button size="sm" variant="ghost" onClick={reload}>Refresh</Button>
      </div>
      {msg && <p className={`text-xs ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>}

      <div className="grid gap-4 lg:grid-cols-2">
        <SpokesCard spokes={spokes.data || []} onFlash={flash} onDone={reload} canAdd={me?.role === "admin" || (ranks[me?.role] || 0) >= (ranks.hub_supervisor || 60)} />
        <AddMember assignable={assignable} spokes={spokes.data || []} onFlash={flash} onDone={users.reload} />
      </div>

      {grouped.length === 0 ? <Card title="Team members"><p className="text-sm text-muted">No team members loaded (need admin / manager / supervisor access).</p></Card> : (
        <Card title="Team members" right={<span className="text-[11px] text-muted">{(users.data || []).length} accounts</span>}>
          {grouped.map(({ role, list }) => (
            <div key={role} className="mb-4">
              <div className="mb-1 flex items-center gap-2">
                <h3 className="text-sm font-semibold text-ink">{ROLE_LABEL[role] || role}</h3>
                <span className="text-[11px] text-muted">{list.length}</span>
              </div>
              <Table head={["Name", "Email", "Team", "Role", "Status", ""]}>
                {list.map((u) => (
                  <MemberRow key={u.id} u={u} me={me} canManage={canManage(u.role)} assignable={assignable}
                    spokeName={spokeMap[u.org_ref]} spokes={spokes.data || []} isField={FIELD_ROLES.includes(u.role)}
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

function SpokesCard({ spokes, onFlash, onDone, canAdd }) {
  const [name, setName] = useState("");
  const [geo, setGeo] = useState("");
  const [busy, setBusy] = useState(false);
  const [regionFor, setRegionFor] = useState("");
  const [region, setRegion] = useState("");

  const addSpoke = async (e) => {
    e.preventDefault(); setBusy(true);
    try { await site.createSpoke({ name, geofence: geo }); onFlash(true, `Spoke "${name}" created.`); setName(""); setGeo(""); onDone(); }
    catch (e) { onFlash(false, e.message); } finally { setBusy(false); }
  };
  const addRegion = async () => {
    if (!regionFor || !region.trim()) return;
    setBusy(true);
    try { await site.changeArea(regionFor, region.trim(), "add"); onFlash(true, `Region "${region.trim()}" added.`); setRegion(""); onDone(); }
    catch (e) { onFlash(false, e.message); } finally { setBusy(false); }
  };

  return (
    <Card title="Regions &amp; spokes">
      {canAdd ? (
        <form onSubmit={addSpoke} className="mb-3 space-y-2 border-b border-border/60 pb-3">
          <div className="grid grid-cols-2 gap-2">
            <Field label="New spoke name"><Input value={name} required placeholder="e.g. Whitefield Spoke" onChange={(e) => setName(e.target.value)} /></Field>
            <Field label="Geofence (optional)"><Input value={geo} placeholder="e.g. east zone" onChange={(e) => setGeo(e.target.value)} /></Field>
          </div>
          <Button size="sm" type="submit" disabled={busy || !name.trim()}>Add spoke</Button>
        </form>
      ) : <p className="mb-3 text-[11px] text-muted">Only a supervisor and above can add spokes/regions.</p>}

      <div className="space-y-1.5">
        {spokes.length === 0 ? <p className="text-sm text-muted">No spokes yet.</p> : spokes.map((s) => (
          <div key={s.id} className="border border-border/60 bg-panel2 px-2.5 py-1.5 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-ink/85">📍 {s.name} <span className="text-[11px] text-muted">({s.id})</span></span>
              {canAdd && <button className="text-[11px] text-accent hover:underline" onClick={() => setRegionFor(regionFor === s.id ? "" : s.id)}>{regionFor === s.id ? "cancel" : "add region"}</button>}
            </div>
            <p className="mt-0.5 text-[11px] text-muted">Regions: {(s.areas || []).map((a) => a.area || a).join(", ") || "none"}</p>
            {regionFor === s.id && (
              <div className="mt-1.5 flex gap-2">
                <Input value={region} placeholder="region keyword" onChange={(e) => setRegion(e.target.value)} />
                <Button size="sm" onClick={addRegion} disabled={busy || !region.trim()}>Add</Button>
              </div>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}

function AddMember({ assignable, spokes, onFlash, onDone }) {
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
    <Card title="Add team member">
      {assignable.length === 0 ? <p className="text-sm text-muted">Your role cannot create members.</p> : (
        <form onSubmit={save} className="space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <Field label="Email"><Input type="email" value={f.email} required placeholder="name@consmat.com" onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
            <Field label="Name"><Input value={f.name} placeholder="full name" onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Role">
              <Select value={f.role} required onChange={(e) => setF({ ...f, role: e.target.value })}>
                <option value="">- pick role -</option>
                {assignable.map((r) => <option key={r} value={r}>{ROLE_LABEL[r] || r}</option>)}
              </Select>
            </Field>
            <Field label="Temp password"><Input value={f.password} required placeholder="min 4 chars" onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
          </div>
          {isField && (
            <Field label="Team (spoke)">
              <Select value={f.org_ref} onChange={(e) => setF({ ...f, org_ref: e.target.value })}>
                <option value="">- unassigned -</option>
                {spokes.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </Select>
            </Field>
          )}
          <Button size="sm" type="submit" disabled={busy || !f.role || !f.email.trim()}>Create member</Button>
          <p className="text-[11px] text-muted">You can only create roles below your own. The member signs in with the temp password.</p>
        </form>
      )}
    </Card>
  );
}

function MemberRow({ u, me, canManage, assignable, spokeName, spokes, isField, onFlash, onDone }) {
  const [busy, setBusy] = useState(false);
  const isSelf = u.id === me?.sub || u.id === me?.email || u.id === me?.id;
  // roles this actor may move the user INTO (their assignable set), always including the current role for display
  const roleOptions = [...new Set([u.role, ...assignable])];

  const patch = async (b, ok) => {
    setBusy(true);
    try { await team.updateUser(u.id, b); onFlash(true, ok); onDone(); }
    catch (e) { onFlash(false, e.message); } finally { setBusy(false); }
  };

  return (
    <tr className="border-b border-border/50">
      <Td>{u.name}</Td>
      <Td className="text-muted">{u.id}</Td>
      <Td className="text-muted">{isField ? (spokeName || u.org_ref || "-") : "-"}</Td>
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
        ) : <span className="text-[11px] text-muted">{isSelf ? "you" : "-"}</span>}
      </Td>
    </tr>
  );
}
