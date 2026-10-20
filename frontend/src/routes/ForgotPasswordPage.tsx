import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { AuthShell } from "../components/layout/AuthShell";
import { CheckCircle2 } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (email.includes("@")) setSent(true);
  }

  return (
    <AuthShell>
      {sent ? (
        <div className="text-center py-4">
          <CheckCircle2 className="mx-auto text-white/80 mb-3" size={28} />
          <h1 className="text-xl font-medium text-white">Check your email</h1>
          <p className="text-white/55 text-sm mt-2">We sent password reset instructions to {email}.</p>
          <Link to="/login" className="inline-block mt-6 text-sm text-white hover:underline">Back to login</Link>
        </div>
      ) : (
        <>
          <h1 className="text-2xl font-medium text-white text-center tracking-tight">Reset your password</h1>
          <p className="text-white/55 text-sm text-center mt-2 mb-7">
            Enter your email and we'll send you reset instructions.
          </p>
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-white/60 mb-1.5">Email</label>
              <input
                type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                className="w-full liquid-glass rounded-xl px-4 py-2.5 text-sm text-white outline-none placeholder:text-white/35"
                placeholder="you@company.com"
              />
            </div>
            <button type="submit" className="w-full liquid-glass-strong rounded-full py-2.5 text-sm font-medium text-white">
              Send Reset Link
            </button>
          </form>
          <p className="text-center text-xs text-white/50 mt-6">
            <Link to="/login" className="text-white hover:underline">Back to login</Link>
          </p>
        </>
      )}
    </AuthShell>
  );
}
