import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../services/api";
import { pctLabel, statusBadgeClass } from "../lib/format";
import type { Campaign, CampaignReport, TimelinePoint } from "../types";

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl bg-neutral-900 p-5 shadow-sm">
      <p className="text-sm font-medium text-neutral-400">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-neutral-100">{value}</p>
    </div>
  );
}

export function DashboardPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [report, setReport] = useState<CampaignReport | null>(null);
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await api.listCampaigns();
        if (cancelled) return;
        setCampaigns(list);
        // The list is ordered newest-first by the API.
        const latest = list[0];
        if (latest) {
          const [rep, tl] = await Promise.all([
            api.campaignReport(latest.id),
            api.campaignTimeline(latest.id),
          ]);
          if (cancelled) return;
          setReport(rep);
          setTimeline(tl);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load dashboard");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const recent = useMemo(() => campaigns.slice(0, 5), [campaigns]);
  const total = report?.total_targets ?? 0;

  if (loading) return <p className="text-neutral-400">Loading dashboard&hellip;</p>;

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-semibold text-neutral-100">Dashboard</h2>
        {report ? (
          <p className="mt-1 text-sm text-neutral-400">
            Latest campaign: <span className="font-medium">{campaigns[0]?.name}</span>
          </p>
        ) : (
          <p className="mt-1 text-sm text-neutral-400">No campaigns yet.</p>
        )}
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Total Targets" value={total} />
        <MetricCard label="Open Rate" value={pctLabel(report?.unique_opens ?? 0, total)} />
        <MetricCard label="Click Rate" value={pctLabel(report?.unique_clicks ?? 0, total)} />
        <MetricCard label="Submit Rate" value={pctLabel(report?.unique_submissions ?? 0, total)} />
      </div>

      <div className="rounded-xl bg-neutral-900 p-5 shadow-sm">
        <h3 className="mb-4 text-lg font-semibold text-neutral-100">Campaign trend</h3>
        {timeline.length === 0 ? (
          <p className="text-sm text-neutral-400">No tracking activity recorded yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={timeline} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="day" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="opened" stroke="#6366f1" name="Opened" />
              <Line type="monotone" dataKey="clicked" stroke="#f59e0b" name="Clicked" />
              <Line type="monotone" dataKey="submitted" stroke="#ef4444" name="Submitted" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="rounded-xl bg-neutral-900 p-5 shadow-sm">
        <h3 className="mb-4 text-lg font-semibold text-neutral-100">Recent campaigns</h3>
        {recent.length === 0 ? (
          <p className="text-sm text-neutral-400">Nothing to show.</p>
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
              {recent.map((c) => (
                <tr key={c.id} className="border-b border-neutral-800 last:border-0">
                  <td className="py-2 font-medium text-neutral-100">{c.name}</td>
                  <td className="py-2">
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${statusBadgeClass(c.status)}`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="py-2 text-neutral-400">{new Date(c.created_at).toLocaleDateString()}</td>
                  <td className="py-2 text-right">
                    <Link to={`/reports?campaign=${c.id}`} className="font-medium text-green-400 hover:text-green-300">
                      View
                    </Link>
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
