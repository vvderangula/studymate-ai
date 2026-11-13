import { request } from "./client";

export interface DailyCount {
  day: string;
  count: number;
}

export interface AdminStats {
  totals: Record<string, number>;
  active_users_7d: number;
  active_users_30d: number;
  signups_daily: DailyCount[];
  activity_daily: DailyCount[];
  events: Record<string, number>;
}

export interface AdminUser {
  id: string;
  full_name: string;
  email: string;
  role: "admin" | "user";
  created_at: string;
  last_active: string | null;
  pdfs: number;
  videos: number;
  conversations: number;
  quizzes: number;
  notes: number;
  searches: number;
}

export function getAdminStats(): Promise<AdminStats> {
  return request("GET", "/admin/stats");
}

export function getAdminUsers(): Promise<AdminUser[]> {
  return request("GET", "/admin/users");
}
