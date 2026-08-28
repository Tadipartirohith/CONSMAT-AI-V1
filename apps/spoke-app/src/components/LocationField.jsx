import { useEffect } from "react";
import { site } from "../api.js";
import { getUser } from "../auth.js";
import { Input, Select, useAsync } from "./ui.jsx";

// A location input that defaults to the spoke's assigned region; if the spoke covers more than one
// region it becomes a dropdown of those regions.
export default function LocationField({ value, onChange, placeholder = "e.g. Medchal" }) {
  const me = getUser();
  const detail = useAsync(() => (me?.org_ref ? site.spoke(me.org_ref) : Promise.resolve(null)), [me?.org_ref]);
  const regions = detail.data?.areas || [];

  useEffect(() => {
    if (!value && regions.length === 1) onChange(regions[0]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [regions.length]);

  if (regions.length > 1) {
    return (
      <Select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">select area…</option>
        {regions.map((r) => <option key={r} value={r}>{r}</option>)}
      </Select>
    );
  }
  return <Input value={value} placeholder={regions[0] || placeholder} onChange={(e) => onChange(e.target.value)} />;
}
