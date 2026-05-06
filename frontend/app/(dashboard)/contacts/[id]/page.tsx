"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { contactsApi } from "@/lib/api";
import { Contact, ContactBooking } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import {
  ArrowLeft, Mail, Phone, Globe, MapPin, Calendar, Clock,
  ShoppingBag, Filter, StickyNote, Save, Plus, Trash2, ChevronDown, ChevronUp,
} from "lucide-react";
import Link from "next/link";

// ── Predefined custom-field questions ────────────────────────────────────────
const PREDEFINED: { key: string; label: string; placeholder: string }[] = [
  { key: "acompanantes",        label: "Nombres de acompañantes",     placeholder: "ej. Ana García, Pedro García" },
  { key: "hijos",               label: "Nombres de hijos",            placeholder: "ej. Sofía (8), Mateo (5)" },
  { key: "cumple_acompanantes", label: "Cumpleaños de acompañantes",  placeholder: "ej. Ana 15/03, Pedro 22/07" },
  { key: "cumple_hijos",        label: "Cumpleaños de hijos",         placeholder: "ej. Sofía 10/04, Mateo 01/09" },
  { key: "actividades",         label: "Actividades favoritas",       placeholder: "ej. wakeboard, snorkel" },
  { key: "alergias",            label: "Alergias / restricciones",    placeholder: "ej. sin gluten" },
];

const STATUS_COLORS: Record<string, string> = {
  completed:  "bg-green-100 text-green-700",
  confirmed:  "bg-blue-100 text-blue-700",
  pending:    "bg-yellow-100 text-yellow-700",
  cancelled:  "bg-red-100 text-red-700",
  no_show:    "bg-gray-100 text-gray-500",
};

function initials(name: string | null, email: string) {
  if (name) return name.split(" ").slice(0, 2).map((w) => w[0]).join("").toUpperCase();
  return email[0].toUpperCase();
}

