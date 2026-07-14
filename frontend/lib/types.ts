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
  location: string | null;
  opted_in: boolean;
  opted_in_at: string | null;
  opted_out_at: string | null;
  veces_hotboat: number;
  ultima_visita: string | null;
  ha_alojamiento: boolean;
  extras_favoritos: string[] | null;
  ticket_medio: number | null;
  birthday: string | null;
  notes: string | null;
  custom_fields: Record<string, string> | null;
  created_at: string;
  updated_at: string;
}

export interface ContactBooking {
  fecha: string;
  status: string;
  ingreso_total: number | null;
  como_supieron: string | null;
  extras: Record<string, unknown>;
}

export interface ContactEmailEvent {
  type: "sent" | "delivered" | "opened" | "clicked" | "bounced";
  campaign_id: number;
  campaign_name: string;
  timestamp: string;
}

export interface CampaignEmailSend {
  campaign_id: number;
  campaign_name: string;
  status: string;
  sent_at: string | null;
  delivered_at: string | null;
  opened_at: string | null;
  clicked_at: string | null;
  bounced_at: string | null;
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

export interface CampaignConversions {
  campaign_id: number;
  window_days: number;
  bookings: number;
  revenue: number;
  converted_contacts: number;
}

export type FormTrigger = "delay" | "exit_intent" | "scroll";

export interface FormField {
  key: string;
  label: string;
  type: "text" | "email" | "tel" | "date" | "number" | "textarea" | "select";
  required: boolean;
  placeholder?: string;
  options?: string[];
}

export interface SignupForm {
  id: number;
  name: string;
  title: string;
  description: string | null;
  button_text: string;
  success_message: string;
  collect_name: boolean;
  collect_phone: boolean;
  popup_trigger: FormTrigger;
  popup_delay_seconds: number;
  popup_scroll_pct: number;
  custom_form_fields: FormField[] | null;
  html_override: string | null;
  coupon_code: string | null;
  status: "active" | "paused";
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface FormSubmission {
  id: number;
  form_id: number;
  email: string;
  name: string | null;
  phone: string | null;
  source_url: string | null;
  extra_data: Record<string, string> | null;
  created_at: string;
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

export interface BrandAsset {
  id: number;
  categoria: string;
  nombre: string;
  valor: string;
  descripcion: string | null;
  created_at: string;
  updated_at: string;
}

export type CallStatus = "pending" | "called" | "no_answer" | "booked" | "not_interested";

export interface ContactCRM {
  id: number;
  phone: string | null;
  email: string | null;
  name: string | null;
  linked_contact_id: number | null;
  ad_source: string | null;
  ad_platform: string | null;
  ad_creative_url: string | null;
  utm_campaign: string | null;
  lead_status: string | null;
  last_interaction_at: string | null;
  veces_hotboat: number;
  ultima_visita: string | null;
  ticket_medio: number | null;
  extras_favoritos: string[] | null;
  reservation_score: number | null;
  score_updated_at: string | null;
  score_breakdown: Record<string, number> | null;
  call_status: CallStatus;
  call_status_updated_at: string | null;
  link_clicked: boolean;
  link_viewed_prices: boolean;
  link_selected_date: boolean;
  link_last_seen_at: string | null;
  web_classification: string | null;
  web_classification_desc: string | null;
  web_last_seen_at: string | null;
  web_session_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface CallActivity {
  id: number;
  contact_crm_id: number;
  old_status: string | null;
  new_status: string;
  note: string | null;
  created_by: string | null;
  created_at: string;
}

export interface CrmConversationMessage {
  message_text: string | null;
  response_text: string | null;
  message_type: string | null;
  direction: "incoming" | "outgoing";
  created_at: string | null;
}

export interface CrmWebActivityEvent {
  event_type: string;
  extra_date: string | null;
  time_label: string | null;
  recorded_at: string | null;
  session_id: string | null;
}

export interface FunnelRow {
  total: number;
  viewed_prices: number;
  selected_date: number;
  pending_payment: number;
  paid: number;
  conversion_rate: number;
}

export interface FunnelByAdSource extends FunnelRow {
  ad_source: string;
  ad_id: string | null;
  spend: number | null;
  cpc: number | null;
  cost_per_conversation: number | null;
}

export type AdLevel = "ad" | "adset" | "campaign";

export interface AdSummary {
  id: string;
  name: string;
  status: string | null;
  campaign_name: string | null;
  adset_name: string | null;
  spend: number;
  clicks: number;
  cpc: number | null;
  conversations_started: number;
  cost_per_conversation: number | null;
  first_date: string | null;
  last_date: string | null;
}

export interface AdTimeseriesPoint {
  date: string;
  spend: number;
  clicks: number;
  cpc: number | null;
  conversations_started: number;
  cost_per_conversation: number | null;
}

export interface AdBookingDay {
  date: string;
  count: number;
}

export interface AdTimeseries {
  id: string;
  name: string;
  points: AdTimeseriesPoint[];
  bookings: AdBookingDay[];
}

export interface FunnelByChannel extends FunnelRow {
  channel: string;
}

export interface FunnelAnalytics {
  by_ad_source: FunnelByAdSource[];
  by_channel: FunnelByChannel[];
}

export interface ScoreWeight {
  key: string;
  label: string;
  points: number;
  updated_at: string;
}

export interface SubjectAnalytics {
  campaign_id: number;
  subject: string;
  campaign_name: string;
  sent_at: string;
  sent_count: number;
  open_rate: number;
  click_rate: number;
}
