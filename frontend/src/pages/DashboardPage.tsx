import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { DashboardData, StatCard, ContinueItem, ActivityItem } from "../api/dashboard";
import { getDashboard } from "../api/dashboard";
import { ApiError } from "../api/client";

const MOTIVATIONAL = [
  "Keep pushing — every session brings you closer to mastery.",
  "Great learners are made one question at a time.",
  "Your curiosity is your superpower.",
  "Every study session is an investment in your future.",
];

const STAT_ICONS: Record<string, string> = {
  "PDFs Studied": "📄",
  "YouTube Videos": "▶️",
  "AI Chats": "💬",
  "Research Papers": "🔬",
  "Quizzes Generated": "🧠",
  "Notes Generated": "📝",
};

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

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        Loading your dashboard…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
        {error || "Dashboard unavailable."}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Welcome */}
      <div className="rounded-2xl border border-slate-200 bg-white px-6 py-5 shadow-sm">
        <h1 className="text-2xl font-bold text-slate-800">
          Welcome back, {data.user_name} 👋
        </h1>
        <p className="mt-1 text-sm text-slate-500">{motivational}</p>
      </div>

      {/* Learning Analytics */}
      <section aria-label="Learning Analytics">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
          Learning Analytics
        </h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {data.stats.map((stat) => (
            <StatCardUI key={stat.label} stat={stat} />
          ))}
        </div>
      </section>

      {/* Learning Insights + Continue Learning side by side on larger screens */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Learning Insights */}
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-base font-semibold text-slate-800">Learning Insights</h2>
          <ul className="space-y-3">
            {data.insights.map((insight) => (
              <li key={insight.label} className="flex items-center justify-between text-sm">
                <span className="text-slate-500">{insight.label}</span>
                <span className="font-semibold text-slate-800">{insight.value}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* Continue Learning */}
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-base font-semibold text-slate-800">Continue Learning</h2>
          {data.continue_learning.length === 0 ? (
            <p className="text-sm text-slate-400">
              No recent activity yet. Start learning to see your progress here.
            </p>
          ) : (
            <ul className="space-y-3">
              {data.continue_learning.map((item) => (
                <ContinueItemUI
                  key={`${item.resource_type}-${item.resource_id}`}
                  item={item}
                  onNavigate={() =>
                    navigate("/learn", {
                      state: { module: CONTINUE_TO_MODULE[item.resource_type] ?? "Learn from PDF" },
                    })
                  }
                />
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* Recent Activity + Quick Actions */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent Activity */}
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-2">
          <h2 className="mb-4 text-base font-semibold text-slate-800">Recent Activity</h2>
          {data.recent_activity.length === 0 ? (
            <p className="text-sm text-slate-400">No activity yet.</p>
          ) : (
            <ul className="space-y-2">
              {data.recent_activity.map((entry, i) => (
                <ActivityItemUI key={i} entry={entry} />
              ))}
            </ul>
          )}
        </section>

        {/* Quick Actions */}
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-base font-semibold text-slate-800">Quick Actions</h2>
          <div className="flex flex-col gap-2">
            {MODULE_NAV.map(({ label, module }) => (
              <button
                key={label}
                type="button"
                onClick={() => navigate("/learn", { state: { module } })}
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-2.5 text-left text-sm font-medium text-slate-700 transition hover:border-orange-300 hover:bg-orange-50 hover:text-orange-600"
              >
                {label}
              </button>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function StatCardUI({ stat }: { stat: StatCard }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm text-center">
      <div className="text-2xl">{STAT_ICONS[stat.label] ?? "📊"}</div>
      <div className="mt-1 text-2xl font-bold text-slate-800">{stat.value}</div>
      <div className="mt-0.5 text-xs text-slate-500">{stat.label}</div>
    </div>
  );
}

function ContinueItemUI({ item, onNavigate }: { item: ContinueItem; onNavigate: () => void }) {
  const typeLabel: Record<string, string> = {
    pdf: "📄 PDF",
    youtube: "▶️ Video",
    research: "🔬 Research",
  };
  return (
    <li className="flex items-center justify-between gap-3 rounded-lg border border-slate-100 bg-slate-50 p-3">
      <div className="min-w-0">
        <p className="text-xs font-medium text-slate-400">{typeLabel[item.resource_type] ?? item.resource_type}</p>
        <p className="truncate text-sm font-medium text-slate-700">{item.title}</p>
        <p className="text-xs text-slate-400">{timeAgo(item.last_accessed)}</p>
      </div>
      <button
        type="button"
        onClick={onNavigate}
        className="shrink-0 rounded-lg bg-orange-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-orange-600"
      >
        Continue
      </button>
    </li>
  );
}

function ActivityItemUI({ entry }: { entry: ActivityItem }) {
  return (
    <li className="flex items-center justify-between gap-3 text-sm">
      <span className="text-slate-700">{entry.description}</span>
      <span className="shrink-0 text-xs text-slate-400">{timeAgo(entry.created_at)}</span>
    </li>
  );
}
