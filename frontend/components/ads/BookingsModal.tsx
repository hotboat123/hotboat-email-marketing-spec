"use client";

import { useQuery } from "@tanstack/react-query";
import { adsApi } from "@/lib/api";
import { AdBooking, AdLevel } from "@/lib/types";
import { X, Users } from "lucide-react";

export function formatDate(d: string | null) {
  if (!d) return "—";
  const [y, m, day] = d.split("-");
  return `${day}/${m}/${y}`;
}

export function BookingsModal({
  level,
  id,
  name,
  dateFrom,
  dateTo,
  onClose,
}: {
  level: AdLevel;
  id: string;
  name: string;
  dateFrom?: string;
  dateTo?: string;
  onClose: () => void;
}) {
  const { data: bookings = [], isLoading } = useQuery<AdBooking[]>({
    queryKey: ["ad-bookings", level, id, dateFrom, dateTo],
    queryFn: () => adsApi.bookings(level, id, dateFrom, dateTo).then((r) => r.data),
    staleTime: 60_000,
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-lg w-full max-w-lg max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div>
            <h3 className="font-semibold text-gray-900 flex items-center gap-2">
              <Users size={15} className="text-brand-600" /> Reservas de "{name}"
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">Pago confirmado real, atribuido por nombre de anuncio.</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 shrink-0">
            <X size={18} />
          </button>
        </div>

        <div className="overflow-y-auto px-5 py-3">
          {isLoading ? (
            [...Array(3)].map((_, i) => (
              <div key={i} className="h-14 bg-gray-100 rounded animate-pulse my-2" />
            ))
          ) : bookings.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">No hay reservas para este filtro.</p>
          ) : (
            bookings.map((b) => (
              <div key={b.id} className="py-3 border-b border-gray-50 last:border-0">
                <div className="flex items-center justify-between">
                  <p className="font-medium text-gray-900 text-sm">{b.name || "Sin nombre"}</p>
                  <p className="text-sm text-gray-700 tabular-nums">
                    {b.amount != null ? `$${Math.round(b.amount).toLocaleString("es-CL")}` : "—"}
                  </p>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">
                  {b.phone || "sin teléfono"}{b.email ? ` · ${b.email}` : ""}
                </p>
                <p className="text-[11px] text-gray-400 mt-0.5">
                  Pagó el {formatDate(b.conversion_date)} · paseo {formatDate(b.trip_date)}
                  {b.ad_source && b.ad_source.toLowerCase() !== name.toLowerCase() ? ` · anuncio: ${b.ad_source}` : ""}
                </p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