// ── Custom fields editor ──────────────────────────────────────────────────────
function CustomFieldsCard({
  contact,
  onSave,
  saving,
}: {
  contact: Contact;
  onSave: (fields: Record<string, string>, notes: string, birthday: string) => void;
  saving: boolean;
}) {
  const [fields, setFields] = useState<Record<string, string>>(contact.custom_fields ?? {});
  const [notes, setNotes] = useState(contact.notes ?? "");
  const [birthday, setBirthday] = useState(contact.birthday ?? "");
  const [newKey, setNewKey] = useState("");
  const [showCustom, setShowCustom] = useState(false);

  const allPredefined = PREDEFINED.map((p) => p.key);
  const customKeys = Object.keys(fields).filter((k) => !allPredefined.includes(k));
  const dirty =
    JSON.stringify(fields) !== JSON.stringify(contact.custom_fields ?? {}) ||
    notes !== (contact.notes ?? "") ||
    birthday !== (contact.birthday ?? "");

  function setField(key: string, val: string) {
    setFields((prev) => ({ ...prev, [key]: val }));
  }
  function removeCustomKey(key: string) {
    setFields((prev) => { const n = { ...prev }; delete n[key]; return n; });
  }
  function addCustomKey() {
    const k = newKey.trim().toLowerCase().replace(/\s+/g, "_");
    if (!k || fields[k] !== undefined) return;
    setFields((prev) => ({ ...prev, [k]: "" }));
    setNewKey("");
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
          <StickyNote size={15} className="text-gray-400" /> Perfil ampliado
        </div>
        {dirty && (
          <button
            onClick={() => onSave(fields, notes, birthday)}
            disabled={saving}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 text-white rounded-lg text-xs font-medium hover:bg-brand-700 disabled:opacity-60 transition-colors"
          >
            <Save size={12} /> {saving ? "Guardando…" : "Guardar"}
          </button>
        )}
      </div>

      <div className="p-5 space-y-4">
        {/* Birthday */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1 uppercase tracking-wider">
            Cumpleaños del cliente
          </label>
          <input
            type="date"
            value={birthday}
            onChange={(e) => setBirthday(e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        {/* Predefined fields */}
        {PREDEFINED.map(({ key, label, placeholder }) => (
          <div key={key}>
            <label className="block text-xs font-medium text-gray-500 mb-1 uppercase tracking-wider">
              {label}
            </label>
            <input
              type="text"
              value={fields[key] ?? ""}
              onChange={(e) => setField(key, e.target.value)}
              placeholder={placeholder}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
        ))}

        {/* Custom extra keys */}
        {customKeys.length > 0 && (
          <div className="space-y-3 pt-2 border-t border-gray-100">
            {customKeys.map((key) => (
              <div key={key}>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-gray-500 uppercase tracking-wider">{key}</label>
                  <button onClick={() => removeCustomKey(key)} className="text-red-400 hover:text-red-600">
                    <Trash2 size={12} />
                  </button>
                </div>
                <input
                  type="text"
                  value={fields[key]}
                  onChange={(e) => setField(key, e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
            ))}
          </div>
        )}

        {/* Add custom field */}
        <button
          onClick={() => setShowCustom((v) => !v)}
          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-brand-600 transition-colors"
        >
          <Plus size={12} /> Añadir campo personalizado
        </button>
        {showCustom && (
          <div className="flex gap-2">
            <input
              type="text"
              value={newKey}
              onChange={(e) => setNewKey(e.target.value)}
              placeholder="nombre del campo"
              className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-brand-500"
              onKeyDown={(e) => e.key === "Enter" && addCustomKey()}
            />
            <button
              onClick={addCustomKey}
              className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-xs font-medium text-gray-700 transition-colors"
            >
              Añadir
            </button>
          </div>
        )}

        {/* Notes */}
        <div className="pt-2 border-t border-gray-100">
          <label className="block text-xs font-medium text-gray-500 mb-1 uppercase tracking-wider">
            Notas internas
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            placeholder="Notas privadas sobre el cliente (no se envían en emails)"
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
      </div>
    </div>
  );
}

// ── Bookings panel ────────────────────────────────────────────────────────────
function BookingsCard({ contactId }: { contactId: number }) {
  const [expanded, setExpanded] = useState(true);
  const { data: bookings = [], isLoading } = useQuery<ContactBooking[]>({
    queryKey: ["contact-bookings", contactId],
    queryFn: () => contactsApi.bookings(contactId).then((r) => r.data),
    staleTime: 5 * 60_000,
  });

  const total = bookings.reduce((s, b) => s + (b.ingreso_total ?? 0), 0);

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full px-5 py-4 flex items-center justify-between border-b border-gray-100 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
          <ShoppingBag size={15} className="text-gray-400" />
          Historial de reservas
          {bookings.length > 0 && (
            <span className="ml-1 px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded text-xs">
              {bookings.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          {bookings.length > 0 && (
            <span className="text-sm font-bold text-gray-900">
              ${total.toLocaleString("es-CL")} total
            </span>
          )}
          {expanded ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
        </div>
      </button>

      {expanded && (
        isLoading ? (
          <div className="p-6 text-center text-sm text-gray-400">Cargando reservas…</div>
        ) : bookings.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-400">
            No se encontraron reservas en la base de datos de HotBoat.
          </div>
        ) : (
          <div className="divide-y divide-gray-50">
            {bookings.map((b, i) => {
              const extras = Object.keys(b.extras ?? {}).filter((k) => !k.startsWith("aloj__"));
              return (
                <div key={i} className="px-5 py-3.5 flex items-center gap-4">
                  <div className="w-9 h-9 rounded-lg bg-sky-50 flex items-center justify-center shrink-0">
                    <Calendar size={15} className="text-sky-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{b.fecha}</p>
                    {extras.length > 0 && (
                      <p className="text-xs text-gray-400 truncate mt-0.5">{extras.join(", ")}</p>
                    )}
                    {b.como_supieron && (
                      <p className="text-xs text-gray-400">Vía: {b.como_supieron}</p>
                    )}
                  </div>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium shrink-0 ${STATUS_COLORS[b.status] ?? "bg-gray-100 text-gray-600"}`}>
                    {b.status}
                  </span>
                  {b.ingreso_total != null && (
                    <span className="text-sm font-semibold text-gray-800 shrink-0">
                      ${b.ingreso_total.toLocaleString("es-CL")}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ContactDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const contactId = Number(id);

  const { data: contact, isLoading } = useQuery<Contact>({
    queryKey: ["contact", contactId],
    queryFn: () => contactsApi.get(contactId).then((r) => r.data),
    staleTime: 60_000,
  });

  const { data: segments = [] } = useQuery<{ id: number; name: string; description: string | null }[]>({
    queryKey: ["contact-segments", contactId],
    queryFn: () => contactsApi.segments(contactId).then((r) => r.data),
    staleTime: 2 * 60_000,
    enabled: !!contactId,
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Contact>) => contactsApi.update(contactId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["contact", contactId] }),
  });

  const deleteMutation = useMutation({
    mutationFn: () => contactsApi.delete(contactId),
    onSuccess: () => router.push("/contacts"),
  });

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="h-5 bg-gray-200 rounded w-32 animate-pulse mb-6" />
        <div className="h-20 bg-gray-100 rounded-xl animate-pulse mb-4" />
        <div className="grid grid-cols-4 gap-3">
          {[...Array(4)].map((_, i) => <div key={i} className="h-20 bg-gray-100 rounded-xl animate-pulse" />)}
        </div>
      </div>
    );
  }

  if (!contact) {
    return (
      <div className="p-8">
        <Link href="/contacts" className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-4">
          <ArrowLeft size={15} /> Volver
        </Link>
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          Contacto no encontrado.
        </div>
      </div>
    );
  }

  const avatarColor = contact.opted_in ? "bg-brand-600" : "bg-gray-400";
  const totalGasto = null; // computed in BookingsCard from real data

  return (
    <div className="p-8 max-w-5xl">
      <Link href="/contacts" className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 mb-6">
        <ArrowLeft size={15} /> Volver a contactos
      </Link>

      {/* ── Header ── */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 mb-5 flex items-start gap-5">
        <div className={`w-16 h-16 ${avatarColor} rounded-2xl flex items-center justify-center shrink-0`}>
          <span className="text-white text-2xl font-bold">{initials(contact.name, contact.email)}</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{contact.name || "Sin nombre"}</h1>
              <p className="text-gray-500 text-sm mt-0.5 flex items-center gap-1.5">
                <Mail size={13} /> {contact.email}
              </p>
              {contact.phone && (
                <p className="text-gray-500 text-sm mt-0.5 flex items-center gap-1.5">
                  <Phone size={13} /> {contact.phone}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${contact.opted_in ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                {contact.opted_in ? "Suscrito" : "Dado de baja"}
              </span>
              <button
                onClick={() => updateMutation.mutate({ opted_in: !contact.opted_in })}
                className="px-3 py-1.5 border border-gray-200 text-gray-600 rounded-lg text-xs font-medium hover:bg-gray-50 transition-colors"
              >
                {contact.opted_in ? "Dar de baja" : "Reactivar"}
              </button>
              <button
                onClick={() => { if (confirm(`¿Eliminar contacto ${contact.email}?`)) deleteMutation.mutate(); }}
                className="px-3 py-1.5 border border-red-100 text-red-500 rounded-lg text-xs font-medium hover:bg-red-50 transition-colors"
              >
                Eliminar
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Stats row ── */}
      <div className="grid grid-cols-4 gap-3 mb-5">
        {[
          { label: "Experiencias", value: `${contact.veces_hotboat}x`, icon: ShoppingBag, color: "text-sky-600 bg-sky-50" },
          { label: "Ticket medio", value: contact.ticket_medio ? `$${Math.round(contact.ticket_medio).toLocaleString("es-CL")}` : "—", icon: MapPin, color: "text-green-600 bg-green-50" },
          { label: "Última visita", value: contact.ultima_visita ? formatDate(contact.ultima_visita) : "—", icon: Calendar, color: "text-purple-600 bg-purple-50" },
          { label: "Con alojamiento", value: contact.ha_alojamiento ? "Sí" : "No", icon: Globe, color: "text-orange-600 bg-orange-50" },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white border border-gray-200 rounded-xl p-4">
            <div className={`w-8 h-8 rounded-lg ${color} flex items-center justify-center mb-2`}>
              <Icon size={15} />
            </div>
            <p className="text-xs text-gray-400 uppercase tracking-wider font-medium">{label}</p>
            <p className="text-lg font-bold text-gray-900 mt-0.5">{value}</p>
          </div>
        ))}
      </div>

      {/* ── 2-column layout ── */}
      <div className="grid grid-cols-3 gap-5 mb-5">

        {/* Left: datos + actividad */}
        <div className="col-span-2 space-y-4">

          {/* Datos de contacto */}
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">Datos de contacto</p>
            <div className="space-y-3">
              {[
                { icon: Mail,    label: "Email",    value: contact.email },
                { icon: Phone,   label: "Teléfono", value: contact.phone },
                { icon: Globe,   label: "Idioma",   value: contact.language === "es" ? "Español" : contact.language === "en" ? "English" : contact.language },
                { icon: MapPin,  label: "Origen",   value: contact.origin_utm },
                { icon: Calendar,label: "Cumpleaños", value: contact.birthday ? formatDate(contact.birthday) : null },
              ].map(({ icon: Icon, label, value }) => (
                value ? (
                  <div key={label} className="flex items-center gap-3">
                    <Icon size={14} className="text-gray-300 shrink-0" />
                    <span className="text-xs text-gray-400 w-20 shrink-0">{label}</span>
                    <span className="text-sm text-gray-800">{value}</span>
                  </div>
                ) : null
              ))}
              {contact.extras_favoritos && contact.extras_favoritos.length > 0 && (
                <div className="flex items-start gap-3">
                  <ShoppingBag size={14} className="text-gray-300 shrink-0 mt-0.5" />
                  <span className="text-xs text-gray-400 w-20 shrink-0">Extras</span>
                  <div className="flex flex-wrap gap-1">
                    {contact.extras_favoritos.map((e) => (
                      <span key={e} className="px-2 py-0.5 bg-sky-50 text-sky-700 rounded-full text-xs">{e}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Actividad */}
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">Actividad</p>
            <div className="space-y-3">
              {[
                { label: "Creado",          value: formatDate(contact.created_at) },
                { label: "Actualizado",     value: formatDate(contact.updated_at) },
                { label: "Opt-in desde",    value: contact.opted_in_at  ? formatDate(contact.opted_in_at)  : null },
                { label: "Dado de baja el", value: contact.opted_out_at ? formatDate(contact.opted_out_at) : null },
              ].filter((r) => r.value).map(({ label, value }) => (
                <div key={label} className="flex items-center gap-3">
                  <Clock size={14} className="text-gray-300 shrink-0" />
                  <span className="text-xs text-gray-400 w-28 shrink-0">{label}</span>
                  <span className="text-sm text-gray-700">{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right: segmentos */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <Filter size={14} className="text-gray-400" />
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Segmentos</p>
          </div>
          {segments.length === 0 ? (
            <p className="text-xs text-gray-400 text-center py-4">
              {contact.opted_in ? "No pertenece a ningún segmento activo." : "Sin suscripción activa."}
            </p>
          ) : (
            <div className="space-y-2">
              {segments.map((s) => (
                <Link
                  key={s.id}
                  href={`/segments/${s.id}`}
                  className="block p-3 bg-purple-50 hover:bg-purple-100 border border-purple-100 rounded-lg transition-colors"
                >
                  <p className="text-sm font-medium text-purple-800">{s.name}</p>
                  {s.description && (
                    <p className="text-xs text-purple-500 mt-0.5 truncate">{s.description}</p>
                  )}
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── Booking history ── */}
      <div className="mb-5">
        <BookingsCard contactId={contactId} />
      </div>

      {/* ── Custom fields / profile ── */}
      <CustomFieldsCard
        contact={contact}
        saving={updateMutation.isPending}
        onSave={(fields, notes, birthday) =>
          updateMutation.mutate({
            custom_fields: fields,
            notes: notes || null,
            birthday: birthday || null,
          } as Partial<Contact>)
        }
      />
    </div>
  );
}
