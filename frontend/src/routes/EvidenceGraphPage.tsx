import { useState } from "react";
import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard } from "../components/glass/Glass";
import { graphNodes, graphEdges } from "../services/mock/fixtures";
import { Search, X } from "lucide-react";

const typeShapes: Record<string, string> = {
  campaign: "circle", channel: "square", metric: "diamond", objection: "triangle",
  product: "square", recommendation: "circle", experiment: "diamond", source: "square",
};

export default function EvidenceGraphPage() {
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  const types = Array.from(new Set(graphNodes.map((n) => n.type)));
  const visibleNodes = graphNodes.filter(
    (n) => (!typeFilter || n.type === typeFilter) && n.label.toLowerCase().includes(query.toLowerCase())
  );
  const visibleIds = new Set(visibleNodes.map((n) => n.id));
  const visibleEdges = graphEdges.filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target));
  const selectedNode = graphNodes.find((n) => n.id === selected);
  const connectedEdges = graphEdges.filter((e) => e.source === selected || e.target === selected);

  return (
    <DashboardShell title="Campaign Evidence Graph">
      <GlassCard className="flex flex-wrap items-center gap-2">
        <div className="liquid-glass rounded-full px-3 py-1.5 flex items-center gap-2 flex-1 min-w-[180px]">
          <Search size={13} className="text-white/40" />
          <input
            value={query} onChange={(e) => setQuery(e.target.value)}
            placeholder="Search nodes…"
            className="bg-transparent outline-none text-xs text-white/85 placeholder:text-white/35 w-full"
          />
        </div>
        <button onClick={() => setTypeFilter(null)} className={`liquid-glass px-3 py-1.5 rounded-full text-xs ${!typeFilter ? "bg-white/15 text-white" : "text-white/55"}`}>
          All types
        </button>
        {types.map((t) => (
          <button key={t} onClick={() => setTypeFilter(t)} className={`liquid-glass px-3 py-1.5 rounded-full text-xs capitalize ${typeFilter === t ? "bg-white/15 text-white" : "text-white/55"}`}>
            {t}
          </button>
        ))}
      </GlassCard>

      <GlassCard strong className="relative overflow-hidden" style={{ height: 460 }}>
        {visibleNodes.length === 0 ? (
          <div className="h-full flex items-center justify-center text-white/40 text-sm">No nodes match your search.</div>
        ) : (
          <svg viewBox="0 0 1080 440" className="w-full h-full">
            <g stroke="rgba(255,255,255,0.35)" fill="none">
              {visibleEdges.map((e) => {
                const s = graphNodes.find((n) => n.id === e.source)!;
                const t = graphNodes.find((n) => n.id === e.target)!;
                return (
                  <line
                    key={e.id} x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                    strokeWidth={1.3} strokeDasharray={e.observed ? undefined : "4 3"}
                    opacity={0.6}
                  />
                );
              })}
            </g>
            {visibleNodes.map((n) => (
              <g key={n.id} transform={`translate(${n.x},${n.y})`} onClick={() => setSelected(n.id)} className="cursor-pointer">
                <NodeShape shape={typeShapes[n.type]} active={selected === n.id} />
                <text x={0} y={34} textAnchor="middle" fill="rgba(255,255,255,0.75)" fontSize={11}>
                  {n.label.length > 22 ? n.label.slice(0, 20) + "…" : n.label}
                </text>
              </g>
            ))}
          </svg>
        )}
      </GlassCard>

      <p className="text-[11px] text-white/35">
        Solid lines indicate observed relationships; dashed lines indicate inferred relationships. Shapes distinguish node types independent of color.
      </p>

      {selectedNode && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/50" onClick={() => setSelected(null)}>
          <div className="w-full max-w-sm h-full glass-panel-solid p-6 overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <p className="font-medium text-white text-sm">{selectedNode.label}</p>
              <button onClick={() => setSelected(null)} className="text-white/50 hover:text-white"><X size={18} /></button>
            </div>
            <p className="text-xs text-white/50 mb-4 capitalize">Type: {selectedNode.type}</p>
            <p className="text-xs text-white/50 mb-2">Connected relationships</p>
            <div className="space-y-2">
              {connectedEdges.map((e) => {
                const other = graphNodes.find((n) => n.id === (e.source === selected ? e.target : e.source));
                return (
                  <div key={e.id} className="liquid-glass rounded-xl p-3 text-xs">
                    <p className="text-white/80">{e.relation} → {other?.label}</p>
                    <p className="text-white/40 mt-1">{e.observed ? "Observed relationship" : "Inferred relationship"}</p>
                  </div>
                );
              })}
              {!connectedEdges.length && <p className="text-xs text-white/40">No connected relationships.</p>}
            </div>
          </div>
        </div>
      )}
    </DashboardShell>
  );
}

function NodeShape({ shape, active }: { shape: string; active: boolean }) {
  const fill = active ? "rgba(255,255,255,0.95)" : "rgba(255,255,255,0.75)";
  if (shape === "square") return <rect x={-7} y={-7} width={14} height={14} fill={fill} rx={2} />;
  if (shape === "diamond") return <rect x={-7} y={-7} width={14} height={14} fill={fill} transform="rotate(45)" />;
  if (shape === "triangle") return <polygon points="0,-9 8,7 -8,7" fill={fill} />;
  return <circle r={8} fill={fill} />;
}
