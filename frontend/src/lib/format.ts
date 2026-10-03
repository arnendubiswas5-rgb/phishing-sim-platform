/** Percentage of `value` out of `total`, guarded against divide-by-zero. */
export function pct(value: number, total: number): number {
  if (!total) return 0;
  return Math.round((value / total) * 1000) / 10;
}

export function pctLabel(value: number, total: number): string {
  return `${pct(value, total)}%`;
}

const STATUS_CLASSES: Record<string, string> = {
  draft: "bg-slate-100 text-slate-700",
  scheduled: "bg-blue-100 text-blue-700",
  running: "bg-emerald-100 text-emerald-700",
  paused: "bg-amber-100 text-amber-700",
  completed: "bg-indigo-100 text-indigo-700",
  cancelled: "bg-red-100 text-red-700",
};

export function statusBadgeClass(status: string): string {
  return STATUS_CLASSES[status] ?? "bg-slate-100 text-slate-700";
}
