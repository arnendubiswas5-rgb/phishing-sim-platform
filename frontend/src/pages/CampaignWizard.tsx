import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, describeApiError, type ApiErrorInfo } from "../services/api";
import type {
  CampaignType,
  EmailTemplate,
  Page,
  SmtpProfile,
  Target,
  TargetGroup,
  TrainingModule,
} from "../types";

const CAMPAIGN_TYPES: { value: CampaignType; label: string }[] = [
  { value: "credential_harvest", label: "Credential Harvest" },
  { value: "link_click", label: "Link Click" },
  { value: "attachment", label: "Attachment" },
];

const STEPS = ["Details", "Content & Targets", "Review"];

interface WizardState {
  name: string;
  description: string;
  campaign_type: CampaignType;
  template_id: string;
  page_id: string;
  smtp_id: string;
  training_module_id: string;
  groupIds: Set<string>;
}

export function CampaignWizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [error, setError] = useState<ApiErrorInfo | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [pages, setPages] = useState<Page[]>([]);
  const [smtpProfiles, setSmtpProfiles] = useState<SmtpProfile[]>([]);
  const [groups, setGroups] = useState<TargetGroup[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [trainingModules, setTrainingModules] = useState<TrainingModule[]>([]);

  const [form, setForm] = useState<WizardState>({
    name: "",
    description: "",
    campaign_type: "credential_harvest",
    template_id: "",
    page_id: "",
    smtp_id: "",
    training_module_id: "",
    groupIds: new Set(),
  });

  useEffect(() => {
    Promise.all([
      api.listTemplates(),
      api.listPages(),
      api.listSmtpProfiles(),
      api.listGroups(),
      api.listTargets(),
      api.listTrainingModules(),
    ])
      .then(([t, p, s, g, tg, tm]) => {
        setTemplates(t);
        setPages(p);
        setSmtpProfiles(s);
        setGroups(g);
        setTargets(tg);
        setTrainingModules(tm);
      })
      .catch((err) => setError(describeApiError(err)));
  }, []);

  // Derive the concrete target_ids the API needs from the checked groups.
  const targetIds = useMemo(
    () => targets.filter((t) => form.groupIds.has(t.group_id)).map((t) => t.id),
    [targets, form.groupIds],
  );

  function update<K extends keyof WizardState>(key: K, value: WizardState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function toggleGroup(id: string) {
    setForm((f) => {
      const next = new Set(f.groupIds);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return { ...f, groupIds: next };
    });
  }

  // Single source of truth for what each step still needs. The Next button is
  // gated on this being empty, and the same list is shown to the user so a
  // disabled button always explains itself (e.g. a selected group that has no
  // targets leaves targetIds empty - previously indistinguishable from a bug).
  const missingFields = useMemo<string[]>(() => {
    if (step === 0) {
      return form.name.trim().length > 0 ? [] : ["Campaign name"];
    }
    if (step === 1) {
      const missing: string[] = [];
      if (!form.template_id) missing.push("Email template");
      if (!form.page_id) missing.push("Landing page");
      if (!form.smtp_id) missing.push("SMTP profile");
      if (targetIds.length === 0) missing.push("At least one target group containing targets");
      return missing;
    }
    return [];
  }, [step, form.name, form.template_id, form.page_id, form.smtp_id, targetIds.length]);

  const canAdvance = missingFields.length === 0;

  async function handleLaunch() {
    setError(null);
    setSubmitting(true);
    try {
      const campaign = await api.createCampaign({
        name: form.name,
        template_id: form.template_id,
        page_id: form.page_id,
        smtp_id: form.smtp_id,
        campaign_type: form.campaign_type,
        training_module_id: form.training_module_id || null,
        target_ids: targetIds,
      });
      await api.launchCampaign(campaign.id);
      navigate(`/reports?campaign=${campaign.id}`);
    } catch (err) {
      setError(describeApiError(err));
      setSubmitting(false);
    }
  }

  const inputClass =
    "w-full rounded-md border border-neutral-700 px-3 py-2 text-sm focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500";

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h2 className="text-2xl font-semibold text-neutral-100">New Campaign</h2>

      {/* Step indicator */}
      <ol className="flex items-center gap-2 text-sm">
        {STEPS.map((label, i) => (
          <li key={label} className="flex items-center gap-2">
            <span
              className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold ${
                i <= step ? "bg-green-600 text-white" : "bg-neutral-800 text-neutral-400"
              }`}
            >
              {i + 1}
            </span>
            <span className={i === step ? "font-medium text-neutral-100" : "text-neutral-500"}>{label}</span>
            {i < STEPS.length - 1 && <span className="mx-1 text-neutral-400">/</span>}
          </li>
        ))}
      </ol>

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-red-900 bg-red-950 p-4 shadow-sm"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-red-300">
                {error.status !== null ? `Request failed: HTTP ${error.status}` : "Request failed: network error"}
              </p>
              <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-words rounded bg-red-950/60 p-2 text-xs text-red-300">
                {error.body}
              </pre>
            </div>
            <button
              type="button"
              onClick={() => setError(null)}
              aria-label="Dismiss error"
              className="shrink-0 rounded px-2 py-1 text-xs font-medium text-red-400 hover:bg-red-900 hover:text-red-300"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      <div className="rounded-xl bg-neutral-900 p-6 shadow-sm">
        {step === 0 && (
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-neutral-200">Campaign name</label>
              <input className={inputClass} value={form.name} onChange={(e) => update("name", e.target.value)} required />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-neutral-200">Description</label>
              <textarea
                className={inputClass}
                rows={3}
                value={form.description}
                onChange={(e) => update("description", e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-neutral-200">Type</label>
              <select
                className={inputClass}
                value={form.campaign_type}
                onChange={(e) => update("campaign_type", e.target.value as CampaignType)}
              >
                {CAMPAIGN_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-neutral-200">Email template</label>
              <select className={inputClass} value={form.template_id} onChange={(e) => update("template_id", e.target.value)}>
                <option value="">Select a template</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-neutral-200">Landing page</label>
              <select className={inputClass} value={form.page_id} onChange={(e) => update("page_id", e.target.value)}>
                <option value="">Select a landing page</option>
                {pages.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-neutral-200">SMTP profile</label>
              <select className={inputClass} value={form.smtp_id} onChange={(e) => update("smtp_id", e.target.value)}>
                <option value="">Select an SMTP profile</option>
                {smtpProfiles.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-neutral-200">
                Training module <span className="font-normal text-neutral-500">(optional)</span>
              </label>
              <select
                className={inputClass}
                value={form.training_module_id}
                onChange={(e) => update("training_module_id", e.target.value)}
              >
                <option value="">None</option>
                {trainingModules.map((m) => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
              <p className="mt-1 text-xs text-neutral-400">
                Assigned automatically to targets who submit credentials.
              </p>
            </div>
            <div>
              <span className="mb-1 block text-sm font-medium text-neutral-200">Target groups</span>
              <div className="space-y-2 rounded-md border border-neutral-800 p-3">
                {groups.length === 0 && <p className="text-sm text-neutral-400">No target groups yet.</p>}
                {groups.map((g) => (
                  <label key={g.id} className="flex items-center gap-2 text-sm text-neutral-200">
                    <input
                      type="checkbox"
                      checked={form.groupIds.has(g.id)}
                      onChange={() => toggleGroup(g.id)}
                    />
                    {g.name} <span className="text-neutral-500">({g.target_count})</span>
                  </label>
                ))}
              </div>
              <p className="mt-1 text-xs text-neutral-400">{targetIds.length} target(s) selected</p>
            </div>
          </div>
        )}

        {step === 2 && (
          <dl className="space-y-3 text-sm">
            <Row label="Name" value={form.name} />
            <Row label="Description" value={form.description || "-"} />
            <Row
              label="Type"
              value={CAMPAIGN_TYPES.find((t) => t.value === form.campaign_type)?.label ?? form.campaign_type}
            />
            <Row label="Template" value={templates.find((t) => t.id === form.template_id)?.name ?? "-"} />
            <Row label="Landing page" value={pages.find((p) => p.id === form.page_id)?.name ?? "-"} />
            <Row label="SMTP profile" value={smtpProfiles.find((s) => s.id === form.smtp_id)?.name ?? "-"} />
            <Row
              label="Training module"
              value={trainingModules.find((m) => m.id === form.training_module_id)?.name ?? "None"}
            />
            <Row label="Targets" value={`${targetIds.length} recipient(s)`} />
          </dl>
        )}
      </div>

      <div className="flex items-center justify-between">
        <button
          onClick={() => (step === 0 ? navigate("/campaigns") : setStep((s) => s - 1))}
          className="rounded-md px-4 py-2 text-sm font-medium text-neutral-300 hover:bg-neutral-700"
        >
          {step === 0 ? "Cancel" : "Back"}
        </button>

        {step < 2 ? (
          <div className="flex items-center gap-3">
            {!canAdvance && (
              <p className="text-right text-xs text-amber-400">
                Required before continuing:{" "}
                <span className="font-medium">{missingFields.join(", ")}</span>
              </p>
            )}
            <button
              disabled={!canAdvance}
              title={canAdvance ? undefined : `Missing: ${missingFields.join(", ")}`}
              onClick={() => setStep((s) => s + 1)}
              className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next
            </button>
          </div>
        ) : (
          <button
            disabled={submitting}
            onClick={handleLaunch}
            className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-500 disabled:opacity-50"
          >
            {submitting ? "Launching…" : "Launch Campaign"}
          </button>
        )}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-neutral-800 pb-2">
      <dt className="text-neutral-400">{label}</dt>
      <dd className="font-medium text-neutral-100">{value}</dd>
    </div>
  );
}
