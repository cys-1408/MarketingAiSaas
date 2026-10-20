import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { AuthShell } from "../components/layout/AuthShell";
import { useAuth } from "../hooks/useAuth";

export default function LoginPage() {
  const [email, setEmail] = useState("avery@northfield.io");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!email.includes("@")) { setError("Enter a valid email address."); return; }
    if (password.length < 4) { setError("Enter your password."); return; }
    setLoading(true);
    try {
      await login(email, password);
      navigate("/app/overview");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthShell>
      <h1 className="text-2xl font-medium text-white text-center tracking-tight">Welcome back</h1>
      <p className="text-white/55 text-sm text-center mt-2 mb-7">
        Sign in to continue to your marketing workspace.
      </p>

      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <div>
          <label htmlFor="email" className="block text-xs text-white/60 mb-1.5">Email</label>
          <input
            id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
            className="w-full liquid-glass rounded-xl px-4 py-2.5 text-sm text-white outline-none placeholder:text-white/35 focus:ring-1 focus:ring-white/30"
            placeholder="you@company.com" autoComplete="email"
          />
        </div>
        <div>
          <label htmlFor="password" className="block text-xs text-white/60 mb-1.5">Password</label>
          <div className="relative">
            <input
              id="password" type={show ? "text" : "password"} value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full liquid-glass rounded-xl px-4 py-2.5 pr-10 text-sm text-white outline-none placeholder:text-white/35 focus:ring-1 focus:ring-white/30"
              placeholder="••••••••" autoComplete="current-password"
            />
            <button
              type="button" onClick={() => setShow((s) => !s)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/80"
              aria-label={show ? "Hide password" : "Show password"}
            >
              {show ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>
        </div>

        <div className="flex items-center justify-between text-xs">
          <label className="flex items-center gap-2 text-white/60">
            <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} className="accent-white/80" />
            Remember me
          </label>
          <Link to="/forgot-password" className="text-white/60 hover:text-white">Forgot password?</Link>
        </div>

        {error && <p role="alert" className="text-xs text-white/80 liquid-glass rounded-xl px-3 py-2">{error}</p>}

        <button
          type="submit" disabled={loading}
          className="w-full liquid-glass-strong rounded-full py-2.5 text-sm font-medium text-white flex items-center justify-center gap-2 transition-transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-60"
        >
          {loading && <Loader2 size={14} className="animate-spin" />}
          {loading ? "Signing in…" : "Log In"}
        </button>
      </form>

      <p className="text-center text-xs text-white/50 mt-6">
        Don't have a workspace?{" "}
        <Link to="/signup" className="text-white hover:underline">Sign up</Link>
      </p>
      <p className="text-center text-[10px] text-white/30 mt-3">
        Development mode: any email/password combination signs you into a demo workspace.
      </p>
    </AuthShell>
  );
}
