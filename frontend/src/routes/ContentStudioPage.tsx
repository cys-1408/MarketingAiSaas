import { useState } from "react";
import { DashboardShell } from "../components/layout/DashboardShell";
import { GlassCard, GlassButton } from "../components/glass/Glass";
import { Copy, RefreshCw, Pencil, AlertTriangle, Check } from "lucide-react";

const contentTypes = ["Email subject line", "Email body", "Landing page copy", "Ad concept", "Headline", "CTA variant"];
const tones = ["Confident", "Friendly", "Direct", "Playful", "Formal"];

interface Variant { id: string; text: string; words: number; flagged: boolean; }

function generate(topic: string, tone: string): Variant[] {
  const base = [
    `${topic} — now with answers, not guesswork.`,
    `See what's actually driving ${topic.toLowerCase()} results.`,
    `${tone} marketing, backed by real evidence.`,
  ];
  return base.map((t, i) => ({ id: `v${i}`, text: t, words: t.split(" ").length, flagged: i === 1 }));
}

export default function ContentStudioPage() {
  const [type, setType] = useState(contentTypes[0]);
  const [tone, setTone] = useState(tones[0]);
  const [keyMessage, setKeyMessage] = useState("Evidence-backed marketing decisions");
  const [variants, setVariants] = useState<Variant[]>([]);
  const [copied, setCopied] = useState<string | null>(null);

  function onGenerate() {
    setVariants(generate(keyMessage, tone));
  }

  function copy(v: Variant) {
    navigator.clipboard?.writeText(v.text);
    setCopied(v.id);
    setTimeout(() => setCopied(null), 1500);
  }

  return (
    <DashboardShell title="Content Studio">
      <div className="grid lg:grid-cols-[320px_1fr] gap-3 items-start">
        <GlassCard strong className="space-y-4">
          <div>
            <p className="text-xs text-white/50 mb-1.5">Content type</p>
            <select value={type} onChange={(e) => setType(e.target.value)} className="w-full liquid-glass rounded-xl px-3 py-2 text-sm text-white bg-transparent outline-none">
              {contentTypes.map((c) => <option key={c} value={c} className="bg-ink-900">{c}</option>)}
            </select>
          </div>
          <div>
            <p className="text-xs text-white/50 mb-1.5">Tone</p>
            <div className="flex flex-wrap gap-1.5">
              {tones.map((t) => (
                <button key={t} onClick={() => setTone(t)} className={`liquid-glass px-3 py-1 rounded-full text-xs ${tone === t ? "bg-white/15 text-white" : "text-white/55"}`}>
                  {t}
                </button>
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs text-white/50 mb-1.5">Key message</p>
            <textarea value={keyMessage} onChange={(e) => setKeyMessage(e.target.value)} rows={3} className="w-full liquid-glass rounded-xl px-3 py-2 text-sm text-white outline-none resize-none" />
          </div>
          <GlassButton strong className="w-full" onClick={onGenerate}>Generate</GlassButton>
          <p className="text-[10px] text-white/35">Content requires review before publishing. Nothing is sent or published automatically.</p>
        </GlassCard>

        <div className="space-y-3">
          {variants.length === 0 && (
            <GlassCard><p className="text-sm text-white/40 text-center py-10">Generated {type.toLowerCase()} variants will appear here.</p></GlassCard>
          )}
          {variants.map((v) => (
            <GlassCard key={v.id}>
              <p className="text-sm text-white/90 mb-3">{v.text}</p>
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-white/35">{v.words} words</span>
                  {v.flagged ? (
                    <span className="liquid-glass px-2 py-0.5 rounded-full text-[10px] text-white/70 flex items-center gap-1">
                      <AlertTriangle size={10} /> Unsupported claim review
                    </span>
                  ) : (
                    <span className="liquid-glass px-2 py-0.5 rounded-full text-[10px] text-white/50">Brand rules passed</span>
                  )}
                </div>
                <div className="flex gap-1.5">
                  <button onClick={() => copy(v)} className="liquid-glass w-7 h-7 rounded-full flex items-center justify-center text-white/55 hover:text-white" aria-label="Copy">
                    {copied === v.id ? <Check size={12} /> : <Copy size={12} />}
                  </button>
                  <button className="liquid-glass w-7 h-7 rounded-full flex items-center justify-center text-white/55 hover:text-white" aria-label="Edit"><Pencil size={12} /></button>
                  <button onClick={onGenerate} className="liquid-glass w-7 h-7 rounded-full flex items-center justify-center text-white/55 hover:text-white" aria-label="Regenerate"><RefreshCw size={12} /></button>
                </div>
              </div>
            </GlassCard>
          ))}
        </div>
      </div>
    </DashboardShell>
  );
}
