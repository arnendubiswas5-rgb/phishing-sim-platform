import { useEffect, useState } from "react";
import { api, describeApiError } from "../services/api";
import type { SmtpProfile, SmtpProfileCreatePayload } from "../types";

const smtpInputClass =
  "w-full rounded-md border border-neutral-700 px-3 py-2 text-sm focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500";

const EMPTY_SMTP: SmtpProfileCreatePayload = {
  name: "",
  host: "",
  port: 587,
  username: "",
  password: "",
  use_tls: true,
  from_name: "",
  from_email: "",
};

export function SettingsPage() {
  const [retentionDays, setRetentionDays] = useState<number>(90);
  const [loading, setLoading] = useState(true);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [purging, setPurging] = useState(false);
  const [purgeMsg, setPurgeMsg] = useState<string | null>(null);

  const [smtpProfiles, setSmtpProfiles] = useState<SmtpProfile[]>([]);
  const [smtpForm, setSmtpForm] = useState<SmtpProfileCreatePayload>(EMPTY_SMTP);
  const [smtpSaving, setSmtpSaving] = useState(false);
  const [smtpMsg, setSmtpMsg] = useState<string | null>(null);

  useEffect(() => {
    api
      .getSettings()
      .then((s) => setRetentionDays(s.retention_days))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load settings"))
      .finally(() => setLoading(false));
    api.listSmtpProfiles().then(setSmtpProfiles).catch(() => {});
  }, []);

  function setSmtp<K extends keyof SmtpProfileCreatePayload>(key: K, value: SmtpProfileCreatePayload[K]) {
    setSmtpForm((f) => ({ ...f, [key]: value }));
  }

  async function addSmtpProfile() {
    setError(null);
    setSmtpMsg(null);
    setSmtpSaving(true);
    try {
      // port 465 = implicit TLS; otherwise STARTTLS when "use TLS" is on.
      const created = await api.createSmtpProfile({ ...smtpForm, use_tls: smtpForm.port === 465 ? true : smtpForm.use_tls });
      setSmtpProfiles((list) => [...list, created]);
      setSmtpForm(EMPTY_SMTP);
      setSmtpMsg(`Saved SMTP profile "${created.name}".`);
    } catch (err) {
      setError(describeApiError(err).message);
    } finally {
      setSmtpSaving(false);
    }
  }

  async function save() {
    setError(null);
    setSavedMsg(null);
    setSaving(true);
    try {
      const s = await api.updateSettings(retentionDays);
      setRetentionDays(s.retention_days);
      setSavedMsg("Settings saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  }

  async function purgeNow() {
    if (!window.confirm("Permanently delete all campaign data older than the retention period? This cannot be undone.")) {
      return;
    }
    setError(null);
    setPurgeMsg(null);
    setPurging(true);
    try {
      const res = await api.purgeNow();
      setPurgeMsg(`Purge complete. Removed ${res.purged_campaigns} campaign(s) and their data.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Purge failed");
    } finally {
      setPurging(false);
    }
  }

  if (loading) return <p className="text-neutral-400">Loading&hellip;</p>;

  return (
    <div className="max-w-xl space-y-6">
      <h2 className="text-2xl font-semibold text-neutral-100">Admin Settings</h2>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="space-y-4 rounded-xl bg-neutral-900 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-neutral-100">Data retention</h3>
        <p className="text-sm text-neutral-400">
          Campaign and tracking data older than this many days is removed by the daily purge job.
        </p>
        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-200">Retention period (days)</label>
          <input
            type="number"
            min={1}
            max={3650}
            value={retentionDays}
            onChange={(e) => setRetentionDays(Number(e.target.value))}
            className="w-40 rounded-md border border-neutral-700 px-3 py-2 text-sm focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
          />
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={save}
            disabled={saving}
            className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-500 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save"}
          </button>
          {savedMsg && <span className="text-sm text-green-400">{savedMsg}</span>}
        </div>
      </div>

      <div className="space-y-4 rounded-xl bg-neutral-900 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-neutral-100">SMTP profiles (real email delivery)</h3>
        <p className="text-sm text-neutral-400">
          Add a real mail relay so campaigns send to real inboxes. Use port 587 (STARTTLS) or 465 (implicit TLS)
          with your provider's host, username, and an app password. The password is encrypted at rest and never
          shown again.
        </p>

        {smtpProfiles.length > 0 && (
          <ul className="divide-y divide-neutral-800 rounded-md border border-neutral-800 text-sm">
            {smtpProfiles.map((p) => (
              <li key={p.id} className="flex items-center justify-between px-3 py-2">
                <span className="font-medium text-neutral-200">{p.name}</span>
                <span className="text-neutral-400">
                  {p.host}:{p.port} {p.use_tls || p.port === 465 ? "(TLS)" : "(plaintext)"}
                </span>
              </li>
            ))}
          </ul>
        )}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <input className={smtpInputClass} placeholder="Profile name (e.g. Company Relay)" value={smtpForm.name} onChange={(e) => setSmtp("name", e.target.value)} />
          <input className={smtpInputClass} placeholder="Host (e.g. smtp.gmail.com)" value={smtpForm.host} onChange={(e) => setSmtp("host", e.target.value)} />
          <input className={smtpInputClass} type="number" placeholder="Port" value={smtpForm.port} onChange={(e) => setSmtp("port", Number(e.target.value))} />
          <label className="flex items-center gap-2 text-sm text-neutral-300">
            <input type="checkbox" checked={smtpForm.use_tls} onChange={(e) => setSmtp("use_tls", e.target.checked)} disabled={smtpForm.port === 465} />
            Use TLS {smtpForm.port === 465 && <span className="text-neutral-500">(implicit on 465)</span>}
          </label>
          <input className={smtpInputClass} placeholder="Username" value={smtpForm.username ?? ""} onChange={(e) => setSmtp("username", e.target.value)} autoComplete="off" />
          <input className={smtpInputClass} type="password" placeholder="Password / app password" value={smtpForm.password ?? ""} onChange={(e) => setSmtp("password", e.target.value)} autoComplete="new-password" />
          <input className={smtpInputClass} placeholder="From name (e.g. IT Security)" value={smtpForm.from_name} onChange={(e) => setSmtp("from_name", e.target.value)} />
          <input className={smtpInputClass} type="email" placeholder="From email (verified sender)" value={smtpForm.from_email} onChange={(e) => setSmtp("from_email", e.target.value)} />
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={addSmtpProfile}
            disabled={smtpSaving || !smtpForm.name || !smtpForm.host || !smtpForm.from_email}
            className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-500 disabled:opacity-50"
          >
            {smtpSaving ? "Saving…" : "Add SMTP profile"}
          </button>
          {smtpMsg && <span className="text-sm text-green-400">{smtpMsg}</span>}
        </div>
      </div>

      <div className="space-y-4 rounded-xl border border-red-900 bg-neutral-900 p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-neutral-100">Purge now</h3>
        <p className="text-sm text-neutral-400">
          Immediately run the retention purge for your organization instead of waiting for the daily job.
        </p>
        <div className="flex items-center gap-3">
          <button
            onClick={purgeNow}
            disabled={purging}
            className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-500 disabled:opacity-50"
          >
            {purging ? "Purging…" : "Purge Now"}
          </button>
          {purgeMsg && <span className="text-sm text-neutral-200">{purgeMsg}</span>}
        </div>
      </div>
    </div>
  );
}
