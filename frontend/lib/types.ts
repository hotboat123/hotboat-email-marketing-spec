export interface User {
  id: number;
  email: string;
  name: string;
  role: "admin" | "editor" | "viewer";
  created_at: string;
}

export interface Contact {
  id: number;
  email: string;
  name: string | null;
  phone: string | null;
  language: string | null;
  origin_utm: string | null;
  opted_in: boolean;
  opted_in_at: string | null;
  opted_out_at: string | null;
  veces_hotboat: number;
  ultima_visita: string | null;
  ha_alojamiento: boolean;
  extras_favoritos: string[] | null;
  ticket_medio: number | null;
  created_at: string;
  updated_at: string;
}

export interface SegmentRule {
  field: string;
  op: string;
  value: unknown;
}

export interface SegmentConditions {
  operator: "AND" | "OR";
  rules: (SegmentRule | SegmentConditions)[];
}

export interface Segment {
  id: number;
  name: string;
  description: string | null;
  conditions: SegmentConditions | null;
  contact_count: number | null;
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface Template {
  id: number;
  name: string;
  subject_default: string;
  preview_text: string | null;
  html_content: string;
  json_blocks: Record<string, unknown> | null;
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

export type CampaignStatus = "draft" | "scheduled" | "sending" | "sent" | "cancelled";

export interface Campaign {
  id: number;
  name: string;
  subject: string;
  preview_text: string | null;
  template_id: number;
  segment_id: number;
  status: CampaignStatus;
  scheduled_at: string | null;
  sent_at: string | null;
  created_by: number | null;
  created_at: string;
}

export interface CampaignStats {
  campaign_id: number;
  total: number;
  sent: number;
  delivered: number;
  opened: number;
  clicked: number;
  bounced: number;
  complained: number;
  open_rate: number;
  click_rate: number;
  bounce_rate: number;
}

export type AutomationTrigger = "abandoned_booking" | "welcome" | "post_visit" | "reactivation";
export type AutomationStatus = "active" | "paused";

export interface Automation {
  id: number;
  name: string;
  trigger_type: AutomationTrigger;
  trigger_config: Record<string, number> | null;
  template_id: number;
  subject: string;
  status: AutomationStatus;
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface AutomationRun {
  id: number;
  automation_id: number;
  contact_id: number | null;
  contact_email: string;
  trigger_key: string;
  status: "sent" | "failed" | "skipped";
  triggered_at: string;
  executed_at: string | null;
  resend_id: string | null;
  error: string | null;
}

export interface AutomationStats {
  total: number;
  sent: number;
  failed: number;
  last_run: string | null;
}

export interface OverviewStats {
  contacts: { total: number; opted_in: number };
  campaigns: { total: number; sent: number };
  sends: { total: number; delivered: number; opened: number; open_rate: number };
  segments: number;
  templates: number;
}
