"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { templatesApi } from "@/lib/api";
import { ArrowLeft, Eye } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

const STARTER_HTML = `<div style="font-family: Inter, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 32px 24px; color: #111;">
  <img src="https://via.placeholder.com/600x120?text=HotBoat" alt="HotBoat" style="width:100%; border-radius:12px; margin-bottom:24px;" />
  <h1 style="font-size: 24px; font-weight: 700; margin: 0 0 8px;">Hola, {{nombre}} 👋</h1>
  <p style="font-size: 15px; line-height: 1.6; color: #444;">
    Queremos contarte algo especial para ti.
  </p>
  <a href="#" style="display:inline-block; margin-top:24px; background:#e51e0e; color:#fff; font-weight:600; padding:12px 28px; border-radius:8px; text-decoration:none; font-size:14px;">
    Ver más
  </a>
  <hr style="margin: 32px 0; border: none; border-top: 1px solid #eee;" />
  <p style="font-size: 12px; color: #999;">
    HotBoat · Santiago, Chile<br/>
    <a href="#" style="color:#999;">Cancelar suscripción</a>
  </p>
</div>`;

export default function NewTemplatePage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [subject, setSubject] = useState("");
  const [previewText, setPreviewText] = useState("");
  const [html, setHtml] = useState(STARTER_HTML);
  const [tab, setTab] = useState<"editor" | "preview">("editor");

  const mutation = useMutation({
    mutationFn: () =>
      templatesApi.create({ name, subject_default: subject, preview_text: previewText || undefined, html_content: html }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["templates"] });
      router.push("/templates");
    },
  });

  return (
    <div className="p-8 h-full flex flex-col">
      <div className="flex items-center gap-4 mb-6">
        <Link href="/templates" className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900">
          <ArrowLeft size={15} /> Volver
        </Link>
        <h1 className="text-xl font-bold text-gray-900 flex-1">Nueva plantilla</h1>
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending || !name || !subject}
          className="px-5 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-60 transition-colors"
        >
          {mutation.isPending ? "Guardando..." : "Guardar plantilla"}
        </button>
      </div>

      <div className="grid grid-cols-5 gap-6 flex-1">
        <div className="col-span-2 space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nombre interno *</label>
              <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="Ej: Bienvenida nueva reserva" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Asunto por defecto *</label>
              <input value={subject} onChange={(e) => setSubject(e.target.value)} required placeholder="Ej: Hola {{nombre}}, ¡gracias por reservar!" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Preview text</label>
              <input value={previewText} onChange={(e) => setPreviewText(e.target.value)} placeholder="Texto que aparece en el cliente de correo" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
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
                className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${tab === t ? "border-brand-600 text-brand-700" : "border-transparent text-gray-500 hover:text-gray-800"}`}
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
