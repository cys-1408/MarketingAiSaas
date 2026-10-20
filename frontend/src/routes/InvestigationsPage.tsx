import { useState } from "react";
import { DashboardShell } from "../components/layout/DashboardShell";
import { evidenceRecords } from "../services/mock/fixtures";
import { Send, Sparkles, X } from "lucide-react";
import type { InvestigationMessage, EvidenceRecord } from "../types";

const suggestions = [
  "Why did this campaign receive clicks but generate few purchases?",
  "Which customer objections appear most frequently?",
  "Compare the performance of these two campaigns.",
  "What evidence supports this recommendation?",
  "What should we test next?",
  "Which data sources are missing for this investigation?",
];

function mockAnswer(prompt: string): InvestigationMessage {
  return {
    id: crypto.randomUUID(), role: "assistant", content: prompt,
    summary: "Clicks are strong, but signup completion lags the campaign-type benchmark, and qualitative and support data both point toward pricing clarity as a contributing factor.",
    observedFacts: [
      "Click-to-signup rate is 1.9%, versus a 3.4% benchmark for this campaign type.",
      "CTR for the campaign is 1.73%, above the 90-day account median of 1.1%.",
    ],
    supportingEvidence: ["e2", "e3"],
    contradictoryEvidence: ["No landing-page scroll-depth data is connected, so on-page engagement before drop-off is unmeasured."],
    hypotheses: ["A clearer pricing summary near the top of the landing page may reduce drop-off at signup."],
    nextSteps: ["Review the 'Add pricing summary' recommendation.", "Consider an A/B test of a simplified pricing module."],
    limitations: ["This explanation is a hypothesis, not a confirmed cause. Scroll-depth and session-replay data would strengthen it."],
  };
}

