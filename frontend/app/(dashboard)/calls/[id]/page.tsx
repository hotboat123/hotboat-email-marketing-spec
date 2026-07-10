"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { crmApi } from "@/lib/api";
import { ContactCRM, CallActivity, CallStatus, CrmConversationMessage, CrmWebActivityEvent } from "@/lib/types";
import { formatDate, formatDateTime } from "@/lib/utils";
import { ArrowLeft, MessageCircle, MousePointerClick, PhoneCall, Bot, User } from "lucide-react";
import { statusMeta, StatusModal } from "@/components/crm/StatusModal";

const EVENT_LABELS: Record<string, string> = {
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

function Tab({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
        active ? "border-gray-900 text-gray-900" : "border-transparent text-gray-500 hover:text-gray-700"
      }`}
    >
      {label}
    </button>
  );
}

function ConversationTab({ contactId }: { contactId: number }) {
  const { data: messages = [], isLoading } = useQuery<CrmConversationMessage[]>({
    queryKey: ["crm-conversations", contactId],
    queryFn: () => crmApi.conversations(contactId).then((r) => r.data),
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

function WebActivityTab({ contactId }: { contactId: number }) {
  const { data: events = [], isLoading } = useQuery<CrmWebActivityEvent[]>({
    queryKey: ["crm-web-activity", contactId],
    queryFn: () => crmApi.webActivity(contactId).then((r) => r.data),
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

function CallHistoryTab({ contactId }: { contactId: number }) {
  const { data: activity = [], isLoading } = useQuery<CallActivity[]>({
    queryKey: ["crm-call-activity", contactId],
    queryFn: () => crmApi.callActivity(contactId).then((r) => r.data),
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

export default function CallDetailPage() {
  const params = useParams();
  const contactId = Number(params.id);
  const qc = useQueryClient();
  const [tab, setTab] = useState<"conversation" | "web" | "calls">("conversation");
  const [editing, setEditing] = useState(false);

  const { data: contact, isLoading } = useQuery<ContactCRM>({
    queryKey: ["crm-contact", contactId],
    queryFn: () => crmApi.get(contactId).then((r) => r.data),
  });

  const statusMutation = useMutation({
    mutationFn: ({ status, note }: { status: CallStatus; note: string }) =>
      crmApi.updateCallStatus(contactId, { call_status: status, note: note || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["crm-contact", contactId] });
      qc.invalidateQueries({ queryKey: ["crm-call-activity", contactId] });
      setEditing(false);
    },
  });

  if (isLoading) {
    return (
      <div className="p-8 max-w-4xl">
        <div className="h-4 bg-gray-200 rounded w-28 animate-pulse mb-6" />
        <div className="h-24 bg-gray-100 rounded-xl animate-pulse" />
      </div>
    );
  }

  if (!contact) {
    return (
      <div className="p-8">
        <Link href="/calls" className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-4">
          <ArrowLeft size={15} /> Volver
        </Link>
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          Contacto no encontrado.
        </div>
      </div>
    );
  }

  const meta = statusMeta(contact.call_status);
  const breakdown = contact.score_breakdown || {};

  return (
    <div className="p-8 max-w-4xl">
      <Link href="/calls" className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 mb-5">
        <ArrowLeft size={14} /> Volver a llamadas
      </Link>

      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{contact.name || "Sin nombre"}</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {contact.phone}
            {contact.email && <> · {contact.email}</>}
            {contact.ad_source && <> · llegó por: {contact.ad_source}</>}
          </p>
          {contact.linked_contact_id && (
            <Link href={`/contacts/${contact.linked_contact_id}`} className="text-xs text-brand-600 hover:underline">
              ver historial de emails
            </Link>
          )}
        </div>
        <button
          onClick={() => setEditing(true)}
          className={`inline-flex items-center px-3 py-1.5 rounded-full text-xs font-medium shrink-0 ${meta.color} hover:opacity-80 transition-opacity`}
        >
          {meta.label}
        </button>
      </div>

      {/* Score card */}
      <div className="bg-white border border-gray-200 rounded-xl p-4 mb-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Score de reserva</span>
          <span className="text-2xl font-bold text-gray-900">{contact.reservation_score ?? "—"}</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(breakdown).map(([key, points]) => (
            <span key={key} className="px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-600">
              {key} {points > 0 ? "+" : ""}{points}
            </span>
          ))}
          {Object.keys(breakdown).length === 0 && <span className="text-xs text-gray-400">Sin señales todavía</span>}
        </div>
        <div className="grid grid-cols-3 gap-3 mt-3 pt-3 border-t border-gray-100 text-xs text-gray-500">
          <div><span className="block text-gray-400">Veces HotBoat</span>{contact.veces_hotboat}</div>
          <div><span className="block text-gray-400">Última visita</span>{formatDate(contact.ultima_visita)}</div>
          <div><span className="block text-gray-400">Ticket medio</span>{contact.ticket_medio ? `$${Math.round(contact.ticket_medio).toLocaleString("es-CL")}` : "—"}</div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="flex gap-0 border-b border-gray-200 px-2">
          <Tab label="Conversación WhatsApp" active={tab === "conversation"} onClick={() => setTab("conversation")} />
          <Tab label="Actividad web" active={tab === "web"} onClick={() => setTab("web")} />
          <Tab label="Historial de llamadas" active={tab === "calls"} onClick={() => setTab("calls")} />
        </div>
        {tab === "conversation" && <ConversationTab contactId={contactId} />}
        {tab === "web" && <WebActivityTab contactId={contactId} />}
        {tab === "calls" && <CallHistoryTab contactId={contactId} />}
      </div>

      {editing && (
        <StatusModal
          contact={contact}
          onClose={() => setEditing(false)}
          saving={statusMutation.isPending}
          onSave={(status, note) => statusMutation.mutate({ status, note })}
        />
      )}
    </div>
  );
}
