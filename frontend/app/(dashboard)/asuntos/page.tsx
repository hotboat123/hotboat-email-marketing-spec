"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "@/lib/api";
import { SubjectAnalytics } from "@/lib/types";
import { Search, ChevronUp, ChevronDown, ChevronsUpDown, TrendingUp } from "lucide-react";
import { formatDate } from "@/lib/utils";
import Link from "next/link";

// ── Patrones de asuntos ──────────────────────────────────────────────────────

const PATTERNS = [
  {
    key: "urgencia",
    label: "Urgencia",
    example: '"últimas 24 horas 🔥"',
    description: "Escasez y tiempo límite",
    keywords: ["últim", "hora", "hoy", "ahora", "cupo", "quedan", "ya ", "tarde", "queda", "vence"],
    bg: "bg-orange-50",
    border: "border-orange-200",
    tag: "text-orange-600 bg-orange-100",
  },
  {
    key: "personalizacion",
    label: "Personalización",
    example: '"esto es para vos"',
    description: "Informal y cercano",
    keywords: ["tu ", "tuyo", "tus ", "vos", "te ", "para ti", "para vos"],
    bg: "bg-blue-50",
    border: "border-blue-200",
    tag: "text-blue-600 bg-blue-100",
  },
  {
    key: "curiosidad",
    label: "Curiosidad",
    example: '"¿sabías esto?"',
    description: "Intriga sin spoilear",
    keywords: ["?", "sabías", "revisa", "adivina", "por qué", "secreto", "te contamos", "sorpresa"],
    bg: "bg-purple-50",
    border: "border-purple-200",
    tag: "text-purple-600 bg-purple-100",
  },
  {
    key: "oferta",
    label: "Oferta especial",
    example: '"foto + dron gratis"',
    description: "Descuento o regalo incluido",
    keywords: ["%", "gratis", "off", "regalo", "dron", "descuento", "gift", "cyber", "free", "foto", "video"],
    bg: "bg-green-50",
    border: "border-green-200",
    tag: "text-green-600 bg-green-100",
  },
];

function matchesPattern(subject: string, keywords: string[]): boolean {
  const s = subject.toLowerCase();
  return keywords.some((kw) => s.includes(kw.toLowerCase()));
}

// ── Colores de open rate ─────────────────────────────────────────────────────

function openRateClass(rate: number) {
  if (rate >= 40) return "text-green-600 font-bold";
  if (rate >= 25) return "text-green-500 font-semibold";
  if (rate >= 15) return "text-yellow-600 font-semibold";
  return "text-red-500";
}

function clickRateClass(rate: number) {
  if (rate >= 4) return "text-green-600 font-semibold";
  if (rate >= 2) return "text-yellow-600";
  return "text-gray-400";
}

// ── Tipos de orden ───────────────────────────────────────────────────────────

type SortField = "open_rate" | "click_rate" | "sent_count" | "sent_at";
type SortDir = "asc" | "desc";

function SortIcon({ field, active, dir }: { field: string; active: boolean; dir: SortDir }) {
  if (!active) return <ChevronsUpDown size={13} className="text-gray-300 ml-1 inline" />;
  return dir === "desc"
    ? <ChevronDown size={13} className="text-brand-600 ml-1 inline" />
    : <ChevronUp size={13} className="text-brand-600 ml-1 inline" />;
}

// ── Skeleton ─────────────────────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <tr className="border-b border-gray-100">
      {[...Array(6)].map((_, i) => (
        <td key={i} className="px-5 py-3">
          <div className="h-4 bg-gray-100 rounded animate-pulse" />
        </td>
      ))}
    </tr>
  );
}

// ── Página ───────────────────────────────────────────────────────────────────

