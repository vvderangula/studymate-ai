import { API_BASE_URL, ApiError, authHeaders, readErrorDetail } from "./client";

export interface StatCard {
  label: string;
  value: number;
}

export interface InsightItem {
  label: string;
  value: string;
}

export interface ContinueItem {
  resource_type: string;
  resource_id: string;
  title: string;
  last_accessed: string;
}

export interface ActivityItem {
  event_type: string;
  description: string;
  created_at: string;
}

export interface DashboardData {
  user_name: string;
  stats: StatCard[];
  insights: InsightItem[];
  continue_learning: ContinueItem[];
  recent_activity: ActivityItem[];
}

/** Fetch the current user's dashboard data. */
export async function getDashboard(): Promise<DashboardData> {
  const response = await fetch(`${API_BASE_URL}/dashboard`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }
  return response.json();
}
