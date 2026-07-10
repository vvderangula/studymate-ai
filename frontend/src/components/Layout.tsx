import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { logout } from "../api/auth";

const NAV_LINKS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/learn", label: "Learn", end: false },
] as const;

/** Shared application shell: header navigation and a content outlet. */
export default function Layout() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    signOut();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-y-2 px-4 py-3 sm:flex-nowrap sm:px-6 sm:py-4">
          <Link to="/" className="text-xl font-bold text-orange-500">
            StudyMate AI
          </Link>

          <nav className="order-last flex w-full items-center justify-center gap-1 sm:order-none sm:w-auto sm:justify-start">
            {NAV_LINKS.map(({ to, label, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors " +
                  (isActive
                    ? "bg-orange-50 text-orange-600"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-800")
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            {user && (
              <span className="hidden text-sm text-slate-500 sm:inline">
                {user.full_name}
              </span>
            )}
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:bg-slate-100"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-10">
        <Outlet />
      </main>
    </div>
  );
}
