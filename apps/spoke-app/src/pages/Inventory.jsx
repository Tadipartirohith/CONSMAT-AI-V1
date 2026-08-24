import { useMemo, useState } from "react";
import { inv } from "../api.js";
import { Card, Table, Td, Badge, Input, Select, useAsync } from "../components/ui.jsx";

// Read-only view of hub stock so the spoke can plan a BOQ against what the hub actually holds.
function tone(s) {
  const rv = Number(s.reserved) || 0, av = Number(s.available) || 0;
  if (rv <= 0) return "green";
  const r = av / rv;
  if (r < 1) return "red";
  if (r < 1.5) return "orange";
  if (r < 3) return "yellow";
  return "green";
}
const TONE = { green: "#22c55e", yellow: "#eab308", orange: "#f59e0b", red: "#ef4444" };

export default function Inventory() {
  const pstock = useAsync(() => inv.productStock());
  const products = useAsync(() => inv.products());
  const materials = useAsync(() => inv.materials());
  const [q, setQ] = useState("");
  const [mat, setMat] = useState("");

  const nameMap = useMemo(() => Object.fromEntries((products.data || []).map((p) => [p.id, p])), [products.data]);
  const rows = (pstock.data || []).map((s) => ({ ...s, p: nameMap[s.product_id] || {} })).filter((s) => {
    if (mat && s.material_id !== mat) return false;
    if (q) {
      const hay = `${s.p.name || ""} ${s.p.brand || ""} ${s.material_id}`.toLowerCase();
      if (!hay.includes(q.toLowerCase())) return false;
    }
    return true;
  });

  return (
    <div className="space-y-5">
      <div>
        <h1 className="font-head text-2xl font-extrabold text-white">Hub inventory</h1>
        <p className="text-xs text-muted">Live hub stock (read-only). Plan BOQs against what the hub holds; low/out items may need a purchase order.</p>
      </div>

      <Card title="Product stock" right={
        <div className="flex items-center gap-2">
          <div className="w-48"><Input value={q} placeholder="search product / brand" onChange={(e) => setQ(e.target.value)} /></div>
          <Select value={mat} onChange={(e) => setMat(e.target.value)}>
            <option value="">all categories</option>
            {(materials.data || []).map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </Select>
        </div>}>
        <Table head={["Product", "Brand", "Category", "On hand", "Reserved", "Available", "Status"]}>
          {rows.map((s) => {
            const t = tone(s);
            return (
              <tr key={s.product_id} className="border-b border-border/50">
                <Td className="text-white/85">{s.p.name || s.product_id}</Td>
                <Td className="text-muted">{s.p.brand || "-"}</Td>
                <Td className="text-muted">{s.material_id}</Td>
                <Td mono>{s.on_hand}</Td>
                <Td mono>{s.reserved}</Td>
                <Td mono>{Math.max(0, s.available)}</Td>
                <Td><span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: TONE[t] }} /></Td>
              </tr>
            );
          })}
          {rows.length === 0 && <tr><Td className="text-muted">No stock rows{q || mat ? " match the filter" : " yet"}.</Td></tr>}
        </Table>
      </Card>
    </div>
  );
}
