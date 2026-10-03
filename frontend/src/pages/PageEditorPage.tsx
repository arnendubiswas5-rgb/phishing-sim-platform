import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, describeApiError } from "../services/api";
import type { PageType } from "../types";

const PAGE_TYPES: { value: PageType; label: string; hint: string }[] = [
  { value: "credential", label: "Credential (fake login)", hint: "Renders the page's form and captures submissions." },
  { value: "education", label: "Education", hint: "Shows awareness content; nothing is submitted." },
  { value: "redirect", label: "Redirect", hint: "Sends the target on to the redirect URL." },
];

const STARTER_HTML = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Sign in</title>
</head>
<body style="font-family: Arial, sans-serif; background:#f4f5f7; display:flex; justify-content:center; padding-top:80px;">
  <div style="background:#fff; padding:32px; border-radius:8px; width:320px; box-shadow:0 2px 10px rgba(0,0,0,.1);">
    {% if logo_url %}<img src="{{ logo_url }}" alt="" style="max-height:40px; display:block; margin:0 auto 16px;">{% endif %}
    <h2>Sign in to continue</h2>
    <p>Hi {{ first_name }}, please re-authenticate.</p>
    <form method="post" action="{{ submit_url }}">
      <input type="email" name="username" value="{{ email }}" readonly style="width:100%; padding:10px; margin:8px 0; box-sizing:border-box;">
      <input type="password" name="password" placeholder="Password" required style="width:100%; padding:10px; margin:8px 0; box-sizing:border-box;">
      <button type="submit" style="width:100%; padding:10px; background:#0d9488; color:#fff; border:none; border-radius:4px;">Sign In</button>
    </form>
  </div>
</body>
</html>`;

const inputClass =
  "w-full rounded-md border border-neutral-700 px-3 py-2 text-sm focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500";

export function PageEditorPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isNew = !id || id === "new";

  const [name, setName] = useState("");
  const [pageType, setPageType] = useState<PageType>("credential");
  const [logoUrl, setLogoUrl] = useState("");
  const [redirectUrl, setRedirectUrl] = useState("");
  const [html, setHtml] = useState(STARTER_HTML);

  const [previewHtml, setPreviewHtml] = useState<string | null>(null); // sample-data render
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(isNew ? null : (id ?? null));

  useEffect(() => {
    if (isNew) return;
    api
      .getPage(id!)
      .then((p) => {
        setName(p.name);
        setPageType(p.page_type);
        setLogoUrl(p.logo_url ?? "");
        setRedirectUrl(p.redirect_url ?? "");
        setHtml(p.html_content);
      })
      .catch((err) => setError(describeApiError(err).message))
      .finally(() => setLoading(false));
  }, [id, isNew]);

  async function save() {
    setError(null);
    setSaving(true);
    try {
      const payload = {
        name,
        page_type: pageType,
        html_content: html,
        logo_url: logoUrl || null,
        redirect_url: redirectUrl || null,
      };
      const saved = savedId ? await api.updatePage(savedId, payload) : await api.createPage(payload);
      setSavedId(saved.id);
      if (isNew) navigate(`/pages/${saved.id}`, { replace: true });
    } catch (err) {
      setError(describeApiError(err).message);
    } finally {
      setSaving(false);
    }
  }

  async function previewWithSampleData() {
    if (!savedId) {
      setError("Save the page first, then preview it with sample data.");
      return;
    }
    setError(null);
    try {
      const { html: rendered } = await api.previewPage(savedId);
      setPreviewHtml(rendered);
    } catch (err) {
      setError(describeApiError(err).message);
    }
  }

  if (loading) return <p className="text-neutral-400">Loading&hellip;</p>;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-neutral-100">{isNew ? "New Landing Page" : "Edit Landing Page"}</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate("/pages")}
            className="rounded-md px-4 py-2 text-sm font-medium text-neutral-300 hover:bg-neutral-700"
          >
            Back
          </button>
          <button
            onClick={save}
            disabled={saving || !name || !html}
            className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-500 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="grid grid-cols-1 gap-3 rounded-xl bg-neutral-900 p-4 shadow-sm sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-200">Name</label>
          <input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Acme SSO login" />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-200">Page type</label>
          <select className={inputClass} value={pageType} onChange={(e) => setPageType(e.target.value as PageType)}>
            {PAGE_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          <p className="mt-1 text-xs text-neutral-400">{PAGE_TYPES.find((t) => t.value === pageType)?.hint}</p>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-200">Logo URL (optional)</label>
          <input className={inputClass} value={logoUrl} onChange={(e) => setLogoUrl(e.target.value)} placeholder="https://…/logo.png" />
          <p className="mt-1 text-xs text-neutral-400">Available in HTML as <code>{"{{ logo_url }}"}</code>.</p>
        </div>
        {pageType === "redirect" && (
          <div>
            <label className="mb-1 block text-sm font-medium text-neutral-200">Redirect URL</label>
            <input className={inputClass} value={redirectUrl} onChange={(e) => setRedirectUrl(e.target.value)} placeholder="https://real-site.example" />
          </div>
        )}
      </div>

      {/* Split view: raw HTML (left) / live preview (right) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl bg-neutral-900 p-3 shadow-sm">
          <label className="mb-1 block text-sm font-medium text-neutral-200">HTML</label>
          <textarea
            className="h-[28rem] w-full rounded-md border border-neutral-700 p-3 font-mono text-xs focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
            value={html}
            onChange={(e) => {
              setHtml(e.target.value);
              if (previewHtml) setPreviewHtml(null); // editing drops back to live preview
            }}
            spellCheck={false}
          />
        </div>
        <div className="rounded-xl bg-neutral-900 p-3 shadow-sm">
          <div className="mb-1 flex items-center justify-between">
            <label className="text-sm font-medium text-neutral-200">
              {previewHtml ? "Preview (sample data)" : "Live preview (raw template)"}
            </label>
            <div className="flex items-center gap-2">
              {previewHtml && (
                <button onClick={() => setPreviewHtml(null)} className="text-xs font-medium text-neutral-400 hover:text-neutral-200">
                  Back to live
                </button>
              )}
              <button
                onClick={previewWithSampleData}
                disabled={!savedId}
                title={savedId ? undefined : "Save the page first"}
                className="rounded-md border border-neutral-700 px-3 py-1 text-xs font-medium text-neutral-200 hover:bg-neutral-800 disabled:opacity-50"
              >
                Preview with sample data
              </button>
            </div>
          </div>
          <iframe
            title="Page preview"
            srcDoc={previewHtml ?? html}
            sandbox=""
            className="h-[28rem] w-full rounded-md border border-neutral-800"
          />
        </div>
      </div>
    </div>
  );
}
