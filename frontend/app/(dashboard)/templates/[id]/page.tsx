"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { templatesApi } from "@/lib/api";
import { Template } from "@/lib/types";
import { ArrowLeft, Save } from "lucide-react";
import Link from "next/link";

export default function EditTemplatePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const tplId = Number(id);

  const { data: tpl, isLoading, isError } = useQuery<Template>({
    queryKey: ["template", tplId],
    queryFn: () => templatesApi.get(tplId).then((r) => r.data),
    staleTime: 0,
  });

  const [name, setName] = useState("");
  const [subject, setSubject] = useState("");
  const [previewText, setPreviewText] = useState("");
  const [html, setHtml] = useState("");
  const [tab, setTab] = useState<"editor" | "preview">("editor");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (tpl) {
      setName(tpl.name);
      setSubject(tpl.subject_default);
      setPreviewText(tpl.preview_text ?? "");
      setHtml(tpl.html_content);
    }
  }, [tpl]);

  const mutation = useMutation({
    mutationFn: () =>
      templatesApi.update(tplId, {
        name,
        subject_default: subject,
        preview_text: previewText || null,
        html_content: html,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["templates"] });
      qc.invalidateQueries({ queryKey: ["template", tplId] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    },
  });

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="h-5 bg-gray-200 rounded w-40 animate-pulse mb-6" />
        <div className="h-8 bg-gray-200 rounded w-64 animate-pulse" />
      </div>
    );
  }

  if (isError || !tpl) {
    return (
      <div className="p-8">
        <Link href="/templates" className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-4">
          <ArrowLeft size={15} /> Volver
        </Link>
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          No se encontró la plantilla.
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 h-full flex flex-col">
      <div className="flex items-center gap-4 mb-6">
        <Link href="/templates" className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900">
          <ArrowLeft size={15} /> Volver
        </Link>
        <h1 className="text-xl font-bold text-gray-900 flex-1 truncate">{tpl.name}</h1>
        {saved && (
          <span className="text-sm text-green-600 font-medium flex items-center gap-1">
            <Save size={13} /> Guardado
          </span>
        )}
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending || !name || !subject}
          className="px-5 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-60 transition-colors"
        >
          {mutation.isPending ? "Guardando..." : "Guardar cambios"}
        </button>
      </div>

      {mutation.isError && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          Error al guardar. Intenta de nuevo.
        </div>
      )}

      <div className="grid grid-cols-5 gap-6 flex-1">
        <div className="col-span-2 space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nombre interno *</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Asunto por defecto *</label>
              <input
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Preview text</label>
              <input
                value={previewText}
                onChange={(e) => setPreviewText(e.target.value)}
                placeholder="Texto que aparece en el cliente de correo"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>

          <div className="bg-brand-50 border border-brand-200 rounded-xl p-4 text-xs text-brand-700">
            <p className="font-semibold mb-2">Variables disponibles:</p>
            <ul className="space-y-0.5 font-mono">
              <li>{"{{nombre}}"} — nombre del contacto</li>
              <li>{"{{email}}"} — email</li>
              <li>{"{{ultima_visita}}"} — última visita</li>
              <li>{"{{veces_hotboat}}"} — nº experiencias</li>
              <li>{"{{ticket_medio}}"} — gasto promedio</li>
            </ul>
          </div>
        </div>

        <div className="col-span-3 flex flex-col bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="flex border-b border-gray-100">
            {(["editor", "preview"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                  tab === t ? "border-brand-600 text-brand-700" : "border-transparent text-gray-500 hover:text-gray-800"
                }`}
              >
                {t === "editor" ? "Editor HTML" : "Preview"}
              </button>
            ))}
          </div>
          {tab === "editor" ? (
            <textarea
              value={html}
              onChange={(e) => setHtml(e.target.value)}
              className="flex-1 p-4 font-mono text-xs text-gray-800 resize-none focus:outline-none"
              style={{ minHeight: 500 }}
            />
          ) : (
            <iframe
              srcDoc={html}
              className="flex-1 w-full border-0"
              style={{ minHeight: 500 }}
              title="Preview"
            />
          )}
        </div>
      </div>
    </div>
  );
}
