"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { templatesApi } from "@/lib/api";
import { Template } from "@/lib/types";
import { Plus, Copy, Trash2, FileText } from "lucide-react";
import Link from "next/link";
import { formatDate } from "@/lib/utils";

export default function TemplatesPage() {
  const qc = useQueryClient();
  const { data: templates = [], isLoading } = useQuery<Template[]>({
    queryKey: ["templates"],
    queryFn: () => templatesApi.list().then((r) => r.data),
  });

  const dupMutation = useMutation({
    mutationFn: (id: number) => templatesApi.duplicate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["templates"] }),
  });

  const delMutation = useMutation({
    mutationFn: (id: number) => templatesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["templates"] }),
  });

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Plantillas</h1>
          <p className="text-gray-500 mt-1 text-sm">{templates.length} plantillas disponibles</p>
        </div>
        <Link
          href="/templates/new"
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors"
        >
          <Plus size={15} />
          Nueva plantilla
        </Link>
      </div>

      {isLoading ? (
        <div className="text-gray-400 text-sm">Cargando...</div>
      ) : templates.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <FileText size={40} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500 font-medium">No hay plantillas</p>
          <p className="text-gray-400 text-sm mt-1">Crea tu primera plantilla de email</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates.map((tpl) => (
            <div key={tpl.id} className="bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-sm transition-shadow group">
              <div className="bg-gray-50 h-32 flex items-center justify-center border-b border-gray-100">
                <FileText size={32} className="text-gray-300" />
              </div>
              <div className="p-4">
                <h3 className="font-semibold text-gray-900 truncate">{tpl.name}</h3>
                <p className="text-gray-400 text-xs mt-0.5 truncate">{tpl.subject_default}</p>
                <p className="text-gray-400 text-xs mt-2">{formatDate(tpl.created_at)}</p>
                <div className="mt-3 flex items-center gap-2">
                  <Link
                    href={`/templates/${tpl.id}`}
                    className="flex-1 text-center px-3 py-1.5 border border-gray-300 rounded-lg text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    Editar
                  </Link>
                  <button
                    onClick={() => dupMutation.mutate(tpl.id)}
                    title="Duplicar"
                    className="p-1.5 text-gray-400 hover:text-gray-700 transition-colors"
                  >
                    <Copy size={14} />
                  </button>
                  <button
                    onClick={() => delMutation.mutate(tpl.id)}
                    title="Eliminar"
                    className="p-1.5 text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
