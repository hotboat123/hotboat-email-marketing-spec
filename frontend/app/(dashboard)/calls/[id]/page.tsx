"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { crmApi } from "@/lib/api";
import { ContactCRM, CallStatus } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import { ArrowLeft } from "lucide-react";
import { statusMeta, StatusModal } from "@/components/crm/StatusModal";
import { ConversationTab, WebActivityTab, CallHistoryTab } from "@/components/crm/CrmActivityTabs";

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
              ver perfil completo de email marketing
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
        {tab === "conversation" && <ConversationTab contactCrmId={contactId} />}
        {tab === "web" && <WebActivityTab contactCrmId={contactId} />}
        {tab === "calls" && <CallHistoryTab contactCrmId={contactId} />}
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
