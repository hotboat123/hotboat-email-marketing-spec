"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { segmentsApi } from "@/lib/api";
import { Segment } from "@/lib/types";
import { Plus, Trash2, Filter, Users } from "lucide-react";
import Link from "next/link";
import { formatDate } from "@/lib/utils";

export default function SegmentsPage() {
  const qc = useQueryClient();
  const { data: segments = [], isLoading, isError } = useQuery<Segment[]>({
    queryKey: ["segments"],
    queryFn: () => segmentsApi.list().then((r) => r.data),
    staleTime: 5 * 60_000,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => segmentsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["segments"] }),
  });

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Segmentos</h1>
          <p className="text-gray-500 mt-1 text-sm">{segments.length} segmentos definidos</p>
        </div>
        <Link
          href="/segments/new"
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors"
        >
          <Plus size={15} />
          Nuevo segmento
        </Link>
      </div>

      {isError && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          Error al cargar segmentos.
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-xl p-5 animate-pulse">
              <div className="w-9 h-9 bg-gray-200 rounded-lg mb-3" />
              <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
              <div className="h-3 bg-gray-100 rounded w-full mb-1" />
              <div className="h-3 bg-gray-100 rounded w-1/2 mt-4" />
            </div>
          ))}
        </div>
      ) : segments.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <Filter size={40} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500 font-medium">No hay segmentos</p>
          <p className="text-gray-400 text-sm mt-1">Crea tu primer segmento para filtrar contactos</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {segments.map((seg) => (
            <div key={seg.id} className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-sm transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div className="w-9 h-9 bg-purple-100 rounded-lg flex items-center justify-center">
                  <Filter size={16} className="text-purple-600" />
                </div>
                <button
                  onClick={() => deleteMutation.mutate(seg.id)}
                  className="text-gray-300 hover:text-red-500 transition-colors"
                >
                  <Trash2 size={14} />
                </button>
              </div>
              <Link href={`/segments/${seg.id}`}>
                <h3 className="font-semibold text-gray-900 hover:text-brand-600 transition-colors">{seg.name}</h3>
              </Link>
              {seg.description && (
                <p className="text-gray-500 text-xs mt-1 line-clamp-2">{seg.description}</p>
              )}
              <div className="mt-4 flex items-center gap-1 text-sm font-medium text-gray-900">
                <Users size={14} className="text-gray-400" />
                {seg.contact_count?.toLocaleString() ?? "—"} contactos
              </div>
              <p className="text-xs text-gray-400 mt-1">{formatDate(seg.created_at)}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
