import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { EmailTemplate } from "../types";

interface EditorState {
  name: string;
  subject: string;
  sender_name: string;
  sender_email: string;
  html_body: string;
  text_body: string;
}

const EMPTY: EditorState = {
  name: "",
  subject: "",
  sender_name: "",
  sender_email: "",
  html_body: "<p>Hello {{ first_name }},</p>\n<p><a href=\"{{ tracking_url }}\">Click here</a></p>",
  text_body: "",
};

export function TemplatesPage() {
  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [editor, setEditor] = useState<EditorState>(EMPTY);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  // What the iframe shows: the live editor HTML, or a server-rendered preview.
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function refresh() {
    api.listTemplates().then(setTemplates).catch((err) => setError(err.message));
  }

  useEffect(refresh, []);

  function selectTemplate(t: EmailTemplate) {
    setSelectedId(t.id);
    setPreviewHtml(null);
    setEditor({
      name: t.name,
      subject: t.subject,
      sender_name: t.sender_name,
      sender_email: t.sender_email,
      html_body: t.html_body,
      text_body: t.text_body ?? "",
    });
  }

  function newTemplate() {
    setSelectedId(null);
    setPreviewHtml(null);
    setEditor(EMPTY);
  }

  function set<K extends keyof EditorState>(key: K, value: EditorState[K]) {
    setEditor((e) => ({ ...e, [key]: value }));
    if (key === "html_body") setPreviewHtml(null); // fall back to live preview on edit
  }

  async function save() {
    setError(null);
    setBusy(true);
    try {
      await api.createTemplate({
        name: editor.name,
        subject: editor.subject,
        sender_name: editor.sender_name,
        sender_email: editor.sender_email,
        html_body: editor.html_body,
        text_body: editor.text_body || null,
      });
      refresh();
      newTemplate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save template");
    } finally {
      setBusy(false);
    }
  }

  async function serverPreview() {
    if (!selectedId) return;
    setError(null);
    try {
      const res = await api.previewTemplate(selectedId);
      setPreviewHtml(res.html_body);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preview failed");
    }
  }

  const inputClass =
    "w-full rounded-md border border-neutral-700 px-3 py-2 text-sm focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-neutral-100">Templates</h2>
        <button onClick={newTemplate} className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-500">
          New Template
        </button>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[220px_1fr]">
        {/* Template list */}
        <aside className="rounded-xl bg-neutral-900 p-3 shadow-sm">
          {templates.length === 0 ? (
            <div className="p-2 text-sm text-neutral-400">
              <p>No templates yet.</p>
              <button
                onClick={newTemplate}
                className="mt-1 font-medium text-green-400 hover:text-green-300 hover:underline"
              >
                Create your first one
              </button>
            </div>
          ) : (
            <ul className="space-y-1">
              {templates.map((t) => (
                <li key={t.id}>
                  <button
                    onClick={() => selectTemplate(t)}
                    className={`w-full rounded-md px-3 py-2 text-left text-sm ${
                      selectedId === t.id ? "bg-green-950 font-medium text-green-400" : "text-neutral-200 hover:bg-neutral-800"
                    }`}
                  >
                    {t.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>

        {/* Editor */}
        <section className="space-y-4 rounded-xl bg-neutral-900 p-5 shadow-sm">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <input className={inputClass} placeholder="Template name" value={editor.name} onChange={(e) => set("name", e.target.value)} />
            <input className={inputClass} placeholder="Subject" value={editor.subject} onChange={(e) => set("subject", e.target.value)} />
            <input className={inputClass} placeholder="Sender name" value={editor.sender_name} onChange={(e) => set("sender_name", e.target.value)} />
            <input className={inputClass} placeholder="Sender email" type="email" value={editor.sender_email} onChange={(e) => set("sender_email", e.target.value)} />
          </div>

          {/* Split view: HTML source (left) / preview (right) */}
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-neutral-200">HTML</label>
              <textarea
                className="h-80 w-full rounded-md border border-neutral-700 p-3 font-mono text-xs focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
                value={editor.html_body}
                onChange={(e) => set("html_body", e.target.value)}
              />
            </div>
            <div>
              <div className="mb-1 flex items-center justify-between">
                <label className="text-sm font-medium text-neutral-200">
                  Preview {previewHtml ? "(server-rendered)" : "(live)"}
                </label>
                <button
                  onClick={serverPreview}
                  disabled={!selectedId}
                  title={selectedId ? "" : "Save the template first"}
                  className="rounded-md border border-neutral-700 px-2 py-1 text-xs font-medium text-neutral-300 hover:bg-neutral-800 disabled:opacity-50"
                >
                  Preview
                </button>
              </div>
              <iframe
                title="Template preview"
                className="h-80 w-full rounded-md border border-neutral-700 bg-neutral-900"
                srcDoc={previewHtml ?? editor.html_body}
                sandbox=""
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              onClick={save}
              disabled={busy || !editor.name || !editor.subject}
              className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-500 disabled:opacity-50"
            >
              {busy ? "Saving…" : "Save Template"}
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
