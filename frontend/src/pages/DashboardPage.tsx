import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { DashboardData, StatCard, ContinueItem, ActivityItem } from "../api/dashboard";
import { getDashboard } from "../api/dashboard";
import { ApiError } from "../api/client";
import { IconAlert, IconChevronRight } from "../components/icons";
import { PageBody, PageHeader } from "../components/workspace";

const MOTIVATIONAL = [
  "Keep pushing — every session brings you closer to mastery.",
  "Great learners are made one question at a time.",
  "Your curiosity is your superpower.",
  "Every study session is an investment in your future.",
];

const MODULE_NAV = [
  { label: "Learn from PDF", module: "Learn from PDF" },
  { label: "Learn from YouTube", module: "Learn from YouTube" },
  { label: "AI Study Tools", module: "AI Study Tools" },
  { label: "AI Assistant", module: "AI Assistant" },
] as const;

const CONTINUE_TO_MODULE: Record<string, (typeof MODULE_NAV)[number]["module"]> = {
  pdf: "Learn from PDF",
  youtube: "Learn from YouTube",
  research: "AI Assistant",
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

/** Dashboard — landing page after login. */
export default function DashboardPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const motivational = MOTIVATIONAL[new Date().getDay() % MOTIVATIONAL.length];

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          navigate("/login", { replace: true });
        } else {
          setError("Could not load dashboard. Please refresh.");
        }
      })
      .finally(() => setLoading(false));
  }, [navigate]);

  return (
    <>
      <PageHeader
        title={data ? `Welcome back, ${data.user_name}` : "Dashboard"}
        description={motivational}
      />
      <PageBody>
        {loading ? (
          <DashboardSkeleton />
        ) : error || !data ? (
          <div className="notice-error rounded-card px-4 py-3">
            <IconAlert className="mt-1 h-4 w-4 shrink-0" />
            <span>{error || "Dashboard unavailable."}</span>
          </div>
        ) : (
          <div className="space-y-8">
            <section aria-label="Learning Analytics">
              <h2 className="section-title mb-3">Learning Analytics</h2>
              <div className="grid grid-cols-2 gap-px overflow-hidden rounded-card border border-line bg-line shadow-card sm:grid-cols-3 xl:grid-cols-6">
                {data.stats.map((stat) => (
                  <StatCardUI key={stat.label} stat={stat} />
                ))}
              </div>
            </section>

            <div className="grid gap-6 lg:grid-cols-3">
              <section className="card card-pad lg:col-span-2">
                <h2 className="section-title">Continue Learning</h2>
                {data.continue_learning.length === 0 ? (
                  <p className="empty-box mt-3">
                    No recent activity yet. Start learning to see your progress here.
                  </p>
                ) : (
                  <ul className="mt-2 divide-y divide-line">
                    {data.continue_learning.map((item) => (
                      <ContinueItemUI
                        key={`${item.resource_type}-${item.resource_id}`}
                        item={item}
                        onNavigate={() =>
                          navigate("/learn", {
                            state: {
                              module: CONTINUE_TO_MODULE[item.resource_type] ?? "Learn from PDF",
                            },
                          })
                        }
                      />
                    ))}
                  </ul>
                )}
              </section>

              <section className="card card-pad">
                <h2 className="section-title">Quick Actions</h2>
                <div className="-mx-2 mt-2 flex flex-col">
                  {MODULE_NAV.map(({ label, module }) => (
                    <button
                      key={label}
                      type="button"
                      onClick={() => navigate("/learn", { state: { module } })}
                      className="group flex h-11 w-full items-center justify-between gap-3 rounded-control px-2 text-left text-sm font-medium text-ink-soft transition-colors hover:bg-accent-soft hover:text-accent-ink"
                    >
                      {label}
                      <IconChevronRight className="h-4 w-4 text-faint transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-accent" />
                    </button>
                  ))}
                </div>
              </section>
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
              <section className="card card-pad lg:col-span-2">
                <h2 className="section-title">Recent Activity</h2>
                {data.recent_activity.length === 0 ? (
                  <p className="empty-box mt-3">No activity yet.</p>
                ) : (
                  <ul className="mt-2 divide-y divide-line">
                    {data.recent_activity.map((entry, i) => (
                      <ActivityItemUI key={i} entry={entry} />
                    ))}
                  </ul>
                )}
              </section>

              <section className="card card-pad">
                <h2 className="section-title">Learning Insights</h2>
                <ul className="mt-2 divide-y divide-line">
                  {data.insights.map((insight) => (
                    <li
                      key={insight.label}
                      className="flex items-baseline justify-between gap-4 py-3 text-sm last:pb-0"
                    >
                      <span className="text-muted">{insight.label}</span>
                      <span className="text-right font-medium tabular-nums text-ink">
                        {insight.value}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            </div>
          </div>
        )}
      </PageBody>
    </>
  );
}

/** Placeholder that mirrors the dashboard layout so nothing jumps on load. */
function DashboardSkeleton() {
  return (
    <div className="space-y-8" role="status" aria-label="Loading your dashboard">
      <div>
        <div className="skeleton mb-3 h-5 w-40" />
        <div className="grid grid-cols-2 gap-px overflow-hidden rounded-card border border-line bg-line sm:grid-cols-3 xl:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="space-y-3 bg-surface p-4 sm:p-5">
              <div className="skeleton h-3 w-2/3" />
              <div className="skeleton h-7 w-1/3" />
            </div>
          ))}
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        {[2, 1].map((span, i) => (
          <div key={i} className={"card card-pad space-y-4 " + (span === 2 ? "lg:col-span-2" : "")}>
            <div className="skeleton h-5 w-36" />
            {[0, 1, 2].map((row) => (
              <div key={row} className="skeleton h-10 w-full" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function StatCardUI({ stat }: { stat: StatCard }) {
  return (
    <div className="flex flex-col justify-between gap-3 bg-gradient-to-b from-white to-[#FFF9F4] px-4 py-4 sm:px-5 sm:py-5">
      <div className="text-[13px] leading-snug text-muted">{stat.label}</div>
      <div className="text-[1.75rem] font-semibold leading-none tracking-[-0.03em] tabular-nums text-ink">
        {stat.value}
      </div>
    </div>
  );
}

const TYPE_LABEL: Record<string, string> = {
  pdf: "PDF",
  youtube: "Video",
  research: "Research",
};

function ContinueItemUI({ item, onNavigate }: { item: ContinueItem; onNavigate: () => void }) {
  return (
    <li className="flex items-center justify-between gap-4 py-3 last:pb-0">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-ink">{item.title}</p>
        <p className="mt-0.5 text-xs text-muted">
          <span className="font-medium text-ink-soft">
            {TYPE_LABEL[item.resource_type] ?? item.resource_type}
          </span>
          <span className="mx-1.5 text-faint">/</span>
          {timeAgo(item.last_accessed)}
        </p>
      </div>
      <button
        type="button"
        onClick={onNavigate}
        className="btn btn-sm border border-line-strong bg-surface text-ink hover:border-faint hover:bg-sunken"
      >
        Continue
      </button>
    </li>
  );
}

function ActivityItemUI({ entry }: { entry: ActivityItem }) {
  return (
    <li className="flex items-baseline justify-between gap-4 py-3 text-sm last:pb-0">
      <span className="min-w-0 break-words text-ink-soft">{entry.description}</span>
      <span className="shrink-0 text-xs tabular-nums text-faint">{timeAgo(entry.created_at)}</span>
    </li>
  );
}