export default function AsuntosPage() {
  const [search, setSearch] = useState("");
  const [sortField, setSortField] = useState<SortField>("open_rate");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const { data: rows = [], isLoading } = useQuery<SubjectAnalytics[]>({
    queryKey: ["asuntos"],
    queryFn: () => analyticsApi.asuntos().then((r) => r.data),
    staleTime: 5 * 60_000,
  });

  // ── Stats agregadas ──────────────────────────────────────────────────────
  const stats = useMemo(() => {
    if (!rows.length) return null;
    const avgOpen = rows.reduce((s, r) => s + r.open_rate, 0) / rows.length;
    const best = rows.reduce((a, b) => (a.open_rate >= b.open_rate ? a : b));
    return { total: rows.length, avgOpen: avgOpen.toFixed(1), best };
  }, [rows]);

  // ── Patrones: mejor asunto por categoría ────────────────────────────────
  const patternBests = useMemo(() => {
    return PATTERNS.map((p) => {
      const matches = rows.filter((r) => matchesPattern(r.subject, p.keywords));
      const best = matches.length
        ? matches.reduce((a, b) => (a.open_rate >= b.open_rate ? a : b))
        : null;
      return { ...p, best, count: matches.length };
    });
  }, [rows]);

  // ── Filtro + orden ───────────────────────────────────────────────────────
  const filtered = useMemo(() => {
    const s = search.toLowerCase();
    const f = rows.filter(
      (r) =>
        !s ||
        r.subject.toLowerCase().includes(s) ||
        r.campaign_name.toLowerCase().includes(s)
    );
    return [...f].sort((a, b) => {
      const av = a[sortField] as number | string;
      const bv = b[sortField] as number | string;
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortDir === "desc" ? -cmp : cmp;
    });
  }, [rows, search, sortField, sortDir]);

  function toggleSort(field: SortField) {
    if (sortField === field) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortField(field);
      setSortDir("desc");
    }
  }

  return (
    <div className="p-8 max-w-6xl">

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Análisis de asuntos</h1>
        <p className="text-sm text-gray-500 mt-1">
          Ranking de asuntos por open rate — basado en tus campañas enviadas
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">
            Asuntos analizados
          </p>
          <p className="text-3xl font-black text-gray-900">
            {isLoading ? "—" : stats?.total ?? 0}
          </p>
          <p className="text-xs text-gray-400 mt-1">con datos de open rate</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">
            Open rate promedio
          </p>
          <p className="text-3xl font-black text-green-500">
            {isLoading ? "—" : stats ? `${stats.avgOpen}%` : "0%"}
          </p>
          <p className="text-xs text-gray-400 mt-1">histórico de campañas</p>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">
            Mejor asunto
          </p>
          <p className="text-3xl font-black text-green-500">
            {isLoading ? "—" : stats ? `${stats.best.open_rate}%` : "0%"}
          </p>
          <p className="text-xs text-gray-500 mt-1 truncate" title={stats?.best.subject}>
            {isLoading ? "—" : stats?.best.subject ?? "—"}
          </p>
        </div>
      </div>

      {/* Patrones */}
      {!isLoading && rows.length > 0 && (
        <div className="mb-8">
          <p className="text-sm font-semibold text-brand-600 mb-3">
            Patrones de asuntos con mayor open rate
          </p>
          <div className="grid grid-cols-4 gap-3">
            {patternBests.map((p) => (
              <div
                key={p.key}
                className={`rounded-xl border p-4 ${p.bg} ${p.border}`}
              >
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${p.tag}`}>
                  {p.label}
                </span>
                <p className="text-sm font-semibold text-gray-800 mt-2 leading-tight">
                  {p.best ? `"${p.best.subject}"` : p.example}
                </p>
                <p className="text-xs text-gray-500 mt-1">{p.description}</p>
                {p.best && (
                  <p className="text-xs font-bold text-gray-700 mt-2">
                    {p.best.open_rate}% open · {p.count} campañas
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabla */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between gap-3">
          <p className="font-semibold text-gray-800">Todos los asuntos</p>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-400 w-52"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase w-6">#</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Asunto</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Campaña</th>
                <th
                  className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase cursor-pointer select-none hover:text-gray-700"
                  onClick={() => toggleSort("open_rate")}
                >
                  Open %
                  <SortIcon field="open_rate" active={sortField === "open_rate"} dir={sortDir} />
                </th>
                <th
                  className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase cursor-pointer select-none hover:text-gray-700"
                  onClick={() => toggleSort("click_rate")}
                >
                  Click %
                  <SortIcon field="click_rate" active={sortField === "click_rate"} dir={sortDir} />
                </th>
                <th
                  className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase cursor-pointer select-none hover:text-gray-700"
                  onClick={() => toggleSort("sent_count")}
                >
                  Enviados
                  <SortIcon field="sent_count" active={sortField === "sent_count"} dir={sortDir} />
                </th>
                <th
                  className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase cursor-pointer select-none hover:text-gray-700"
                  onClick={() => toggleSort("sent_at")}
                >
                  Fecha
                  <SortIcon field="sent_at" active={sortField === "sent_at"} dir={sortDir} />
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(6)].map((_, i) => <SkeletonRow key={i} />)
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-16 text-center text-gray-400">
                    {rows.length === 0
                      ? "Todavía no hay campañas enviadas con datos de open rate."
                      : "Sin resultados para esa búsqueda."}
                  </td>
                </tr>
              ) : (
                filtered.map((row, idx) => (
                  <tr key={row.campaign_id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-3 text-gray-400 text-xs font-medium">{idx + 1}</td>
                    <td className="px-5 py-3">
                      <Link
                        href={`/campaigns/${row.campaign_id}`}
                        className="font-medium text-gray-900 hover:text-brand-600 hover:underline"
                      >
                        {row.subject}
                      </Link>
                    </td>
                    <td className="px-5 py-3 text-gray-500 text-xs">{row.campaign_name}</td>
                    <td className={`px-5 py-3 ${openRateClass(row.open_rate)}`}>
                      {row.open_rate.toFixed(1)}%
                    </td>
                    <td className={`px-5 py-3 ${clickRateClass(row.click_rate)}`}>
                      {row.click_rate.toFixed(1)}%
                    </td>
                    <td className="px-5 py-3 text-gray-600">
                      {row.sent_count.toLocaleString("es-CL")}
                    </td>
                    <td className="px-5 py-3 text-gray-400 text-xs whitespace-nowrap">
                      {row.sent_at ? formatDate(row.sent_at) : "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
