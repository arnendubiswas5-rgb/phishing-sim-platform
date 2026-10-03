export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "manager" | "operator" | "viewer";
  is_active: boolean;
}

export interface Target {
  id: string;
  group_id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  department: string | null;
  position: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TargetGroup {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  target_count: number;
}

export interface TargetImportResult {
  group_id: string;
  group_name: string;
  inserted: number;
  skipped_duplicates: number;
  skipped_invalid: number;
}

export interface EmailTemplate {
  id: string;
  tenant_id: string;
  name: string;
  subject: string;
  html_body: string;
  text_body: string | null;
  sender_name: string;
  sender_email: string;
  created_at: string;
}

export interface TemplatePreview {
  subject: string;
  html_body: string;
  text_body: string | null;
}

export type PageType = "credential" | "education" | "redirect";

export interface Page {
  id: string;
  tenant_id: string;
  name: string;
  page_type: PageType;
  capture_credentials: boolean;
  redirect_url: string | null;
  logo_url: string | null;
  html_content: string;
  created_at: string;
}

export interface PageCreatePayload {
  name: string;
  page_type: PageType;
  html_content: string;
  logo_url?: string | null;
  redirect_url?: string | null;
}

export type PageUpdatePayload = Partial<PageCreatePayload>;

export interface PagePreview {
  html: string;
}

export interface SmtpProfile {
  id: string;
  tenant_id: string;
  name: string;
  host: string;
  port: number;
  username: string | null;
  use_tls: boolean;
  from_name: string;
  from_email: string;
  created_at: string;
}

export interface SmtpProfileCreatePayload {
  name: string;
  host: string;
  port: number;
  username?: string | null;
  password?: string | null;
  use_tls: boolean;
  from_name: string;
  from_email: string;
}

export type CampaignStatus =
  | "draft"
  | "scheduled"
  | "running"
  | "paused"
  | "completed"
  | "cancelled";

export type CampaignType = "credential_harvest" | "link_click" | "attachment";

export interface Campaign {
  id: string;
  tenant_id: string;
  name: string;
  template_id: string;
  page_id: string;
  smtp_profile_id: string;
  training_module_id: string | null;
  campaign_type: CampaignType;
  status: CampaignStatus;
  launch_at: string | null;
  created_by: string;
  created_at: string;
}

export interface CampaignCreatePayload {
  name: string;
  template_id: string;
  page_id: string;
  smtp_id: string;
  campaign_type: CampaignType;
  training_module_id?: string | null;
  target_ids: string[];
}

export interface TrainingModule {
  id: string;
  tenant_id: string;
  name: string;
  content: string;
  quiz: { question: string; options: string[]; answer: number }[];
  pass_threshold: number;
  created_at: string;
}

export interface AppSettings {
  retention_days: number;
}

export interface PurgeResult {
  purged_campaigns: number;
}

export interface CampaignReport {
  campaign_id: string;
  total_targets: number;
  emails_sent: number;
  unique_opens: number;
  unique_clicks: number;
  unique_submissions: number;
  report_rate: number;
}

export interface TimelinePoint {
  day: string;
  opened: number;
  clicked: number;
  submitted: number;
}

export interface DepartmentBreakdown {
  department: string;
  total_targets: number;
  opened: number;
  clicked: number;
  submitted: number;
}
