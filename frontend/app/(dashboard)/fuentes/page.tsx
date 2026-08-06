"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ResponsiveContainer, AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from "recharts";
import { sourcesApi } from "@/lib/api";
import {
  PlatformBucket, PlatformComparisonResponse, FlujoPlatformCrosstabRow,
  WebTrafficResponse, WhatsappTrafficResponse, ConversionDetailRow,
} from "@/lib/types";
import {
  Granularity, StatCard, ChartCard, ConversionsModal, makeClickableDot,
  pct2, tooltipStyle, groupByGranularity, groupByGranularityWA,
  ChartRow, ChartRowWA, money,
} from "@/components/analytics/traffic-shared";

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}
function daysAgoISO(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

const PLATFORM_LABEL: Record<PlatformBucket, { text: string; dot: string }> = {
  meta: { text: "Meta", dot: "bg-blue-500" },
  google: { text: "Google", dot: "bg-amber-500" },
  otro: { text: "Otro", dot: "bg-gray-400" },
};

// A diferencia de FLUJO_LABEL en traffic-shared (que solo cubre flujo_2/3,
// porque ahí solo aparece dentro del modal de reservas pagadas de Web), acá
// el cruce necesita los 3 flujos.
const FLUJO_LABEL_FULL: Record<string, string> = {
  flujo_1: "Flujo 1 · WhatsApp puro",
  flujo_2: "Flujo 2 · Solo web",
  flujo_3: "Flujo 3 · Web → WhatsApp",
};

type RangePreset = "7" | "30" | "60" | "custom";
type Channel = "web" | "whatsapp";

const ALL_PLATFORMS: PlatformBucket[] = ["meta", "google", "otro"];

export default function FuentesPage() {
  const [desde, setDesde] = useState(daysAgoISO(60));
  const [hasta, setHasta] = useState(todayISO());
  const [preset, setPreset] = useState<RangePreset>("60");

  const [channel, setChannel] = useState<Channel>("web");
  // Multi-select: cualquier combinación de Meta/Google/Otro a la vez (ej.
  // Meta + Google, sin Otro) — no solo una a la vez. Al menos una queda
  // siempre seleccionada (togglePlatform no permite vaciar del todo).
  const [platforms, setPlatforms] = useState<PlatformBucket[]>(ALL_PLATFORMS);
  const [granularity, setGranularity] = useState<Granularity>("day");

  function togglePlatform(p: PlatformBucket) {
    setPlatforms((prev) => {
      if (prev.includes(p)) {
        return prev.length > 1 ? prev.filter((x) => x !== p) : prev;
      }
      return [...prev, p];
    });
  }

  function applyPreset(p: RangePreset) {
    setPreset(p);
    if (p === "7") { setDesde(daysAgoISO(7)); setHasta(todayISO()); }
    else if (p === "30") { setDesde(daysAgoISO(30)); setHasta(todayISO()); }
    else if (p === "60") { setDesde(daysAgoISO(60)); setHasta(todayISO()); }
  }

  const { data: comparison, isLoading: comparisonLoading } = useQuery<PlatformComparisonResponse>({
    queryKey: ["sources-comparison", desde, hasta],
    queryFn: () => sourcesApi.comparison(desde, hasta).then((r) => r.data),
    staleTime: 2 * 60_000,
  });

  const { data: crosstab, isLoading: crosstabLoading } = useQuery<FlujoPlatformCrosstabRow[]>({
    queryKey: ["sources-crosstab", desde, hasta],
    queryFn: () => sourcesApi.crosstab(desde, hasta).then((r) => r.data),
    staleTime: 2 * 60_000,
  });

  const platformsKey = platforms.join(",");

  const { data: webData, isLoading: webLoading } = useQuery<WebTrafficResponse>({
    queryKey: ["sources-daily-web", desde, hasta, platformsKey],
    queryFn: () => sourcesApi.daily("web", platforms, desde, hasta).then((r) => r.data),
    staleTime: 2 * 60_000,
    enabled: channel === "web",
  });

  const { data: waData, isLoading: waLoading } = useQuery<WhatsappTrafficResponse>({
    queryKey: ["sources-daily-whatsapp", desde, hasta, platformsKey],
    queryFn: () => sourcesApi.daily("whatsapp", platforms, desde, hasta).then((r) => r.data),
    staleTime: 2 * 60_000,
    enabled: channel === "whatsapp",
  });

  const [conversionsRange, setConversionsRange] = useState<{
    desde: string; hasta: string; dayLabel?: string; cohortFrom?: string; cohortTo?: string;
  } | null>(null);

  const { data: conversions, isLoading: conversionsLoading } = useQuery<ConversionDetailRow[]>({
    queryKey: ["sources-conversions", channel, platformsKey, conversionsRange?.desde, conversionsRange?.hasta, conversionsRange?.cohortFrom, conversionsRange?.cohortTo],
    queryFn: () =>
      sourcesApi
        .conversions(channel, platforms, conversionsRange!.desde, conversionsRange!.hasta, conversionsRange!.cohortFrom, conversionsRange!.cohortTo)
        .then((r) => r.data),
    staleTime: 2 * 60_000,
    enabled: !!conversionsRange,
  });

  const chartData = useMemo(
    () => groupByGranularity(webData?.daily ?? [], granularity),
    [webData, granularity]
  );
  const waChartData = useMemo(
    () => groupByGranularityWA(waData?.daily ?? [], granularity),
    [waData, granularity]
  );

  const t = webData?.totals;
  const wt = waData?.totals;

  const rows = comparison?.rows ?? [];
  const totalBookings = rows.reduce((s, r) => s + r.bookings, 0);

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Fuentes</h1>
        <p className="text-sm text-gray-500 mt-1">
          Google, Meta u otra fuente — quién trae más gente, quién convierte mejor y quién sale más barato.
        </p>
      </div>

      {/* Rango de fechas — controla también la tabla comparativa y el cruce de flujos */}
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
          {(["7", "30", "60"] as RangePreset[]).map((p) => (
            <button
              key={p}
              onClick={() => applyPreset(p)}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                preset === p ? "bg-brand-600 text-white" : "border border-gray-200 text-gray-600 hover:bg-gray-50"
              }`}
            >
              {p} días
            </button>
          ))}
        </div>
      </div>

      {/* Tabla comparativa — la respuesta directa a "dónde invertir" */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden mb-8">
        <div className="px-5 py-4 border-b border-gray-100">
          <p className="text-sm font-semibold text-gray-800">Comparación por plataforma</p>
          <p className="text-xs text-gray-400 mt-0.5">
            Nivel de plataforma (Google/Meta/Otro) en los 3 flujos combinados — el detalle por anuncio individual de Meta está en la pestaña Anuncios.
          </p>
        </div>
        {comparisonLoading ? (
          <p className="text-sm text-gray-400 px-5 py-8 text-center">Cargando...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr className="border-b border-gray-100">
                  <th className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Plataforma</th>
                  <th className="px-4 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Sesiones web útiles</th>
                  <th className="px-4 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Conversaciones WA útiles</th>
                  <th className="px-4 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Reservas (todas las señales)</th>
                  <th className="px-4 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">% del total</th>
                  <th className="px-4 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Conversión</th>
                  <th className="px-4 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Gasto</th>
                  <th className="px-4 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Costo / reserva</th>
                  <th className="px-4 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Reservas con anuncio identificado</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.platform} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-2 font-medium text-gray-800">
                        <span className={`w-2 h-2 rounded-full ${PLATFORM_LABEL[r.platform].dot}`} />
                        {PLATFORM_LABEL[r.platform].text}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-700">{r.web_useful_sessions.toLocaleString("es-CL")}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-700">{r.whatsapp_useful_conversations.toLocaleString("es-CL")}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-900 font-semibold">{r.bookings.toLocaleString("es-CL")}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-500">
                      {totalBookings ? `${Math.round((r.bookings / totalBookings) * 1000) / 10}%` : "—"}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-700">{pct2(r.conversion_rate)}%</td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-700">{r.spend != null ? money(r.spend) : "—"}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-700">{r.cost_per_booking != null ? money(r.cost_per_booking) : "—"}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-500">{r.meta_bookings_matched != null ? r.meta_bookings_matched.toLocaleString("es-CL") : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="px-5 py-2.5 bg-amber-50/60 border-t border-amber-100 text-xs text-amber-800">
          Google no tiene integración de gasto en ningún sistema — su costo por reserva siempre se muestra como "—", nunca inventado. "Reservas con anuncio identificado" es el subconjunto de Meta que además matcheó un anuncio real (mismo criterio que la pestaña Anuncios) — es normal que sea menor a "Reservas (todas las señales)".
        </div>
      </div>

      {/* Cruce Flujo x Plataforma */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden mb-8">
        <div className="px-5 py-4 border-b border-gray-100">
          <p className="text-sm font-semibold text-gray-800">Reservas por flujo y plataforma</p>
          <p className="text-xs text-gray-400 mt-0.5">Ej.: cuánto de Meta pasó por WhatsApp antes de reservar</p>
        </div>
        {crosstabLoading ? (
          <p className="text-sm text-gray-400 px-5 py-8 text-center">Cargando...</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr className="border-b border-gray-100">
                  <th className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Flujo</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Plataforma</th>
                  <th className="px-4 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Reservas pagadas</th>
                  <th className="px-4 py-2.5 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">% del total</th>
                </tr>
              </thead>
              <tbody>
                {(crosstab ?? []).map((c) => (
                  <tr key={`${c.flujo}-${c.platform}`} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="px-4 py-2.5 text-gray-600">{FLUJO_LABEL_FULL[c.flujo] ?? c.flujo}</td>
                    <td className="px-4 py-2.5">
                      <span className="flex items-center gap-2 text-gray-800">
                        <span className={`w-2 h-2 rounded-full ${PLATFORM_LABEL[c.platform].dot}`} />
                        {PLATFORM_LABEL[c.platform].text}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-gray-800 font-medium">{c.paid.toLocaleString("es-CL")}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-gray-500">{pct2(c.share_of_total_pct)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Evolución — mismos gráficos que Tráfico Web, filtrables por plataforma */}
      <div className="mb-4 flex items-start justify-between flex-wrap gap-3">
        <div>
          <p className="text-sm font-semibold text-gray-800">Evolución</p>
          <p className="text-xs text-gray-400 mt-0.5">Mismo desglose que Tráfico Web, filtrado por plataforma</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex gap-1.5 bg-gray-100 rounded-lg p-1">
            {(["web", "whatsapp"] as Channel[]).map((c) => (
              <button
                key={c}
                onClick={() => setChannel(c)}
                className={`px-3.5 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  channel === c ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
                }`}
              >
                {c === "web" ? "Sitio Web" : "WhatsApp"}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-1.5 bg-gray-100 rounded-lg p-1" title="Selecciona una o varias — ej. Meta + Google, sin Otro">
            <button
              onClick={() => setPlatforms(ALL_PLATFORMS)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                platforms.length === ALL_PLATFORMS.length ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
              }`}
            >
              Todos
            </button>
            <span className="w-px h-4 bg-gray-300 mx-0.5" />
            {ALL_PLATFORMS.map((p) => {
              const active = platforms.includes(p);
              return (
                <button
                  key={p}
                  onClick={() => togglePlatform(p)}
                  aria-pressed={active}
                  className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center gap-1.5 ${
                    active ? "bg-white text-gray-900 shadow-sm" : "text-gray-400 hover:text-gray-600"
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full ${active ? PLATFORM_LABEL[p].dot : "bg-gray-300"}`} />
                  {PLATFORM_LABEL[p].text}
                </button>
              );
            })}
          </div>
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

      {channel === "web" && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <StatCard label="Sesiones totales" value={(t?.total_sessions ?? 0).toLocaleString("es-CL")} />
            <StatCard
              label="Sesiones útiles"
              value={(t?.useful_sessions ?? 0).toLocaleString("es-CL")}
              sub={`${t?.bounce_rate ?? 0}% rebote (≤5s)`}
            />
            <StatCard
              label="Conversión"
              value={`${t?.conversion_rate ?? 0}%`}
              sub={`${t?.paid ?? 0} pagaron`}
              onClick={() => setConversionsRange({ desde, hasta })}
            />
            <StatCard
              label="Encontraron caro"
              value={`${t?.found_expensive_rate ?? 0}%`}
              sub={`${(t?.viewed_price_left ?? 0).toLocaleString("es-CL")} de ${(t?.viewed_price ?? 0).toLocaleString("es-CL")} vieron precio`}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
            <ChartCard title="Sesiones totales vs. útiles" sub="Sesión útil = más de 5 segundos en el sitio">
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

            <ChartCard title="% Conversión" sub="Pagaron ÷ sesiones útiles, por día. Click en un punto para ver quiénes pagaron ese día">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                  <YAxis yAxisId="left" tick={{ fontSize: 11 }} unit="%" />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip contentStyle={tooltipStyle} formatter={(v, name) => (name === "Conversión" ? [`${v}%`, name] : [v, name])} />
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
        </>
      )}

      {channel === "whatsapp" && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <StatCard label="Conversaciones totales" value={(wt?.total_conversations ?? 0).toLocaleString("es-CL")} />
            <StatCard
              label="Conversaciones útiles"
              value={(wt?.useful_conversations ?? 0).toLocaleString("es-CL")}
              sub={`${wt?.discard_rate ?? 0}% descartadas (1 mensaje)`}
            />
            <StatCard
              label="Conversión"
              value={`${pct2(wt?.conversion_rate)}%`}
              sub={`${wt?.paid ?? 0} pagaron`}
              onClick={() => setConversionsRange({ desde, hasta })}
            />
            <StatCard
              label="Encontraron caro"
              value={`${pct2(wt?.found_expensive_rate)}%`}
              sub={`${(wt?.found_expensive ?? 0).toLocaleString("es-CL")} de ${(wt?.asked_price ?? 0).toLocaleString("es-CL")} preguntaron precio`}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
            <ChartCard title="Conversaciones totales vs. útiles" sub="Conversación útil = 2 o más mensajes del cliente">
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

            <ChartCard title="% Conversión" sub="Pagaron ÷ conversaciones útiles, por día. Click en un punto para ver quiénes pagaron ese día">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={waChartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                  <YAxis yAxisId="left" tick={{ fontSize: 11 }} unit="%" />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip contentStyle={tooltipStyle} formatter={(v, name) => (name === "Conversión" ? [`${v}%`, name] : [v, name])} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line
                    yAxisId="left" type="monotone" dataKey="conversion_rate" name="Conversión" stroke="#16a34a" strokeWidth={2}
                    dot={makeClickableDot<ChartRowWA>((row) =>
                      setConversionsRange({ desde, hasta, cohortFrom: row.desde, cohortTo: row.hasta, dayLabel: row.label })
                    )}
                    connectNulls
                  />
                  <Line yAxisId="right" type="monotone" dataKey="paid" name="# Pagos" stroke="#0369a1" strokeWidth={1.5} strokeDasharray="4 3" dot={false} connectNulls />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </>
      )}

      {((channel === "web" && webLoading) || (channel === "whatsapp" && waLoading)) && (
        <p className="text-sm text-gray-400 mt-4">Cargando...</p>
      )}

      {conversionsRange && (
        <ConversionsModal
          title={
            (channel === "web" ? "Quiénes pagaron — Web" : "Quiénes pagaron — WhatsApp") +
            (platforms.length < ALL_PLATFORMS.length ? ` · ${platforms.map((p) => PLATFORM_LABEL[p].text).join(" + ")}` : "") +
            (conversionsRange.dayLabel ? ` · ${conversionsRange.dayLabel}` : "")
          }
          onClose={() => setConversionsRange(null)}
          rows={conversions ?? []}
          isLoading={conversionsLoading}
        />
      )}
    </div>
  );
}