export default function InvestigationsPage() {
  const [messages, setMessages] = useState<InvestigationMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [evidencePanel, setEvidencePanel] = useState<EvidenceRecord | null>(null);

  function send(text: string) {
    if (!text.trim()) return;
    const userMsg: InvestigationMessage = { id: crypto.randomUUID(), role: "user", content: text };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);
    setTimeout(() => {
      setMessages((m) => [...m, mockAnswer(text)]);
      setLoading(false);
    }, 900);
  }

  return (
    <DashboardShell title="AI Investigations">
      <div className="flex gap-3 h-[calc(100vh-7.5rem)]">
        <div className="hidden lg:flex flex-col liquid-glass rounded-3xl p-4 w-60 shrink-0">
          <p className="text-xs text-white/50 mb-2">Context</p>
          <div className="space-y-1.5 mb-4">
            <span className="liquid-glass block px-3 py-1.5 rounded-full text-xs text-white/70">Autumn Acquisition Push</span>
            <span className="liquid-glass block px-3 py-1.5 rounded-full text-xs text-white/70">Sep 1 – Sep 30</span>
          </div>
          <p className="text-xs text-white/50 mb-2">Suggested prompts</p>
          <div className="space-y-1.5 overflow-y-auto">
            {suggestions.map((s) => (
              <button key={s} onClick={() => send(s)} className="liquid-glass w-full text-left px-3 py-2 rounded-xl text-[11px] text-white/60 hover:text-white">
                {s}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 flex flex-col liquid-glass-strong rounded-3xl p-5 min-w-0">
          <div className="flex-1 overflow-y-auto space-y-4 pr-1">
            {messages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center px-6">
                <Sparkles className="text-white/50 mb-4" size={26} />
                <h2 className="text-xl font-medium text-white mb-2">What would you like to investigate?</h2>
                <p className="text-sm text-white/50 max-w-md">
                  Ask questions about campaign performance, customer feedback, product messaging, or marketing experiments.
                </p>
                <div className="grid sm:grid-cols-2 gap-2 mt-6 max-w-lg">
                  {suggestions.map((s) => (
                    <button key={s} onClick={() => send(s)} className="liquid-glass px-3 py-2.5 rounded-xl text-xs text-white/70 text-left hover:text-white">
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m) =>
              m.role === "user" ? (
                <div key={m.id} className="flex justify-end">
                  <div className="liquid-glass rounded-2xl px-4 py-2.5 max-w-lg text-sm text-white/90">{m.content}</div>
                </div>
              ) : (
                <div key={m.id} className="liquid-glass rounded-2xl p-4 space-y-3 max-w-2xl">
                  <Section title="Summary" text={m.summary} />
                  <Section title="Observed facts" list={m.observedFacts} />
                  {m.supportingEvidence && (
                    <div>
                      <p className="text-xs text-white/50 mb-1.5">Supporting evidence</p>
                      <div className="flex flex-wrap gap-1.5">
                        {m.supportingEvidence.map((id) => {
                          const ev = evidenceRecords.find((e) => e.id === id);
                          if (!ev) return null;
                          return (
                            <button key={id} onClick={() => setEvidencePanel(ev)} className="liquid-glass px-2.5 py-1 rounded-full text-[11px] text-white/70 hover:text-white">
                              {ev.sourceName}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                  <Section title="Contradictory evidence" list={m.contradictoryEvidence} />
                  <Section title="Hypotheses" list={m.hypotheses} badge="Hypothesis" />
                  <Section title="Recommended next steps" list={m.nextSteps} />
                  <Section title="Limitations & missing data" list={m.limitations} />
                </div>
              )
            )}
            {loading && <div className="liquid-glass rounded-2xl p-4 text-xs text-white/50 max-w-xs">Analyzing evidence…</div>}
          </div>

          <div className="mt-4 liquid-glass rounded-2xl p-2 flex items-end gap-2">
            <textarea
              value={input} onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
              placeholder="Ask about campaign performance, objections, or experiments…"
              rows={1}
              className="flex-1 bg-transparent outline-none text-sm text-white/90 placeholder:text-white/35 resize-none px-2 py-1.5"
            />
            <button
              onClick={() => send(input)} disabled={!input.trim() || loading}
              className="liquid-glass-strong w-9 h-9 rounded-full flex items-center justify-center text-white disabled:opacity-40"
              aria-label="Send"
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      </div>

      {evidencePanel && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-black/50" onClick={() => setEvidencePanel(null)}>
          <div className="w-full max-w-sm h-full glass-panel-solid p-6 overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <p className="font-medium text-white text-sm">Evidence detail</p>
              <button onClick={() => setEvidencePanel(null)} className="text-white/50 hover:text-white"><X size={18} /></button>
            </div>
            <div className="space-y-3 text-xs">
              <Row label="Source" value={evidencePanel.sourceName} />
              <Row label="Version" value={`v${evidencePanel.sourceVersion}`} />
              <Row label="Date range" value={evidencePanel.dateRange} />
              <Row label="Evidence type" value={evidencePanel.evidenceType} />
            </div>
            <div className="mt-4 liquid-glass rounded-xl p-3">
              <p className="text-sm text-white/80 leading-relaxed">{evidencePanel.excerpt}</p>
            </div>
          </div>
        </div>
      )}
    </DashboardShell>
  );
}

function Section({ title, text, list, badge }: { title: string; text?: string; list?: string[]; badge?: string }) {
  if (!text && (!list || !list.length)) return null;
  return (
    <div>
      <div className="flex items-center gap-2 mb-1.5">
        <p className="text-xs text-white/50">{title}</p>
        {badge && <GlassPillTiny>{badge}</GlassPillTiny>}
      </div>
      {text && <p className="text-sm text-white/80 leading-relaxed">{text}</p>}
      {list && (
        <ul className="space-y-1">
          {list.map((item) => (
            <li key={item} className="text-sm text-white/75 leading-relaxed flex gap-2">
              <span className="text-white/30">—</span>{item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function GlassPillTiny({ children }: { children: import("react").ReactNode }) {
  return <span className="liquid-glass px-2 py-0.5 rounded-full text-[10px] text-white/60">{children}</span>;
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-white/45">{label}</span>
      <span className="text-white/85">{value}</span>
    </div>
  );
}
