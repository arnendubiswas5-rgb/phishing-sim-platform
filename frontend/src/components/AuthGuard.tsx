import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

/**
 * Layout route that gates every child route behind authentication.
 * While the session is being restored we hold on a spinner; once resolved,
 * unauthenticated users are redirected to /login (remembering where they
 * were headed so the login flow can send them back).
 */
export function AuthGuard() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-neutral-400">
        Loading&hellip;
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
