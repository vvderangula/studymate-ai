import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { login } from "../api/auth";
import { useAuth } from "../context/AuthContext";
import { IconAlert } from "../components/icons";
import AuthShell from "../components/AuthShell";

/** Login page. */
export default function LoginPage() {
  const navigate = useNavigate();
  const { signIn } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (!email.trim()) {
      setError("Email is required.");
      return;
    }
    if (!password) {
      setError("Password is required.");
      return;
    }

    setBusy(true);
    try {
      const user = await login({ email: email.trim(), password });
      signIn(user);
      navigate("/", { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || "Invalid email or password.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell>
      <h1 className="text-title text-ink">Welcome back</h1>
      <p className="mt-1 text-sm text-muted">Sign in to pick up where you left off.</p>

      {error && (
        <div role="alert" className="notice-error mt-6">
          <IconAlert className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={(e) => void handleSubmit(e)} noValidate className="mt-6 space-y-4">
        <div>
          <label htmlFor="email" className="field-label">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={busy}
            placeholder="you@example.com"
            className="field"
          />
        </div>

        <div>
          <label htmlFor="password" className="field-label">
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={busy}
            placeholder="••••••••"
            className="field"
          />
        </div>

        <button type="submit" disabled={busy} className="btn-primary !mt-6 w-full">
          {busy && <span className="spinner" aria-hidden="true" />}
          {busy ? "Signing in…" : "Sign In"}
        </button>
      </form>

      <p className="mt-6 border-t border-line pt-5 text-center text-sm text-muted">
        Don&apos;t have an account?{" "}
        <Link
          to="/register"
          className="rounded font-medium text-accent underline-offset-4 hover:text-accent-hover hover:underline"
        >
          Create one
        </Link>
      </p>
    </AuthShell>
  );
}
