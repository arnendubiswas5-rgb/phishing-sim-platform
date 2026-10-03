import axios, { AxiosError, type AxiosInstance } from "axios";
import type {
  AppSettings,
  Campaign,
  CampaignCreatePayload,
  CampaignReport,
  DepartmentBreakdown,
  EmailTemplate,
  Page,
  PageCreatePayload,
  PagePreview,
  PageUpdatePayload,
  PurgeResult,
  SmtpProfile,
  SmtpProfileCreatePayload,
  Target,
  TargetGroup,
  TargetImportResult,
  TemplatePreview,
  TimelinePoint,
  TrainingModule,
  User,
} from "../types";

const TOKEN_KEY = "phishsim_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export const http: AxiosInstance = axios.create({
  baseURL: "/api/v1",
});

export interface ApiErrorInfo {
  /** HTTP status code, or null for network/timeout errors with no response. */
  status: number | null;
  /** The response body, rendered as text (FastAPI's `detail` unwrapped; other
   *  JSON pretty-printed; strings passed through). */
  body: string;
  /** Combined, human-readable one-liner, e.g. "HTTP 422: ...". */
  message: string;
}

/** Normalizes any thrown error (Axios or otherwise) into a status + response
 *  body so callers can surface exactly what the backend returned instead of a
 *  generic "Request failed with status code 422". */
export function describeApiError(err: unknown): ApiErrorInfo {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status ?? null;
    const data = err.response?.data;
    let body: string;
    if (data == null) {
      body = err.message; // no response body (network error, timeout, CORS)
    } else if (typeof data === "string") {
      body = data;
    } else if (typeof data === "object" && "detail" in data) {
      const detail = (data as { detail: unknown }).detail;
      body = typeof detail === "string" ? detail : JSON.stringify(detail, null, 2);
    } else {
      body = JSON.stringify(data, null, 2);
    }
    const statusText = status !== null ? `HTTP ${status}` : "Network error";
    return { status, body, message: `${statusText}: ${body}` };
  }
  const message = err instanceof Error ? err.message : String(err);
  return { status: null, body: message, message };
}

// Attach the JWT from localStorage to every outgoing request.
http.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

// On 401, drop the stale token and bounce to the login screen.
http.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      clearToken();
      if (window.location.pathname !== "/login") {
        window.location.assign("/login");
      }
    }
    return Promise.reject(error);
  },
);

export const api = {
  login: async (email: string, password: string) => {
    // FastAPI's OAuth2 password flow expects form-encoded credentials.
    const form = new URLSearchParams({ username: email, password });
    const { data } = await http.post<{ access_token: string; token_type: string }>(
      "/auth/login",
      form,
    );
    return data;
  },
  register: async (email: string, password: string, full_name: string) => {
    const { data } = await http.post<User>("/auth/register", { email, password, full_name });
    return data;
  },
  me: async () => (await http.get<User>("/auth/me")).data,

  // Targets & groups
  listTargets: async () => (await http.get<Target[]>("/targets")).data,
  listGroups: async () => (await http.get<TargetGroup[]>("/targets/groups")).data,
  importTargets: async (file: File, groupName?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (groupName) form.append("group_name", groupName);
    return (await http.post<TargetImportResult>("/targets/import", form)).data;
  },

  // Templates
  listTemplates: async () => (await http.get<EmailTemplate[]>("/templates")).data,
  createTemplate: async (payload: Record<string, unknown>) =>
    (await http.post<EmailTemplate>("/templates", payload)).data,
  previewTemplate: async (id: string) =>
    (await http.post<TemplatePreview>(`/templates/${id}/preview`)).data,

  // Landing pages & SMTP profiles
  listPages: async () => (await http.get<Page[]>("/pages")).data,
  getPage: async (id: string) => (await http.get<Page>(`/pages/${id}`)).data,
  createPage: async (payload: PageCreatePayload) => (await http.post<Page>("/pages", payload)).data,
  updatePage: async (id: string, payload: PageUpdatePayload) =>
    (await http.put<Page>(`/pages/${id}`, payload)).data,
  previewPage: async (id: string) => (await http.post<PagePreview>(`/pages/${id}/preview`)).data,
  listSmtpProfiles: async () => (await http.get<SmtpProfile[]>("/smtp")).data,
  createSmtpProfile: async (payload: SmtpProfileCreatePayload) =>
    (await http.post<SmtpProfile>("/smtp", payload)).data,

  // Campaigns
  listCampaigns: async () => (await http.get<Campaign[]>("/campaigns")).data,
  getCampaign: async (id: string) => (await http.get<Campaign>(`/campaigns/${id}`)).data,
  createCampaign: async (payload: CampaignCreatePayload) =>
    (await http.post<Campaign>("/campaigns", payload)).data,
  launchCampaign: async (id: string) =>
    (await http.post<Campaign>(`/campaigns/${id}/launch`)).data,
  pauseCampaign: async (id: string) =>
    (await http.post<Campaign>(`/campaigns/${id}/pause`)).data,

  // Reports
  campaignReport: async (id: string) =>
    (await http.get<CampaignReport>(`/reports/campaign/${id}`)).data,
  campaignTimeline: async (id: string) =>
    (await http.get<TimelinePoint[]>(`/reports/campaign/${id}/timeline`)).data,
  campaignDepartments: async (id: string) =>
    (await http.get<DepartmentBreakdown[]>(`/reports/campaign/${id}/departments`)).data,

  // Training modules
  listTrainingModules: async () =>
    (await http.get<TrainingModule[]>("/training-modules")).data,

  // Admin settings
  getSettings: async () => (await http.get<AppSettings>("/settings")).data,
  updateSettings: async (retention_days: number) =>
    (await http.put<AppSettings>("/settings", { retention_days })).data,
  purgeNow: async () => (await http.post<PurgeResult>("/settings/purge")).data,
};
