import { Link } from "react-router-dom";
import { Sparkles, ArrowRight, Network, WandSparkles, BarChart3 } from "lucide-react";

const pillars = [
  { icon: Sparkles, title: "AI Investigations", text: "Ask open-ended questions about campaign performance and get evidence-backed answers, not guesses." },
  { icon: Network, title: "Evidence Graph", text: "See how metrics, objections, product facts, and recommendations connect — and trace every claim to its source." },
  { icon: WandSparkles, title: "Content Studio", text: "Generate brand-compliant copy with built-in claim validation, ready for review before it ships." },
  { icon: BarChart3, title: "Campaign Analytics", text: "Unified reporting across channels with clear metric definitions and provenance." },
];

export default function ProductPage() {
  return (
    <div className="min-h-screen bg-ink-950 text-white px-6 py-10">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-16">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center"><Sparkles size={15} /></div>
            <span className="font-semibold text-sm">Marketing Copilot</span>
          </Link>
          <Link to="/signup" className="liquid-glass-strong px-4 py-2 rounded-full text-xs font-medium flex items-center gap-1.5">
            Get Started <ArrowRight size={12} />
          </Link>
        </div>
        <h1 className="text-5xl font-medium tracking-tight mb-4">
          The product, <span className="editorial-italic text-white/80">in detail.</span>
        </h1>
        <p className="text-white/60 max-w-xl mb-14">
          Marketing Copilot connects your campaign data, customer evidence, and AI reasoning into a single, traceable workspace.
        </p>
        <div className="grid md:grid-cols-2 gap-4">
          {pillars.map((p) => (
            <div key={p.title} className="liquid-glass rounded-3xl p-6">
              <div className="w-9 h-9 rounded-full bg-white/10 flex items-center justify-center mb-4"><p.icon size={16} /></div>
              <p className="font-medium mb-2">{p.title}</p>
              <p className="text-sm text-white/55 leading-relaxed">{p.text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
