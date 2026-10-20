import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Upload, Plug, ArrowRight, Loader2 } from "lucide-react";
import { AuthShell } from "../components/layout/AuthShell";

const steps = ["Workspace", "Role", "Connect Data", "Review", "Ready"];

export default function OnboardingPage() {
  const [step, setStep] = useState(0);
  const [role, setRole] = useState("Marketing Manager");
  const [workspaceName, setWorkspaceName] = useState("Northfield Growth Team");
  const [ingesting, setIngesting] = useState(false);
  const [progress, setProgress] = useState(0);
  const navigate = useNavigate();

  function next() {
    if (step === 2) {
      setIngesting(true);
      let p = 0;
      const t = setInterval(() => {
        p += 20;
        setProgress(p);
        if (p >= 100) { clearInterval(t); setIngesting(false); setStep(3); }
      }, 350);
      return;
    }
    setStep((s) => Math.min(s + 1, steps.length - 1));
  }

  return (
    <AuthShell>
      <div className="flex items-center justify-between mb-6">
        {steps.map((s, i) => (
          <div key={s} className="flex-1 flex items-center">
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] shrink-0 ${
                i <= step ? "bg-white text-black" : "liquid-glass text-white/50"
              }`}
            >
              {i < step ? <Check size={11} /> : i + 1}
            </div>
            {i < steps.length - 1 && <div className={`h-px flex-1 mx-1 ${i < step ? "bg-white/60" : "bg-white/15"}`} />}
          </div>
        ))}
      </div>

      {step === 0 && (
        <div>
          <h2 className="text-lg font-medium text-white mb-1">Confirm your workspace</h2>
          <p className="text-white/55 text-sm mb-5">This is where your team's campaigns, data, and evidence will live.</p>
          <input
            value={workspaceName} onChange={(e) => setWorkspaceName(e.target.value)}
            className="w-full liquid-glass rounded-xl px-4 py-2.5 text-sm text-white outline-none mb-6"
          />
          <button onClick={next} className="w-full liquid-glass-strong rounded-full py-2.5 text-sm font-medium text-white flex items-center justify-center gap-2">
            Continue <ArrowRight size={14} />
          </button>
        </div>
      )}

      {step === 1 && (
        <div>
          <h2 className="text-lg font-medium text-white mb-1">What's your role?</h2>
          <p className="text-white/55 text-sm mb-5">This helps tailor dashboards and recommendations.</p>
          <div className="grid grid-cols-2 gap-2 mb-6">
            {["Marketing Manager", "Growth Marketer", "Analyst", "CRM Specialist", "Product Marketer"].map((r) => (
              <button
                key={r} onClick={() => setRole(r)}
                className={`liquid-glass rounded-xl px-3 py-2.5 text-xs text-left ${role === r ? "bg-white/15 text-white" : "text-white/60"}`}
              >
                {r}
              </button>
            ))}
          </div>
          <button onClick={next} className="w-full liquid-glass-strong rounded-full py-2.5 text-sm font-medium text-white flex items-center justify-center gap-2">
            Continue <ArrowRight size={14} />
          </button>
        </div>
      )}

      {step === 2 && !ingesting && (
        <div>
          <h2 className="text-lg font-medium text-white mb-1">Connect your data</h2>
          <p className="text-white/55 text-sm mb-5">Upload files or connect a marketing platform. You can skip and do this later.</p>
          <div className="space-y-2.5 mb-6">
            <button className="w-full liquid-glass rounded-xl px-4 py-3 text-sm text-white/85 flex items-center gap-3">
              <Upload size={16} /> Upload files from your computer
            </button>
            <button className="w-full liquid-glass rounded-xl px-4 py-3 text-sm text-white/85 flex items-center gap-3">
              <Plug size={16} /> Connect a marketing platform
            </button>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setStep(3)} className="flex-1 liquid-glass rounded-full py-2.5 text-sm font-medium text-white/70">
              Skip for now
            </button>
            <button onClick={next} className="flex-1 liquid-glass-strong rounded-full py-2.5 text-sm font-medium text-white">
              Continue
            </button>
          </div>
        </div>
      )}

      {ingesting && (
        <div className="text-center py-6">
          <Loader2 className="mx-auto animate-spin text-white/80 mb-4" size={24} />
          <h2 className="text-lg font-medium text-white mb-1">Indexing your data…</h2>
          <p className="text-white/55 text-sm mb-5">Inspecting, mapping, and preparing your workspace.</p>
          <div className="liquid-glass h-2 rounded-full overflow-hidden">
            <div className="h-full bg-white/70 transition-all duration-300" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {step === 3 && (
        <div>
          <h2 className="text-lg font-medium text-white mb-1">Review field mappings</h2>
          <p className="text-white/55 text-sm mb-5">Most fields mapped automatically. 2 need a quick confirmation.</p>
          <div className="space-y-2 mb-6">
            {["lead_src → acquisition_channel", "ctr_pct → click_through_rate"].map((m) => (
              <div key={m} className="liquid-glass rounded-xl px-3 py-2.5 text-xs text-white/75 flex justify-between items-center">
                {m}
                <span className="text-white/40">Needs review</span>
              </div>
            ))}
          </div>
          <button onClick={() => setStep(4)} className="w-full liquid-glass-strong rounded-full py-2.5 text-sm font-medium text-white">
            I'll review these in the app
          </button>
        </div>
      )}

      {step === 4 && (
        <div className="text-center py-4">
          <div className="w-12 h-12 rounded-full liquid-glass-strong flex items-center justify-center mx-auto mb-4">
            <Check size={20} className="text-white" />
          </div>
          <h2 className="text-lg font-medium text-white mb-1">Your workspace is ready</h2>
          <p className="text-white/55 text-sm mb-6">{workspaceName} is set up for {role.toLowerCase()} workflows.</p>
          <button onClick={() => navigate("/app/overview")} className="w-full liquid-glass-strong rounded-full py-2.5 text-sm font-medium text-white flex items-center justify-center gap-2">
            Go to Dashboard <ArrowRight size={14} />
          </button>
        </div>
      )}
    </AuthShell>
  );
}
