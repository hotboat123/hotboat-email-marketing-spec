"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { crmApi } from "@/lib/api";
import { ContactCRM, CallStatus } from "@/lib/types";
import { formatDate, formatDateTime } from "@/lib/utils";
import { PhoneCall, Download, Settings, Search, ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import { CALL_STATUSES, statusMeta, linkFunnelLabel, StatusModal } from "@/components/crm/StatusModal";
import { ScoreWeightsModal } from "@/components/crm/ScoreWeightsModal";
import { AnonymousVisitModal } from "@/components/crm/AnonymousVisitModal";

const PAGE_SIZE = 50;

function SkeletonRow() {
  return (
    <tr className="border-b border-gray-100">
      <td className="px-5 py-3"><div className="h-4 bg-gray-200 rounded w-36 animate-pulse" /></td>
      <td className="px-5 py-3"><div className="h-4 bg-gray-100 rounded w-28 animate-pulse" /></td>
      <td className="px-5 py-3"><div className="h-4 bg-gray-100 rounded w-16 animate-pulse" /></td>
      <td className="px-5 py-3"><div className="h-4 bg-gray-100 rounded w-24 animate-pulse" /></td>
      <td className="px-5 py-3"><div className="h-4 bg-gray-100 rounded w-24 animate-pulse" /></td>
      <td className="px-5 py-3"><div className="h-4 bg-gray-100 rounded w-24 animate-pulse" /></td>
      <td className="px-5 py-3"><div className="h-4 bg-gray-100 rounded w-20 animate-pulse" /></td>
      <td className="px-5 py-3"><div className="h-5 bg-gray-100 rounded-full w-20 animate-pulse" /></td>
    </tr>
  );
}

export default function CallsPage() {
  const qc = useQueryClient();
  const [callStatus, setCallStatus] = useState<string>("");
  const [minScore, setMinScore] = useState<string>("");
  const [sort, setSort] = useState<"score" | "last_interaction" | "booking" | "recent">("score");
  const [page, setPage] = useState(0);
  const [editing, setEditing] = useState<ContactCRM | null>(null);
  const [exporting, setExporting] = useState(false);
  const [showWeights, setShowWeights] = useState(false);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [viewingVisit, setViewingVisit] = useState<string | null>(null);

  // Simple debounce on search
  function handleSearch(val: string) {
    setSearch(val);
    setPage(0);
    clearTimeout((window as unknown as { _callsSt?: ReturnType<typeof setTimeout> })._callsSt);
    (window as unknown as { _callsSt?: ReturnType<typeof setTimeout> })._callsSt = setTimeout(
      () => setDebouncedSearch(val),
      300,
    );
  }

  const filters = {
    call_status: callStatus || undefined,
    min_score: minScore ? Number(minScore) : undefined,
    q: debouncedSearch || undefined,
    sort,
    skip: page * PAGE_SIZE,
    limit: PAGE_SIZE,
  };

  const { data: contacts = [], isLoading, isError, refetch } = useQuery<ContactCRM[]>({
    queryKey: ["crm-contacts", callStatus, minScore, debouncedSearch, sort, page],
    queryFn: () => crmApi.list(filters).then((r) => r.data),
    staleTime: 60_000,
    retry: 1,
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status, note }: { id: number; status: CallStatus; note: string }) =>
      crmApi.updateCallStatus(id, { call_status: status, note: note || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["crm-contacts"] });
      setEditing(null);
    },
  });

  async function handleExport() {
    setExporting(true);
    try {
      await crmApi.exportCsv({ call_status: callStatus || undefined, min_score: minScore ? Number(minScore) : undefined });
    } finally {
      setExporting(false);
    }
  }

  const hasNextPage = contacts.length === PAGE_SIZE;
  const hasPrevPage = page > 0;

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Llamadas</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowWeights(true)}
            className="flex items-center gap-2 px-3.5 py-2 border border-gray-300 text-gray-600 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
          >
            <Settings size={14} />
            Configuración
          </button>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="flex items-center gap-2 px-3.5 py-2 border border-gray-300 text-gray-600 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            <Download size={14} />
            {exporting ? "Exportando..." : "Exportar CSV"}
          </button>
        </div>
      </div>

      {isError && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3 flex items-center justify-between">
          <span>Error al cargar la cola de llamadas.</span>
          <button onClick={() => refetch()} className="text-xs font-medium underline">Reintentar</button>
        </div>
      )}
      {statusMutation.isError && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          Error al actualizar el estado.
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-5 py-3.5 border-b border-gray-100 flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="Buscar por nombre o teléfono..."
              className="pl-8 pr-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 placeholder-gray-400 w-56 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            />
          </div>
          <select
            value={callStatus}
            onChange={(e) => { setCallStatus(e.target.value); setPage(0); }}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">Todos los estados</option>
            {CALL_STATUSES.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
          <select
            value={minScore}
            onChange={(e) => { setMinScore(e.target.value); setPage(0); }}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">Cualquier score</option>
            <option value="80">Score ≥ 80</option>
            <option value="60">Score ≥ 60</option>
            <option value="40">Score ≥ 40</option>
          </select>
          <select
            value={sort}
            onChange={(e) => { setSort(e.target.value as typeof sort); setPage(0); }}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="score">Ordenar por score</option>
            <option value="last_interaction">Ordenar por último contacto</option>
            <option value="booking">Ordenar por última reserva</option>
            <option value="recent">Actividad reciente (incluye visitantes web)</option>
          </select>
          {!isLoading && (
            <span className="text-xs text-gray-400 ml-auto">
              {contacts.length < PAGE_SIZE
                ? `${contacts.length} contacto${contacts.length !== 1 ? "s" : ""}`
                : `${page * PAGE_SIZE + 1}–${page * PAGE_SIZE + contacts.length}`}
            </span>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[860px]">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Perfil</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Teléfono</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Score</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Anuncio</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Actividad web</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Último contacto</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Última reserva</th>
                <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Estado</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(8)].map((_, i) => <SkeletonRow key={i} />)
              ) : contacts.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-5 py-16 text-center">
                    <PhoneCall size={36} className="mx-auto text-gray-300 mb-3" />
                    <p className="text-gray-500 font-medium">No hay contactos en esta vista</p>
                    <p className="text-gray-400 text-xs mt-1">Prueba cambiando los filtros, o espera a que corra la próxima sincronización</p>
                  </td>
                </tr>
              ) : (
                contacts.map((c) => {
                  const meta = statusMeta(c.call_status);
                  return (
                    <tr
                      key={c.id}
                      className={`border-b border-gray-100 hover:bg-gray-50 transition-colors ${c.is_anonymous ? "opacity-70" : ""}`}
                    >
                      <td className="px-5 py-3">
                        {c.is_anonymous ? (
                          <span className="font-medium text-gray-500 italic">Visitante anónimo</span>
                        ) : (
                          <Link href={`/calls/${c.id}`} className="font-medium text-gray-900 hover:text-brand-600 hover:underline">
                            {c.name || "Sin nombre"}
                          </Link>
                        )}
                        {c.linked_contact_id && (
                          <>
                            {" · "}
                            <Link
                              href={`/contacts/${c.linked_contact_id}`}
                              className="text-xs text-brand-600 hover:underline"
                            >
                              historial de emails
                            </Link>
                          </>
                        )}
                      </td>
                      <td className="px-5 py-3 text-gray-500 text-xs whitespace-nowrap">
                        {c.phone || <span className="text-gray-300">—</span>}
                      </td>
                      <td className="px-5 py-3">
                        <span className="font-semibold text-gray-900">{c.reservation_score ?? "—"}</span>
                      </td>
                      <td className="px-5 py-3 text-gray-500 text-xs max-w-[160px] truncate">
                        {c.ad_source || <span className="text-gray-300">—</span>}
                      </td>
                      <td className="px-5 py-3 text-gray-500 text-xs whitespace-nowrap">
                        {c.is_anonymous && c.session_id ? (
                          <button
                            onClick={() => setViewingVisit(c.session_id)}
                            className="text-brand-600 hover:underline"
                          >
                            {linkFunnelLabel(c) || "Ver actividad"}
                          </button>
                        ) : (
                          linkFunnelLabel(c) || <span className="text-gray-300">—</span>
                        )}
                      </td>
                      <td className="px-5 py-3 text-gray-500 text-xs whitespace-nowrap">
                        {c.is_anonymous
                          ? (c.web_last_seen_at ? formatDateTime(c.web_last_seen_at) : <span className="text-gray-300">—</span>)
                          : (c.last_interaction_at ? formatDateTime(c.last_interaction_at) : <span className="text-gray-300">—</span>)}
                      </td>
                      <td className="px-5 py-3 text-gray-500 text-xs whitespace-nowrap">
                        {c.ultima_visita ? formatDate(c.ultima_visita) : <span className="text-gray-300">—</span>}
                      </td>
                      <td className="px-5 py-3">
                        {c.is_anonymous ? (
                          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-400">
                            No contactable
                          </span>
                        ) : (
                          <button
                            onClick={() => setEditing(c)}
                            className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${meta.color} hover:opacity-80 transition-opacity`}
                          >
                            {meta.label}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {(hasPrevPage || hasNextPage) && (
          <div className="px-5 py-3 border-t border-gray-100 flex items-center justify-between">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={!hasPrevPage}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-200 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft size={13} /> Anterior
            </button>
            <span className="text-xs text-gray-400">Página {page + 1}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasNextPage}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-200 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Siguiente <ChevronRight size={13} />
            </button>
          </div>
        )}
      </div>

      {editing && (
        <StatusModal
          contact={editing}
          onClose={() => setEditing(null)}
          saving={statusMutation.isPending}
          onSave={(status, note) => statusMutation.mutate({ id: editing.id, status, note })}
        />
      )}

      {showWeights && <ScoreWeightsModal onClose={() => setShowWeights(false)} />}

      {viewingVisit && (
        <AnonymousVisitModal sessionId={viewingVisit} onClose={() => setViewingVisit(null)} />
      )}
    </div>
  );
}
