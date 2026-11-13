import { useEffect, useState } from "react";

import { getAdminStats, getAdminUsers, type AdminStats, type AdminUser, type DailyCount } from "../api/admin";
import { ApiError } from "../api/client";
import { PageBody, PageHeader } from "../components/workspace";
import { ErrorNotice } from "../components/ui";
import { timeAgo } from "../lib/time";

const TOTAL_LABELS: { key: string; label: string }[] = [
  { key: "users", label: "Users" },
  { key: "pdfs", label: "PDFs" },
  { key: "videos", label: "Videos" },
  { key: "conversations", label: "Conversations" },
  { key: "messages", label: "Messages" },
  { key: "quizzes", label: "Quizzes" },
  { key: "notes", label: "Notes" },
  { key: "searches", label: "Paper searches" },
];

const EVENT_LABELS: Record<string, string> = {
  pdf_uploaded: "PDF uploads",
  pdf_chat: "PDF questions",
  youtube_processed: "Videos processed",
  youtube_chat: "Video questions",
  quiz_generated: "Quizzes generated",
  notes_generated: "Notes generated",
  research_search: "Paper searches",
  research_asked: "Paper questions",
  assistant_chat: "Assistant messages",
};

/** Admin overview: platform totals, 14-day trends, usage mix and all users. */
export default function AdminPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");

  useEffect(() => {
    Promise.all([getAdminStats(), getAdminUsers()])
      .then(([statsResult, usersResult]) => {
        setStats(statsResult);
        setUsers(usersResult);
      })
      .catch((err) =>
        setError(
          err instanceof ApiError && err.status === 403
            ? "This page is for admins only."
            : "Could not load admin data. Please refresh.",
        ),
      );
  }, []);

  const filtered = users.filter((user) => {
    const q = query.trim().toLowerCase();
    return !q || user.full_name.toLowerCase().includes(q) || user.email.toLowerCase().includes(q);
  });

  const events = stats
    ? Object.entries(stats.events).sort((a, b) => b[1] - a[1])
    : [];
  const topEvent = events[0]?.[1] ?? 1;

  return (
    <>
      <PageHeader title="Admin" description="Platform activity and every account, visible to admins only." />
      <PageBody>
        {error ? (
          <ErrorNotice>{error}</ErrorNotice>
        ) : !stats ? (
          <div className="space-y-6" role="status" aria-label="Loading admin data">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="skeleton h-24" />
              ))}
            </div>
            <div className="skeleton h-56" />
          </div>
        ) : (
          <div className="space-y-8">
            <section aria-label="Totals">
              <div className="grid grid-cols-2 gap-px overflow-hidden rounded-card border border-line bg-line shadow-card sm:grid-cols-4">
                {TOTAL_LABELS.map(({ key, label }) => (
                  <div key={key} className="bg-gradient-to-b from-white to-[#FFF9F4] px-4 py-4 sm:px-5">
                    <p className="text-[13px] text-muted">{label}</p>
                    <p className="mt-2 text-[1.75rem] font-semibold leading-none tracking-[-0.03em] tabular-nums text-ink">
                      {(stats.totals[key] ?? 0).toLocaleString()}
                    </p>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-sm text-muted">
                <span className="font-medium text-ink">{stats.active_users_7d}</span> active in the
                last 7 days, <span className="font-medium text-ink">{stats.active_users_30d}</span>{" "}
                in the last 30.
              </p>
            </section>

            <div className="grid gap-6 lg:grid-cols-2">
              <TrendCard title="Sign-ups, last 14 days" days={stats.signups_daily} />
              <TrendCard title="Activity, last 14 days" days={stats.activity_daily} />
            </div>

            <section className="card card-pad">
              <h2 className="section-title">What people use</h2>
              {events.length === 0 ? (
                <p className="empty-box mt-3">No activity yet.</p>
              ) : (
                <ul className="mt-4 space-y-3">
                  {events.map(([type, count]) => (
                    <li key={type} className="grid grid-cols-[10rem_1fr_3rem] items-center gap-3 text-sm sm:grid-cols-[12rem_1fr_4rem]">
                      <span className="truncate text-ink-soft">{EVENT_LABELS[type] ?? type}</span>
                      <span className="h-2 overflow-hidden rounded-full bg-sunken">
                        <span
                          className="block h-full rounded-full bg-gradient-to-r from-accent-light to-accent-strong"
                          style={{ width: `${Math.max(4, (count / topEvent) * 100)}%` }}
                        />
                      </span>
                      <span className="text-right tabular-nums text-muted">{count}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="card overflow-hidden">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-3 sm:px-6">
                <h2 className="section-title">
                  Users <span className="ml-1 text-xs font-normal text-muted">{users.length}</span>
                </h2>
                <input
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search name or email"
                  aria-label="Search users"
                  className="field h-9 w-full sm:w-64"
                />
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[56rem] text-left text-sm">
                  <thead className="bg-canvas text-[13px] text-muted">
                    <tr>
                      <th className="px-5 py-3 font-medium sm:px-6">User</th>
                      <th className="px-3 py-3 font-medium">Joined</th>
                      <th className="px-3 py-3 font-medium">Last active</th>
                      <th className="px-3 py-3 text-right font-medium">PDFs</th>
                      <th className="px-3 py-3 text-right font-medium">Videos</th>
                      <th className="px-3 py-3 text-right font-medium">Chats</th>
                      <th className="px-3 py-3 text-right font-medium">Quizzes</th>
                      <th className="px-3 py-3 text-right font-medium">Notes</th>
                      <th className="px-5 py-3 text-right font-medium sm:px-6">Searches</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {filtered.map((user) => (
                      <tr key={user.id} className="hover:bg-canvas">
                        <td className="px-5 py-3 sm:px-6">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-ink">{user.full_name}</span>
                            {user.role === "admin" && (
                              <span className="rounded-full border border-accent-line bg-accent-soft px-2 py-0.5 text-[11px] font-semibold text-accent-ink">
                                Admin
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-muted">{user.email}</div>
                        </td>
                        <td className="px-3 py-3 text-muted">{timeAgo(user.created_at)}</td>
                        <td className="px-3 py-3 text-muted">
                          {user.last_active ? timeAgo(user.last_active) : "Never"}
                        </td>
                        {[user.pdfs, user.videos, user.conversations, user.quizzes, user.notes].map(
                          (value, index) => (
                            <td key={index} className="px-3 py-3 text-right tabular-nums text-ink-soft">
                              {value}
                            </td>
                          ),
                        )}
                        <td className="px-5 py-3 text-right tabular-nums text-ink-soft sm:px-6">
                          {user.searches}
                        </td>
                      </tr>
                    ))}
                    {filtered.length === 0 && (
                      <tr>
                        <td colSpan={9} className="px-6 py-8 text-center text-muted">
                          No users match "{query}".
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        )}
      </PageBody>
    </>
  );
}

/** Simple bar chart of daily counts. */
function TrendCard({ title, days }: { title: string; days: DailyCount[] }) {
  const max = Math.max(1, ...days.map((day) => day.count));
  const total = days.reduce((sum, day) => sum + day.count, 0);
  return (
    <section className="card card-pad">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="section-title">{title}</h2>
        <span className="text-sm tabular-nums text-muted">{total} total</span>
      </div>
      <div className="mt-6 flex h-36 items-end gap-1.5" role="img" aria-label={`${title}: ${total} total`}>
        {days.map((day) => (
          <div key={day.day} className="group flex h-full flex-1 flex-col justify-end">
            <div
              className="rounded-t-[4px] bg-gradient-to-t from-accent-strong to-accent-light transition-opacity group-hover:opacity-80"
              style={{ height: `${day.count === 0 ? 2 : Math.max(6, (day.count / max) * 100)}%` }}
              title={`${new Date(day.day).toLocaleDateString(undefined, { day: "numeric", month: "short" })}: ${day.count}`}
            />
          </div>
        ))}
      </div>
      <div className="mt-2 flex justify-between text-xs text-faint">
        <span>
          {days[0] &&
            new Date(days[0].day).toLocaleDateString(undefined, { day: "numeric", month: "short" })}
        </span>
        <span>Today</span>
      </div>
    </section>
  );
}
