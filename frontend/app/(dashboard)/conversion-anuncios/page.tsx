"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { adsApi } from "@/lib/api";
import { AdLevel, AdConversionSummary } from "@/lib/types";
import { LineChart, ArrowUpDown } from "lucide-react";
import { ConversionBookingsModal } from "@/components/ads/ConversionBookingsModal";

const LEVELS: { value: AdLevel; label: string }[] = [
  { value: "ad", label: "Anuncios" },
  { value: "adset", label: "Conjuntos de anuncios" },
  { value: "campaign", label: "Campañas" },
];

type SortKey = "spend" | "clicks" | "cpc" | "bookings" | "cost_per_booking" | "conversion_rate";

const SORT_COLUMNS: { key: SortKey; label: string }[] = [
  { key: "spend", label: "Gasto" },
  { key: "clicks", label: "Clicks" },
  { key: "cpc", label: "CPC" },
  { key: "bookings", label: "Reservas" },
  { key: "conversion_rate", label: "Conversión" },
  { key: "cost_per_booking", label: "Costo/reserva" },
];

function money(n: number | null) {
  return n == null ? <span className="text-gray-300">—</span> : `$${n.toLocaleString("es-CL")}`;
}

function pct(n: number | null) {
  return n == null ? <span className="text-gray-300">—</span> : `${n.toLocaleString("es-CL")}%`;
}

function SkeletonRow() {
  return (
    <tr className="border-b border-gray-100">
      {[...Array(8)].map((_, i) => (
        <td key={i} className="px-5 py-3">
          <div className="h-4 bg-gray-100 rounded animate-pulse w-20" />
        </td>
      ))}
    </tr>
  );
}

export default function ConversionAnunciosPage() {
  const [level, setLevel] = useState<AdLevel>("ad");
  const [sortKey, setSortKey] = useState<SortKey>("spend");
  const [sortDesc, setSortDesc] = useState(true);
  const [minSpend, setMinSpend] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [bookingsModal, setBookingsModal] = useState<{ id: string; name: string } | null>(null);

  const { data, isLoading, isError } = useQuery<AdConversionSummary[]>({
    queryKey: ["ads-conversion-summary", level, dateFrom, dateTo],
    queryFn: () => adsApi.conversionSummary(level, dateFrom, dateTo).then((r) => r.data),
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

  const totals = useMemo(() => {
    const list = data ?? [];
    const spend = list.reduce((s, r) => s + r.spend, 0);
    const bookings = list.reduce((s, r) => s + r.bookings, 0);
    const conversations = list.reduce((s, r) => s + r.conversations_started, 0);
    return {
      spend, bookings, conversations,
      conversionRate: conversations ? Math.round((bookings / conversations) * 10000) / 100 : null,
      costPerBooking: bookings ? Math.round(spend / bookings) : null,
    };
  }, [data]);

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
        <h1 className="text-2xl font-bold text-gray-900">Conversión Anuncios</h1>
        <p className="text-sm text-gray-500 mt-1">
          Gasto y reservas por anuncio, conjunto o campaña — "reservas" usa el mismo criterio de "pagó" que Tráfico Web
          (pagos/payment_status), no el de la pestaña Anuncios (reservas confirmadas). Solo cuenta reservas con un
          anuncio de Meta identificado — el total real de "pagaron" (todas las fuentes) está en Tráfico Web/Fuentes.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3 mb-4">
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
        <div className="flex items-center gap-1.5 text-sm text-gray-500">
          <span>Desde</span>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="px-2.5 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <span>Hasta</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="px-2.5 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          {(dateFrom || dateTo) && (
            <button
              onClick={() => { setDateFrom(""); setDateTo(""); }}
              className="text-xs text-gray-400 hover:text-gray-600 underline"
            >
              Limpiar
            </button>
          )}
        </div>
      </div>

      {!isLoading && data && data.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <div className="bg-white border border-gray-200 rounded-xl px-4 py-3">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Gasto total</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">{money(Math.round(totals.spend))}</p>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl px-4 py-3">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Reservas (con anuncio identificado)</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">{totals.bookings.toLocaleString("es-CL")}</p>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl px-4 py-3">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Conversión</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">{pct(totals.conversionRate)}</p>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl px-4 py-3">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Costo / reserva</p>
            <p className="text-xl font-bold text-gray-900 tabular-nums">{money(totals.costPerBooking)}</p>
          </div>
        </div>
      )}

      {isError && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          No se pudo cargar — puede que los datos de Meta Ads no estén disponibles en este entorno.
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[1000px]">
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
                  <td colSpan={8} className="px-5 py-16 text-center">
                    <LineChart size={32} className="mx-auto text-gray-300 mb-2" />
                    <p className="text-gray-400 text-sm">Sin datos de Meta Ads disponibles.</p>
                  </td>
                </tr>
              ) : (
                rows.map((row) => (
                  <tr key={row.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-3 sticky left-0 bg-white">
                      <span className="font-medium text-gray-900 max-w-[220px] truncate block" title={row.name}>
                        {row.name}
                      </span>
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
                    <td className="px-5 py-3 text-right tabular-nums">
                      {row.bookings > 0 ? (
                        <button
                          onClick={() => setBookingsModal({ id: row.id, name: row.name })}
                          className="font-medium text-brand-600 hover:underline"
                        >
                          {row.bookings.toLocaleString("es-CL")}
                        </button>
                      ) : (
                        <span className="text-gray-700 font-medium">0</span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right text-gray-500 tabular-nums">{pct(row.conversion_rate)}</td>
                    <td className="px-5 py-3 text-right text-gray-500 tabular-nums">{money(row.cost_per_booking)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <p className="text-xs text-gray-400 mt-3">
        Reservas = pago real registrado (transferencia, efectivo, tarjeta o Transbank aprobado), atribuido por nombre
        exacto de anuncio — mismo criterio que Tráfico Web/Fuentes. Solo cubre reservas cuyo contacto llegó por un clic
        directo en el anuncio de WhatsApp (Meta CTWA) con nombre identificado — es normal que este total sea menor
        al de "pagaron" en Tráfico Web, que incluye todos los canales. Cuando dos anuncios comparten nombre en Meta,
        la misma reserva puede aparecer en ambas filas — sumar la columna entre filas puede sobrecontar.
      </p>

      {bookingsModal && (
        <ConversionBookingsModal
          level={level}
          id={bookingsModal.id}
          name={bookingsModal.name}
          dateFrom={dateFrom}
          dateTo={dateTo}
          onClose={() => setBookingsModal(null)}
        />
      )}
    </div>
  );
}
