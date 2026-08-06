"use client";

// Piezas reusables entre "Tráfico Web" (frontend/app/(dashboard)/trafico-web/page.tsx)
// y "Fuentes" (frontend/app/(dashboard)/fuentes/page.tsx) — extraídas tal
// cual de trafico-web/page.tsx (sin cambio de comportamiento), para no
// duplicar ~150 líneas entre las dos páginas.

import { startOfWeek, startOfMonth, format } from "date-fns";
import { es } from "date-fns/locale";
import { X, Loader2 } from "lucide-react";
import {
  ConversionDetailRow, WebTrafficDay, WhatsappTrafficDay,
} from "@/lib/types";

export type Granularity = "day" | "week" | "month";

export function shortDate(d: string) {
  const [, m, day] = d.split("-");
  return `${day}/${m}`;
}

export function round1(n: number) { return Math.round(n * 10) / 10; }
export function round2(n: number) { return Math.round(n * 100) / 100; }

export function bucketKey(day: string, granularity: Granularity): { key: string; label: string; sortDate: Date } {
  const date = new Date(day + "T00:00:00");
  if (granularity === "week") {
    const start = startOfWeek(date, { weekStartsOn: 1 }); // semana empieza lunes
    return { key: format(start, "yyyy-MM-dd"), label: format(start, "dd/MM"), sortDate: start };
  }
  if (granularity === "month") {
    const start = startOfMonth(date);
    return { key: format(start, "yyyy-MM"), label: format(start, "MMM yyyy", { locale: es }), sortDate: start };
  }
  return { key: day, label: shortDate(day), sortDate: date };
}

// Campos que se suman al agrupar por semana/mes — todo lo demás (las tasas)
// se recalcula desde estas sumas, nunca promediando los % diarios.
const SUM_FIELDS = [
  "total_sessions", "useful_sessions", "whatsapp_clicks", "went_to_booking",
  "viewed_price", "selected_date", "booking_completed_events",
  "viewed_price_left", "paid", "popup_fills",
] as const;

export interface ChartRow {
  label: string;
  desde: string; hasta: string;
  total_sessions: number; useful_sessions: number;
  whatsapp_clicks: number; went_to_booking: number;
  viewed_price: number; selected_date: number; booking_completed_events: number;
  viewed_price_left: number; paid: number; popup_fills: number;
  conversion_rate: number; found_expensive_rate: number;
  popup_fill_rate: number; whatsapp_click_rate: number; went_to_booking_rate: number;
}

export function groupByGranularity(daily: WebTrafficDay[], granularity: Granularity): ChartRow[] {
  if (granularity === "day") {
    return daily.map((d) => ({ ...d, label: shortDate(d.day), desde: d.day, hasta: d.day }));
  }

  type Sums = { [K in (typeof SUM_FIELDS)[number]]: number };
  const buckets = new Map<string, { label: string; sortDate: Date; minDay: string; maxDay: string; sums: Sums }>();
  for (const d of daily) {
    const { key, label, sortDate } = bucketKey(d.day, granularity);
    let bucket = buckets.get(key);
    if (!bucket) {
      const zeroed = Object.fromEntries(SUM_FIELDS.map((f) => [f, 0])) as Sums;
      bucket = { label, sortDate, minDay: d.day, maxDay: d.day, sums: zeroed };
      buckets.set(key, bucket);
    }
    if (d.day < bucket.minDay) bucket.minDay = d.day;
    if (d.day > bucket.maxDay) bucket.maxDay = d.day;
    for (const f of SUM_FIELDS) bucket.sums[f] += d[f];
  }

  return Array.from(buckets.values())
    .sort((a, b) => a.sortDate.getTime() - b.sortDate.getTime())
    .map(({ label, minDay, maxDay, sums: s }) => ({
      label,
      desde: minDay,
      hasta: maxDay,
      ...s,
      conversion_rate: s.useful_sessions ? round2((s.paid / s.useful_sessions) * 100) : 0,
      found_expensive_rate: s.viewed_price ? round1((s.viewed_price_left / s.viewed_price) * 100) : 0,
      popup_fill_rate: s.total_sessions ? round1((s.popup_fills / s.total_sessions) * 100) : 0,
      whatsapp_click_rate: s.total_sessions ? round1((s.whatsapp_clicks / s.total_sessions) * 100) : 0,
      went_to_booking_rate: s.total_sessions ? round1((s.went_to_booking / s.total_sessions) * 100) : 0,
    }));
}

