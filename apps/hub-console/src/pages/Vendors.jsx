import { useState } from "react";
import { inv, proc, MATERIALS, inr } from "../api.js";
import { getUser } from "../auth.js";
import { Card, Table, Td, Badge, Button, Field, Input, Select, useAsync } from "../components/ui.jsx";

export default function Vendors() {
  const role = getUser()?.role;
  const isApprover = ["hub_supervisor", "hub_manager", "admin"].includes(role);
  const vendors = useAsync(() => proc.vendors());
  const requests = useAsync(() => proc.vendorRequests("pending"));
  const products = useAsync(() => inv.products());
  const [material, setMaterial] = useState("cement");
  const market = useAsync(() => proc.market(material), [material]);
  const [msg, setMsg] = useState(null);

  const [nv, setNv] = useState({ name: "", city: "" });
  const addVendor = async (e) => {
    e.preventDefault(); setMsg(null);
    try {
      if (isApprover) { await proc.addVendor({ name: nv.name, city: nv.city }); setMsg("Vendor added."); }
      else { await proc.requestVendor({ action: "add", name: nv.name, city: nv.city }); setMsg("Add request submitted for approval."); }
      setNv({ name: "", city: "" }); vendors.reload(); requests.reload();
    } catch (e) { setMsg(e.message); }
  };
  const removeVendor = async (v) => {
    setMsg(null);
    try {
      if (isApprover) { await proc.deactivateVendor(v.id); setMsg(`${v.name} deactivated.`); }
      else { await proc.requestVendor({ action: "remove", vendor_id: v.id }); setMsg("Remove request submitted for approval."); }
      vendors.reload(); requests.reload();
    } catch (e) { setMsg(e.message); }
  };
  const decide = async (id, approve) => {
    setMsg(null);
    try { await proc.decideVendor(id, approve); setMsg(approve ? "Approved." : "Rejected."); requests.reload(); vendors.reload(); }
    catch (e) { setMsg(e.message); }
  };
  const toggleBlock = async (v) => {
    setMsg(null);
    try {
      if (v.blocked) { await proc.unblockVendor(v.id); setMsg(`${v.name} removed from the blacklist.`); }
      else { await proc.blockVendor(v.id); setMsg(`${v.name} blacklisted - excluded from all procurement.`); }
      vendors.reload();
    } catch (e) { setMsg(e.message); }
  };


  return (
    <div className="space-y-5">
      <h1 className="font-head text-2xl font-extrabold text-ink">Vendors & Products</h1>
      {msg && <p className="text-xs text-red-400">{msg}</p>}

      <ProductSearch />

      {requests.data?.length > 0 && (
        <Card title={isApprover ? "Vendor requests awaiting approval" : "Your pending vendor requests"}>
          <Table head={["Action", "Vendor", "City", "Requested by", isApprover ? "Decide" : "Status"]}>
            {requests.data.map((r) => (
              <tr key={r.id} className="border-b border-border/50">
                <Td><Badge tone={r.action === "remove" ? "bad" : "ok"}>{r.action}</Badge></Td>
                <Td>{r.name || r.vendor_id}</Td>
                <Td className="text-muted">{r.city || "-"}</Td>
                <Td className="text-muted">{r.requested_by || r.requested_by_role}</Td>
                <Td>
                  {isApprover ? (
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => decide(r.id, true)}>Approve</Button>
                      <Button size="sm" variant="ghost" onClick={() => decide(r.id, false)}>Reject</Button>
                    </div>
                  ) : <Badge tone="warn">pending</Badge>}
                </Td>
              </tr>
            ))}
          </Table>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Vendor registry" className="lg:col-span-2" right={<Button size="sm" variant="ghost" onClick={vendors.reload}>Refresh</Button>}>
          <Table head={["ID", "Name", "City", "Status", ""]}>
            {(vendors.data || []).map((v) => (
              <tr key={v.id} className={`border-b border-border/50 ${v.blocked ? "opacity-60" : ""}`}>
                <Td mono className="text-muted">{v.id}</Td>
                <Td>{v.name}</Td>
                <Td>{v.city || "-"}</Td>
                <Td>
                  {v.is_hub_self ? <Badge tone="accent">hub</Badge>
                    : v.blocked ? <Badge tone="bad">blacklisted</Badge>
                    : <Badge tone={v.active ? "ok" : "muted"}>{v.active ? "active" : "inactive"}</Badge>}
                </Td>
                <Td>{!v.is_hub_self && (
                  <div className="flex gap-2">
                    {v.active && !v.blocked && (
                      <Button size="sm" variant="ghost" onClick={() => removeVendor(v)}>{isApprover ? "Remove" : "Request remove"}</Button>
                    )}
                    {isApprover && (
                      <Button size="sm" variant={v.blocked ? "ghost" : "danger"} onClick={() => toggleBlock(v)}>
                        {v.blocked ? "Unblock" : "Block"}
                      </Button>
                    )}
                  </div>
                )}</Td>
              </tr>
            ))}
          </Table>
        </Card>

        <div className="space-y-4">
          <Card title={isApprover ? "Add vendor" : "Request to add vendor"}>
            <form onSubmit={addVendor} className="space-y-3">
              <Field label="Name"><Input value={nv.name} required onChange={(e) => setNv({ ...nv, name: e.target.value })} /></Field>
              <Field label="City"><Input value={nv.city} onChange={(e) => setNv({ ...nv, city: e.target.value })} /></Field>
              <Button type="submit">{isApprover ? "Add vendor" : "Submit request"}</Button>
              {!isApprover && <p className="text-[11px] text-muted">A supervisor or manager will approve this.</p>}
            </form>
          </Card>
          <Card title="Vendor prices">
            <p className="text-sm text-muted">Prices are now captured when you <b className="text-ink/80">receive stock</b> (Inventory to Receive stock records the vendor, product and rate together). The market view below reflects the latest rates.</p>
          </Card>
        </div>
      </div>

      <Card title="Market view, branded products (cheapest first)"
        right={<Select value={material} onChange={(e) => setMaterial(e.target.value)}>{MATERIALS.map((m) => <option key={m} value={m}>{m}</option>)}</Select>}>
        {market.error ? <p className="text-sm text-red-400">{market.error}</p> : (
          <Table head={["#", "Product", "Brand", "Vendor", "Price", ""]}>
            {(market.data || []).map((r, i) => (
              <tr key={`${r.vendor_id}-${r.product_id}`} className="border-b border-border/50">
                <Td mono className="text-muted">{i + 1}</Td>
                <Td>{r.product_name}</Td>
                <Td>{r.brand || <span className="text-muted">-</span>}</Td>
                <Td>{r.vendor_name} {r.is_hub_self && <Badge tone="accent">hub</Badge>}{i === 0 && <Badge tone="ok">best</Badge>}</Td>
                <Td mono className={i === 0 ? "text-accent" : ""}>{inr(r.price)}</Td>
                <Td><BuyNow row={r} onOrdered={() => setMsg("Order placed.")} /></Td>
              </tr>
            ))}
            {market.data?.length === 0 && <tr><Td className="text-muted">No vendor prices for {material}.</Td></tr>}
          </Table>
        )}
      </Card>

      <MarketScan />
    </div>
  );
}

function BuyNow({ row, onOrdered }) {
  const [open, setOpen] = useState(false);
  const [qty, setQty] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const place = async (e) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try {
      await proc.createOrder({ lines: [{ material_id: row.material_id, product_id: row.product_id, product_name: row.product_name, vendor_id: row.vendor_id, qty: Number(qty), unit_cost: row.price }], note: "buy-now from market view" });
      setOpen(false); setQty(""); onOrdered();
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };
  if (!open) return <Button size="sm" onClick={() => setOpen(true)}>Buy now</Button>;
  return (
    <form onSubmit={place} className="flex items-center gap-1">
      <div className="w-20"><Input type="number" step="any" value={qty} placeholder="qty" required onChange={(e) => setQty(e.target.value)} /></div>
      <Button size="sm" type="submit" disabled={busy}>Order</Button>
      <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>✕</Button>
      {err && <span className="text-[11px] text-red-400">{err}</span>}
    </form>
  );
}

function MarketScan() {
  const offers = useAsync(() => proc.externalOffers());
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [cat, setCat] = useState("all");
  const scanAll = async () => {
    setBusy(true); setMsg(null);
    try {
      const targets = cat === "all" ? MATERIALS : [cat];
      let n = 0, prov = "";
      for (const m of targets) { const r = await proc.scout(m); n += r.count; prov = r.provider; }
      setMsg(`Scouted ${n} offer(s) across ${targets.length} categor(ies) via ${prov}.`);
      offers.reload();
    } catch (e) { setMsg(e.message); } finally { setBusy(false); }
  };
  const list = (offers.data || []).filter((o) => cat === "all" || o.material_id === cat);
  return (
    <Card title="External market scan (all categories)"
      right={<div className="flex items-center gap-2">
        <Select value={cat} onChange={(e) => setCat(e.target.value)}>
          <option value="all">all categories</option>
          {MATERIALS.map((m) => <option key={m} value={m}>{m}</option>)}
        </Select>
        <Button size="sm" onClick={scanAll} disabled={busy}>{busy ? "Scanning…" : "Scan the market"}</Button>
      </div>}>
      {msg && <p className="mb-2 text-xs text-muted">{msg}</p>}
      <p className="mb-2 text-[11px] text-[#f59e0b]">Advisory only - indicative internet prices, not firm quotes. Verify before purchase.</p>
      {list.length ? (
        <Table head={["Category", "Seller", "Product", "Price", "Source", ""]}>
          {list.map((o) => (
            <tr key={o.id} className="border-b border-border/50">
              <Td className="text-muted">{o.material_id}</Td>
              <Td>{o.seller || "-"}</Td>
              <Td className="text-muted">{o.product_name || "-"}</Td>
              <Td mono>{inr(o.price)}</Td>
              <Td><Badge tone={o.confidence === "firm" ? "ok" : "warn"}>{o.source}</Badge></Td>
              <Td>{o.url ? <a href={o.url} target="_blank" rel="noreferrer"><Button size="sm">Buy now </Button></a> : <span className="text-muted">-</span>}</Td>
            </tr>
          ))}
        </Table>
      ) : <p className="text-sm text-muted">No external offers yet - pick a category and click “Scan the market”.</p>}
    </Card>
  );
}

function ProductSearch() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState(null);
  const [busy, setBusy] = useState(false);
  const search = async (e) => {
    e.preventDefault();
    setBusy(true);
    try { setResults(await inv.searchProducts(q)); } catch { setResults([]); } finally { setBusy(false); }
  };
  return (
    <Card title="Search product catalog">
      <form onSubmit={search} className="mb-3 flex gap-2">
        <Input value={q} placeholder="e.g. ultratech 53, ppc cement, aac block" onChange={(e) => setQ(e.target.value)} />
        <Button type="submit" disabled={busy}>Search</Button>
      </form>
      {results && (
        results.length === 0 ? <p className="text-sm text-muted">No products match “{q}”.</p> : (
          <Table head={["Product", "Brand", "Grade", "Material"]}>
            {results.map((p) => (
              <tr key={p.id} className="border-b border-border/50">
                <Td>{p.name}</Td>
                <Td>{p.brand || "-"}</Td>
                <Td className="text-muted">{p.grade || "-"}</Td>
                <Td mono className="text-muted">{p.material_id}</Td>
              </tr>
            ))}
          </Table>
        )
      )}
    </Card>
  );
}
