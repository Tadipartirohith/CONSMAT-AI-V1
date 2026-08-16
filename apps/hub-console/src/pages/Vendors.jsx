import { useState } from "react";
import { proc, MATERIALS, inr } from "../api.js";
import { Card, Table, Td, Badge, Button, Field, Input, Select, useAsync } from "../components/ui.jsx";

export default function Vendors() {
  const vendors = useAsync(() => proc.vendors());
  const [material, setMaterial] = useState("cement");
  const market = useAsync(() => proc.market(material), [material]);
  const [msg, setMsg] = useState(null);

  const [nv, setNv] = useState({ name: "", city: "" });
  const addVendor = async (e) => {
    e.preventDefault();
    setMsg(null);
    try { await proc.addVendor({ name: nv.name, city: nv.city }); setNv({ name: "", city: "" }); vendors.reload(); market.reload(); }
    catch (e) { setMsg(e.message); }
  };

  const [pr, setPr] = useState({ vendor_id: "", material_id: "cement", price: "" });
  const setPrice = async (e) => {
    e.preventDefault();
    setMsg(null);
    try { await proc.setPrice(pr.vendor_id, { material_id: pr.material_id, price: Number(pr.price) }); setPr({ ...pr, price: "" }); market.reload(); }
    catch (e) { setMsg(e.message); }
  };

  return (
    <div className="space-y-5">
      <h1 className="font-head text-2xl font-extrabold text-white">Vendors & Pricing</h1>
      {msg && <p className="text-xs text-red-400">{msg}</p>}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Vendor registry" className="lg:col-span-2" right={<Button size="sm" variant="ghost" onClick={vendors.reload}>Refresh</Button>}>
          <Table head={["ID", "Name", "City", "Type"]}>
            {(vendors.data || []).map((v) => (
              <tr key={v.id} className="border-b border-border/50">
                <Td mono className="text-muted">{v.id}</Td>
                <Td>{v.name}</Td>
                <Td>{v.city || "—"}</Td>
                <Td>{v.is_hub_self ? <Badge tone="accent">hub</Badge> : <Badge>{v.active ? "active" : "inactive"}</Badge>}</Td>
              </tr>
            ))}
          </Table>
        </Card>

        <div className="space-y-4">
          <Card title="Add vendor">
            <form onSubmit={addVendor} className="space-y-3">
              <Field label="Name"><Input value={nv.name} required onChange={(e) => setNv({ ...nv, name: e.target.value })} /></Field>
              <Field label="City"><Input value={nv.city} onChange={(e) => setNv({ ...nv, city: e.target.value })} /></Field>
              <Button type="submit">Add vendor</Button>
            </form>
          </Card>
          <Card title="Set / update price">
            <form onSubmit={setPrice} className="space-y-3">
              <Field label="Vendor">
                <Select value={pr.vendor_id} required onChange={(e) => setPr({ ...pr, vendor_id: e.target.value })}>
                  <option value="">select…</option>
                  {(vendors.data || []).map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
                </Select>
              </Field>
              <Field label="Material">
                <Select value={pr.material_id} onChange={(e) => setPr({ ...pr, material_id: e.target.value })}>
                  {MATERIALS.map((m) => <option key={m} value={m}>{m}</option>)}
                </Select>
              </Field>
              <Field label="Price (₹/unit)"><Input type="number" step="any" value={pr.price} required onChange={(e) => setPr({ ...pr, price: e.target.value })} /></Field>
              <Button type="submit">Save price</Button>
            </form>
          </Card>
        </div>
      </div>

      <Card title="Market view (cheapest first)"
        right={<Select value={material} onChange={(e) => setMaterial(e.target.value)}>{MATERIALS.map((m) => <option key={m} value={m}>{m}</option>)}</Select>}>
        {market.error ? <p className="text-sm text-red-400">{market.error}</p> : (
          <Table head={["#", "Vendor", "City", "Price", ""]}>
            {(market.data || []).map((r, i) => (
              <tr key={r.vendor_id} className="border-b border-border/50">
                <Td mono className="text-muted">{i + 1}</Td>
                <Td>{r.vendor_name} {r.is_hub_self && <Badge tone="accent">hub</Badge>}</Td>
                <Td>{r.city || "—"}</Td>
                <Td mono className={i === 0 ? "text-accent" : ""}>{inr(r.price)}</Td>
                <Td>{i === 0 && <Badge tone="ok">best</Badge>}</Td>
              </tr>
            ))}
            {market.data?.length === 0 && <tr><Td className="text-muted">No active vendor prices for {material}.</Td></tr>}
          </Table>
        )}
      </Card>
    </div>
  );
}
