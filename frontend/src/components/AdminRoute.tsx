import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";

import { useAuth } from "../context/AuthContext";

/**
 * Shows admin pages only to admins; everyone else goes to the dashboard.
 * (The API enforces this too: admin endpoints return 403 for non-admins.)
 */
export default function AdminRoute({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  if (user?.role !== "admin") {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
