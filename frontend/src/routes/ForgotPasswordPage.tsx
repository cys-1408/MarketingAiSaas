import { Link } from "react-router-dom";
import { AuthShell } from "../components/layout/AuthShell";

/**
 * Password reset is not supported by the current backend (/api/v1 has no
 * reset endpoints). This screen is honest about that instead of faking a
 * "reset email sent" success path.
 */
export default function ForgotPasswordPage() {
  return (
    <AuthShell>
      <h1 className="text-2xl font-medium text-white text-center tracking-tight">Reset your password</h1>
      <p className="text-white/55 text-sm text-center mt-2 mb-7">
        Enter your email and we'd send you reset instructions.
      </p>

      <div role="status" className="liquid-glass rounded-xl px-3 py-2.5 text-xs text-white/75 mb-5">
        Password reset is not available in this build: the service does not yet offer a
        password-reset flow. Contact your workspace owner or administrator for account help.
      </div>

      <fieldset disabled className="space-y-4" aria-disabled="true">
        <div>
          <label className="block text-xs text-white/60 mb-1.5">Email</label>
          <input
            type="email"
            className="w-full liquid-glass rounded-xl px-4 py-2.5 text-sm text-white outline-none placeholder:text-white/35 opacity-50"
            placeholder="you@company.com"
          />
        </div>
        <button type="button" className="w-full liquid-glass-strong rounded-full py-2.5 text-sm font-medium text-white opacity-50" aria-label="Send reset link (disabled — not supported)">
          Send Reset Link
        </button>
      </fieldset>

      <p className="text-center text-xs text-white/50 mt-6">
        <Link to="/login" className="text-white hover:underline">Back to login</Link>
      </p>
    </AuthShell>
  );
}
