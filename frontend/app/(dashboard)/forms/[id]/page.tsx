"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { formsApi } from "@/lib/api";
import { SignupForm, FormSubmission } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import { ArrowLeft, Copy, Check, Users, Code } from "lucide-react";
import Link from "next/link";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  (typeof window !== "undefined" && window.location.hostname === "localhost"
    ? "http://localhost:8000"
    : "https://hotboat-backend-email-marketing-staging.up.railway.app");

export default function FormDetailPage() {
  const { id } = useParams<{ id: string }>();
  const formId = Number(id);
  const [copied, setCopied] = useState(false);

  const { data: form, isLoading } = useQuery<SignupForm>({
    queryKey: ["form", formId],
    queryFn: () => formsApi.get(formId).then((r) => r.data),
    staleTime: 30_000,
  });

  const { data: subsData } = useQuery<{ total: number; submissions: FormSubmission[] }>({
    queryKey: ["form-submissions", formId],
    queryFn: () => formsApi.submissions(formId).then((r) => r.data),
    staleTime: 30_000,
    enabled: !!formId,
  });

  const embedCode = `<script src="${BACKEND_URL}/api/forms/${formId}/embed.js" async></script>`;

  function copyEmbed() {
    navigator.clipboard.writeText(embedCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="h-5 bg-gray-200 rounded w-40 animate-pulse mb-4" />
        <div className="h-8 bg-gray-200 rounded w-64 animate-pulse" />
      </div>
    );
  }

  if (!form) {
    return (
      <div className="p-8">
        <Link href="/forms" className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-4">
          <ArrowLeft size={15} /> Volver
        </Link>
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          Formulario no encontrado.
        </div>
      </div>
    );
  }

  const TRIGGER_LABEL: Record<string, string> = {
    delay: `Después de ${form.popup_delay_seconds}s`,
    exit_intent: "Exit intent (al salir)",
    scroll: `Al ${form.popup_scroll_pct}% de scroll`,
  };

  return (
    <div className="p-8 max-w-3xl">
      <Link href="/forms" className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 mb-6">
        <ArrowLeft size={15} /> Volver a formularios
      </Link>

      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{form.name}</h1>
          <div className="flex items-center gap-3 mt-2 text-sm text-gray-500">
            <span
              className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                form.status === "active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
              }`}
            >
              {form.status === "active" ? "Activo" : "Pausado"}
            </span>
            <span>{TRIGGER_LABEL[form.popup_trigger]}</span>
            <span>·</span>
            <span>Creado {formatDate(form.created_at)}</span>
          </div>
        </div>
        <div className="text-right">
          <p className="text-3xl font-bold text-gray-900">{subsData?.total ?? "—"}</p>
          <p className="text-xs text-gray-400 flex items-center gap-1 justify-end mt-0.5">
            <Users size={11} /> suscriptores captados
          </p>
        </div>
      </div>

      {/* Embed code */}
      <div className="bg-gray-950 rounded-xl p-5 mb-8">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 text-gray-400">
            <Code size={15} />
            <span className="text-sm font-medium">Código de instalación</span>
          </div>
          <button
            onClick={copyEmbed}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg text-xs font-medium transition-colors"
          >
            {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
            {copied ? "¡Copiado!" : "Copiar"}
          </button>
        </div>
        <p className="text-xs text-gray-500 mb-3">
          Pega este código antes del <code className="text-gray-400">&lt;/body&gt;</code> de hotboat.cl:
        </p>
        <pre className="text-xs text-green-400 font-mono break-all whitespace-pre-wrap">{embedCode}</pre>
      </div>

      {/* Preview */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 mb-8">
        <p className="text-sm font-semibold text-gray-700 mb-4">Vista previa del popup</p>
        <div className="bg-gradient-to-b from-sky-50 to-gray-100 rounded-xl p-6 flex justify-center">
          <div className="bg-white rounded-2xl shadow-2xl overflow-hidden max-w-sm w-full border border-gray-200">
            <div className="bg-gradient-to-r from-sky-700 to-sky-500 px-6 py-5 relative">
              <p className="text-xs text-sky-200 font-bold tracking-widest uppercase mb-1">HotBoat</p>
              <h3 className="text-white font-bold text-lg leading-snug">{form.title}</h3>
            </div>
            <div className="px-6 py-5">
              {form.description && (
                <p className="text-gray-500 text-sm mb-4">{form.description}</p>
              )}
              <div className="space-y-2">
                {form.collect_name && (
                  <div className="h-9 rounded-lg border border-gray-200 bg-gray-50 px-3 flex items-center text-sm text-gray-400">
                    Tu nombre
                  </div>
                )}
                <div className="h-9 rounded-lg border border-gray-200 bg-gray-50 px-3 flex items-center text-sm text-gray-400">
                  Tu email *
                </div>
                {form.collect_phone && (
                  <div className="h-9 rounded-lg border border-gray-200 bg-gray-50 px-3 flex items-center text-sm text-gray-400">
                    Tu teléfono
                  </div>
                )}
                <div className="h-10 rounded-xl bg-gradient-to-r from-sky-700 to-sky-500 flex items-center justify-center text-white text-sm font-bold">
                  {form.button_text}
                </div>
              </div>
              <p className="text-center text-gray-400 text-xs mt-3">
                Respetamos tu privacidad. Puedes darte de baja cuando quieras.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Submissions */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-700">
            Últimas suscripciones
            {subsData && subsData.total > subsData.submissions.length && (
              <span className="ml-2 text-xs font-normal text-gray-400">
                (mostrando últimas {subsData.submissions.length} de {subsData.total})
              </span>
            )}
          </h2>
        </div>

        {!subsData || subsData.submissions.length === 0 ? (
          <div className="p-12 text-center">
            <Users size={32} className="mx-auto text-gray-200 mb-3" />
            <p className="text-gray-400 text-sm">Aún no hay suscripciones. Instala el popup en hotboat.cl.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nombre</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Página</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fecha</th>
              </tr>
            </thead>
            <tbody>
              {subsData.submissions.map((s) => (
                <tr key={s.id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-6 py-3 font-mono text-xs text-gray-700">{s.email}</td>
                  <td className="px-6 py-3 text-gray-600">{s.name || "—"}</td>
                  <td className="px-6 py-3 text-gray-400 text-xs truncate max-w-[200px]">
                    {s.source_url ? (
                      <a href={s.source_url} target="_blank" rel="noopener noreferrer" className="hover:text-brand-600">
                        {s.source_url.replace(/^https?:\/\/[^/]+/, "")}
                      </a>
                    ) : "—"}
                  </td>
                  <td className="px-6 py-3 text-gray-400 text-xs">{formatDate(s.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
