"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { crmApi } from "@/lib/api";
import { ContactCRM, CallStatus } from "@/lib/types";
import { formatDate, formatDateTime } from "@/lib/utils";
import { PhoneCall, Download, ChevronLeft, ChevronRight, X } from "lucide-react";
import Link from "next/link";

const PAGE_SIZE = 50;

const CALL_STATUSES: { value: CallStatus; label: string; color: string }[] = [
  { value: "pending", label: "Pendiente", color: "bg-gray-100 text-gray-700" },
  { value: "called", label: "Llamado", color: "bg-blue-100 text-blue-700" },
  { value: "no_answer", label: "Sin respuesta", color: "bg-yellow-100 text-yellow-700" },
  { value: "booked", label: "Reservó", color: "bg-green-100 text-green-700" },
  { value: "not_interested", label: "No interesado", color: "bg-red-100 text-red-700" },
];

function statusMeta(status: string) {
  return CALL_STATUSES.find((s) => s.value === status) ?? CALL_STATUSES[0];
}

function linkFunnelLabel(c: ContactCRM): string | null {
  if (c.link_selected_date) return "🗓️ Eligió fecha";
  if (c.link_viewed_prices) return "💲 Vio precios";
  if (c.link_clicked) return "🔗 Clic en link";
  return null;
}

function SkeletonRow() {
  return (
    <tr className="border-b border-gray-100">
      <td className="px-5 py-3"><div className="h-4 bg-gray-200 rounded w-36 animate-pulse" /></td>
      <td className="px-5 py-3"><div className="h-4 bg-gray-100 rounded w-28 animate-pulse" /></td>
      <td className="px-5 py-3"><div className="h-4 bg-gray-100 rounded w-16 animate-pulse" /></td>
      <td className="px-5 py-3"><div className="h-4 bg-gray-100 rounded w-24 animate-pulse" /></td>
      <td className="px-5 py-3"><div className="h-4 bg-gray-100 rounded w-24 animate-pulse" /></td>
      <td className="px-5 py-3"><div className="h-4 bg-gray-100 rounded w-20 animate-pulse" /></td>
      <td className="px-5 py-3"><div className="h-5 bg-gray-100 rounded-full w-20 animate-pulse" /></td>
    </tr>
  );
}

function StatusModal({
  contact,
  onClose,
  onSave,
  saving,
}: {
  contact: ContactCRM;
  onClose: () => void;
  onSave: (status: CallStatus, note: string) => void;
  saving: boolean;
}) {
  const [status, setStatus] = useState<CallStatus>(contact.call_status);
  const [note, setNote] = useState("");

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-lg w-full max-w-sm p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-900">
            {contact.name || contact.phone}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        <label className="block text-xs font-medium text-gray-500 mb-1.5">Estado</label>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value as CallStatus)}
          className="w-full mb-3 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          {CALL_STATUSES.map((s) => (
            <option key={s.value} value={s.value}>{s.label}</option>
          ))}
        </select>

        <label className="block text-xs font-medium text-gray-500 mb-1.5">Nota (opcional)</label>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={3}
          placeholder="Ej: pidió que la llamemos el viernes"
          className="w-full mb-4 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-3.5 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 rounded-lg"
          >
            Cancelar
          </button>
          <button
            onClick={() => onSave(status, note)}
            disabled={saving}
            className="px-3.5 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-50"
          >
            {saving ? "Guardando..." : "Guardar"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function CallsPage() {
  const qc = useQueryClient();
  const [callStatus, setCallStatus] = useState<string>("");
  const [minScore, setMinScore] = useState<string>("");
  const [page, setPage] = useState(0);
  const [editing, setEditing] = useState<ContactCRM | null>(null);
  const [exporting, setExporting] = useState(false);

  const filters = {
    call_status: callStatus || undefined,
    min_score: minScore ? Number(minScore) : undefined,
    skip: page * PAGE_SIZE,
    limit: PAGE_SIZE,
  };

  const { data: contacts = [], isLoading, isError, refetch } = useQuery<ContactCRM[]>({
    queryKey: ["crm-contacts", callStatus, minScore, page],
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
        <button
          onClick={handleExport}
          disabled={exporting}
          className="flex items-center gap-2 px-3.5 py-2 border border-gray-300 text-gray-600 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors"
        >
          <Download size={14} />
          {exporting ? "Exportando..." : "Exportar CSV"}
        </button>
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
        <div className="px-5 py-3.5 border-b border-gray-100 flex items-center gap-3">
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
          {!isLoading && (
            <span className="text-xs text-gray-400 ml-auto">
              {contacts.length < PAGE_SIZE
                ? `${contacts.length} contacto${contacts.length !== 1 ? "s" : ""}`
                : `${page * PAGE_SIZE + 1}–${page * PAGE_SIZE + contacts.length}`}
            </span>
          )}
        </div>

        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Perfil</th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Teléfono</th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Score</th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Anuncio</th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Actividad web</th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Última visita</th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Estado</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              [...Array(8)].map((_, i) => <SkeletonRow key={i} />)
            ) : contacts.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-5 py-16 text-center">
                  <PhoneCall size={36} className="mx-auto text-gray-300 mb-3" />
                  <p className="text-gray-500 font-medium">No hay contactos en esta vista</p>
                  <p className="text-gray-400 text-xs mt-1">Prueba cambiando los filtros, o espera a que corra la próxima sincronización</p>
                </td>
              </tr>
            ) : (
              contacts.map((c) => {
                const meta = statusMeta(c.call_status);
                return (
                  <tr key={c.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-3">
                      <div className="font-medium text-gray-900">{c.name || "Sin nombre"}</div>
                      {c.linked_contact_id && (
                        <Link
                          href={`/contacts/${c.linked_contact_id}`}
                          className="text-xs text-brand-600 hover:underline"
                        >
                          ver historial de emails
                        </Link>
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
                      {linkFunnelLabel(c) || <span className="text-gray-300">—</span>}
                    </td>
                    <td className="px-5 py-3 text-gray-500 text-xs whitespace-nowrap">
                      {c.ultima_visita ? formatDate(c.ultima_visita) : <span className="text-gray-300">—</span>}
                    </td>
                    <td className="px-5 py-3">
                      <button
                        onClick={() => setEditing(c)}
                        className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${meta.color} hover:opacity-80 transition-opacity`}
                      >
                        {meta.label}
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>

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
    </div>
  );
}
