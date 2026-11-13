import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { logout } from "../api/auth";
import { BrandMark, IconBook, IconHome, IconLogout, IconShield } from "./icons";

const NAV_LINKS = [
  { to: "/", label: "Dashboard", end: true, Icon: IconHome },
  { to: "/learn", label: "Learn", end: false, Icon: IconBook },
];
const ADMIN_LINK = { to: "/admin", label: "Admin", end: false, Icon: IconShield };

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "";
  const first = parts[0][0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] ?? "" : "";
  return (first + last).toUpperCase();
}

/**
 * Shared application shell.
 * The shell is exactly one viewport tall and never scrolls itself.
 * Phones/tablets: a top bar (brand + logout, nav tabs underneath on phones).
 * Desktop (lg+): a fixed left sidebar with the user block pinned to the bottom.
 */
export default function Layout() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    signOut();
    navigate("/login", { replace: true });
  }

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-canvas text-ink lg:flex-row">
      <header className="z-30 shrink-0 border-b border-line bg-gradient-to-b from-white to-[#FFFAF6] lg:h-full lg:w-60 lg:border-b-0 lg:border-r">
        <div className="flex flex-wrap items-center gap-x-6 px-4 sm:flex-nowrap sm:px-6 lg:h-full lg:flex-col lg:items-stretch lg:px-3 lg:py-5">
          <Link
            to="/"
            className="flex items-center gap-2.5 rounded-control py-3 text-[15px] font-semibold tracking-[-0.01em] text-ink sm:py-3.5 lg:px-2 lg:py-1"
          >
            <BrandMark className="h-8 w-8" />
            StudyMate AI
          </Link>

          <nav
            aria-label="Main"
            className="order-last -mx-1 flex w-full gap-1 pb-2.5 sm:order-none sm:mx-0 sm:w-auto sm:pb-0 lg:mt-8 lg:flex-col lg:gap-0.5"
          >
            {(user?.role === "admin" ? [...NAV_LINKS, ADMIN_LINK] : NAV_LINKS).map(({ to, label, end, Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  "group relative flex flex-1 items-center justify-center gap-2.5 rounded-control px-3 py-2 text-sm font-medium transition-colors sm:flex-none lg:justify-start " +
                  (isActive
                    ? "bg-gradient-to-r from-accent-soft to-accent-tint/70 text-accent-ink ring-1 ring-inset ring-accent-line/70"
                    : "text-ink-soft hover:bg-sunken hover:text-ink")
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon
                      className={
                        "h-[18px] w-[18px] " +
                        (isActive ? "text-accent-strong" : "text-faint group-hover:text-muted")
                      }
                    />
                    {label}
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-3 lg:ml-0 lg:mt-auto lg:flex-col lg:items-stretch lg:gap-2 lg:border-t lg:border-line lg:pt-4">
            {user && (
              <div className="hidden min-w-0 items-center gap-2.5 sm:flex lg:px-2 lg:py-1">
                <span
                  aria-hidden="true"
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-accent-soft to-accent-tint text-xs font-semibold text-accent-ink ring-1 ring-inset ring-accent-line"
                >
                  {initials(user.full_name)}
                </span>
                <span className="min-w-0 truncate text-sm font-medium text-ink-soft">
                  {user.full_name}
                </span>
              </div>
            )}
            <button
              type="button"
              onClick={handleLogout}
              className="btn btn-sm border border-line-strong bg-surface text-ink-soft hover:bg-sunken hover:text-ink lg:h-9 lg:justify-start lg:border-transparent lg:bg-transparent lg:px-2.5 lg:text-muted"
            >
              <IconLogout className="hidden h-[18px] w-[18px] lg:block" />
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Each page renders a frozen PageHeader + its own scrolling PageBody. */}
      <main className="flex min-h-0 min-w-0 flex-1 flex-col">
        <Outlet />
      </main>
    </div>
  );
}
