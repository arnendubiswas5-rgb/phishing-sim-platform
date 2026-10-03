import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, describeApiError } from "../services/api";
import type { Page, PageType } from "../types";

const TYPE_LABELS: Record<PageType, string> = {
  credential: "Credential",
  education: "Education",
  redirect: "Redirect",
};

const TYPE_BADGE: Record<PageType, string> = {
  credential: "bg-amber-950 text-amber-300",
  education: "bg-green-900 text-green-400",
  redirect: "bg-neutral-800 text-neutral-200",
};

export function PagesListPage() {
  const navigate = useNavigate();
  const [pages, setPages] = useState<Page[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listPages()
      .then(setPages)
      .catch((err) => setError(describeApiError(err).message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-neutral-100">Landing Pages</h2>
        <button
          onClick={() => navigate("/pages/new")}
          className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-500"
        >
          New Page
        </button>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {loading ? (
        <p className="text-sm text-neutral-400">Loading&hellip;</p>
      ) : pages.length === 0 ? (
        <p className="text-sm text-neutral-400">
          No landing pages yet.{" "}
          <button onClick={() => navigate("/pages/new")} className="font-medium text-green-400 hover:underline">
            Create your first one
          </button>
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {pages.map((p) => (
            <button
              key={p.id}
              onClick={() => navigate(`/pages/${p.id}`)}
              className="group overflow-hidden rounded-xl border border-neutral-800 bg-neutral-900 text-left shadow-sm transition hover:border-green-500 hover:shadow"
            >
              <div className="relative h-40 overflow-hidden border-b border-neutral-800 bg-neutral-900">
                {/* Scaled, non-interactive thumbnail of the page HTML. */}
                <iframe
                  title={`Preview of ${p.name}`}
                  srcDoc={p.html_content}
                  sandbox=""
                  tabIndex={-1}
                  className="pointer-events-none absolute left-0 top-0 origin-top-left"
                  style={{ width: "250%", height: "250%", transform: "scale(0.4)" }}
                />
              </div>
              <div className="flex items-center justify-between gap-2 px-4 py-3">
                <span className="truncate font-medium text-neutral-100">{p.name}</span>
                <span className={`shrink-0 rounded px-2 py-0.5 text-xs font-medium ${TYPE_BADGE[p.page_type]}`}>
                  {TYPE_LABELS[p.page_type]}
                </span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
