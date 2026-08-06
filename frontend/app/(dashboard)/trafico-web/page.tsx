"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { webTrafficApi } from "@/lib/api";
import {
  WebTrafficResponse, WebTrafficDurationHistogram, WhatsappTrafficResponse,
  ConversionDetailRow, WhatsappConversionDetailRow,
} from "@/lib/types";
import {
  Granularity, ChartRow, ChartRowWA, StatCard, ChartCard, ConversionsModal,
  makeClickableDot, pct2, tooltipStyle, groupByGranularity, groupByGranularityWA,
} from "@/components/analytics/traffic-shared";

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgoISO(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

function DurationHistogram({ histogram }: { histogram?: WebTrafficDurationHistogram }) {
  const buckets = histogram?.buckets ?? [];
  const maxN = Math.max(1, ...buckets.map((b) => b.n));

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <p className="text-sm font-semibold text-gray-800">Distribución del tiempo en el sitio</p>
      <p className="text-xs text-gray-400 mt-0.5 mb-1">
        Cuántas sesiones duran cuánto — no varía por día/semana/mes, es del rango de fechas elegido arriba
      </p>
      <div className="flex items-center gap-4 text-xs text-gray-500 mb-4">
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-brand-600 inline-block" />Útil (&gt;5s)</span>
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-orange-400 inline-block" />Rebote (≤5s)</span>
      </div>

      <div className="flex items-end gap-2 h-52 border-b border-gray-100">
        {buckets.map((b) => {
          const heightPct = (b.n / maxN) * 100;
          const usefulPct = b.n ? (b.n_useful / b.n) * 100 : 0;
          return (
            <div key={b.label} className="flex-1 flex flex-col items-center justify-end h-full group relative">
              <div className="absolute -top-9 opacity-0 group-hover:opacity-100 transition-opacity bg-gray-900 text-white text-[11px] rounded px-2 py-1 whitespace-nowrap z-10 tabular-nums">
                {b.n.toLocaleString("es-CL")} ({b.pct}%) · {b.n_useful.toLocaleString("es-CL")} útiles
              </div>
              <span className="text-[10px] text-gray-400 mb-1 tabular-nums">{b.pct}%</span>
              <div
                className="w-full max-w-[38px] rounded-t-sm overflow-hidden flex flex-col-reverse"
                style={{ height: `${heightPct}%`, minHeight: b.n ? 2 : 0 }}
              >
                <div className="w-full bg-orange-400" style={{ height: `${100 - usefulPct}%` }} />
                <div className="w-full bg-brand-600" style={{ height: `${usefulPct}%` }} />
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex gap-2 mt-1.5">
        {buckets.map((b) => (
          <span key={b.label} className="flex-1 text-center text-[10px] text-gray-400">{b.label}</span>
        ))}
      </div>
    </div>
  );
}

type RangePreset = "7" | "30" | "todo" | "custom";
type Source = "web" | "whatsapp";

export default function TraficoWebPage() {
  const [source, setSource] = useState<Source>("web");
  const [preset, setPreset] = useState<RangePreset>("30");
  const [desde, setDesde] = useState(daysAgoISO(30));
  const [hasta, setHasta] = useState(todayISO());
  const [granularity, setGranularity] = useState<Granularity>("day");

  function applyPreset(p: RangePreset) {
    setPreset(p);
    if (p === "7") { setDesde(daysAgoISO(7)); setHasta(todayISO()); }
    else if (p === "30") { setDesde(daysAgoISO(30)); setHasta(todayISO()); }
    else if (p === "todo") { setDesde(daysAgoISO(365)); setHasta(todayISO()); }
  }

  const { data, isLoading } = useQuery<WebTrafficResponse>({
    queryKey: ["web-traffic-daily", desde, hasta],
    queryFn: () => webTrafficApi.daily(desde, hasta).then((r) => r.data),
    staleTime: 2 * 60_000,
    enabled: source === "web",
  });

  const { data: histogram } = useQuery<WebTrafficDurationHistogram>({
    queryKey: ["web-traffic-duration-histogram", desde, hasta],
    queryFn: () => webTrafficApi.durationHistogram(desde, hasta).then((r) => r.data),
    staleTime: 2 * 60_000,
    enabled: source === "web",
  });

  const { data: waData, isLoading: waLoading } = useQuery<WhatsappTrafficResponse>({
    queryKey: ["whatsapp-traffic-daily", desde, hasta],
    queryFn: () => webTrafficApi.whatsappDaily(desde, hasta).then((r) => r.data),
    staleTime: 2 * 60_000,
    enabled: source === "whatsapp",
  });

  // null = modal cerrado. dayLabel presente = se hizo click en un punto del gráfico
  // (un día/semana/mes puntual) en vez de en la tarjeta de resumen (todo el rango elegido arriba).
  // cohortFrom/cohortTo: solo para WhatsApp — ver comentario en el click del gráfico WA más abajo,
  // el "día" de cada teléfono se calcula sobre desde/hasta completo, nunca sobre un rango angosto.
  const [conversionsRange, setConversionsRange] = useState<{
    desde: string; hasta: string; dayLabel?: string; cohortFrom?: string; cohortTo?: string;
  } | null>(null);

  const { data: webConversions, isLoading: webConversionsLoading } = useQuery<ConversionDetailRow[]>({
    queryKey: ["web-conversions-detail", conversionsRange?.desde, conversionsRange?.hasta],
    queryFn: () => webTrafficApi.conversions(conversionsRange!.desde, conversionsRange!.hasta).then((r) => r.data),
    staleTime: 2 * 60_000,
    enabled: !!conversionsRange && source === "web",
  });

  const { data: waConversions, isLoading: waConversionsLoading } = useQuery<WhatsappConversionDetailRow[]>({
    queryKey: ["whatsapp-conversions-detail", conversionsRange?.desde, conversionsRange?.hasta, conversionsRange?.cohortFrom, conversionsRange?.cohortTo],
    queryFn: () =>
      webTrafficApi
        .whatsappConversions(conversionsRange!.desde, conversionsRange!.hasta, conversionsRange!.cohortFrom, conversionsRange!.cohortTo)
        .then((r) => r.data),
    staleTime: 2 * 60_000,
    enabled: !!conversionsRange && source === "whatsapp",
  });

  const chartData = useMemo(
    () => groupByGranularity(data?.daily ?? [], granularity),
    [data, granularity]
  );

  const waChartData = useMemo(
    () => groupByGranularityWA(waData?.daily ?? [], granularity),
    [waData, granularity]
  );

  const t = data?.totals;
  const wt = waData?.totals;

  return (
    <div className="p-8">
      <div className="mb-6 flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tráfico {source === "web" ? "Web" : "WhatsApp"}</h1>
          <p className="text-sm text-gray-500 mt-1">
            {source === "web"
              ? "Sesiones de hotboat.cl (landing) + el sitio de reservas, día a día."
              : "Conversaciones de WhatsApp, día a día."}
          </p>
        </div>
        <div className="flex gap-1.5 bg-gray-100 rounded-lg p-1">
          {(["web", "whatsapp"] as Source[]).map((s) => (
            <button
              key={s}
              onClick={() => setSource(s)}
              className={`px-3.5 py-1.5 rounded-md text-sm font-medium transition-colors ${
                source === s ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {s === "web" ? "Sitio Web" : "WhatsApp"}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-end gap-3 mb-6 bg-white border border-gray-200 rounded-xl px-4 py-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Desde</label>
          <input
            type="date"
            value={desde}
            onChange={(e) => { setDesde(e.target.value); setPreset("custom"); }}
            className="px-2.5 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Hasta</label>
          <input
            type="date"
            value={hasta}
            onChange={(e) => { setHasta(e.target.value); setPreset("custom"); }}
            className="px-2.5 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
        <div className="flex gap-1.5">
          {(["7", "30", "todo"] as RangePreset[]).map((p) => (
            <button
              key={p}
              onClick={() => applyPreset(p)}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                preset === p ? "bg-brand-600 text-white" : "border border-gray-200 text-gray-600 hover:bg-gray-50"
              }`}
            >
              {p === "7" ? "7 días" : p === "30" ? "30 días" : "Todo"}
            </button>
          ))}
        </div>

        <div className="ml-auto">
          <label className="block text-xs text-gray-400 mb-1">Agrupar por</label>
          <div className="flex gap-1.5">
            {(["day", "week", "month"] as Granularity[]).map((g) => (
              <button
                key={g}
                onClick={() => setGranularity(g)}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  granularity === g ? "bg-gray-900 text-white" : "border border-gray-200 text-gray-600 hover:bg-gray-50"
                }`}
              >
                {g === "day" ? "Día" : g === "week" ? "Semana" : "Mes"}
              </button>
            ))}
          </div>
        </div>
      </div>

      {source === "web" && (
      <>
      {/* Resumen del rango */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard
          label="Sesiones totales"
          value={(t?.total_sessions ?? 0).toLocaleString("es-CL")}
          def="Todas las sesiones que entraron al sitio, sin filtrar"
        />
        <StatCard
          label="Sesiones útiles"
          value={(t?.useful_sessions ?? 0).toLocaleString("es-CL")}
          sub={`${t?.bounce_rate ?? 0}% rebote (≤5s)`}
          def="Estuvieron más de 5 segundos en el sitio"
        />
        <StatCard
          label="Conversión"
          value={`${t?.conversion_rate ?? 0}%`}
          sub={`${t?.paid ?? 0} pagaron`}
          def="Sesiones útiles que terminaron con un pago real registrado"
          onClick={() => setConversionsRange({ desde, hasta })}
        />
        <StatCard
          label="Encontraron caro"
          value={`${t?.found_expensive_rate ?? 0}%`}
          sub={`${(t?.viewed_price_left ?? 0).toLocaleString("es-CL")} de ${(t?.viewed_price ?? 0).toLocaleString("es-CL")} vieron precio`}
          def="Vieron el precio y no llegaron a elegir fecha en la misma sesión"
        />
      </div>

      {/* Las 3 evoluciones pedidas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <ChartCard
          title="Sesiones totales vs. útiles"
          sub="Sesión útil = más de 5 segundos en el sitio"
        >
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Area type="monotone" dataKey="total_sessions" name="Totales" stroke="#94a3b8" fill="#94a3b8" fillOpacity={0.25} strokeWidth={2} />
              <Area type="monotone" dataKey="useful_sessions" name="Útiles" stroke="#2563eb" fill="#2563eb" fillOpacity={0.35} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="% Conversión" sub="Pagaron ÷ sesiones útiles, por día — línea punteada: # de pagos. Click en un punto para ver quiénes pagaron ese día">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="left" tick={{ fontSize: 11 }} unit="%" />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(v, name) => (name === "Conversión" ? [`${v}%`, name] : [v, name])}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line
                yAxisId="left" type="monotone" dataKey="conversion_rate" name="Conversión" stroke="#16a34a" strokeWidth={2}
                dot={makeClickableDot<ChartRow>((row) => setConversionsRange({ desde: row.desde, hasta: row.hasta, dayLabel: row.label }))}
                connectNulls
              />
              <Line yAxisId="right" type="monotone" dataKey="paid" name="# Pagos" stroke="#0369a1" strokeWidth={1.5} strokeDasharray="4 3" dot={false} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 gap-4 mb-8">
        <ChartCard
          title="% Encontraron caro"
          sub="De quienes vieron el precio, % que NO avanzó a elegir fecha en la misma sesión"
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} unit="%" />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v}%`, "Encontraron caro"]} />
              <Line type="monotone" dataKey="found_expensive_rate" name="Encontraron caro" stroke="#dc2626" strokeWidth={2} dot={false} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 gap-4 mb-8">
        <DurationHistogram histogram={histogram} />
      </div>

      {/* Pop-up / WhatsApp / entraron al sistema de reservas — % siempre sobre sesiones útiles */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-8">
        <StatCard
          label="Llenaron el pop-up"
          value={`${pct2(t?.popup_fill_rate)}%`}
          sub={`${(t?.popup_fills ?? 0).toLocaleString("es-CL")} de ${(t?.useful_sessions ?? 0).toLocaleString("es-CL")} sesiones útiles`}
          def="Completaron el pop-up de suscripción del sitio"
        />
        <StatCard
          label="Abrieron WhatsApp"
          value={`${pct2(t?.whatsapp_click_rate)}%`}
          sub={`${(t?.whatsapp_clicks ?? 0).toLocaleString("es-CL")} de ${(t?.useful_sessions ?? 0).toLocaleString("es-CL")} sesiones útiles`}
          def="Hicieron click en el botón o link de WhatsApp del sitio"
        />
        <StatCard
          label="Fueron al sistema de reservas"
          value={`${pct2(t?.went_to_booking_rate)}%`}
          sub={`${(t?.went_to_booking ?? 0).toLocaleString("es-CL")} de ${(t?.useful_sessions ?? 0).toLocaleString("es-CL")} sesiones útiles`}
          def="Hicieron click en 'Reservar' desde la landing"
        />
      </div>

      {/* Dentro del sistema de reservas — % también sobre sesiones útiles */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <p className="text-sm font-semibold text-gray-800 mb-1">Dentro del sistema de reservas</p>
        <p className="text-xs text-gray-400 mb-4">Cada etapa, % sobre sesiones útiles del rango elegido</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Vio el precio</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">{pct2(t?.viewed_price_rate)}%</p>
            <p className="text-xs text-gray-400 tabular-nums">{(t?.viewed_price ?? 0).toLocaleString("es-CL")} sesiones</p>
            <p className="text-[11px] text-gray-400 italic mt-1 leading-snug">Llegó a la pantalla de precios del sistema de reservas</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Eligió fecha</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">{pct2(t?.selected_date_rate)}%</p>
            <p className="text-xs text-gray-400 tabular-nums">{(t?.selected_date ?? 0).toLocaleString("es-CL")} sesiones</p>
            <p className="text-[11px] text-gray-400 italic mt-1 leading-snug">Seleccionó una fecha disponible en el calendario</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Reservó</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">{pct2(t?.reserved_rate)}%</p>
            <p className="text-xs text-gray-400 tabular-nums">{(t?.booking_completed_events ?? 0).toLocaleString("es-CL")} sesiones</p>
            <p className="text-[11px] text-gray-400 italic mt-1 leading-snug">Completó el flujo de reserva (no implica que pagó)</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Pagó</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">{pct2(t?.conversion_rate)}%</p>
            <p className="text-xs text-gray-400 tabular-nums">{(t?.paid ?? 0).toLocaleString("es-CL")} sesiones</p>
            <p className="text-[11px] text-gray-400 italic mt-1 leading-snug">Tiene un pago real registrado — transferencia, efectivo o tarjeta</p>
          </div>
        </div>
      </div>
      </>
      )}

      {source === "whatsapp" && (
      <>
      {/* Resumen del rango */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard
          label="Conversaciones totales"
          value={(wt?.total_conversations ?? 0).toLocaleString("es-CL")}
          def="Todos los números que escribieron en el rango elegido"
        />
        <StatCard
          label="Conversaciones útiles"
          value={(wt?.useful_conversations ?? 0).toLocaleString("es-CL")}
          sub={`${wt?.discard_rate ?? 0}% descartadas (1 mensaje)`}
          def="2 o más mensajes del cliente (descarta el saludo automático del anuncio)"
        />
        <StatCard
          label="Conversión"
          value={`${pct2(wt?.conversion_rate)}%`}
          sub={`${wt?.paid ?? 0} pagaron`}
          def="Conversaciones útiles que terminaron con un pago real registrado"
          onClick={() => setConversionsRange({ desde, hasta })}
        />
        <StatCard
          label="Encontraron caro"
          value={`${pct2(wt?.found_expensive_rate)}%`}
          sub={`${(wt?.found_expensive ?? 0).toLocaleString("es-CL")} de ${(wt?.asked_price ?? 0).toLocaleString("es-CL")} preguntaron precio`}
          def="Preguntaron precio y no siguieron avanzando (sin preguntar fecha, click en el link ni reserva)"
        />
      </div>

      {/* Las 3 evoluciones pedidas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <ChartCard
          title="Conversaciones totales vs. útiles"
          sub="Conversación útil = 2 o más mensajes del cliente (descarta el texto automático del anuncio)"
        >
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={waChartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Area type="monotone" dataKey="total_conversations" name="Totales" stroke="#94a3b8" fill="#94a3b8" fillOpacity={0.25} strokeWidth={2} />
              <Area type="monotone" dataKey="useful_conversations" name="Útiles" stroke="#25d366" fill="#25d366" fillOpacity={0.3} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="% Conversión" sub="Pagaron ÷ conversaciones útiles, por día — línea punteada: # de pagos. Click en un punto para ver quiénes pagaron ese día">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={waChartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="left" tick={{ fontSize: 11 }} unit="%" />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(v, name) => (name === "Conversión" ? [`${v}%`, name] : [v, name])}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line
                yAxisId="left" type="monotone" dataKey="conversion_rate" name="Conversión" stroke="#16a34a" strokeWidth={2}
                dot={makeClickableDot<ChartRowWA>((row) =>
                  // A diferencia de Web, acá "pagó" se le atribuye al día del PRIMER mensaje del
                  // teléfono dentro del rango completo (cohorte) — así que desde/hasta del filtro
                  // siguen siendo el rango completo de la página, y row.desde/row.hasta (el día
                  // puntual clickeado) van como cohortFrom/cohortTo para no romper ese cálculo.
                  setConversionsRange({ desde, hasta, cohortFrom: row.desde, cohortTo: row.hasta, dayLabel: row.label })
                )}
                connectNulls
              />
              <Line yAxisId="right" type="monotone" dataKey="paid" name="# Pagos" stroke="#0369a1" strokeWidth={1.5} strokeDasharray="4 3" dot={false} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 gap-4 mb-8">
        <ChartCard
          title="% Encontraron caro"
          sub="De quienes preguntaron precio, % que no preguntó fecha, no hizo click en el link ni reservó"
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={waChartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} unit="%" />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v}%`, "Encontraron caro"]} />
              <Line type="monotone" dataKey="found_expensive_rate" name="Encontraron caro" stroke="#dc2626" strokeWidth={2} dot={false} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Preguntaron por fecha / hicieron click / reservaron / pagaron — % sobre conversaciones útiles */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <p className="text-sm font-semibold text-gray-800 mb-1">Dentro de la conversación</p>
        <p className="text-xs text-gray-400 mb-4">Cada etapa, % sobre conversaciones útiles del rango elegido</p>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Preguntó precio</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">{pct2(wt?.asked_price_rate)}%</p>
            <p className="text-xs text-gray-400 tabular-nums">{(wt?.asked_price ?? 0).toLocaleString("es-CL")} conversaciones</p>
            <p className="text-[11px] text-gray-400 italic mt-1 leading-snug">Mencionó precio, valor, cuánto cuesta, etc. en algún mensaje</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Preguntó fecha</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">{pct2(wt?.asked_date_rate)}%</p>
            <p className="text-xs text-gray-400 tabular-nums">{(wt?.asked_date ?? 0).toLocaleString("es-CL")} conversaciones</p>
            <p className="text-[11px] text-gray-400 italic mt-1 leading-snug">Mencionó fecha, disponibilidad, agendar, etc. en algún mensaje</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Click en el link</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">{pct2(wt?.clicked_link_rate)}%</p>
            <p className="text-xs text-gray-400 tabular-nums">{(wt?.clicked_link ?? 0).toLocaleString("es-CL")} conversaciones</p>
            <p className="text-[11px] text-gray-400 italic mt-1 leading-snug">Hizo click en el link de cotización enviado por WhatsApp</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Reservó</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">{pct2(wt?.reserved_rate)}%</p>
            <p className="text-xs text-gray-400 tabular-nums">{(wt?.reserved ?? 0).toLocaleString("es-CL")} conversaciones</p>
            <p className="text-[11px] text-gray-400 italic mt-1 leading-snug">Su teléfono está asociado a una reserva (no implica que pagó)</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Pagó</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">{pct2(wt?.conversion_rate)}%</p>
            <p className="text-xs text-gray-400 tabular-nums">{(wt?.paid ?? 0).toLocaleString("es-CL")} conversaciones</p>
            <p className="text-[11px] text-gray-400 italic mt-1 leading-snug">Tiene un pago real registrado — transferencia, efectivo o tarjeta</p>
          </div>
        </div>
      </div>
      </>
      )}

      {(source === "web" ? isLoading : waLoading) && <p className="text-sm text-gray-400 mt-4">Cargando...</p>}

      {conversionsRange && (
        <ConversionsModal
          title={
            (source === "web" ? "Quiénes pagaron — Web" : "Quiénes pagaron — WhatsApp") +
            (conversionsRange.dayLabel ? ` · ${conversionsRange.dayLabel}` : "")
          }
          onClose={() => setConversionsRange(null)}
          rows={source === "web" ? (webConversions ?? []) : (waConversions ?? [])}
          isLoading={source === "web" ? webConversionsLoading : waConversionsLoading}
        />
      )}
    </div>
  );
}
