import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../services/api";
import { statusBadgeClass } from "../lib/format";
import type { Campaign } from "../types";

export function CampaignsPage() {
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  function refresh() {
    api
      .listCampaigns()
      .then(setCampaigns)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load campaigns"))
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function act(fn: Promise<unknown>) {
    setError(null);
    try {
      await fn;
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-neutral-100">Campaigns</h2>
        <button
          onClick={() => navigate("/campaigns/new")}
          className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-500"
        >
          New Campaign
        </button>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="rounded-xl bg-neutral-900 p-5 shadow-sm">
        {loading ? (
          <p className="text-sm text-neutral-400">Loading&hellip;</p>
        ) : campaigns.length === 0 ? (
          <p className="text-sm text-neutral-400">
            No campaigns yet.{" "}
            <Link to="/campaigns/new" className="font-medium text-green-400 hover:text-green-300 hover:underline">
              create your first one
            </Link>
          </p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-neutral-800 text-neutral-400">
                <th className="pb-2 font-medium">Name</th>
                <th className="pb-2 font-medium">Status</th>
                <th className="pb-2 font-medium">Created</th>
                <th className="pb-2 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.map((c) => (
                <tr key={c.id} className="border-b border-neutral-800 last:border-0">
                  <td className="py-2 font-medium text-neutral-100">{c.name}</td>
                  <td className="py-2">
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${statusBadgeClass(c.status)}`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="py-2 text-neutral-400">{new Date(c.created_at).toLocaleDateString()}</td>
                  <td className="py-2 text-right">
                    <div className="flex justify-end gap-3">
                      {(c.status === "draft" || c.status === "paused") && (
                        <button
                          onClick={() => act(api.launchCampaign(c.id))}
                          className="font-medium text-green-400 hover:text-green-300"
                        >
                          Launch
                        </button>
                      )}
                      {c.status === "running" && (
                        <button
                          onClick={() => act(api.pauseCampaign(c.id))}
                          className="font-medium text-amber-400 hover:text-amber-300"
                        >
                          Pause
                        </button>
                      )}
                      <Link to={`/reports?campaign=${c.id}`} className="font-medium text-green-400 hover:text-green-300">
                        View
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
