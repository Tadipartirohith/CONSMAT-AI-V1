import { useState } from "react";
import { inv, price, MATERIALS, TIERS, inr } from "../api.js";
import { Card, Table, Td, Badge, Button, Field, Input, Select, useAsync } from "../components/ui.jsx";

export default function Pricing() {
  const margins = useAsync(() => price.margins());
  const products = useAsync(() => inv.products());
  const [msg, setMsg] = useState(null);

  const [rule, setRule] = useState({ product_id: "", material_id: "", tier: "", margin_pct: "" });
  const saveRule = async (e) => {
    e.preventDefault(); setMsg(null);
    try {
      await price.setMargin({
        product_id: rule.product_id || null,
        material_id: rule.product_id ? null : (rule.material_id || null),
        tier: rule.tier || null,
        margin_pct: Number(rule.margin_pct),
      });
      setRule({ product_id: "", material_id: "", tier: "", margin_pct: "" });
      margins.reload();
    } catch (e) { setMsg(e.message); }
  };

  const [look, setLook] = useState({ product_id: "", tier: "individual" });
  const priced = useAsync(() => (look.product_id ? price.priceProduct(look.product_id, look.tier) : Promise.resolve(null)), [look.product_id, look.tier]);
  const productName = (id) => (products.data || []).find((p) => p.id === id)?.name || id;

  return (
    <div className="space-y-5">
      <h1 className="font-head text-2xl font-extrabold text-white">Pricing & Margins</h1>
      {msg && <p className="text-xs text-red-400">{msg}</p>}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Margin rules" className="lg:col-span-2" right={<Button size="sm" variant="ghost" onClick={margins.reload}>Refresh</Button>}>
          <Table head={["Product", "Material", "Tier", "Margin %", "Updated"]}>
            {(margins.data || []).map((m) => (
              <tr key={m.id} className="border-b border-border/50">
                <Td>{m.product_id ? productName(m.product_id) : <span className="text-muted">any</span>}</Td>
                <Td>{m.material_id || <span className="text-muted">any</span>}</Td>
                <Td>{m.tier || <span className="text-muted">any</span>}</Td>
                <Td mono>{m.margin_pct}%</Td>
                <Td className="text-muted">{m.updated_at ? new Date(m.updated_at).toLocaleDateString() : "-"}</Td>
              </tr>
            ))}
          </Table>
          <p className="mt-3 text-[11px] text-muted">Precedence: product+tier &gt; product &gt; material+tier &gt; material &gt; tier &gt; global.</p>
        </Card>

        <div className="space-y-4">
          <Card title="Set margin rule">
            <form onSubmit={saveRule} className="space-y-3">
              <Field label="Product (brand) — blank = whole category">
                <Select value={rule.product_id} onChange={(e) => setRule({ ...rule, product_id: e.target.value })}>
                  <option value="">any product</option>
                  {(products.data || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </Select>
              </Field>
              <Field label="Material (used only when no product)">
                <Select value={rule.material_id} disabled={!!rule.product_id} onChange={(e) => setRule({ ...rule, material_id: e.target.value })}>
                  <option value="">any</option>{MATERIALS.map((m) => <option key={m} value={m}>{m}</option>)}
                </Select>
              </Field>
              <Field label="Tier (blank = any)">
                <Select value={rule.tier} onChange={(e) => setRule({ ...rule, tier: e.target.value })}>
                  <option value="">any</option>{TIERS.map((t) => <option key={t} value={t}>{t}</option>)}
                </Select>
              </Field>
              <Field label="Margin %"><Input type="number" step="any" value={rule.margin_pct} required onChange={(e) => setRule({ ...rule, margin_pct: e.target.value })} /></Field>
              <Button type="submit">Save rule</Button>
            </form>
          </Card>

          <Card title="Product price lookup">
            <div className="mb-3 flex gap-2">
              <Select value={look.product_id} onChange={(e) => setLook({ ...look, product_id: e.target.value })}>
                <option value="">select product…</option>
                {(products.data || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </Select>
              <Select value={look.tier} onChange={(e) => setLook({ ...look, tier: e.target.value })}>{TIERS.map((t) => <option key={t} value={t}>{t}</option>)}</Select>
            </div>
            {priced.error ? <p className="text-sm text-red-400">{priced.error}</p> : priced.data ? (
              <div className="space-y-1 text-sm">
                <p>Landed cost: <span className="font-mono text-white">{inr(priced.data.landed_cost)}</span></p>
                <p>Margin: <span className="font-mono text-white">{priced.data.margin_pct}%</span> <Badge>{priced.data.rule}</Badge></p>
                <p className="text-base">Selling price: <span className="font-mono font-bold text-accent">{inr(priced.data.unit_price)}</span></p>
              </div>
            ) : <p className="text-sm text-muted">Pick a product to see its price.</p>}
          </Card>
        </div>
      </div>
    </div>
  );
}