// Mismo tratamiento que arriba, para las conversaciones de WhatsApp.
const SUM_FIELDS_WA = [
  "total_conversations", "useful_conversations", "asked_price", "found_expensive",
  "asked_date", "clicked_link", "reserved", "paid",
] as const;

export interface ChartRowWA {
  label: string;
  desde: string; hasta: string;
  total_conversations: number; useful_conversations: number;
  asked_price: number; found_expensive: number; asked_date: number;
  clicked_link: number; reserved: number; paid: number;
  conversion_rate: number; found_expensive_rate: number;
}

export function groupByGranularityWA(daily: WhatsappTrafficDay[], granularity: Granularity): ChartRowWA[] {
  if (granularity === "day") {
    return daily.map((d) => ({ ...d, label: shortDate(d.day), desde: d.day, hasta: d.day }));
  }

  type Sums = { [K in (typeof SUM_FIELDS_WA)[number]]: number };
  const buckets = new Map<string, { label: string; sortDate: Date; minDay: string; maxDay: string; sums: Sums }>();
  for (const d of daily) {
    const { key, label, sortDate } = bucketKey(d.day, granularity);
    let bucket = buckets.get(key);
    if (!bucket) {
      const zeroed = Object.fromEntries(SUM_FIELDS_WA.map((f) => [f, 0])) as Sums;
      bucket = { label, sortDate, minDay: d.day, maxDay: d.day, sums: zeroed };
      buckets.set(key, bucket);
    }
    if (d.day < bucket.minDay) bucket.minDay = d.day;
    if (d.day > bucket.maxDay) bucket.maxDay = d.day;
    for (const f of SUM_FIELDS_WA) bucket.sums[f] += d[f];
  }

  return Array.from(buckets.values())
    .sort((a, b) => a.sortDate.getTime() - b.sortDate.getTime())
    .map(({ label, minDay, maxDay, sums: s }) => ({
      label,
      desde: minDay,
      hasta: maxDay,
      ...s,
      conversion_rate: s.useful_conversations ? round2((s.paid / s.useful_conversations) * 100) : 0,
      found_expensive_rate: s.asked_price ? round1((s.found_expensive / s.asked_price) * 100) : 0,
    }));
}

// Siempre 2 decimales en estas tarjetas (a diferencia de los otros % del
// dashboard) — un valor como 1.00 o 0.40 no debe perder el cero final.
export function pct2(n: number | undefined) { return (n ?? 0).toFixed(2); }

export function StatCard({ label, value, sub, def, onClick }: { label: string; value: string; sub?: string; def?: string; onClick?: () => void }) {
  const clickable = !!onClick;
  return (
    <div
      onClick={onClick}
      className={`bg-white border border-gray-200 rounded-xl px-4 py-3 ${clickable ? "cursor-pointer hover:border-brand-400 hover:shadow-sm transition-all" : ""}`}
      title={clickable ? "Ver quiénes son" : undefined}
    >
      <p className="text-xs text-gray-400 uppercase tracking-wide mb-1 flex items-center gap-1">
        {label}
        {clickable && <span className="text-brand-500 normal-case font-normal">· ver lista</span>}
      </p>
      <p className="text-2xl font-bold text-gray-900 tabular-nums">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      {def && <p className="text-[11px] text-gray-400 italic mt-1 leading-snug">{def}</p>}
    </div>
  );
}

// Punto invisible pero clickeable sobre cada dato de la línea de conversión —
// más confiable que el onClick del propio <LineChart> (en Recharts 3 no
// dispara de forma consistente), y usa las coordenadas reales que Recharts
// ya calculó para cada punto en vez de intentar adivinar la posición del click.
export function makeClickableDot<T extends { desde: string; hasta: string; label: string }>(
  onPick: (row: T) => void
) {
  return (props: any) => {
    const { cx, cy, payload, index } = props;
    if (cx == null || cy == null) return null;
    return (
      <circle
        key={`dot-${index}`}
        cx={cx}
        cy={cy}
        r={9}
        fill="transparent"
        style={{ cursor: "pointer" }}
        onClick={() => onPick(payload as T)}
      />
    );
  };
}

