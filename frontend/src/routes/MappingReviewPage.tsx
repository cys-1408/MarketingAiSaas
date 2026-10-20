import { useState } from "react";
import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, GlassButton } from "../components/glass/Glass";
import { mappingCandidates } from "../services/mock/fixtures";
import { ArrowRight, Check, SkipForward } from "lucide-react";

export default function MappingReviewPage() {
  const [resolved, setResolved] = useState<Set<string>>(new Set());
  const [index, setIndex] = useState(0);
  const items = mappingCandidates;
  const current = items[index];

  function resolve(id: string) {
    setResolved((prev) => new Set(prev).add(id));
    if (index < items.length - 1) setIndex(index + 1);
  }

  return (
    <DashboardShell title="Data Mapping Review">
      <GlassCard>
        <p className="text-sm text-white/70">
          Unambiguous fields are mapped automatically. These {items.length} fields need a quick confirmation because of real ambiguity.
        </p>
        <p className="text-xs text-white/40 mt-2">{resolved.size} of {items.length} mappings reviewed</p>
        <div className="liquid-glass h-1.5 rounded-full overflow-hidden mt-2">
          <div className="h-full bg-white/70 transition-all" style={{ width: `${(resolved.size / items.length) * 100}%` }} />
        </div>
      </GlassCard>

      {current ? (
        <GlassCard strong>
          <div className="flex justify-between text-xs text-white/40 mb-4">
            <span>{current.sourceFile} · {current.sheet}</span>
            <span className="capitalize">{current.confidence} confidence</span>
          </div>

          <div className="grid md:grid-cols-2 gap-4 mb-5">
            <div className="liquid-glass rounded-2xl p-4">
              <p className="text-xs text-white/45 mb-2">Source column</p>
              <p className="text-white font-medium mb-3">{current.column}</p>
              <p className="text-xs text-white/45 mb-1.5">Sample values</p>
              <div className="flex flex-wrap gap-1.5">
                {current.sampleValues.map((v) => (
                  <span key={v} className="liquid-glass px-2 py-1 rounded-full text-[11px] text-white/70">{v}</span>
                ))}
              </div>
            </div>
            <div className="liquid-glass rounded-2xl p-4 flex flex-col">
              <p className="text-xs text-white/45 mb-2">Proposed canonical field</p>
              <p className="text-white font-medium mb-3 flex items-center gap-2">
                <ArrowRight size={14} className="text-white/40" /> {current.proposedField}
              </p>
              <p className="text-xs text-white/45 mb-1.5">Alternatives</p>
              <div className="flex flex-wrap gap-1.5">
                {current.alternatives.map((a) => (
                  <span key={a} className="liquid-glass px-2 py-1 rounded-full text-[11px] text-white/50">{a}</span>
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-2 mb-5 text-xs">
            <p className="text-white/50"><span className="text-white/70 font-medium">Why review is needed:</span> {current.reason}</p>
            <p className="text-white/50"><span className="text-white/70 font-medium">Potential impact:</span> {current.impact}</p>
          </div>

          <div className="flex flex-wrap gap-2">
            <GlassButton strong onClick={() => resolve(current.id)}>
              <Check size={13} /> Confirm mapping
            </GlassButton>
            <GlassButton onClick={() => resolve(current.id)}>Edit mapping</GlassButton>
            <GlassButton onClick={() => resolve(current.id)}>
              <SkipForward size={13} /> Skip for now
            </GlassButton>
          </div>
        </GlassCard>
      ) : (
        <GlassCard>
          <p className="text-sm text-white/80">All mappings reviewed. Your workspace data is fully mapped.</p>
        </GlassCard>
      )}
    </DashboardShell>
  );
}
