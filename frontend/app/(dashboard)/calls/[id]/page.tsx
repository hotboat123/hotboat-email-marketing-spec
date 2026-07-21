"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { crmApi, contactsApi } from "@/lib/api";
import { ContactCRM, CallStatus, Contact } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import { ArrowLeft } from "lucide-react";
import { statusMeta, StatusModal } from "@/components/crm/StatusModal";
import { ConversationTab, WebActivityTab, CallHistoryTab } from "@/components/crm/CrmActivityTabs";
import { Tab, DetailsTab, MetricsTab, SegmentsTab, ObjectsTab, EmptyTabPlaceholder } from "@/components/crm/ContactProfileTabs";

type TabKey = "details" | "metrics" | "segments" | "objects" | "conversation" | "web" | "calls";

function ReferralCell({
  count,
  saving,
  onSave,
}: {
  count: number;
  saving: boolean;
  onSave: (value: number) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(String(count));

  if (editing) {
    return (
      <div>
        <span className="block text-gray-400">Referidos</span>
        <div className="flex items-center gap-1.5 mt-0.5">
          <input
            type="number"
            min={0}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            className="w-16 border border-gray-300 rounded px-1.5 py-0.5 text-xs text-gray-700"
            autoFocus
          />
          <button
            type="button"
            disabled={saving}
            onClick={() => {
              onSave(Math.max(0, parseInt(value, 10) || 0));
              setEditing(false);
            }}
            className="text-brand-600 hover:underline text-[11px] disabled:opacity-50"
          >
            guardar
          </button>
          <button type="button" onClick={() => setEditing(false)} className="text-gray-400 hover:underline text-[11px]">
            cancelar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <span className="block text-gray-400">Referidos</span>
      <div className="flex items-center gap-2 mt-0.5">
        <span className="text-gray-700 font-medium">{count}</span>
        <button
          type="button"
          onClick={() => {
            setValue(String(count));
            setEditing(true);
          }}
          className="text-brand-600 hover:underline text-[11px]"
        >
          editar
        </button>
        <button
          type="button"
          disabled={saving}
          onClick={() => onSave(count + 1)}
          className="text-brand-600 hover:underline text-[11px] disabled:opacity-50"
        >
          +1
        </button>
      </div>
    </div>
  );
}

export default function CallDetailPage() {
  const params = useParams();
  const contactId = Number(params.id);
  const qc = useQueryClient();
  const [tab, setTab] = useState<TabKey>("details");
  const [editing, setEditing] = useState(false);

  const { data: contact, isLoading } = useQuery<ContactCRM>({
    queryKey: ["crm-contact", contactId],
    queryFn: () => crmApi.get(contactId).then((r) => r.data),
  });

  // Perfil de email marketing vinculado (mismo teléfono), si existe — null cuando
  // este lead nunca se suscribió a email (aunque sí escriba por WhatsApp).
  const linkedContactId = contact?.linked_contact_id ?? null;
  const { data: linkedContact } = useQuery<Contact>({
    queryKey: ["contact", linkedContactId],
    queryFn: () => contactsApi.get(linkedContactId!).then((r) => r.data),
    enabled: !!linkedContactId,
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

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Contact>) => contactsApi.update(linkedContactId!, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["contact", linkedContactId] }),
  });

  const referralMutation = useMutation({
    mutationFn: (value: number) => crmApi.updateReferralCount(contactId, value),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["crm-contact", contactId] }),
  });

  if (isLoading) {
    return (
      <div className="p-8 max-w-5xl">
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
    <div className="p-8 max-w-5xl">
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
        <div className="grid grid-cols-4 gap-3 mt-3 pt-3 border-t border-gray-100 text-xs text-gray-500">
          <div><span className="block text-gray-400">Veces HotBoat</span>{contact.veces_hotboat}</div>
          <div><span className="block text-gray-400">Última visita</span>{formatDate(contact.ultima_visita)}</div>
          <div><span className="block text-gray-400">Ticket medio</span>{contact.ticket_medio ? `$${Math.round(contact.ticket_medio).toLocaleString("es-CL")}` : "—"}</div>
          <ReferralCell
            count={contact.referral_count}
            saving={referralMutation.isPending}
            onSave={(value) => referralMutation.mutate(value)}
          />
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="flex gap-0 border-b border-gray-200 px-2 overflow-x-auto">
          <Tab label="Detalles"            active={tab === "details"}     onClick={() => setTab("details")} />
          <Tab label="Métricas e insights" active={tab === "metrics"}     onClick={() => setTab("metrics")} />
          <Tab label="Listas y segmentos"  active={tab === "segments"}    onClick={() => setTab("segments")} />
          <Tab label="Objetos"             active={tab === "objects"}     onClick={() => setTab("objects")} />
          <Tab label="Conversación WhatsApp" active={tab === "conversation"} onClick={() => setTab("conversation")} />
          <Tab label="Actividad web"       active={tab === "web"}         onClick={() => setTab("web")} />
          <Tab label="Historial de llamadas" active={tab === "calls"}     onClick={() => setTab("calls")} />
        </div>

        {tab === "details" && (
          linkedContact ? (
            <DetailsTab
              contact={linkedContact}
              saving={updateMutation.isPending}
              onSave={(fields, notes, birthday) =>
                updateMutation.mutate({ custom_fields: fields, notes: notes || null, birthday: birthday || null } as Partial<Contact>)
              }
            />
          ) : <EmptyTabPlaceholder message="Este contacto no está suscrito a email marketing." />
        )}
        {tab === "metrics" && (
          linkedContact
            ? <MetricsTab contact={linkedContact} />
            : <EmptyTabPlaceholder message="Este contacto no está suscrito a email marketing." />
        )}
        {tab === "segments" && (
          linkedContact
            ? <SegmentsTab contactId={linkedContact.id} />
            : <EmptyTabPlaceholder message="Este contacto no está suscrito a email marketing." />
        )}
        {tab === "objects" && (
          linkedContact
            ? <ObjectsTab contactId={linkedContact.id} />
            : <EmptyTabPlaceholder message="Este contacto no está suscrito a email marketing." />
        )}
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
