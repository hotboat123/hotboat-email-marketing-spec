"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { templatesApi } from "@/lib/api";
import { Template } from "@/lib/types";
import { Plus, Copy, Trash2, Eye, X, Search } from "lucide-react";
import Link from "next/link";
import { formatDate } from "@/lib/utils";

function TemplateSkeleton() {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden animate-pulse">
      <div className="bg-gray-100 h-40" />
      <div className="p-4 space-y-2">
        <div className="h-4 bg-gray-200 rounded w-3/4" />
        <div className="h-3 bg-gray-100 rounded w-full" />
        <div className="h-3 bg-gray-100 rounded w-1/3 mt-3" />
      </div>
    </div>
  );
}

function PreviewModal({ tpl, onClose }: { tpl: Template; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl mx-4 flex flex-col"
        style={{ maxHeight: "90vh" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h3 className="font-semibold text-gray-900">{tpl.name}</h3>
            <p className="text-xs text-gray-400 mt-0.5">{tpl.subject_default}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 transition-colors">
            <X size={20} />
          </button>
        </div>
        <div className="flex-1 overflow-hidden p-4">
          <iframe
            srcDoc={tpl.html_content}
            sandbox="allow-same-origin"
            title={tpl.name}
            className="w-full h-full rounded-lg border border-gray-100"
            style={{ minHeight: "520px" }}
          />
        </div>
      </div>
    </div>
  );
}

export default function TemplatesPage() {
  const qc = useQueryClient();
  const [preview, setPreview] = useState<Template | null>(null);
  const [search, setSearch]   = useState("");

  const { data: templates = [], isLoading, isError } = useQuery<Template[]>({
    queryKey: ["templates"],
    queryFn: () => templatesApi.list().then((r) => r.data),
    staleTime: 5 * 60_000,
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
      {preview && <PreviewModal tpl={preview} onClose={() => setPreview(null)} />}

      <div className="flex items-center justify-between mb-6">
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

      {/* Buscador */}
      <div className="relative mb-6 max-w-sm">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar plantilla..."
          className="w-full pl-9 pr-8 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
        />
        {search && (
          <button onClick={() => setSearch("")} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
            <X size={14} />
          </button>
        )}
      </div>

      {isError && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          Error al cargar plantillas. Verifica tu conexion.
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => <TemplateSkeleton key={i} />)}
        </div>
      ) : (() => {
        const filtered = search.trim()
          ? templates.filter(t =>
              t.name.toLowerCase().includes(search.toLowerCase()) ||
              t.subject_default.toLowerCase().includes(search.toLowerCase())
            )
          : templates;
        return filtered.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center mx-auto mb-3">
              <Search size={20} className="text-gray-400" />
            </div>
            {search ? (
              <>
                <p className="text-gray-500 font-medium">Sin resultados para "{search}"</p>
                <button onClick={() => setSearch("")} className="mt-3 text-sm text-brand-600 hover:underline">Limpiar búsqueda</button>
              </>
            ) : (
              <>
                <p className="text-gray-500 font-medium">No hay plantillas</p>
                <p className="text-gray-400 text-sm mt-1">Crea tu primera plantilla de email</p>
                <Link href="/templates/new" className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors">
                  <Plus size={14} /> Crear plantilla
                </Link>
              </>
            )}
          </div>
        ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((tpl) => (
            <div key={tpl.id} className="bg-white border border-gray-200 rounded-xl overflow-hidden hover:shadow-md transition-shadow group">
              {/* HTML preview thumbnail */}
              <div
                className="bg-gray-50 h-40 relative overflow-hidden border-b border-gray-100 cursor-pointer"
                onClick={() => setPreview(tpl)}
              >
                <iframe
                  srcDoc={tpl.html_content}
                  sandbox="allow-same-origin"
                  title={tpl.name}
                  className="absolute top-0 left-0 border-0 pointer-events-none"
                  style={{ width: "600px", height: "500px", transform: "scale(0.37)", transformOrigin: "top left" }}
                />
                <div className="absolute inset-0 bg-transparent group-hover:bg-black/5 transition-colors flex items-center justify-center">
                  <div className="opacity-0 group-hover:opacity-100 transition-opacity bg-white/90 rounded-lg px-3 py-1.5 text-xs font-medium text-gray-700 flex items-center gap-1.5">
                    <Eye size={13} /> Vista previa
                  </div>
                </div>
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
                    onClick={() => setPreview(tpl)}
                    title="Vista previa"
                    className="p-1.5 text-gray-400 hover:text-brand-600 transition-colors"
                  >
                    <Eye size={14} />
                  </button>
                  <button
                    onClick={() => dupMutation.mutate(tpl.id)}
                    title="Duplicar"
                    className="p-1.5 text-gray-400 hover:text-gray-700 transition-colors"
                  >
                    <Copy size={14} />
                  </button>
                  <button
                    onClick={() => {
                      if (confirm("Eliminar esta plantilla?")) delMutation.mutate(tpl.id);
                    }}
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
        );
      })()}
    </div>
  );
}
