import { Link } from "react-router-dom";
import { Sparkles, ArrowRight } from "lucide-react";

export default function FeatureEvidenceGraphPage() {
  return (
    <div className="min-h-screen bg-ink-950 text-white px-6 py-10">
      <div className="max-w-3xl mx-auto">
        <Link to="/" className="flex items-center gap-2 mb-16 w-fit">
          <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center"><Sparkles size={15} /></div>
          <span className="font-semibold text-sm">Marketing Copilot</span>
        </Link>
        <h1 className="text-5xl font-medium tracking-tight mb-4">
          Campaign <span className="editorial-italic text-white/80">Evidence Graph.</span>
        </h1>
        <p className="text-white/60 leading-relaxed mb-6">
          Every recommendation Marketing Copilot makes is traceable: back through the metric that triggered it, the customer
          feedback that supports it, and the source document it came from. The Evidence Graph makes those relationships visible,
          distinguishing observed facts from inferred hypotheses so decisions never outrun the evidence behind them.
        </p>
        <Link to="/signup" className="liquid-glass-strong inline-flex px-5 py-2.5 rounded-full text-sm font-medium items-center gap-2">
          Explore your workspace <ArrowRight size={14} />
        </Link>
      </div>
    </div>
  );
}
