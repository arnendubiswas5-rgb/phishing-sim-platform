import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { api } from "../services/api";
import { pctLabel } from "../lib/format";
import type { Campaign, CampaignReport, DepartmentBreakdown } from "../types";

const PIE_COLORS = ["#6366f1", "#f59e0b", "#ef4444"];

export function ReportsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selectedId, setSelectedId] = useState<string>(searchParams.get("campaign") ?? "");
  const [report, setReport] = useState<CampaignReport | null>(null);
  const [departments, setDepartments] = useState<DepartmentBreakdown[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listCampaigns().then(setCampaigns).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setReport(null);
      setDepartments([]);
      return;
    }
    let cancelled = false;
    setError(null);
    Promise.all([api.campaignReport(selectedId), api.campaignDepartments(selectedId)])
      .then(([rep, deps]) => {
        if (cancelled) return;
        setReport(rep);
        setDepartments(deps);
      })
      .catch((err) => !cancelled && setError(err instanceof Error ? err.message : "Failed to load report"));
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  function onSelect(id: string) {
    setSelectedId(id);
    setSearchParams(id ? { campaign: id } : {});
  }

  function exportCsv() {
    if (!report) return;
    const campaign = campaigns.find((c) => c.id === report.campaign_id);
    const lines: string[] = [];
    lines.push("Metric,Value");
    lines.push(`Campaign,"${(campaign?.name ?? report.campaign_id).replace(/"/g, '""')}"`);
    lines.push(`Total Targets,${report.total_targets}`);
    lines.push(`Emails Sent,${report.emails_sent}`);
    lines.push(`Unique Opens,${report.unique_opens}`);
    lines.push(`Unique Clicks,${report.unique_clicks}`);
    lines.push(`Unique Submissions,${report.unique_submissions}`);
    lines.push(`Submit Rate,${report.report_rate}%`);
    lines.push("");
    lines.push("Department,Total Targets,Opened,Clicked,Submitted");
    for (const d of departments) {
      lines.push(`"${d.department.replace(/"/g, '""')}",${d.total_targets},${d.opened},${d.clicked},${d.submitted}`);
    }

    const blob = new Blob([lines.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report-${campaign?.name ?? report.campaign_id}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const pieData = report
    ? [
        { name: "Opened", value: report.unique_opens },
        { name: "Clicked", value: report.unique_clicks },
        { name: "Submitted", value: report.unique_submissions },
      ]
    : [];

  const total = report?.total_targets ?? 0;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold text-neutral-100">Reports</h2>

      <div className="flex items-center gap-3">
        <select
          value={selectedId}
          onChange={(e) => onSelect(e.target.value)}
          className="w-full max-w-sm rounded-md border border-neutral-700 px-3 py-2 text-sm focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
        >
          <option value="">Select a campaign&hellip;</option>
          {campaigns.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        {report && (
          <button onClick={exportCsv} className="rounded-md border border-neutral-700 px-4 py-2 text-sm font-medium text-neutral-200 hover:bg-neutral-800">
            Export CSV
          </button>
        )}
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {campaigns.length === 0 ? (
        <p className="text-sm text-neutral-400">
          No campaigns yet.{" "}
          <Link to="/campaigns/new" className="font-medium text-green-400 hover:text-green-300 hover:underline">
            create your first one
          </Link>
        </p>
      ) : (
        !selectedId && <p className="text-sm text-neutral-400">Choose a campaign to see its report.</p>
      )}

      {report && (
        <>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Summary table */}
            <div className="rounded-xl bg-neutral-900 p-5 shadow-sm">
              <h3 className="mb-4 text-lg font-semibold text-neutral-100">Summary</h3>
              <table className="w-full text-sm">
                <tbody>
                  <SummaryRow label="Total targets" value={report.total_targets} />
                  <SummaryRow label="Emails sent" value={report.emails_sent} />
                  <SummaryRow label="Unique opens" value={`${report.unique_opens} (${pctLabel(report.unique_opens, total)})`} />
                  <SummaryRow label="Unique clicks" value={`${report.unique_clicks} (${pctLabel(report.unique_clicks, total)})`} />
                  <SummaryRow label="Unique submissions" value={`${report.unique_submissions} (${pctLabel(report.unique_submissions, total)})`} />
                  <SummaryRow label="Submit rate" value={`${report.report_rate}%`} />
                </tbody>
              </table>
            </div>

            {/* Pie chart */}
            <div className="rounded-xl bg-neutral-900 p-5 shadow-sm">
              <h3 className="mb-4 text-lg font-semibold text-neutral-100">Interaction breakdown</h3>
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Department breakdown */}
          <div className="rounded-xl bg-neutral-900 p-5 shadow-sm">
            <h3 className="mb-4 text-lg font-semibold text-neutral-100">By department</h3>
            {departments.length === 0 ? (
              <p className="text-sm text-neutral-400">No department data.</p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-neutral-800 text-neutral-400">
                    <th className="pb-2 font-medium">Department</th>
                    <th className="pb-2 font-medium text-right">Targets</th>
                    <th className="pb-2 font-medium text-right">Opened</th>
                    <th className="pb-2 font-medium text-right">Clicked</th>
                    <th className="pb-2 font-medium text-right">Submitted</th>
                  </tr>
                </thead>
                <tbody>
                  {departments.map((d) => (
                    <tr key={d.department} className="border-b border-neutral-800 last:border-0">
                      <td className="py-2 font-medium text-neutral-100">{d.department}</td>
                      <td className="py-2 text-right text-neutral-300">{d.total_targets}</td>
                      <td className="py-2 text-right text-neutral-300">{d.opened}</td>
                      <td className="py-2 text-right text-neutral-300">{d.clicked}</td>
                      <td className="py-2 text-right text-neutral-300">{d.submitted}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string | number }) {
  return (
    <tr className="border-b border-neutral-800 last:border-0">
      <td className="py-2 text-neutral-400">{label}</td>
      <td className="py-2 text-right font-medium text-neutral-100">{value}</td>
    </tr>
  );
}
