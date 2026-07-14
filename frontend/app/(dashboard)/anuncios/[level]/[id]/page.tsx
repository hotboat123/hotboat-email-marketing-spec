"use client";

import { useMemo } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
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
} from "recharts";
import { adsApi } from "@/lib/api";
import { AdLevel, AdSummary, AdTimeseries } from "@/lib/types";
import { ArrowLeft } from "lucide-react";

const LEVEL_LABEL: Record<AdLevel, string> = {
  ad: "Anuncio",
  adset: "Conjunto de anuncios",
  campaign: "Campaña",
};

function money(n: number | null | undefined) {
  return n == null ? "—" : `$${Math.round(n).toLocaleString("es-CL")}`;
}

function shortDate(d: string) {
  const [, m, day] = d.split("-");
  return `${day}/${m}`;
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl px-4 py-3">
      <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">{label}</p>
      <p className="text-lg font-semibold text-gray-900 tabular-nums">{value}</p>
    </div>
  );
}

function ChartCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <p className="text-sm font-semibold text-gray-800 mb-3">{title}</p>
      <div className="h-56">{children}</div>
    </div>
  );
}

const tooltipStyle = {
  fontSize: 12,
  borderRadius: 8,
  border: "1px solid #e5e7eb",
};

export default function AdDetailPage() {
  const params = useParams<{ level: string; id: string }>();
  const level = (params.level as AdLevel) ?? "ad";
  const id = decodeURIComponent(params.id ?? "");

  const { data: series, isLoading, isError } = useQuery<AdTimeseries>({
    queryKey: ["ad-timeseries", level, id],
    queryFn: () => adsApi.timeseries(level, id).then((r) => r.data),
    staleTime: 5 * 60_000,
    enabled: !!id,
  });

  const { data: summaryList } = useQuery<AdSummary[]>({
    queryKey: ["ads-summary", level],
    queryFn: () => adsApi.summary(level).then((r) => r.data),
    staleTime: 5 * 60_000,
  });
  const summary = summaryList?.find((r) => r.id === id);

  const points = series?.points ?? [];
  const chartData = useMemo(
    () => points.map((p) => ({ ...p, dateLabel: shortDate(p.date) })),
    [points]
  );

  const totals = useMemo(() => {
    const spend = points.reduce((s, p) => s + p.spend, 0);
    const clicks = points.reduce((s, p) => s + p.clicks, 0);
    const conversations = points.reduce((s, p) => s + p.conversations_started, 0);
    return {
      spend,
      clicks,
      conversations,
      cpc: clicks ? spend / clicks : null,
      costPerConversation: conversations ? spend / conversations : null,
    };
  }, [points]);

  return (
    <div className="p-8">
      <Link href="/anuncios" className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft size={14} /> Volver a Anuncios
      </Link>

      {isLoading ? (
        <div className="space-y-4">
          <div className="h-7 bg-gray-200 rounded w-72 animate-pulse" />
          <div className="h-4 bg-gray-100 rounded w-48 animate-pulse" />
        </div>
      ) : isError || !series ? (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          No se encontraron datos para este {LEVEL_LABEL[level].toLowerCase()}.
        </div>
      ) : (
        <>
          <div className="mb-6">
            <p className="text-xs font-semibold text-brand-600 uppercase tracking-wide mb-1">{LEVEL_LABEL[level]}</p>
            <h1 className="text-2xl font-bold text-gray-900">{series.name}</h1>
            {summary?.campaign_name && (
              <p className="text-sm text-gray-500 mt-1">
                {summary.adset_name ? `${summary.campaign_name} · ${summary.adset_name}` : summary.campaign_name}
              </p>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
            <StatCard label="Gasto total" value={money(totals.spend)} />
            <StatCard label="Clicks" value={totals.clicks.toLocaleString("es-CL")} />
            <StatCard label="CPC promedio" value={money(totals.cpc)} />
            <StatCard label="Conversaciones" value={totals.conversations.toLocaleString("es-CL")} />
            <StatCard label="Costo/conversación" value={money(totals.costPerConversation)} />
          </div>

          {chartData.length === 0 ? (
            <p className="text-sm text-gray-400">Sin puntos diarios para graficar.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <ChartCard title="Gasto diario">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="spendGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#0ea5e9" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="#0ea5e9" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="dateLabel" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 11 }} width={56} tickFormatter={(v) => `$${Math.round(v / 1000)}k`} />
                    <Tooltip contentStyle={tooltipStyle} formatter={(v) => money(Number(v))} labelFormatter={(l) => l} />
                    <Area type="monotone" dataKey="spend" stroke="#0ea5e9" fill="url(#spendGradient)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="CPC (costo por click)">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="dateLabel" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 11 }} width={56} tickFormatter={(v) => `$${v}`} />
                    <Tooltip contentStyle={tooltipStyle} formatter={(v) => money(Number(v))} />
                    <Line type="monotone" dataKey="cpc" stroke="#f59e0b" strokeWidth={2} dot={false} connectNulls />
                  </LineChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Conversaciones de WhatsApp iniciadas">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="convGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#22c55e" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="dateLabel" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 11 }} width={40} allowDecimals={false} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Area type="monotone" dataKey="conversations_started" stroke="#22c55e" fill="url(#convGradient)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Costo por conversación">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="dateLabel" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 11 }} width={56} tickFormatter={(v) => `$${Math.round(v / 1000)}k`} />
                    <Tooltip contentStyle={tooltipStyle} formatter={(v) => money(Number(v))} />
                    <Line type="monotone" dataKey="cost_per_conversation" stroke="#a855f7" strokeWidth={2} dot={false} connectNulls />
                  </LineChart>
                </ResponsiveContainer>
              </ChartCard>
            </div>
          )}

          <p className="text-xs text-gray-400 mt-4">
            No incluye % de conversión a reserva por día — esa atribución se calcula por contacto, no por día, así que
            queda solo como cifra agregada en el Embudo, no como serie de tiempo.
          </p>
        </>
      )}
    </div>
  );
}
