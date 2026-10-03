import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { NeonField } from "./NeonField";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/campaigns", label: "Campaigns" },
  { to: "/targets", label: "Targets" },
  { to: "/templates", label: "Templates" },
  { to: "/pages", label: "Pages" },
  { to: "/reports", label: "Reports" },
  { to: "/settings", label: "Settings" },
];

export function DashboardLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-screen">
      <NeonField />
      <aside className="relative flex w-60 flex-col border-r border-neutral-800 bg-neutral-950 text-neutral-300">
        <div className="font-display px-6 py-5 text-lg font-bold tracking-tight text-green-400 text-glow-green">
          PhishSim
        </div>

        <nav className="flex-1 space-y-1 px-3">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block rounded-md px-3 py-2 text-sm font-medium transition ${
                  isActive
                    ? "bg-green-600 text-white glow-green"
                    : "text-neutral-400 hover:bg-neutral-800 hover:text-white"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-neutral-800 p-3">
          {user && (
            <p className="mb-2 truncate px-3 text-xs text-neutral-500" title={user.email}>
              {user.email}
            </p>
          )}
          <button
            onClick={logout}
            className="w-full rounded-md px-3 py-2 text-left text-sm font-medium text-neutral-400 transition hover:bg-neutral-800 hover:text-white"
          >
            Log out
          </button>
        </div>
      </aside>

      <main className="relative flex-1 overflow-y-auto bg-black/60 p-8 backdrop-blur-sm">
        <Outlet />
      </main>
    </div>
  );
}
