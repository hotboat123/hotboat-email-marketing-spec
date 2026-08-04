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
  ad_source: string | null;
  utm_campaign: string | null;
  utm_medium: string | null;
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
  ultima_reserva_hotboat: UltimaReservaHotboat | null;
  created_at: string;
  updated_at: string;
}

export interface UltimaReservaHotboat {
  booking_ref: string;
  fecha: string | null;
  hora: string | null;
  servicio: string | null;
  num_personas: string | null;
  observaciones: string | null;
  extras: Record<string, { qty: number; unit_price: number }>;
  ingreso_total: number | null;
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
  require_name: boolean;
  require_phone: boolean;
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

export type AutomationTrigger = "abandoned_booking" | "welcome" | "post_visit" | "reactivation" | "birthday";
export type AutomationStatus = "active" | "paused";

export interface Automation {
  id: number;
  name: string;
  trigger_type: AutomationTrigger;
  trigger_config: Record<string, number> | null;
  template_id: number;
  subject: string;
  status: AutomationStatus;
  bcc_admin: boolean;
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
  delivered_at: string | null;
  opened_at: string | null;
  clicked_at: string | null;
  bounced_at: string | null;
}

export interface AutomationStats {
  total: number;
  sent: number;
  failed: number;
  last_run: string | null;
  delivered: number;
  opened: number;
  clicked: number;
  bounced: number;
  open_rate: number;
  click_rate: number;
}

export interface AutomationConversions {
  automation_id: number;
  window_days: number;
  bookings: number;
  revenue: number;
  converted_contacts: number;
}

export type SentEmailOrigin = "campaign" | "automation" | "other";

export interface SentEmail {
  id: number;
  source_type: SentEmailOrigin;
  source_name: string;
  email: string;
  at: string | null;
  subject: string;
  status: string;
  provider: "ses" | "resend";
}

export interface SentEmailDetail {
  subject: string;
  html: string | null;
  available: boolean;
}

export interface SentEmailsPage {
  items: SentEmail[];
  total: number;
  ses_count: number;
  resend_count: number;
}

export interface WebTrafficDay {
  day: string;
  total_sessions: number;
  useful_sessions: number;
  whatsapp_clicks: number;
  went_to_booking: number;
  viewed_price: number;
  selected_date: number;
  booking_completed_events: number;
  viewed_price_left: number;
  paid: number;
  popup_fills: number;
  conversion_rate: number;
  found_expensive_rate: number;
  popup_fill_rate: number;
  whatsapp_click_rate: number;
  went_to_booking_rate: number;
}

export interface WebTrafficTotals {
  total_sessions: number;
  useful_sessions: number;
  bounce_rate: number;
  popup_fills: number;
  popup_fill_rate: number;
  whatsapp_clicks: number;
  whatsapp_click_rate: number;
  went_to_booking: number;
  went_to_booking_rate: number;
  viewed_price: number;
  viewed_price_rate: number;
  viewed_price_left: number;
  found_expensive_rate: number;
  selected_date: number;
  selected_date_rate: number;
  booking_completed_events: number;
  reserved_rate: number;
  paid: number;
  conversion_rate: number;
}

export interface WebTrafficResponse {
  desde: string;
  hasta: string;
  daily: WebTrafficDay[];
  totals: WebTrafficTotals;
}

export interface DurationBucket {
  label: string;
  n: number;
  n_useful: number;
  pct: number;
}

export interface WebTrafficDurationHistogram {
  desde: string;
  hasta: string;
  total_sessions: number;
  buckets: DurationBucket[];
}

export interface WhatsappTrafficDay {
  day: string;
  total_conversations: number;
  useful_conversations: number;
  asked_price: number;
  found_expensive: number;
  asked_date: number;
  clicked_link: number;
  reserved: number;
  paid: number;
  conversion_rate: number;
  found_expensive_rate: number;
}

export interface WhatsappTrafficTotals {
  total_conversations: number;
  useful_conversations: number;
  discard_rate: number;
  asked_price: number;
  asked_price_rate: number;
  found_expensive: number;
  found_expensive_rate: number;
  asked_date: number;
  asked_date_rate: number;
  clicked_link: number;
  clicked_link_rate: number;
  reserved: number;
  reserved_rate: number;
  paid: number;
  conversion_rate: number;
}

export interface WhatsappTrafficResponse {
  desde: string;
  hasta: string;
  daily: WhatsappTrafficDay[];
  totals: WhatsappTrafficTotals;
}

export interface ConversionDetailRow {
  booking_ref: string;
  name: string | null;
  email: string | null;
  phone: string | null;
  servicio: string | null;
  fecha: string | null;
  hora: string | null;
  monto: number | null;
  created_at: string | null; // cuándo se creó la reserva — no cuándo se pagó
  // Solo en la lista de Web: flujo_2 = nunca escribió por WhatsApp, flujo_3 =
  // sí, pero después de una sesión web (por eso se cuenta acá y no en WhatsApp).
  flujo?: "flujo_2" | "flujo_3";
}

// Ya no trae "flujo" — la lista de WhatsApp solo incluye flujo_1 (WhatsApp
// puro); los flujo_3 se mudaron a la lista de Web, ver ConversionDetailRow.
export type WhatsappConversionDetailRow = ConversionDetailRow;

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
  platform: string | null;
  lead_status: string | null;
  last_interaction_at: string | null;
  veces_hotboat: number;
  ultima_visita: string | null;
  ticket_medio: number | null;
  extras_favoritos: string[] | null;
  reservation_score: number | null;
  score_updated_at: string | null;
  score_breakdown: Record<string, number> | null;
  call_status: CallStatus | "anonymous";
  call_status_updated_at: string | null;
  link_clicked: boolean;
  link_viewed_prices: boolean;
  link_selected_date: boolean;
  link_last_seen_at: string | null;
  web_classification: string | null;
  web_classification_desc: string | null;
  web_last_seen_at: string | null;
  web_session_count: number | null;
  referral_count: number;
  created_at: string;
  updated_at: string;
  is_anonymous: boolean;
  session_id: string | null;
}

export interface AnonymousVisitEvent {
  event: string;
  date: string | null;
  time: string | null;
}

export interface AnonymousVisit {
  session_id: string;
  classification: string | null;
  classification_desc: string | null;
  referrer: string | null;
  is_returning: boolean;
  started_at: string;
  ended_at: string | null;
  events: AnonymousVisitEvent[];
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
  bookings: number;
  cost_per_booking: number | null;
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

export interface AdBooking {
  id: number;
  name: string | null;
  phone: string | null;
  email: string | null;
  amount: number | null;
  trip_date: string | null;
  conversion_date: string | null;
  ad_source: string | null;
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

export interface FunnelByVariant extends FunnelRow {
  variant_key: string;
  label: string;
}

export interface FunnelAnalytics {
  by_ad_source: FunnelByAdSource[];
  by_channel: FunnelByChannel[];
  by_bot_variant: FunnelByVariant[];
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
