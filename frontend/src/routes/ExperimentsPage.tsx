import { useState } from "react";
import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, GlassButton, StatusBadge } from "../components/glass/Glass";
import { experiments } from "../services/mock/fixtures";
import { Plus, X } from "lucide-react";

export default function ExperimentsPage() {
  const [creating, setCreating] = useState(false);
  return (
    <DashboardShell
      title="Experiments & A/B Tests"
      actions={<GlassButton strong onClick={() => setCreating(true)}><Plus size={13} /> New brief</GlassButton>}
    >
      <GlassCard>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-white/40 text-xs border-b border-white/10">
                {["Experiment", "Primary metric", "Status", "Duration", ""].map((h) => (
                  <th key={h} className="py-2 pr-4 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {experiments.map((x) => (
                <tr key={x.id} className="border-b border-white/5 hover:bg-white/[0.03]">
                  <td className="py-3 pr-4 text-white/85">{x.name}</td>
                  <td className="py-3 pr-4 text-white/60 text-xs">{x.primaryMetric}</td>
                  <td className="py-3 pr-4"><StatusBadge status={x.status} /></td>
                  <td className="py-3 pr-4 text-white/45 text-xs">{x.duration}</td>
                  <td className="py-3 pr-4"><button className="text-xs text-white/60 hover:text-white">View</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>

      {experiments.map((x) => (
        <GlassCard key={x.id + "-detail"}>
          <p className="text-sm font-medium text-white/90 mb-2">{x.name}</p>
          <p className="text-xs text-white/60 mb-3">{x.hypothesis}</p>
          <div className="grid md:grid-cols-2 gap-3 text-xs">
            <div><span className="text-white/45">Control: </span><span className="text-white/75">{x.control}</span></div>
            <div><span className="text-white/45">Variant: </span><span className="text-white/75">{x.variant}</span></div>
            <div><span className="text-white/45">Guardrails: </span><span className="text-white/75">{x.guardrailMetrics.join(", ")}</span></div>
            <div><span className="text-white/45">Status: </span><StatusBadge status={x.status} /></div>
          </div>
          {x.status !== "completed" && x.status !== "running" && (
            <p className="text-[11px] text-white/35 mt-3">Launching or modifying this experiment requires explicit review approval.</p>
          )}
        </GlassCard>
      ))}

      {creating && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setCreating(false)}>
          <div className="liquid-glass-strong rounded-2xl p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <p className="text-sm font-medium text-white">New experiment brief</p>
              <button onClick={() => setCreating(false)} className="text-white/50 hover:text-white"><X size={16} /></button>
            </div>
            <div className="space-y-3">
              {["Hypothesis", "Primary metric", "Proposed duration"].map((f) => (
                <input key={f} placeholder={f} className="w-full liquid-glass rounded-xl px-3 py-2 text-sm text-white outline-none placeholder:text-white/35" />
              ))}
            </div>
            <GlassButton strong className="w-full mt-4" onClick={() => setCreating(false)}>Save as draft</GlassButton>
          </div>
        </div>
      )}
    </DashboardShell>
  );
}
