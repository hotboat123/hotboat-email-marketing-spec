"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { adsApi } from "@/lib/api";
import { AdLevel, AdSummary } from "@/lib/types";
import { LineChart, ArrowUpDown } from "lucide-react";

const LEVELS: { value: AdLevel; label: string }[] = [
  { value: "ad", label: "Anuncios" },
  { value: "adset", label: "Conjuntos de anuncios" },
  { value: "campaign", label: "Campañas" },
];

type SortKey = "spend" | "clicks" | "cpc" | "conversations_started" | "cost_per_conversation";

const SORT_COLUMNS: { key: SortKey; label: string }[] = [
  { key: "spend", label: "Gasto" },
  { key: "clicks", label: "Clicks" },
  { key: "cpc", label: "CPC" },
  { key: "conversations_started", label: "Conversaciones" },
  { key: "cost_per_conversation", label: "Costo/conversación" },
];

function money(n: number | null) {
  return n == null ? <span className="text-gray-300">—</span> : `$${n.toLocaleString("es-CL")}`;
}

function SkeletonRow() {
  return (
    <tr className="border-b border-gray-100">
      {[...Array(7)].map((_, i) => (
        <td key={i} className="px-5 py-3">
          <div className="h-4 bg-gray-100 rounded animate-pulse w-20" />
        </td>
      ))}
    </tr>
  );
}

export default function AnunciosPage() {
  const [level, setLevel] = useState<AdLevel>("ad");
  const [sortKey, setSortKey] = useState<SortKey>("spend");
  const [sortDesc, setSortDesc] = useState(true);
  const [minSpend, setMinSpend] = useState("");

  const { data, isLoading, isError } = useQuery<AdSummary[]>({
    queryKey: ["ads-summary", level],
    queryFn: () => adsApi.summary(level).then((r) => r.data),
    staleTime: 5 * 60_000,
  });

  const rows = useMemo(() => {
    let list = data ?? [];
    const min = minSpend ? Number(minSpend) : null;
    if (min != null) list = list.filter((r) => r.spend >= min);
    return [...list].sort((a, b) => {
      const av = a[sortKey] ?? -1;
      const bv = b[sortKey] ?? -1;
      return sortDesc ? bv - av : av - bv;
    });
  }, [data, minSpend, sortKey, sortDesc]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) setSortDesc((d) => !d);
    else {
      setSortKey(key);
      setSortDesc(true);
    }
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Anuncios</h1>
        <p className="text-sm text-gray-500 mt-1">
          Gasto, CPC y costo por conversación desde Meta Ads — hacé clic en una fila para ver su evolución en el tiempo.
        </p>
      </div>

      <div className="flex items-center gap-3 mb-4">
        <div className="flex bg-gray-100 rounded-lg p-1">
          {LEVELS.map((l) => (
            <button
              key={l.value}
              onClick={() => setLevel(l.value)}
              className={`px-3.5 py-1.5 rounded-md text-sm font-medium transition-colors ${
                level === l.value ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {l.label}
            </button>
          ))}
        </div>
        <input
          type="number"
          placeholder="Gasto mínimo ($)"
          value={minSpend}
          onChange={(e) => setMinSpend(e.target.value)}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 w-40 focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
      </div>

      {isError && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          No se pudo cargar — puede que los datos de Meta Ads no estén disponibles en este entorno.
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[900px]">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase sticky left-0 bg-gray-50">
                  {LEVELS.find((l) => l.value === level)?.label.replace(/s$/, "")}
                </th>
                {level !== "campaign" && (
                  <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Campaña</th>
                )}
                {level === "ad" && (
                  <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Conjunto</th>
                )}
                {SORT_COLUMNS.map((c) => (
                  <th
                    key={c.key}
                    onClick={() => toggleSort(c.key)}
                    className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase cursor-pointer hover:text-gray-700 select-none"
                  >
                    <span className="inline-flex items-center gap-1">
                      {c.label}
                      {sortKey === c.key && <ArrowUpDown size={11} />}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(8)].map((_, i) => <SkeletonRow key={i} />)
              ) : rows.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-16 text-center">
                    <LineChart size={32} className="mx-auto text-gray-300 mb-2" />
                    <p className="text-gray-400 text-sm">Sin datos de Meta Ads disponibles.</p>
                  </td>
                </tr>
              ) : (
                rows.map((row) => (
                  <tr key={row.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-3 sticky left-0 bg-white">
                      <Link
                        href={`/anuncios/${level}/${encodeURIComponent(row.id)}`}
                        className="font-medium text-gray-900 hover:text-brand-600 hover:underline max-w-[220px] truncate block"
                        title={row.name}
                      >
                        {row.name}
                      </Link>
                      {row.status && (
                        <span
                          className={`text-[11px] font-medium ${row.status === "ACTIVE" ? "text-green-600" : "text-gray-400"}`}
                        >
                          {row.status === "ACTIVE" ? "Activo" : row.status}
                        </span>
                      )}
                    </td>
                    {level !== "campaign" && (
                      <td className="px-5 py-3 text-gray-500 text-xs max-w-[180px] truncate" title={row.campaign_name || ""}>
                        {row.campaign_name || <span className="text-gray-300">—</span>}
                      </td>
                    )}
                    {level === "ad" && (
                      <td className="px-5 py-3 text-gray-500 text-xs max-w-[160px] truncate" title={row.adset_name || ""}>
                        {row.adset_name || <span className="text-gray-300">—</span>}
                      </td>
                    )}
                    <td className="px-5 py-3 text-right text-gray-700 tabular-nums">{money(row.spend)}</td>
                    <td className="px-5 py-3 text-right text-gray-500 tabular-nums">{row.clicks.toLocaleString("es-CL")}</td>
                    <td className="px-5 py-3 text-right text-gray-500 tabular-nums">{money(row.cpc)}</td>
                    <td className="px-5 py-3 text-right text-gray-500 tabular-nums">{row.conversations_started.toLocaleString("es-CL")}</td>
                    <td className="px-5 py-3 text-right text-gray-500 tabular-nums">{money(row.cost_per_conversation)}</td>
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
