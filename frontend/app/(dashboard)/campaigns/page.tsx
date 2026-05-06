"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery, useQueries, useMutation, useQueryClient } from "@tanstack/react-query";
import { campaignsApi, segmentsApi } from "@/lib/api";
import { Campaign, CampaignConversions, CampaignStats, Segment } from "@/lib/types";
import {
  Plus, Send, Trash2, FlaskConical, MoreHorizontal, Mail,
  Search, CheckCircle, Pencil, ChevronDown,
} from "lucide-react";
import Link from "next/link";
import { formatDateTime, statusColor, statusLabel } from "@/lib/utils";

// ─── Status badge ────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium ${statusColor(status)}`}>
      {statusLabel(status)}
    </span>
  );
}

// ─── Stat cell ────────────────────────────────────────────────────────────────
function StatCell({
  pct,
  sub,
  highlight = false,
}: {
  pct: string;
  sub: string;
  highlight?: boolean;
}) {
  return (
    <div>
      <p className={`font-semibold text-sm ${highlight ? "text-brand-600" : "text-gray-900"}`}>{pct}</p>
      <p className="text-gray-400 text-xs mt-0.5">{sub}</p>
    </div>
  );
}

// ─── Actions dropdown ─────────────────────────────────────────────────────────
function ActionsMenu({
  campaign,
  onTest,
  onSend,
  onDelete,
}: {
  campaign: Campaign;
  onTest: () => void;
  onSend: () => void;
  onDelete: () => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handle(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, [open]);

  const canSend = campaign.status === "draft" || campaign.status === "scheduled";
  const canDelete = campaign.status === "draft";

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-700 transition-colors"
      >
        <MoreHorizontal size={16} />
      </button>
      {open && (
        <div className="absolute right-0 top-8 z-20 bg-white border border-gray-200 rounded-lg shadow-lg w-44 py-1 text-sm">
          <Link
            href={`/campaigns/${campaign.id}`}
            className="flex items-center gap-2.5 px-3.5 py-2 hover:bg-gray-50 text-gray-700"
            onClick={() => setOpen(false)}
          >
            <Pencil size={13} className="text-gray-400" /> Ver / editar
          </Link>
          {canSend && (
            <>
              <button
                onClick={() => { setOpen(false); onTest(); }}
                className="w-full flex items-center gap-2.5 px-3.5 py-2 hover:bg-gray-50 text-gray-700"
              >
                <FlaskConical size={13} className="text-gray-400" /> Enviar prueba
              </button>
              <button
                onClick={() => { setOpen(false); onSend(); }}
                className="w-full flex items-center gap-2.5 px-3.5 py-2 hover:bg-gray-50 text-gray-700"
              >
                <Send size={13} className="text-gray-400" /> Enviar ahora
              </button>
            </>
          )}
          {canDelete && (
            <>
              <div className="border-t border-gray-100 my-1" />
              <button
                onClick={() => { setOpen(false); onDelete(); }}
                className="w-full flex items-center gap-2.5 px-3.5 py-2 hover:bg-red-50 text-red-600"
              >
                <Trash2 size={13} /> Eliminar
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Skeleton row ─────────────────────────────────────────────────────────────
function SkeletonRow() {
  return (
    <tr className="border-b border-gray-100">
      <td className="px-5 py-3.5">
        <div className="h-4 bg-gray-200 rounded w-48 animate-pulse mb-1.5" />
        <div className="h-3 bg-gray-100 rounded w-32 animate-pulse" />
      </td>
      <td className="px-5 py-3.5"><div className="h-4 w-4 bg-gray-100 rounded animate-pulse" /></td>
      <td className="px-5 py-3.5"><div className="h-5 bg-gray-100 rounded-full w-16 animate-pulse" /></td>
      <td className="px-5 py-3.5"><div className="h-4 bg-gray-100 rounded w-28 animate-pulse" /></td>
      <td className="px-5 py-3.5"><div className="h-4 bg-gray-100 rounded w-16 animate-pulse" /></td>
      <td className="px-5 py-3.5"><div className="h-4 bg-gray-100 rounded w-16 animate-pulse" /></td>
      <td className="px-5 py-3.5"><div className="h-4 bg-gray-100 rounded w-20 animate-pulse" /></td>
      <td className="px-5 py-3.5" />
    </tr>
  );
}

// ─── Status filter options ────────────────────────────────────────────────────
const STATUS_OPTS = [
  { value: "", label: "Todos" },
  { value: "sent", label: "Enviadas" },
  { value: "draft", label: "Borradores" },
  { value: "scheduled", label: "Programadas" },
  { value: "sending", label: "Enviando" },
  { value: "cancelled", label: "Canceladas" },
];

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function CampaignsPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [statusOpen, setStatusOpen] = useState(false);
  const statusRef = useRef<HTMLDivElement>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    function h(e: MouseEvent) {
      if (statusRef.current && !statusRef.current.contains(e.target as Node)) setStatusOpen(false);
    }
    if (statusOpen) document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [statusOpen]);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 6000);
  };

  const { data: campaigns = [], isLoading, isError } = useQuery<Campaign[]>({
    queryKey: ["campaigns"],
    queryFn: () => campaignsApi.list().then((r) => r.data),
    staleTime: 2 * 60_000,
  });

  const { data: segments = [] } = useQuery<Segment[]>({
    queryKey: ["segments"],
    queryFn: () => segmentsApi.list().then((r) => r.data),
    staleTime: 5 * 60_000,
  });

  const segMap = Object.fromEntries(segments.map((s) => [s.id, s]));

  // Fetch stats + conversions for sent campaigns only
  const sentCampaigns = campaigns.filter((c) => c.status === "sent");
  const statsQueries = useQueries({
    queries: sentCampaigns.map((c) => ({
      queryKey: ["campaign-stats", c.id],
      queryFn: () => campaignsApi.stats(c.id).then((r) => r.data as CampaignStats),
      staleTime: 10 * 60_000,
    })),
  });
  const statsMap: Record<number, CampaignStats> = {};
  statsQueries.forEach((q) => {
    if (q.data) statsMap[q.data.campaign_id] = q.data;
  });

  const convQueries = useQueries({
    queries: sentCampaigns.map((c) => ({
      queryKey: ["campaign-conversions", c.id],
      queryFn: () => campaignsApi.conversions(c.id).then((r) => r.data as CampaignConversions),
      staleTime: 15 * 60_000,
    })),
  });
  const convMap: Record<number, CampaignConversions> = {};
  convQueries.forEach((q) => {
    if (q.data) convMap[q.data.campaign_id] = q.data;
  });

  const sendMutation = useMutation({
    mutationFn: (id: number) => campaignsApi.send(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaigns"] }),
  });

  const testMutation = useMutation({
    mutationFn: (id: number) => campaignsApi.sendTest(id),
    onSuccess: (res) => showToast(`Prueba enviada a ${res.data?.sent_to ?? "tu correo"}`),
  });

  const delMutation = useMutation({
    mutationFn: (id: number) => campaignsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaigns"] }),
  });

  // Filtered list
  const filtered = campaigns.filter((c) => {
    const matchSearch =
      !search ||
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.subject.toLowerCase().includes(search.toLowerCase());
    const matchStatus = !statusFilter || c.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const activeStatusLabel = STATUS_OPTS.find((o) => o.value === statusFilter)?.label ?? "Estado";

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Campañas</h1>
        <Link
          href="/campaigns/new"
          className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors"
        >
          <Plus size={15} />
          Crear campaña
        </Link>
      </div>

      {/* Toast */}
      {toast && (
        <div className="mb-4 bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg px-4 py-3 flex items-center gap-2">
          <CheckCircle size={15} />
          {toast}
        </div>
      )}
      {isError && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          Error al cargar campañas.
        </div>
      )}

      {/* Filter bar */}
      <div className="flex items-center gap-2.5 mb-5 flex-wrap">
        {/* Search */}
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar campañas"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 pr-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent w-52"
          />
        </div>

        {/* Status filter */}
        <div className="relative" ref={statusRef}>
          <button
            onClick={() => setStatusOpen(!statusOpen)}
            className={`flex items-center gap-1.5 px-3 py-2 border rounded-lg text-sm font-medium transition-colors ${
              statusFilter
                ? "border-brand-500 text-brand-700 bg-brand-50"
                : "border-gray-300 text-gray-600 bg-white hover:bg-gray-50"
            }`}
          >
            {activeStatusLabel}
            {statusFilter && (
              <span
                onClick={(e) => { e.stopPropagation(); setStatusFilter(""); }}
                className="ml-1 text-brand-500 hover:text-brand-700 font-bold text-xs"
              >
                ×
              </span>
            )}
            {!statusFilter && <ChevronDown size={13} />}
          </button>
          {statusOpen && (
            <div className="absolute left-0 top-10 z-20 bg-white border border-gray-200 rounded-lg shadow-lg w-44 py-1 text-sm">
              {STATUS_OPTS.map((o) => (
                <button
                  key={o.value}
                  onClick={() => { setStatusFilter(o.value); setStatusOpen(false); }}
                  className={`w-full text-left px-3.5 py-2 hover:bg-gray-50 ${
                    statusFilter === o.value ? "text-brand-600 font-medium" : "text-gray-700"
                  }`}
                >
                  {o.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Count */}
        <span className="text-xs text-gray-400 ml-auto">
          {filtered.length} campaña{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Campaña</th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Tipo</th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Estado</th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Fecha envío</th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Tasa apertura</th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Tasa clics</th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Reservas <span className="normal-case font-normal text-gray-400">(60 días)</span></th>
              <th className="px-5 py-3" />
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              [...Array(5)].map((_, i) => <SkeletonRow key={i} />)
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-5 py-16 text-center">
                  <Send size={36} className="mx-auto text-gray-300 mb-3" />
                  <p className="text-gray-500 font-medium">
                    {search || statusFilter ? "Sin resultados" : "No hay campañas"}
                  </p>
                  <p className="text-gray-400 text-xs mt-1">
                    {search || statusFilter ? "Prueba con otros filtros" : "Crea tu primera campaña de email"}
                  </p>
                  {!search && !statusFilter && (
                    <Link
                      href="/campaigns/new"
                      className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors"
                    >
                      <Plus size={14} /> Crear campaña
                    </Link>
                  )}
                </td>
              </tr>
            ) : (
              filtered.map((c) => {
                const seg = segMap[c.segment_id];
                const stats = statsMap[c.id];
                const conv = convMap[c.id];
                const hasSent = c.status === "sent";
                return (
                  <tr key={c.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                    {/* Campaign name + audience */}
                    <td className="px-5 py-3.5 max-w-xs">
                      <Link href={`/campaigns/${c.id}`} className="group">
                        <p className="font-medium text-brand-600 group-hover:underline truncate">{c.name}</p>
                        <p className="text-gray-400 text-xs mt-0.5 truncate">
                          {seg?.name ?? `Segmento #${c.segment_id}`}
                        </p>
                      </Link>
                    </td>

                    {/* Message type */}
                    <td className="px-5 py-3.5">
                      <Mail size={16} className="text-gray-400" />
                    </td>

                    {/* Status */}
                    <td className="px-5 py-3.5">
                      <StatusBadge status={c.status} />
                    </td>

                    {/* Send date */}
                    <td className="px-5 py-3.5 text-xs text-gray-500 whitespace-nowrap">
                      {formatDateTime(c.sent_at) || formatDateTime(c.scheduled_at) || "—"}
                    </td>

                    {/* Open rate */}
                    <td className="px-5 py-3.5">
                      {hasSent && stats ? (
                        <StatCell
                          pct={`${stats.open_rate.toFixed(2)}%`}
                          sub={`${stats.opened.toLocaleString()} destinatarios`}
                        />
                      ) : hasSent ? (
                        <span className="text-gray-300 text-xs">—</span>
                      ) : (
                        <span className="text-gray-300 text-sm">—</span>
                      )}
                    </td>

                    {/* Click rate */}
                    <td className="px-5 py-3.5">
                      {hasSent && stats ? (
                        <StatCell
                          pct={`${stats.click_rate.toFixed(2)}%`}
                          sub={`${stats.clicked.toLocaleString()} destinatarios`}
                          highlight
                        />
                      ) : hasSent ? (
                        <span className="text-gray-300 text-xs">—</span>
                      ) : (
                        <span className="text-gray-300 text-sm">—</span>
                      )}
                    </td>

                    {/* Conversions / Reservas */}
                    <td className="px-5 py-3.5">
                      {hasSent && conv ? (
                        conv.bookings > 0 ? (
                          <StatCell
                            pct={`${conv.bookings} reserva${conv.bookings !== 1 ? "s" : ""}`}
                            sub={`CLP ${Math.round(conv.revenue).toLocaleString("es-CL")}`}
                            highlight
                          />
                        ) : (
                          <span className="text-gray-300 text-xs">0</span>
                        )
                      ) : hasSent ? (
                        <span className="text-gray-200 text-xs animate-pulse">···</span>
                      ) : (
                        <span className="text-gray-300 text-sm">—</span>
                      )}
                    </td>

                    {/* Actions */}
                    <td className="px-5 py-3.5">
                      <ActionsMenu
                        campaign={c}
                        onTest={() => testMutation.mutate(c.id)}
                        onSend={() => {
                          if (confirm(`¿Enviar "${c.name}" ahora?`)) sendMutation.mutate(c.id);
                        }}
                        onDelete={() => {
                          if (confirm("¿Eliminar esta campaña?")) delMutation.mutate(c.id);
                        }}
                      />
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
