import { useMemo, useState } from "react";
import { inv, price, TIERS, inr } from "../api.js";
import { Card, Table, Td, Badge, Button, Input, Select, useAsync, PageSkeleton } from "../components/ui.jsx";

const ICON = { cement: "🧱", steel: "🔩", sand: "🏖️", aggregate: "🪨", bricks: "🟥" };

// Client-side mirror of the pricing precedence (D22): product+tier > product > material+tier >
// material > tier > global > default(12).
function resolveMargin(rules, product, tier) {
  const find = (p, m, t) => rules.find((r) => (r.product_id || null) === (p || null)
    && (r.material_id || null) === (m || null) && (r.tier || null) === (t || null));
  const cands = [
    [product.id, null, tier, "product+tier"], [product.id, null, null, "product"],
    [null, product.material_id, tier, "material+tier"], [null, product.material_id, null, "material"],
    [null, null, tier, "tier"], [null, null, null, "global"],
  ];
  for (const [p, m, t, label] of cands) { const r = find(p, m, t); if (r) return { pct: Number(r.margin_pct), rule: label, id: r.id }; }
  return { pct: 12, rule: "default", id: null };
}

export default function Pricing() {
  const materials = useAsync(() => inv.materials());
  const products = useAsync(() => inv.products());
  const pstock = useAsync(() => inv.productStock());
  const margins = useAsync(() => price.margins());
  const [cat, setCat] = useState(null);
  const [tier, setTier] = useState("individual");
  const [msg, setMsg] = useState(null);

  const stockOf = (pid) => (pstock.data || []).find((s) => s.product_id === pid);
  const reload = () => margins.reload();

  if (pstock.loading && !pstock.data) return <PageSkeleton stats={0} rows={8} />;
  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-head text-2xl font-extrabold text-ink">Pricing & Margins</h1>
          <p className="text-xs text-muted">Set a margin per product. Precedence: product &gt; material &gt; tier &gt; global.</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] uppercase tracking-wider text-muted">Preview tier</span>
          <Select value={tier} onChange={(e) => setTier(e.target.value)}>{TIERS.map((t) => <option key={t} value={t}>{t}</option>)}</Select>
        </div>
      </div>
      {msg && <p className={`text-xs ${msg.ok ? "text-emerald-400" : "text-red-400"}`}>{msg.text}</p>}

      {!cat ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {(materials.data || []).map((m) => (
            <button key={m.id} onClick={() => setCat(m.id)}
              className="flex flex-col items-start gap-1 rounded-xl border border-border bg-panel p-4 text-left hover:border-accent">
              <span className="text-2xl">{ICON[m.id] || "📦"}</span>
              <span className="text-sm font-semibold text-ink">{m.name}</span>
              <span className="text-[11px] text-muted">{(products.data || []).filter((p) => p.material_id === m.id).length} products</span>
            </button>
          ))}
        </div>
      ) : (
        <CategoryPricing
          material={(materials.data || []).find((m) => m.id === cat)}
          products={(products.data || []).filter((p) => p.material_id === cat)}
          rules={margins.data || []} tier={tier} stockOf={stockOf}
          onBack={() => setCat(null)}
          onSaved={(t) => { setMsg({ ok: true, text: t }); reload(); }}
          onError={(t) => setMsg({ ok: false, text: t })} />
      )}

      <BaseRules rules={margins.data || []} onChanged={reload} onMsg={setMsg} />
    </div>
  );
}

function CategoryPricing({ material, products, rules, tier, stockOf, onBack, onSaved, onError }) {
  return (
    <Card title={`${material?.name} - per-product margins (${tier})`}
      right={<Button size="sm" variant="ghost" onClick={onBack}>Back to Categories</Button>}>
      <Table head={["Product", "Brand", "Landed cost", "Margin %", "Selling price", "Source", ""]}>
        {products.map((p) => (
          <ProductRow key={p.id} product={p} rules={rules} tier={tier} stock={stockOf(p.id)}
            onSaved={onSaved} onError={onError} />
        ))}
        {products.length === 0 && <tr><Td className="text-muted">No products in this category.</Td></tr>}
      </Table>
      <p className="mt-2 text-[11px] text-muted">Setting a margin here creates/updates a rule for that specific product. Blank to fall back to the category/tier default.</p>
    </Card>
  );
}

function ProductRow({ product, rules, tier, stock, onSaved, onError }) {
  const resolved = useMemo(() => resolveMargin(rules, product, tier), [rules, product, tier]);
  const landed = stock ? Number(stock.avg_cost) : 0;
  const sell = landed > 0 ? landed * (1 + resolved.pct / 100) : 0;
  const [val, setVal] = useState("");
  const [busy, setBusy] = useState(false);

  const save = async () => {
    if (val === "") return;
    setBusy(true);
    try { await price.setMargin({ product_id: product.id, margin_pct: Number(val) }); setVal(""); onSaved(`${product.name}: margin set to ${val}%.`); }
    catch (e) { onError(e.message); } finally { setBusy(false); }
  };
  const clearRule = async () => {
    if (resolved.rule !== "product+tier" && resolved.rule !== "product") return;
    setBusy(true);
    try { await price.deleteMargin(resolved.id); onSaved(`${product.name}: product margin removed.`); }
    catch (e) { onError(e.message); } finally { setBusy(false); }
  };
  const isProductRule = resolved.rule === "product" || resolved.rule === "product+tier";

  return (
    <tr className="border-b border-border/50">
      <Td>{product.name}</Td>
      <Td className="text-muted">{product.brand || "-"}</Td>
      <Td mono>{landed > 0 ? inr(landed) : <span className="text-muted">no stock</span>}</Td>
      <Td mono>{resolved.pct}%</Td>
      <Td mono className="text-accent">{sell > 0 ? inr(sell) : "-"}</Td>
      <Td><Badge tone={isProductRule ? "ok" : "muted"}>{resolved.rule}</Badge></Td>
      <Td>
        <div className="flex items-center gap-1">
          <div className="w-16"><Input type="number" step="any" value={val} placeholder="%" onChange={(e) => setVal(e.target.value)} /></div>
          <Button size="sm" onClick={save} disabled={busy || val === ""}>Set</Button>
          {isProductRule && <Button size="sm" variant="ghost" onClick={clearRule} disabled={busy}>clear</Button>}
        </div>
      </Td>
    </tr>
  );
}

function BaseRules({ rules, onChanged, onMsg }) {
  const [open, setOpen] = useState(false);
  const base = rules.filter((r) => !r.product_id);
  const del = async (id) => { try { await price.deleteMargin(id); onChanged(); } catch (e) { onMsg({ ok: false, text: e.message }); } };
  return (
    <Card title="Base rules (category / tier / global fallbacks)" right={<Button size="sm" variant="ghost" onClick={() => setOpen(!open)}>{open ? "Hide" : "Show"}</Button>}>
      {!open ? <p className="text-sm text-muted">The defaults used when a product has no specific margin.</p> : (
        <Table head={["Material", "Tier", "Margin %", ""]}>
          {base.map((m) => (
            <tr key={m.id} className="border-b border-border/50">
              <Td>{m.material_id || <span className="text-muted">any</span>}</Td>
              <Td>{m.tier || <span className="text-muted">any</span>}</Td>
              <Td mono>{m.margin_pct}%</Td>
              <Td><Button size="sm" variant="ghost" onClick={() => del(m.id)}>delete</Button></Td>
            </tr>
          ))}
        </Table>
      )}
    </Card>
  );
}
