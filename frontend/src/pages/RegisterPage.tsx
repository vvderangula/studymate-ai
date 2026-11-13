import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { register } from "../api/auth";
import { useAuth } from "../context/AuthContext";
import { IconAlert } from "../components/icons";
import AuthShell from "../components/AuthShell";

/** Register page. */
export default function RegisterPage() {
  const navigate = useNavigate();
  const { signIn } = useAuth();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function validate(): string | null {
    if (!fullName.trim()) return "Full name is required.";
    if (!email.trim()) return "Email is required.";
    if (!email.includes("@")) return "Enter a valid email address.";
    if (password.length < 8) return "Password must be at least 8 characters.";
    if (password !== confirmPassword) return "Passwords do not match.";
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setBusy(true);
    try {
      const user = await register({ full_name: fullName.trim(), email: email.trim(), password });
      signIn(user);
      navigate("/", { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || "Registration failed. Please try again.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell>
      <h1 className="text-title text-ink">Create your account</h1>
      <p className="mt-1 text-sm text-muted">Study from your own PDFs and videos.</p>

      {error && (
        <div role="alert" className="notice-error mt-6">
          <IconAlert className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={(e) => void handleSubmit(e)} noValidate className="mt-6 space-y-4">
        <div>
          <label htmlFor="fullName" className="field-label">
            Full Name
          </label>
          <input
            id="fullName"
            type="text"
            autoComplete="name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            disabled={busy}
            placeholder="Jane Smith"
            className="field"
          />
        </div>
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
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={busy}
            placeholder="Min. 8 characters"
            className="field"
          />
        </div>
        <div>
          <label htmlFor="confirmPassword" className="field-label">
            Confirm Password
          </label>
          <input
            id="confirmPassword"
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            disabled={busy}
            placeholder="Repeat your password"
            className="field"
          />
        </div>

        <button type="submit" disabled={busy} className="btn-primary !mt-6 w-full">
          {busy && <span className="spinner" aria-hidden="true" />}
          {busy ? "Creating account…" : "Create Account"}
        </button>
      </form>

      <p className="mt-6 border-t border-line pt-5 text-center text-sm text-muted">
        Already have an account?{" "}
        <Link
          to="/login"
          className="rounded font-medium text-accent underline-offset-4 hover:text-accent-hover hover:underline"
        >
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
