import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../services/api";
import type { Target, TargetImportResult } from "../types";

export function TargetsPage() {
  const [targets, setTargets] = useState<Target[]>([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);

  function refresh() {
    api
      .listTargets()
      .then(setTargets)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load targets"))
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return targets;
    return targets.filter((t) =>
      [t.email, t.first_name, t.last_name, t.department]
        .filter(Boolean)
        .some((field) => field!.toLowerCase().includes(q)),
    );
  }, [targets, search]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-neutral-100">Targets</h2>
        <button
          onClick={() => setModalOpen(true)}
          className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-500"
        >
          Import CSV
        </button>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <input
        type="search"
        placeholder="Search by name, email, or department&hellip;"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full max-w-sm rounded-md border border-neutral-700 px-3 py-2 text-sm focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
      />

      <div className="rounded-xl bg-neutral-900 p-5 shadow-sm">
        {loading ? (
          <p className="text-sm text-neutral-400">Loading&hellip;</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-neutral-800 text-neutral-400">
                <th className="pb-2 font-medium">Email</th>
                <th className="pb-2 font-medium">First name</th>
                <th className="pb-2 font-medium">Last name</th>
                <th className="pb-2 font-medium">Department</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-4 text-center text-neutral-400">
                    {targets.length === 0 ? "No targets yet. Import a CSV to begin." : "No matches."}
                  </td>
                </tr>
              ) : (
                filtered.map((t) => (
                  <tr key={t.id} className="border-b border-neutral-800 last:border-0">
                    <td className="py-2 font-medium text-neutral-100">{t.email}</td>
                    <td className="py-2 text-neutral-300">{t.first_name ?? "-"}</td>
                    <td className="py-2 text-neutral-300">{t.last_name ?? "-"}</td>
                    <td className="py-2 text-neutral-300">{t.department ?? "-"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>

      {modalOpen && (
        <ImportModal
          onClose={() => setModalOpen(false)}
          onImported={() => {
            setModalOpen(false);
            refresh();
          }}
        />
      )}
    </div>
  );
}

function ImportModal({ onClose, onImported }: { onClose: () => void; onImported: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [groupName, setGroupName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TargetImportResult | null>(null);

  async function handleUpload() {
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError("Choose a CSV file first.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const res = await api.importTargets(file, groupName || undefined);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-10 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-xl bg-neutral-900 p-6 shadow-lg" onClick={(e) => e.stopPropagation()}>
        <h3 className="mb-4 text-lg font-semibold text-neutral-100">Import targets from CSV</h3>

        {result ? (
          <div className="space-y-3 text-sm text-neutral-200">
            <p>
              Imported into <span className="font-medium">{result.group_name}</span>:
            </p>
            <ul className="list-inside list-disc text-neutral-300">
              <li>{result.inserted} inserted</li>
              <li>{result.skipped_duplicates} duplicates skipped</li>
              <li>{result.skipped_invalid} invalid rows skipped</li>
            </ul>
            <button
              onClick={onImported}
              className="mt-2 w-full rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-500"
            >
              Done
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-neutral-200">Group name (optional)</label>
              <input
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
                placeholder="Imported Targets"
                className="w-full rounded-md border border-neutral-700 px-3 py-2 text-sm focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-neutral-200">CSV file</label>
              <input ref={fileRef} type="file" accept=".csv,text/csv" className="block w-full text-sm text-neutral-300" />
            </div>
            {error && <p className="text-sm text-red-400">{error}</p>}
            <div className="flex justify-end gap-3">
              <button onClick={onClose} className="rounded-md px-4 py-2 text-sm font-medium text-neutral-300 hover:bg-neutral-800">
                Cancel
              </button>
              <button
                onClick={handleUpload}
                disabled={busy}
                className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-500 disabled:opacity-50"
              >
                {busy ? "Uploading…" : "Upload"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
