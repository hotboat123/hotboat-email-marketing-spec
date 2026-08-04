"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { sentEmailsApi } from "@/lib/api";
import { SentEmail, SentEmailDetail, SentEmailsPage } from "@/lib/types";
import { formatDateTime, statusLabel } from "@/lib/utils";
import { Search, Mail, ChevronLeft, ChevronRight, ArrowUp, ArrowDown, ArrowUpDown, X, Loader2 } from "lucide-react";

const PAGE_SIZE = 50;

const ORIGIN_LABEL: Record<string, string> = {
  campaign: "Campaña",
  automation: "Automatización",
  other: "Otro",
};

// Triggers técnicos de app/email/send_email.py -> etiqueta legible, para la
// columna Origen de los envíos que no vienen de una campaña/automatización
// (avisos internos, notificaciones de desuscripción, etc.)
const OTHER_TRIGGER_LABEL: Record<string, string> = {
  unsubscribe_notification: "Aviso de desuscripción",
  campaign_reminder_notification: "Recordatorio interno (campaña)",
  campaign_fired_notification: "Aviso interno (campaña enviada)",
};

function PreviewModal({ sourceType, id, onClose }: { sourceType: string; id: number; onClose: () => void }) {
  const { data, isLoading } = useQuery<SentEmailDetail>({
    queryKey: ["sent-email-detail", sourceType, id],
    queryFn: () => sentEmailsApi.detail(sourceType, id).then((r) => r.data),
    staleTime: 5 * 60_000,
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-start justify-center p-6 overflow-y-auto" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-3xl mt-10 overflow-hidden flex flex-col"
        style={{ maxHeight: "85vh" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 flex-shrink-0">
          <p className="text-sm font-semibold text-gray-800 truncate pr-4">{data?.subject ?? "Cargando…"}</p>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 p-1 flex-shrink-0">
            <X size={18} />
          </button>
        </div>
        <div className="flex-1 overflow-hidden bg-gray-50">
          {isLoading ? (
            <div className="flex items-center justify-center py-16 text-gray-400 gap-2">
              <Loader2 size={18} className="animate-spin" /> Cargando…
            </div>
          ) : !data?.available ? (
            <div className="py-16 text-center text-gray-400 text-sm px-6">
              El contenido de este correo no está disponible — se envió antes de que empezáramos
              a guardar el HTML de cada envío.
            </div>
          ) : (
            <iframe
              srcDoc={data.html ?? ""}
              sandbox=""
              title="Vista previa del correo"
              className="w-full h-full bg-white"
              style={{ minHeight: "60vh" }}
            />
          )}
        </div>
      </div>
    </div>
  );
}

const STATUS_COLOR: Record<string, string> = {
  queued: "bg-gray-100 text-gray-600",
  sent: "bg-blue-50 text-blue-700",
  delivered: "bg-green-50 text-green-700",
  opened: "bg-purple-50 text-purple-700",
  clicked: "bg-brand-50 text-brand-700",
  bounced: "bg-red-50 text-red-600",
  complained: "bg-red-50 text-red-600",
  failed: "bg-red-50 text-red-600",
};

const PROVIDER_LABEL: Record<string, string> = { ses: "SES", resend: "Resend" };

type SortBy = "at" | "email" | "subject" | "origin" | "status";
type SortDir = "asc" | "desc";

const COLUMNS: { key: SortBy; label: string; align?: "center" }[] = [
  { key: "email", label: "Email" },
  { key: "at", label: "Fecha" },
  { key: "subject", label: "Asunto" },
  { key: "origin", label: "Origen" },
  { key: "status", label: "Estado", align: "center" },
];

function SkeletonRow() {
  return (
    <tr className="border-b border-gray-100">
      <td className="px-5 py-3"><div className="h-4 bg-gray-200 rounded w-44 animate-pulse" /></td>
      <td className="px-5 py-3"><div className="h-4 bg-gray-100 rounded w-32 animate-pulse" /></td>
      <td className="px-5 py-3"><div className="h-4 bg-gray-100 rounded w-56 animate-pulse" /></td>
      <td className="px-5 py-3"><div className="h-4 bg-gray-100 rounded w-40 animate-pulse" /></td>
      <td className="px-5 py-3"><div className="h-5 bg-gray-100 rounded-full w-16 animate-pulse mx-auto" /></td>
    </tr>
  );
}

export default function SentEmailsPageRoute() {
  const [email, setEmail] = useState("");
  const [debouncedEmail, setDebouncedEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [debouncedSubject, setDebouncedSubject] = useState("");
  const [origin, setOrigin] = useState("");
  const [status, setStatus] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sortBy, setSortBy] = useState<SortBy>("at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(0);
  const [preview, setPreview] = useState<{ sourceType: string; id: number } | null>(null);

  function debounce(setDebounced: (v: string) => void) {
    return (val: string) => {
      clearTimeout((window as unknown as { _st?: ReturnType<typeof setTimeout> })._st);
      (window as unknown as { _st?: ReturnType<typeof setTimeout> })._st = setTimeout(() => {
        setDebounced(val);
        setPage(0);
      }, 300);
    };
  }

  const debounceEmail = debounce(setDebouncedEmail);
  const debounceSubject = debounce(setDebouncedSubject);

  function toggleSort(col: SortBy) {
    if (sortBy === col) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(col);
      setSortDir(col === "at" ? "desc" : "asc");
    }
    setPage(0);
  }

  const { data, isLoading, isError, refetch } = useQuery<SentEmailsPage>({
    queryKey: ["sent-emails", debouncedEmail, debouncedSubject, origin, status, dateFrom, dateTo, sortBy, sortDir, page],
    queryFn: () =>
      sentEmailsApi
        .list({
          email: debouncedEmail || undefined,
          subject: debouncedSubject || undefined,
          origin: origin || undefined,
          status: status || undefined,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
          sort_by: sortBy,
          sort_dir: sortDir,
          skip: page * PAGE_SIZE,
          limit: PAGE_SIZE,
        })
        .then((r) => r.data),
    staleTime: 60_000,
    retry: 1,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const sesCount = data?.ses_count ?? 0;
  const resendCount = data?.resend_count ?? 0;
  const hasNextPage = (page + 1) * PAGE_SIZE < total;
  const hasPrevPage = page > 0;

  return (
    <div className="p-8">
      <div className="mb-6 flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Correos enviados</h1>
          <p className="text-gray-500 mt-1 text-sm">
            Campañas y automatizaciones — {total.toLocaleString("es-CL")} envíos
          </p>
        </div>

        {/* Resumen para saber cuánto se debe pagar: cuenta por proveedor,
           independiente del filtro de proveedor mismo — así un rango de
           fechas muestra "cuántos SES en esta ventana" sin tener que elegir
           el proveedor en el dropdown primero. */}
        <div className="flex gap-3">
          <div className="bg-white rounded-xl border border-gray-200 px-4 py-2.5 text-right">
            <p className="text-lg font-bold text-gray-900 tabular-nums">{sesCount.toLocaleString("es-CL")}</p>
            <p className="text-[11px] text-gray-400 uppercase tracking-wide">vía SES</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 px-4 py-2.5 text-right">
            <p className="text-lg font-bold text-gray-500 tabular-nums">{resendCount.toLocaleString("es-CL")}</p>
            <p className="text-[11px] text-gray-400 uppercase tracking-wide">vía Resend</p>
          </div>
        </div>
      </div>

      {isError && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3 flex items-center justify-between">
          <span>Error al cargar los envíos.</span>
          <button onClick={() => refetch()} className="text-xs font-medium underline">Reintentar</button>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {/* Filtros */}
        <div className="px-5 py-3.5 border-b border-gray-100 flex flex-wrap items-center gap-3">
          <div className="relative w-56">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={email}
              onChange={(e) => { setEmail(e.target.value); debounceEmail(e.target.value); }}
              placeholder="Buscar por email..."
              className="w-full pl-8 pr-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            />
          </div>
          <div className="relative w-56">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={subject}
              onChange={(e) => { setSubject(e.target.value); debounceSubject(e.target.value); }}
              placeholder="Buscar por asunto..."
              className="w-full pl-8 pr-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
            />
          </div>
          <select
            value={origin}
            onChange={(e) => { setOrigin(e.target.value); setPage(0); }}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">Todos los orígenes</option>
            <option value="campaign">Campaña</option>
            <option value="automation">Automatización</option>
            <option value="other">Otro</option>
          </select>
          <select
            value={status}
            onChange={(e) => { setStatus(e.target.value); setPage(0); }}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">Todos los estados</option>
            <option value="queued">En cola</option>
            <option value="sent">Enviado</option>
            <option value="delivered">Entregado</option>
            <option value="opened">Abierto</option>
            <option value="clicked">Clic</option>
            <option value="bounced">Rebotado</option>
            <option value="complained">Spam</option>
            <option value="failed">Falló</option>
          </select>
          <div className="flex items-center gap-1.5">
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => { setDateFrom(e.target.value); setPage(0); }}
              className="px-2 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
            <span className="text-gray-400 text-xs">–</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => { setDateTo(e.target.value); setPage(0); }}
              className="px-2 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    onClick={() => toggleSort(col.key)}
                    className={`px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer select-none hover:text-gray-700 transition-colors ${col.align === "center" ? "text-center" : "text-left"}`}
                  >
                    <span className={`inline-flex items-center gap-1 ${col.align === "center" ? "justify-center" : ""}`}>
                      {col.label}
                      {sortBy === col.key ? (
                        sortDir === "asc" ? <ArrowUp size={12} /> : <ArrowDown size={12} />
                      ) : (
                        <ArrowUpDown size={12} className="text-gray-300" />
                      )}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(10)].map((_, i) => <SkeletonRow key={i} />)
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-16 text-center">
                    <Mail size={36} className="mx-auto text-gray-300 mb-3" />
                    <p className="text-gray-500 font-medium">Sin envíos</p>
                    <p className="text-gray-400 text-xs mt-1">Prueba con otros filtros o un rango de fechas distinto</p>
                  </td>
                </tr>
              ) : (
                items.map((it: SentEmail) => (
                  <tr
                    key={`${it.source_type}-${it.id}`}
                    onClick={() => setPreview({ sourceType: it.source_type, id: it.id })}
                    className="border-b border-gray-100 hover:bg-gray-50 transition-colors cursor-pointer"
                    title="Ver el correo enviado"
                  >
                    <td className="px-5 py-3 text-gray-700 text-xs max-w-[220px] truncate" title={it.email}>
                      {it.email}
                    </td>
                    <td className="px-5 py-3 text-gray-500 text-xs whitespace-nowrap">
                      {formatDateTime(it.at)}
                    </td>
                    <td className="px-5 py-3 text-gray-700 text-xs max-w-[320px] truncate" title={it.subject}>
                      {it.subject}
                    </td>
                    <td className="px-5 py-3 text-gray-500 text-xs">
                      {ORIGIN_LABEL[it.source_type] ?? it.source_type}
                      <span className="text-gray-300"> · </span>
                      <span className="text-gray-400">
                        {it.source_type === "other" ? (OTHER_TRIGGER_LABEL[it.source_name] ?? it.source_name) : it.source_name}
                      </span>
                      <span
                        className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-500"
                        title="Proveedor de envío"
                      >
                        {PROVIDER_LABEL[it.provider] ?? it.provider}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-center">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[it.status] ?? "bg-gray-100 text-gray-600"}`}>
                        {statusLabel(it.status)}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Paginación */}
        {(hasPrevPage || hasNextPage) && (
          <div className="px-5 py-3 border-t border-gray-100 flex items-center justify-between">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={!hasPrevPage}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-200 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft size={13} /> Anterior
            </button>
            <span className="text-xs text-gray-400">
              {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} de {total.toLocaleString("es-CL")}
            </span>
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

      {preview && (
        <PreviewModal sourceType={preview.sourceType} id={preview.id} onClose={() => setPreview(null)} />
      )}
    </div>
  );
}
