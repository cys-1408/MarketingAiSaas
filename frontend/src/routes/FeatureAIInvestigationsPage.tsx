import { Link } from "react-router-dom";
import { Sparkles, ArrowRight } from "lucide-react";
import { BRAND_NAME } from "../brand";

export default function FeatureAIInvestigationsPage() {
  return (
    <div className="min-h-screen bg-ink-950 text-white px-6 py-10">
      <div className="max-w-3xl mx-auto">
        <Link to="/" className="flex items-center gap-2 mb-16 w-fit">
          <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center"><Sparkles size={15} /></div>
          <span className="font-semibold text-sm">{BRAND_NAME}</span>
        </Link>
        <h1 className="text-5xl font-medium tracking-tight mb-4">
          AI <span className="editorial-italic text-white/80">Investigations.</span>
        </h1>
        <p className="text-white/60 leading-relaxed mb-6">
          Ask open-ended questions about why a campaign performed the way it did. {BRAND_NAME} separates observed facts
          from hypotheses, cites the evidence behind every claim, and is explicit about what it doesn't know — so you can act
          with confidence instead of guesswork.
        </p>
        <Link to="/signup" className="liquid-glass-strong inline-flex px-5 py-2.5 rounded-full text-sm font-medium items-center gap-2">
          Start an investigation <ArrowRight size={14} />
        </Link>
      </div>
    </div>
  );
}
