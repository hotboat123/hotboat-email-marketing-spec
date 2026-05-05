"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { contactsApi } from "@/lib/api";
import { Contact } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import { ArrowLeft, Pencil } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

export default function ContactDetailPage({ params }: { params: { id: string } }) {
  const id = parseInt(params.id);
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);

  const { data: contact, isLoading } = useQuery<Contact>({
    queryKey: ["contact", id],
    queryFn: () => contactsApi.get(id).then((r) => r.data),
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Contact>) => contactsApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contact", id] });
      setEditing(false);
    },
  });

  if (isLoading) return <div className="p-8 text-gray-400 text-sm">Cargando...</div>;
  if (!contact) return <div className="p-8 text-gray-400 text-sm">Contacto no encontrado</div>;

  return (
    <div className="p-8 max-w-3xl">
      <Link href="/contacts" className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 mb-6">
        <ArrowLeft size={15} /> Volver a contactos
      </Link>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{contact.name || contact.email}</h1>
          <p className="text-gray-500 text-sm mt-1">{contact.email}</p>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${contact.opted_in ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
          {contact.opted_in ? "Suscrito" : "Dado de baja"}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {[
          { label: "Teléfono", value: contact.phone },
          { label: "Idioma", value: contact.language },
          { label: "Origen UTM", value: contact.origin_utm },
          { label: "Experiencias HotBoat", value: `${contact.veces_hotboat}x` },
          { label: "Última visita", value: formatDate(contact.ultima_visita) },
          { label: "Con alojamiento", value: contact.ha_alojamiento ? "Sí" : "No" },
          { label: "Ticket medio", value: contact.ticket_medio ? `$${contact.ticket_medio.toLocaleString()}` : "—" },
          { label: "Extras favoritos", value: contact.extras_favoritos?.join(", ") || "—" },
          { label: "Opt-in desde", value: formatDate(contact.opted_in_at) },
          { label: "Creado", value: formatDate(contact.created_at) },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white border border-gray-200 rounded-xl px-5 py-4">
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">{label}</p>
            <p className="text-gray-900 font-medium">{value || "—"}</p>
          </div>
        ))}
      </div>

      <div className="mt-6 flex gap-3">
        <button
          onClick={() => updateMutation.mutate({ opted_in: !contact.opted_in })}
          className="px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 transition-colors"
        >
          {contact.opted_in ? "Dar de baja" : "Reactivar suscripción"}
        </button>
      </div>
    </div>
  );
}
