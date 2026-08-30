import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MagnifyingGlass } from "@phosphor-icons/react";

// Command palette (Cmd/Ctrl K): fuzzy-jump to any page. Keyboard-first.
export default function CommandPalette({ open, setOpen, items }) {
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const nav = useNavigate();
  const inputRef = useRef(null);

  const filtered = items.filter((i) => i.label.toLowerCase().includes(q.trim().toLowerCase()));

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setOpen((v) => !v); }
      else if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [setOpen]);

  useEffect(() => { if (open) { setQ(""); setSel(0); setTimeout(() => inputRef.current?.focus(), 0); } }, [open]);
  useEffect(() => { setSel(0); }, [q]);

  if (!open) return null;
  const go = (to) => { setOpen(false); nav(to); };
  const onKeyDown = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setSel((s) => Math.min(s + 1, filtered.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setSel((s) => Math.max(s - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); const it = filtered[sel]; if (it) go(it.to); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/55 px-4 pt-[12vh]" onMouseDown={() => setOpen(false)}>
      <div className="w-full max-w-lg overflow-hidden rounded-2xl bg-panel nm-raised" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2.5 border-b border-border/70 px-4 py-3">
          <MagnifyingGlass size={16} className="text-muted" />
          <input ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={onKeyDown}
            placeholder="Jump to a page..." className="w-full bg-transparent text-sm text-ink outline-none placeholder:text-muted" />
          <span className="rounded border border-border px-1.5 py-px font-mono text-[10px] text-muted">Esc</span>
        </div>
        <div className="max-h-80 overflow-auto p-1.5">
          {filtered.length === 0 ? <p className="px-3 py-6 text-center text-sm text-muted">No matches.</p> :
            filtered.map((it, i) => {
              const Icon = it.icon;
              return (
                <button key={it.to} onMouseEnter={() => setSel(i)} onClick={() => go(it.to)}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors ${i === sel ? "bg-accent/[0.12] text-accent" : "text-ink/80 hover:bg-muted/10"}`}>
                  {Icon && <Icon size={17} weight={i === sel ? "fill" : "regular"} />}{it.label}
                </button>
              );
            })}
        </div>
      </div>
    </div>
  );
}
