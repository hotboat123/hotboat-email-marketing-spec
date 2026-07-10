"use client";

import { useQuery } from "@tanstack/react-query";
import { crmApi } from "@/lib/api";
import { CallActivity, CrmConversationMessage, CrmWebActivityEvent } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";
import { MessageCircle, MousePointerClick, PhoneCall, Bot, User } from "lucide-react";
import { statusMeta } from "@/components/crm/StatusModal";

export const EVENT_LABELS: Record<string, string> = {
  page_visit: "Visitó la página",
  view_prices: "Vio precios",
  view_features: "Vio características",
  view_ubicacion: "Vio ubicación",
  view_experiencias: "Vio experiencias",
  view_experiencia_detail: "Vio detalle de experiencia",
  view_alojamientos: "Vio alojamientos",
  view_alojamiento_detail: "Vio detalle de alojamiento",
  view_packs: "Vio packs",
  view_pack_detail: "Vio detalle de pack",
  view_reservar: "Entró a reservar",
  date_selected: "Eligió fecha",
  view_arma_pack: "Armó un pack",
  view_exp_cart: "Vio carrito de experiencia",
  cart_only_payment_ready: "Carrito listo para pagar",
  solicitud_form: "Llenó el formulario de solicitud",
  booking_completed: "Completó la reserva",
  selected_people: "Eligió cantidad de personas",
  extras_selected: "Eligió extras",
  page_left: "Abandonó la página",
};

export function ConversationTab({ contactCrmId }: { contactCrmId: number }) {
  const { data: messages = [], isLoading } = useQuery<CrmConversationMessage[]>({
    queryKey: ["crm-conversations", contactCrmId],
    queryFn: () => crmApi.conversations(contactCrmId).then((r) => r.data),
  });

  if (isLoading) return <div className="p-8 text-center text-sm text-gray-400">Cargando conversación...</div>;
  if (messages.length === 0) {
    return (
      <div className="p-12 text-center">
        <MessageCircle size={32} className="mx-auto text-gray-300 mb-2" />
        <p className="text-sm text-gray-500">Sin mensajes de WhatsApp registrados para este teléfono.</p>
      </div>
    );
  }

  const chronological = [...messages].reverse();

  return (
    <div className="p-5 space-y-3 max-h-[600px] overflow-y-auto">
      {chronological.map((m, i) => {
        const isOut = m.direction === "outgoing";
        const text = isOut ? (m.response_text || m.message_text) : (m.message_text || m.response_text);
        return (
          <div key={i} className={`flex ${isOut ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[70%] rounded-xl px-3.5 py-2 text-sm ${isOut ? "bg-brand-600 text-white" : "bg-gray-100 text-gray-800"}`}>
              <div className="flex items-center gap-1.5 mb-0.5 opacity-70 text-[10px] uppercase tracking-wide">
                {isOut ? <Bot size={11} /> : <User size={11} />}
                {isOut ? "Bot" : "Cliente"}
              </div>
              <p className="whitespace-pre-wrap break-words">{text || "—"}</p>
              <p className={`text-[10px] mt-1 ${isOut ? "text-white/70" : "text-gray-400"}`}>
                {formatDateTime(m.created_at)}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function WebActivityTab({ contactCrmId }: { contactCrmId: number }) {
  const { data: events = [], isLoading } = useQuery<CrmWebActivityEvent[]>({
    queryKey: ["crm-web-activity", contactCrmId],
    queryFn: () => crmApi.webActivity(contactCrmId).then((r) => r.data),
  });

  if (isLoading) return <div className="p-8 text-center text-sm text-gray-400">Cargando actividad web...</div>;
  if (events.length === 0) {
    return (
      <div className="p-12 text-center">
        <MousePointerClick size={32} className="mx-auto text-gray-300 mb-2" />
        <p className="text-sm text-gray-500">Sin actividad web registrada.</p>
        <p className="text-xs text-gray-400 mt-1">Solo se registra cuando el cliente hizo clic en un link de seguimiento enviado por WhatsApp.</p>
      </div>
    );
  }

  return (
    <div className="p-5">
      <ol className="relative border-l border-gray-200 ml-2 space-y-4">
        {events.map((e, i) => (
          <li key={i} className="ml-4">
            <div className="absolute w-2 h-2 bg-brand-500 rounded-full -left-[4.5px] mt-1.5 border border-white" />
            <p className="text-sm font-medium text-gray-900">{EVENT_LABELS[e.event_type] || e.event_type}</p>
            <p className="text-xs text-gray-400">
              {formatDateTime(e.recorded_at)}
              {e.extra_date && <> · fecha vista: {e.extra_date}</>}
              {e.time_label && <> · horario: {e.time_label}</>}
            </p>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function CallHistoryTab({ contactCrmId }: { contactCrmId: number }) {
  const { data: activity = [], isLoading } = useQuery<CallActivity[]>({
    queryKey: ["crm-call-activity", contactCrmId],
    queryFn: () => crmApi.callActivity(contactCrmId).then((r) => r.data),
  });

  if (isLoading) return <div className="p-8 text-center text-sm text-gray-400">Cargando historial...</div>;
  if (activity.length === 0) {
    return (
      <div className="p-12 text-center">
        <PhoneCall size={32} className="mx-auto text-gray-300 mb-2" />
        <p className="text-sm text-gray-500">Sin cambios de estado registrados todavía.</p>
      </div>
    );
  }

  return (
    <div className="p-5 space-y-3">
      {activity.map((a) => (
        <div key={a.id} className="border border-gray-100 rounded-lg p-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-900">
              {statusMeta(a.old_status || "pending").label} → {statusMeta(a.new_status).label}
            </span>
            <span className="text-xs text-gray-400">{formatDateTime(a.created_at)}</span>
          </div>
          {a.note && <p className="text-sm text-gray-600 mt-1">{a.note}</p>}
          {a.created_by && <p className="text-xs text-gray-400 mt-1">por {a.created_by}</p>}
        </div>
      ))}
    </div>
  );
}