export const FLUJO_LABEL: Record<string, { text: string; color: string }> = {
  flujo_2: { text: "Flujo 2 · Solo web", color: "bg-gray-50 text-gray-600" },
  flujo_3: { text: "Flujo 3 · Web → WhatsApp", color: "bg-blue-50 text-blue-700" },
};

export function money(n: number | null) {
  return n != null ? `$${Math.round(n).toLocaleString("es-CL")}` : "—";
}

export function fmtDateTime(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es-CL", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function ConversionsModal({
  title,
  onClose,
  rows,
  isLoading,
}: {
  title: string;
  onClose: () => void;
  rows: ConversionDetailRow[];
  isLoading: boolean;
}) {
  // El campo "flujo" solo viene en la lista de Web (flujo_2/flujo_3) — la
  // de WhatsApp ya no lo manda, porque solo incluye flujo_1 (ver
  // ConversionDetailRow.flujo). Mostrar la columna según qué trajo el
  // backend, no según qué pestaña está activa.
  const hasFlujo = rows.some((r) => r.flujo);

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-start justify-center p-6 overflow-y-auto" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-4xl mt-10 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div>
            <p className="text-sm font-semibold text-gray-800">{title}</p>
            <p className="text-xs text-gray-400 mt-0.5">{rows.length} reserva{rows.length !== 1 ? "s" : ""} pagada{rows.length !== 1 ? "s" : ""}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 p-1">
            <X size={18} />
          </button>
        </div>

        {hasFlujo && rows.length > 0 && (
          <div className="px-5 py-2.5 bg-blue-50/60 border-b border-blue-100 text-xs text-blue-800">
            <strong>Flujo 3</strong> = tenía una sesión web orgánica (no llegó por un link del bot de WhatsApp) <em>antes</em> de su primer mensaje de WhatsApp — se cuenta como venta web porque la web fue la entrada real. <strong>Flujo 2</strong> = nunca escribió por WhatsApp.
          </div>
        )}

        <div className="overflow-x-auto max-h-[60vh] overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-16 text-gray-400 gap-2">
              <Loader2 size={18} className="animate-spin" /> Cargando…
            </div>
          ) : rows.length === 0 ? (
            <div className="py-16 text-center text-gray-400 text-sm">Sin reservas pagadas en este rango.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-gray-50">
                <tr className="border-b border-gray-100">
                  <th className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Cliente</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Contacto</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Reserva</th>
                  <th className="px-4 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Monto</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Reservó</th>
                  {hasFlujo && <th className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Flujo</th>}
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.booking_ref} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="px-4 py-2.5 text-gray-800 font-medium">{r.name || "—"}</td>
                    <td className="px-4 py-2.5 text-gray-500 text-xs">
                      {r.phone && <div>{r.phone}</div>}
                      {r.email && <div className="text-gray-400">{r.email}</div>}
                    </td>
                    <td className="px-4 py-2.5 text-gray-500 text-xs">
                      <div className="font-mono">{r.booking_ref}</div>
                      <div className="text-gray-400">{r.servicio} {r.fecha ? `· ${r.fecha}` : ""}</div>
                    </td>
                    <td className="px-4 py-2.5 text-right text-gray-800 tabular-nums">{money(r.monto)}</td>
                    <td className="px-4 py-2.5 text-gray-500 text-xs whitespace-nowrap">{fmtDateTime(r.created_at)}</td>
                    {hasFlujo && (
                      <td className="px-4 py-2.5">
                        {r.flujo && (
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium whitespace-nowrap ${FLUJO_LABEL[r.flujo]?.color ?? "bg-gray-100 text-gray-600"}`}>
                            {FLUJO_LABEL[r.flujo]?.text ?? r.flujo}
                          </span>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

export function ChartCard({ title, sub, children }: { title: string; sub?: string; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <p className="text-sm font-semibold text-gray-800">{title}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5 mb-2">{sub}</p>}
      <div className="h-64 mt-2">{children}</div>
    </div>
  );
}

export const tooltipStyle = { fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb" };
