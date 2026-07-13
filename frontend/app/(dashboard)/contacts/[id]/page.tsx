"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { contactsApi, crmApi } from "@/lib/api";
import { Contact, ContactCRM, CallStatus } from "@/lib/types";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { statusMeta, StatusModal } from "@/components/crm/StatusModal";
import { ConversationTab, WebActivityTab, CallHistoryTab } from "@/components/crm/CrmActivityTabs";
import { Tab, DetailsTab, MetricsTab, SegmentsTab, ObjectsTab, EmptyTabPlaceholder } from "@/components/crm/ContactProfileTabs";

// ─── Main page ────────────────────────────────────────────────────────────────
export default function ContactDetailPage() {
  const { id }      = useParams<{ id: string }>();
  const router      = useRouter();
  const qc          = useQueryClient();
  const contactId   = Number(id);
  const [tab, setTab] = useState<"details" | "metrics" | "segments" | "objects" | "whatsapp" | "web" | "calls">("details");
  const [editingStatus, setEditingStatus] = useState(false);

  const { data: contact, isLoading } = useQuery<Contact>({
    queryKey: ["contact", contactId],
    queryFn:  () => contactsApi.get(contactId).then((r) => r.data),
    staleTime: 60_000,
  });

  // Registro CRM (WhatsApp/telefono) vinculado a este contacto, si existe —
  // null cuando el contacto nunca escribio por WhatsApp / no tiene telefono asociado.
  const { data: crmContact } = useQuery<ContactCRM | null>({
    queryKey: ["crm-contact-by-contact", contactId],
    queryFn: () => crmApi.getByContact(contactId).then((r) => r.data).catch(() => null),
    staleTime: 60_000,
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Contact>) => contactsApi.update(contactId, data),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ["contact", contactId] }),
  });

  const deleteMutation = useMutation({
    mutationFn: () => contactsApi.delete(contactId),
    onSuccess:  () => router.push("/contacts"),
  });

  const statusMutation = useMutation({
    mutationFn: ({ status, note }: { status: CallStatus; note: string }) =>
      crmApi.updateCallStatus(crmContact!.id, { call_status: status, note: note || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["crm-contact-by-contact", contactId] });
      qc.invalidateQueries({ queryKey: ["crm-call-activity", crmContact?.id] });
      setEditingStatus(false);
    },
  });

  if (isLoading) return (
    <div className="p-8 max-w-5xl">
      <div className="h-4 bg-gray-200 rounded w-28 animate-pulse mb-6" />
      <div className="h-24 bg-gray-100 rounded-xl animate-pulse mb-4" />
      <div className="h-10 bg-gray-100 rounded animate-pulse mb-6" />
      <div className="h-64 bg-gray-100 rounded-xl animate-pulse" />
    </div>
  );

  if (!contact) return (
    <div className="p-8">
      <Link href="/contacts" className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft size={15} /> Volver
      </Link>
      <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
        Contacto no encontrado.
      </div>
    </div>
  );

  return (
    <div className="p-8 max-w-5xl">
      <Link href="/contacts" className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 mb-5">
        <ArrowLeft size={14} /> Volver a clientes
      </Link>

      {/* ── Header ── */}
      <div className="mb-0">
        <div className="flex items-start justify-between gap-4 mb-1">
          <div>
            <h1 className="text-xl font-bold text-gray-900">{contact.name || "Sin nombre"}</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {contact.email}
              {contact.phone && <> · {contact.phone}</>}
              {contact.location && <> · {contact.location}</>}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {crmContact && (
              <>
                <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700" title="Score de probabilidad de reserva">
                  Score {crmContact.reservation_score ?? "—"}
                </span>
                <button
                  onClick={() => setEditingStatus(true)}
                  className={`px-2.5 py-1 rounded-full text-xs font-medium ${statusMeta(crmContact.call_status).color} hover:opacity-80 transition-opacity`}
                >
                  {statusMeta(crmContact.call_status).label}
                </button>
              </>
            )}
            <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${contact.opted_in ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
              {contact.opted_in ? "Suscrito" : "Dado de baja"}
            </span>
            <button
              onClick={() => updateMutation.mutate({ opted_in: !contact.opted_in })}
              className="px-3 py-1.5 border border-gray-200 text-gray-600 rounded-lg text-xs font-medium hover:bg-gray-50"
            >
              {contact.opted_in ? "Dar de baja" : "Reactivar"}
            </button>
            <button
              onClick={() => { if (confirm(`¿Eliminar ${contact.email}?`)) deleteMutation.mutate(); }}
              className="px-3 py-1.5 border border-red-100 text-red-500 rounded-lg text-xs font-medium hover:bg-red-50"
            >
              Eliminar
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-0 border-b border-gray-200 mt-4 mb-6 overflow-x-auto">
          <Tab label="Detalles"            active={tab === "details"}  onClick={() => setTab("details")} />
          <Tab label="Métricas e insights" active={tab === "metrics"}  onClick={() => setTab("metrics")} />
          <Tab label="Listas y segmentos"  active={tab === "segments"} onClick={() => setTab("segments")} />
          <Tab label="Objetos"             active={tab === "objects"}  onClick={() => setTab("objects")} />
          <Tab label="WhatsApp"          active={tab === "whatsapp"} onClick={() => setTab("whatsapp")} />
          <Tab label="Actividad web"     active={tab === "web"}      onClick={() => setTab("web")} />
          <Tab label="Historial llamadas" active={tab === "calls"}   onClick={() => setTab("calls")} />
        </div>
      </div>

      {/* ── Tab content ── */}
      {tab === "details" && (
        <DetailsTab
          contact={contact}
          saving={updateMutation.isPending}
          onSave={(fields, notes, birthday) =>
            updateMutation.mutate({ custom_fields: fields, notes: notes || null, birthday: birthday || null } as Partial<Contact>)
          }
        />
      )}
      {tab === "metrics"  && <MetricsTab  contact={contact} />}
      {tab === "segments" && <SegmentsTab contactId={contactId} />}
      {tab === "objects"  && <ObjectsTab  contactId={contactId} />}
      {tab === "whatsapp" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {crmContact
            ? <ConversationTab contactCrmId={crmContact.id} />
            : <EmptyTabPlaceholder message="Este contacto no tiene conversación de WhatsApp asociada." />}
        </div>
      )}
      {tab === "web" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {crmContact
            ? <WebActivityTab contactCrmId={crmContact.id} />
            : <EmptyTabPlaceholder message="Este contacto no tiene actividad web asociada a un teléfono." />}
        </div>
      )}
      {tab === "calls" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {crmContact
            ? <CallHistoryTab contactCrmId={crmContact.id} />
            : <EmptyTabPlaceholder message="Este contacto no tiene historial de llamadas asociado." />}
        </div>
      )}

      {editingStatus && crmContact && (
        <StatusModal
          contact={crmContact}
          onClose={() => setEditingStatus(false)}
          saving={statusMutation.isPending}
          onSave={(status, note) => statusMutation.mutate({ status, note })}
        />
      )}
    </div>
  );
}
