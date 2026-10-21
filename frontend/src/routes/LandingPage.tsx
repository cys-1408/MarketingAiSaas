import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Sparkles, WandSparkles, Network, Plus, Globe, MessageCircle } from "lucide-react";
import { motion } from "framer-motion";
import { BRAND_NAME } from "../brand";

const VIDEO_SRC =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260315_073750_51473149-4350-4920-ae24-c8214286f323.mp4";

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-black">
      <video
        className="fixed inset-0 w-full h-full object-cover z-0"
        src={VIDEO_SRC}
        autoPlay
        muted
        loop
        playsInline
        aria-hidden="true"
      />
      <div className="fixed inset-0 z-[1] bg-black/45" />

      <div className="relative z-10 min-h-screen flex flex-col lg:flex-row">
        {/* LEFT PANEL */}
        <div className="w-full lg:w-[52%] p-4 lg:p-6">
          <div className="liquid-glass-strong rounded-3xl h-full min-h-[calc(100vh-2rem)] lg:min-h-[calc(100vh-3rem)] flex flex-col px-6 py-6 lg:px-10 lg:py-8">
            {/* Nav */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
                  <Sparkles size={15} className="text-white" />
                </div>
                <span className="font-semibold tracking-tight text-white text-[15px]">{BRAND_NAME}</span>
              </div>
              <div className="flex items-center gap-2">
                <Link to="/product" className="liquid-glass hidden sm:inline-flex px-4 py-2 rounded-full text-xs font-medium text-white/80">
                  Product
                </Link>
                <Link to="/login" className="liquid-glass px-4 py-2 rounded-full text-xs font-medium text-white/80">
                  Login
                </Link>
                <Link to="/signup" className="liquid-glass-strong px-4 py-2 rounded-full text-xs font-medium text-white">
                  Sign Up
                </Link>
              </div>
            </div>

            {/* Hero */}
            <div className="flex-1 flex flex-col items-center justify-center text-center py-10">
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.8 }}
                className="w-16 h-16 lg:w-20 lg:h-20 rounded-full liquid-glass-strong flex items-center justify-center mb-8"
              >
                <Sparkles size={28} className="text-white" />
              </motion.div>

              <motion.h1
                initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.1 }}
                className="text-6xl lg:text-7xl font-medium tracking-[-0.05em] leading-[0.98] text-white max-w-xl"
              >
                Marketing <span className="editorial-italic text-white/80">Intelligence,</span>
                <br />
                Reimagined <span className="editorial-italic text-white/80">with AI.</span>
              </motion.h1>

              <motion.p
                initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.25 }}
                className="mt-6 max-w-[480px] text-white/70 text-[15px] leading-relaxed"
              >
                Turn fragmented marketing data into clear answers, evidence-backed decisions, and campaigns worth testing.
              </motion.p>

              <motion.div
                initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.7, delay: 0.4 }}
                className="mt-9 flex flex-wrap items-center justify-center gap-3"
              >
                <button
                  onClick={() => navigate("/signup")}
                  className="liquid-glass-strong pl-5 pr-2 py-2 rounded-full text-sm font-medium text-white flex items-center gap-3 transition-transform hover:scale-[1.05] active:scale-[0.95]"
                >
                  Explore Workspace
                  <span className="w-7 h-7 rounded-full bg-white/15 flex items-center justify-center">
                    <ArrowRight size={13} />
                  </span>
                </button>
                <a
                  href="#how-it-works"
                  className="liquid-glass px-5 py-2.5 rounded-full text-sm font-medium text-white/80 flex items-center gap-2 transition-transform hover:scale-[1.05] active:scale-[0.95]"
                >
                  See How It Works <ArrowRight size={13} />
                </a>
              </motion.div>

              <motion.div
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.7, delay: 0.6 }}
                className="mt-10 flex flex-wrap justify-center gap-2.5"
              >
                {["Campaign Intelligence", "AI Investigations", "Evidence Graph"].map((p) => (
                  <span key={p} className="liquid-glass px-4 py-1.5 rounded-full text-xs font-medium text-white/80 hover:bg-white/5 transition-colors">
                    {p}
                  </span>
                ))}
              </motion.div>
            </div>

            {/* Editorial quote */}
            <div id="how-it-works" className="text-center pt-6">
              <p className="text-[10px] tracking-[0.2em] text-white/50 uppercase mb-3">Marketing, with evidence</p>
              <p className="editorial-italic text-xl text-white/85 mb-3">
                “Better decisions begin with <span>better evidence</span>.”
              </p>
              <div className="flex items-center justify-center gap-3 text-[10px] tracking-[0.15em] text-white/50 uppercase">
                <span className="h-px w-8 bg-white/25" />
                {BRAND_NAME}
                <span className="h-px w-8 bg-white/25" />
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div className="hidden lg:flex w-[48%] p-6 pl-0 flex-col gap-4">
          <div className="liquid-glass rounded-full px-3 py-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Link to="/product" className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-white/70 hover:text-white">
                <Globe size={14} />
              </Link>
              <Link to="/features/ai-investigations" className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-white/70 hover:text-white">
                <MessageCircle size={14} />
              </Link>
            </div>
            <Link to="/signup" className="liquid-glass-strong px-4 py-1.5 rounded-full text-xs font-medium text-white flex items-center gap-1.5">
              Get Started <ArrowRight size={12} />
            </Link>
          </div>

          <div className="liquid-glass rounded-3xl p-5 w-56 self-end">
            <p className="text-sm font-medium text-white mb-1.5">Your Marketing Intelligence Hub</p>
            <p className="text-xs text-white/60 leading-relaxed">
              One workspace for campaign data, customer evidence, and AI-assisted decisions.
            </p>
          </div>

          <div className="liquid-glass rounded-[2.5rem] p-5 flex-1 flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="liquid-glass rounded-3xl p-4">
                <div className="w-9 h-9 rounded-full bg-white/10 flex items-center justify-center mb-3">
                  <WandSparkles size={16} className="text-white/85" />
                </div>
                <p className="text-sm font-medium text-white mb-1">AI Investigations</p>
                <p className="text-xs text-white/55 leading-relaxed">
                  Trace performance patterns across your marketing data.
                </p>
              </div>
              <div className="liquid-glass rounded-3xl p-4">
                <div className="w-9 h-9 rounded-full bg-white/10 flex items-center justify-center mb-3">
                  <Network size={16} className="text-white/85" />
                </div>
                <p className="text-sm font-medium text-white mb-1">Evidence Graph</p>
                <p className="text-xs text-white/55 leading-relaxed">
                  Explore how metrics, feedback, and recommendations connect.
                </p>
              </div>
            </div>

            <div className="liquid-glass rounded-3xl p-5 flex-1 flex flex-col justify-between relative overflow-hidden">
              <svg viewBox="0 0 320 120" className="absolute inset-0 w-full h-full opacity-[0.35]" preserveAspectRatio="none">
                <g stroke="white" strokeWidth="1" fill="none">
                  <line x1="40" y1="30" x2="140" y2="60" />
                  <line x1="140" y1="60" x2="240" y2="25" />
                  <line x1="140" y1="60" x2="220" y2="100" />
                  <line x1="40" y1="30" x2="60" y2="95" />
                </g>
                <g fill="white">
                  <circle cx="40" cy="30" r="4" />
                  <circle cx="140" cy="60" r="5" />
                  <circle cx="240" cy="25" r="3.5" />
                  <circle cx="220" cy="100" r="3.5" />
                  <circle cx="60" cy="95" r="3" />
                </g>
              </svg>
              <div className="relative z-10">
                <p className="text-sm font-medium text-white mb-1">Campaign Evidence Graph</p>
                <p className="text-xs text-white/60 leading-relaxed max-w-[75%]">
                  Every recommendation connects to its supporting sources, metrics, and experiments.
                </p>
              </div>
              <button
                onClick={() => navigate("/features/evidence-graph")}
                className="relative z-10 self-end w-10 h-10 rounded-full liquid-glass-strong flex items-center justify-center text-white hover:scale-105 active:scale-95 transition-transform"
                aria-label="Explore evidence graph"
              >
                <Plus size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
