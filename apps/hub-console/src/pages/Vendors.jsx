import { useState } from "react";
import { inv, proc, MATERIALS, inr } from "../api.js";
import { Card, Table, Td, Badge, Button, Field, Input, Select, useAsync } from "../components/ui.jsx";

export default function Vendors() {
  const vendors = useAsync(() => proc.vendors());
  const products = useAsync(() => inv.products());
  const [material, setMaterial] = useState("cement");
  const market = useAsync(() => proc.market(material), [material]);
  const [msg, setMsg] = useState(null);

  const [nv, setNv] = useState({ name: "", city: "" });
  const addVendor = async (e) => {
    e.preventDefault(); setMsg(null);
    try { await proc.addVendor({ name: nv.name, city: nv.city }); setNv({ name: "", city: "" }); vendors.reload(); }
    catch (e) { setMsg(e.message); }
  };

  const [pr, setPr] = useState({ vendor_id: "", product_id: "", price: "" });
  const setPrice = async (e) => {
    e.preventDefault(); setMsg(null);
    try { await proc.setPrice(pr.vendor_id, { product_id: pr.product_id, price: Number(pr.price) }); setPr({ ...pr, price: "" }); market.reload(); }
    catch (e) { setMsg(e.message); }
  };

  return (
    <div className="space-y-5">
      <h1 className="font-head text-2xl font-extrabold text-white">Vendors & Products</h1>
      {msg && <p className="text-xs text-red-400">{msg}</p>}

      <ProductSearch />

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
          <Card title="Set product price">
            <form onSubmit={setPrice} className="space-y-3">
              <Field label="Vendor">
                <Select value={pr.vendor_id} required onChange={(e) => setPr({ ...pr, vendor_id: e.target.value })}>
                  <option value="">select…</option>
                  {(vendors.data || []).map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
                </Select>
              </Field>
              <Field label="Product (brand)">
                <Select value={pr.product_id} required onChange={(e) => setPr({ ...pr, product_id: e.target.value })}>
                  <option value="">select…</option>
                  {(products.data || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </Select>
              </Field>
              <Field label="Price (₹/unit)"><Input type="number" step="any" value={pr.price} required onChange={(e) => setPr({ ...pr, price: e.target.value })} /></Field>
              <Button type="submit">Save price</Button>
            </form>
          </Card>
        </div>
      </div>

      <Card title="Market view — branded products (cheapest first)"
        right={<Select value={material} onChange={(e) => setMaterial(e.target.value)}>{MATERIALS.map((m) => <option key={m} value={m}>{m}</option>)}</Select>}>
        {market.error ? <p className="text-sm text-red-400">{market.error}</p> : (
          <Table head={["#", "Product", "Brand", "Vendor", "Price", ""]}>
            {(market.data || []).map((r, i) => (
              <tr key={`${r.vendor_id}-${r.product_id}`} className="border-b border-border/50">
                <Td mono className="text-muted">{i + 1}</Td>
                <Td>{r.product_name}</Td>
                <Td>{r.brand || <span className="text-muted">—</span>}</Td>
                <Td>{r.vendor_name} {r.is_hub_self && <Badge tone="accent">hub</Badge>}</Td>
                <Td mono className={i === 0 ? "text-accent" : ""}>{inr(r.price)}</Td>
                <Td>{i === 0 && <Badge tone="ok">best</Badge>}</Td>
              </tr>
            ))}
            {market.data?.length === 0 && <tr><Td className="text-muted">No vendor prices for {material}.</Td></tr>}
          </Table>
        )}
      </Card>

      <MarketScan material={material} />
    </div>
  );
}

function MarketScan({ material }) {
  const offers = useAsync(() => proc.externalOffers(material), [material]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const scan = async () => {
    setBusy(true); setMsg(null);
    try { const r = await proc.scout(material); setMsg(`Scouted ${r.count} offer(s) via ${r.provider}.`); offers.reload(); }
    catch (e) { setMsg(e.message); } finally { setBusy(false); }
  };
  return (
    <Card title={`External market scan — ${material}`}
      right={<Button size="sm" onClick={scan} disabled={busy}>{busy ? "Scanning…" : "Scan the market"}</Button>}>
      {msg && <p className="mb-2 text-xs text-muted">{msg}</p>}
      <p className="mb-2 text-[11px] text-[#f59e0b]">Advisory only — indicative internet prices, not firm quotes. Verify before purchase.</p>
      {offers.data?.length ? (
        <Table head={["Seller", "Product", "Price", "Source", ""]}>
          {offers.data.map((o) => (
            <tr key={o.id} className="border-b border-border/50">
              <Td>{o.seller || "—"}</Td>
              <Td className="text-muted">{o.product_name || "—"}</Td>
              <Td mono>{inr(o.price)}</Td>
              <Td className="text-muted">{o.source}</Td>
              <Td><Badge tone={o.confidence === "firm" ? "ok" : "warn"}>{o.confidence}</Badge></Td>
            </tr>
          ))}
        </Table>
      ) : <p className="text-sm text-muted">No external offers yet — click “Scan the market”.</p>}
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
                <Td>{p.brand || "—"}</Td>
                <Td className="text-muted">{p.grade || "—"}</Td>
                <Td mono className="text-muted">{p.material_id}</Td>
              </tr>
            ))}
          </Table>
        )
      )}
    </Card>
  );
}
