"use client";

import { useQuery } from "@tanstack/react-query";
import { crmApi } from "@/lib/api";
import { AnonymousVisit } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";
import { X, Globe } from "lucide-react";

const EVENT_LABELS: Record<string, { icon: string; label: string }> = {
  page_visit: { icon: "👀", label: "Entró a la página" },
  page_visit_booking: { icon: "👀", label: "Entró a la página de reservas" },
  view_reservar: { icon: "🗓️", label: "Fue al calendario de reservas" },
  click_reservar: { icon: "🗓️", label: "Hizo clic en Reservar" },
  date_selected: { icon: "📅", label: "Seleccionó una fecha" },
  view_prices: { icon: "💰", label: "Vio los precios" },
  view_precio: { icon: "💰", label: "Vio los precios" },
  view_features: { icon: "⚡", label: "Vio las características" },
  view_incluye: { icon: "⚡", label: "Vio qué incluye" },
  view_ubicacion: { icon: "📍", label: "Vio cómo llegar" },
  view_alojamientos: { icon: "🏠", label: "Vio la lista de alojamientos" },
  view_alojamiento_detail: { icon: "🔍", label: "Vio el detalle de un alojamiento" },
  view_experiencias: { icon: "🎭", label: "Vio otras experiencias" },
  view_packs: { icon: "📦", label: "Vio los packs completos" },
  view_arma_pack: { icon: "🛠️", label: "Exploró Arma tu Pack" },
  solicitud_form: { icon: "📋", label: "Abrió el formulario de solicitud" },
  booking_completed: { icon: "🎉", label: "Completó una reserva" },
  click_whatsapp: { icon: "💬", label: "Hizo clic para escribir por WhatsApp" },
  faq_open: { icon: "❓", label: "Abrió una pregunta frecuente" },
  exit: { icon: "🚪", label: "Salió de la página" },
};

export function AnonymousVisitModal({
  sessionId,
  onClose,
}: {
  sessionId: string;
  onClose: () => void;
}) {
  const { data: visit, isLoading } = useQuery<AnonymousVisit>({
    queryKey: ["anonymous-visit", sessionId],
    queryFn: () => crmApi.anonymousVisit(sessionId).then((r) => r.data),
    staleTime: 60_000,
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-lg w-full max-w-md max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div>
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <Globe size={15} className="text-brand-600" /> Actividad del visitante
            </h3>
            {visit && (
              <p className="text-xs text-gray-400 mt-0.5">{visit.classification} · {visit.classification_desc}</p>
            )}
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 shrink-0">
            <X size={18} />
          </button>
        </div>

        <div className="overflow-y-auto px-5 py-3">
          {isLoading ? (
            [...Array(4)].map((_, i) => (
              <div key={i} className="h-8 bg-gray-100 rounded animate-pulse my-2" />
            ))
          ) : !visit || visit.events.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">No hay actividad registrada para esta visita.</p>
          ) : (
            <>
              <p className="text-xs text-gray-400 mb-2">
                {formatDateTime(visit.started_at)}
                {visit.referrer ? ` · llegó desde ${visit.referrer.replace(/^https?:\/\//, "")}` : ""}
              </p>
              <ol className="space-y-2">
                {visit.events.map((ev, i) => {
                  const meta = EVENT_LABELS[ev.event] || { icon: "•", label: ev.event };
                  return (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <span className="text-gray-400 text-xs tabular-nums w-10 shrink-0 pt-0.5">{ev.time || "—"}</span>
                      <span>{meta.icon}</span>
                      <span className="text-gray-700">
                        {meta.label}
                        {ev.date ? <strong className="ml-1">{ev.date}</strong> : null}
                      </span>
                    </li>
                  );
                })}
              </ol>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
