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
import { WebTrafficResponse } from "@/lib/types";

function shortDate(d: string) {
  const [, m, day] = d.split("-");
  return `${day}/${m}`;
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgoISO(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl px-4 py-3">
      <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">{label}</p>
      <p className="text-2xl font-bold text-gray-900 tabular-nums">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

function ChartCard({ title, sub, children }: { title: string; sub?: string; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <p className="text-sm font-semibold text-gray-800">{title}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5 mb-2">{sub}</p>}
      <div className="h-64 mt-2">{children}</div>
    </div>
  );
}

const tooltipStyle = { fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb" };

type RangePreset = "7" | "30" | "todo" | "custom";

export default function TraficoWebPage() {
  const [preset, setPreset] = useState<RangePreset>("30");
  const [desde, setDesde] = useState(daysAgoISO(30));
  const [hasta, setHasta] = useState(todayISO());

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
  });

  const chartData = useMemo(
    () => (data?.daily ?? []).map((d) => ({ ...d, label: shortDate(d.day) })),
    [data]
  );

  const t = data?.totals;

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Tráfico Web</h1>
        <p className="text-sm text-gray-500 mt-1">
          Sesiones de hotboat.cl (landing) + el sitio de reservas, día a día. WhatsApp se agrega más adelante.
        </p>
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
      </div>

      {/* Resumen del rango */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="Sesiones totales" value={(t?.total_sessions ?? 0).toLocaleString("es-CL")} />
        <StatCard
          label="Sesiones útiles"
          value={(t?.useful_sessions ?? 0).toLocaleString("es-CL")}
          sub={`${t?.bounce_rate ?? 0}% sin interacción`}
        />
        <StatCard label="Conversión" value={`${t?.conversion_rate ?? 0}%`} sub={`${t?.paid ?? 0} pagaron`} />
        <StatCard
          label="Encontraron caro"
          value={`${t?.found_expensive_rate ?? 0}%`}
          sub={`${(t?.viewed_price_left ?? 0).toLocaleString("es-CL")} de ${(t?.viewed_price ?? 0).toLocaleString("es-CL")} vieron precio`}
        />
      </div>

      {/* Las 3 evoluciones pedidas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <ChartCard
          title="Sesiones totales vs. útiles"
          sub="Sesión útil = tuvo al menos una interacción aparte de cargar la página"
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

        <ChartCard title="% Conversión" sub="Pagaron ÷ sesiones útiles, por día">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} unit="%" />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v}%`, "Conversión"]} />
              <Line type="monotone" dataKey="conversion_rate" name="Conversión" stroke="#16a34a" strokeWidth={2} dot={false} connectNulls />
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

      {/* Pop-up / WhatsApp / entraron al sistema de reservas */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-8">
        <StatCard
          label="Llenaron el pop-up"
          value={`${t?.popup_fill_rate ?? 0}%`}
          sub={`${t?.popup_fills ?? 0} de ${(t?.total_sessions ?? 0).toLocaleString("es-CL")} sesiones`}
        />
        <StatCard
          label="Abrieron WhatsApp"
          value={`${t?.whatsapp_click_rate ?? 0}%`}
          sub={`${t?.whatsapp_clicks ?? 0} clicks en el botón`}
        />
        <StatCard
          label="Fueron al sistema de reservas"
          value={`${t?.went_to_booking_rate ?? 0}%`}
          sub={`${t?.went_to_booking ?? 0} clicks en reservar/ver disponibilidad`}
        />
      </div>

      {/* Dentro del sistema de reservas */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <p className="text-sm font-semibold text-gray-800 mb-1">Dentro del sistema de reservas</p>
        <p className="text-xs text-gray-400 mb-4">Cada etapa, del total del rango elegido</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Vio el precio</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">{(t?.viewed_price ?? 0).toLocaleString("es-CL")}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Eligió fecha</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">{(t?.selected_date ?? 0).toLocaleString("es-CL")}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Reservó</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">
              {(data?.daily.reduce((s, d) => s + d.booking_completed_events, 0) ?? 0).toLocaleString("es-CL")}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide">Pagó</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">{(t?.paid ?? 0).toLocaleString("es-CL")}</p>
          </div>
        </div>
      </div>

      {isLoading && <p className="text-sm text-gray-400 mt-4">Cargando...</p>}
    </div>
  );
}
