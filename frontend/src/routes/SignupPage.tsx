import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { AuthShell } from "../components/layout/AuthShell";
import { useAuth } from "../hooks/useAuth";

export default function SignupPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { signup } = useAuth();
  const navigate = useNavigate();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!name || !email.includes("@") || !company) { setError("Please complete all required fields."); return; }
    if (password.length < 8) { setError("Password must be at least 8 characters."); return; }
    if (password !== confirm) { setError("Passwords do not match."); return; }
    if (!agreed) { setError("Please accept the terms to continue."); return; }
    setLoading(true);
    try {
      await signup(name, email);
      navigate("/onboarding");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell>
      <h1 className="text-2xl font-medium text-white text-center tracking-tight">Create your workspace</h1>
      <p className="text-white/55 text-sm text-center mt-2 mb-7">
        Start turning marketing data into evidence-backed decisions.
      </p>

      <form onSubmit={onSubmit} className="space-y-3.5" noValidate>
        <Field label="Full name" value={name} onChange={setName} placeholder="Avery Chen" />
        <Field label="Work email" type="email" value={email} onChange={setEmail} placeholder="you@company.com" />
        <Field label="Company / workspace name" value={company} onChange={setCompany} placeholder="Northfield Growth Team" />
        <Field label="Password" type="password" value={password} onChange={setPassword} placeholder="At least 8 characters" />
        <Field label="Confirm password" type="password" value={confirm} onChange={setConfirm} placeholder="Re-enter password" />

        <label className="flex items-start gap-2 text-xs text-white/55 pt-1">
          <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} className="accent-white/80 mt-0.5" />
          I agree to the Terms of Service and Privacy Policy.
        </label>

        {error && <p role="alert" className="text-xs text-white/80 liquid-glass rounded-xl px-3 py-2">{error}</p>}

        <button
          type="submit" disabled={loading}
          className="w-full liquid-glass-strong rounded-full py-2.5 text-sm font-medium text-white flex items-center justify-center gap-2 transition-transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-60"
        >
          {loading && <Loader2 size={14} className="animate-spin" />}
          {loading ? "Creating account…" : "Create Account"}
        </button>
      </form>

      <p className="text-center text-xs text-white/50 mt-6">
        Already have an account?{" "}
        <Link to="/login" className="text-white hover:underline">Log in</Link>
      </p>
    </AuthShell>
  );
}

function Field({
  label, value, onChange, placeholder, type = "text",
}: { label: string; value: string; onChange: (v: string) => void; placeholder: string; type?: string }) {
  return (
    <div>
      <label className="block text-xs text-white/60 mb-1.5">{label}</label>
      <input
        type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder}
        className="w-full liquid-glass rounded-xl px-4 py-2.5 text-sm text-white outline-none placeholder:text-white/35 focus:ring-1 focus:ring-white/30"
      />
    </div>
  );
}
