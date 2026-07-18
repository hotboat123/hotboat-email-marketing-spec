"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { crmApi } from "@/lib/api";
import { FunnelAnalytics, FunnelRow, FunnelByAdSource } from "@/lib/types";
import { Megaphone, Smartphone, Globe, FlaskConical } from "lucide-react";

function money(n: number | null) {
  return n == null ? <span className="text-gray-300">—</span> : `$${n.toLocaleString("es-CL")}`;
}

function conversionClass(rate: number) {
  if (rate >= 15) return "text-green-600 font-bold";
  if (rate >= 5) return "text-yellow-600 font-semibold";
  return "text-gray-400";
}

function FunnelHeaderCells() {
  return (
    <>
      <th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Total</th>
      <th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Vio precios</th>
      <th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Eligió fecha</th>
      <th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Por pagar</th>
      <th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Pago confirmado</th>
      <th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Conversión</th>
    </>
  );
}

function FunnelValueCells({ row }: { row: FunnelRow }) {
  return (
    <>
      <td className="px-5 py-3 text-right text-gray-700">{row.total.toLocaleString("es-CL")}</td>
      <td className="px-5 py-3 text-right text-gray-500">{row.viewed_prices.toLocaleString("es-CL")}</td>
      <td className="px-5 py-3 text-right text-gray-500">{row.selected_date.toLocaleString("es-CL")}</td>
      <td className="px-5 py-3 text-right text-yellow-600">{row.pending_payment.toLocaleString("es-CL")}</td>
      <td className="px-5 py-3 text-right text-gray-500">{row.paid.toLocaleString("es-CL")}</td>
      <td className={`px-5 py-3 text-right ${conversionClass(row.conversion_rate)}`}>
        {row.conversion_rate.toFixed(1)}%
      </td>
    </>
  );
}

function AdSpendHeaderCells() {
  return (
    <>
      <th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Gasto</th>
      <th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">CPC</th>
      <th className="px-5 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Costo/conversación</th>
    </>
  );
}

function AdSpendValueCells({ row }: { row: FunnelByAdSource }) {
  return (
    <>
      <td className="px-5 py-3 text-right text-gray-700">{money(row.spend)}</td>
      <td className="px-5 py-3 text-right text-gray-500">{money(row.cpc)}</td>
      <td className="px-5 py-3 text-right text-gray-500">{money(row.cost_per_conversation)}</td>
    </>
  );
}

function SkeletonRow({ cols }: { cols: number }) {
  return (
    <tr className="border-b border-gray-100">
      {[...Array(cols)].map((_, i) => (
        <td key={i} className="px-5 py-3">
          <div className="h-4 bg-gray-100 rounded animate-pulse ml-auto w-16" />
        </td>
      ))}
    </tr>
  );
}

export default function EmbudoPage() {
  const router = useRouter();
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const { data, isLoading } = useQuery<FunnelAnalytics>({
    queryKey: ["crm-funnel-analytics", dateFrom, dateTo],
    queryFn: () => crmApi.funnelAnalytics(dateFrom, dateTo).then((r) => r.data),
    staleTime: 2 * 60_000,
  });

  const byAdSource = data?.by_ad_source ?? [];
  const byChannel = data?.by_channel ?? [];
  const byVariant = data?.by_bot_variant ?? [];

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Embudo de conversión</h1>
        <p className="text-sm text-gray-500 mt-1">
          Quién llega a cada etapa (vio precios → eligió fecha → pagó), por anuncio y por canal de llegada.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 text-sm text-gray-500 mb-8">
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
        <span className="text-xs text-gray-400 ml-1">Filtra por la actividad más reciente conocida de cada contacto</span>
      </div>

      {/* Por canal */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden mb-8 max-w-4xl">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
          <Smartphone size={15} className="text-brand-600" />
          <p className="font-semibold text-gray-800">Web directo vs WhatsApp</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Canal</th>
                <FunnelHeaderCells />
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(2)].map((_, i) => <SkeletonRow key={i} cols={7} />)
              ) : byChannel.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-10 text-center text-gray-400 text-sm">
                    Todavía no hay actividad web o de links de seguimiento registrada.
                  </td>
                </tr>
              ) : (
                byChannel.map((row) => (
                  <tr key={row.channel} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-3 font-medium text-gray-900 flex items-center gap-2">
                      {row.channel === "WhatsApp" ? <Smartphone size={14} className="text-green-500" /> : <Globe size={14} className="text-blue-500" />}
                      {row.channel}
                    </td>
                    <FunnelValueCells row={row} />
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Por variante de Popeye (A/B) */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden mb-8 max-w-4xl">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
          <FlaskConical size={15} className="text-brand-600" />
          <p className="font-semibold text-gray-800">Por variante de Popeye (test A/B)</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Variante</th>
                <FunnelHeaderCells />
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(2)].map((_, i) => <SkeletonRow key={i} cols={7} />)
              ) : byVariant.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-10 text-center text-gray-400 text-sm">
                    Todavía no hay ningún test A/B configurado en el bot de WhatsApp.
                  </td>
                </tr>
              ) : (
                byVariant.map((row) => (
                  <tr key={row.variant_key} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-3 font-medium text-gray-900">{row.label}</td>
                    <FunnelValueCells row={row} />
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Por anuncio */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Megaphone size={15} className="text-brand-600" />
            <p className="font-semibold text-gray-800">Por anuncio</p>
          </div>
          <p className="text-xs text-gray-400">
            Gasto/CPC/costo por conversación: solo para anuncios de Meta con datos importados. Click en la fila → evolución en el tiempo.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[1100px]">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase sticky left-0 bg-gray-50 z-10">Anuncio</th>
                <FunnelHeaderCells />
                <AdSpendHeaderCells />
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(6)].map((_, i) => <SkeletonRow key={i} cols={10} />)
              ) : byAdSource.length === 0 ? (
                <tr>
                  <td colSpan={10} className="px-5 py-10 text-center text-gray-400 text-sm">
                    Sin datos todavía.
                  </td>
                </tr>
              ) : (
                byAdSource.map((row) => {
                  const clickable = !!row.ad_id;
                  const rowContent = (
                    <>
                      <td className="px-5 py-3 font-medium text-gray-900 max-w-[240px] truncate sticky left-0 bg-white group-hover:bg-gray-50" title={row.ad_source}>
                        {row.ad_source}
                      </td>
                      <FunnelValueCells row={row} />
                      <AdSpendValueCells row={row} />
                    </>
                  );
                  return clickable ? (
                    <tr
                      key={row.ad_source}
                      className="group border-b border-gray-100 hover:bg-gray-50 transition-colors cursor-pointer"
                      onClick={() => router.push(`/anuncios/ad/${encodeURIComponent(row.ad_id!)}`)}
                    >
                      {rowContent}
                    </tr>
                  ) : (
                    <tr key={row.ad_source} className="group border-b border-gray-100 hover:bg-gray-50 transition-colors">
                      {rowContent}
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
