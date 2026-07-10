"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { CallStatus, ContactCRM } from "@/lib/types";

export const CALL_STATUSES: { value: CallStatus; label: string; color: string }[] = [
  { value: "pending", label: "Pendiente", color: "bg-gray-100 text-gray-700" },
  { value: "called", label: "Llamado", color: "bg-blue-100 text-blue-700" },
  { value: "no_answer", label: "Sin respuesta", color: "bg-yellow-100 text-yellow-700" },
  { value: "booked", label: "Reservó", color: "bg-green-100 text-green-700" },
  { value: "not_interested", label: "No interesado", color: "bg-red-100 text-red-700" },
];

export function statusMeta(status: string) {
  return CALL_STATUSES.find((s) => s.value === status) ?? CALL_STATUSES[0];
}

export function linkFunnelLabel(c: ContactCRM): string | null {
  if (c.link_selected_date) return "🗓️ Eligió fecha";
  if (c.link_viewed_prices) return "💲 Vio precios";
  if (c.link_clicked) return "🔗 Clic en link";
  return null;
}

export function StatusModal({
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
