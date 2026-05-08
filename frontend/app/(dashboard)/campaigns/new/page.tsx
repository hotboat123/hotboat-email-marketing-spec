"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { campaignsApi, segmentsApi, templatesApi } from "@/lib/api";
import { Segment, Template } from "@/lib/types";
import { ArrowLeft, ArrowRight, Check, Calendar } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

const STEPS = ["Información", "Segmento", "Plantilla", "Revisar"];

export default function NewCampaignPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({
    name: "",
    subject: "",
    preview_text: "",
    segment_id: 0,
    template_id: 0,
    scheduled_at: "",
  });

  const { data: segments = [] } = useQuery<Segment[]>({
    queryKey: ["segments"],
    queryFn: () => segmentsApi.list().then((r) => r.data),
  });

  const { data: templates = [] } = useQuery<Template[]>({
    queryKey: ["templates"],
    queryFn: () => templatesApi.list().then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: () => campaignsApi.create({
      ...form,
      scheduled_at: form.scheduled_at || undefined,
      status: form.scheduled_at ? "scheduled" : "draft",
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["campaigns"] });
      router.push("/campaigns");
    },
  });

  const selectedSeg = segments.find((s) => s.id === form.segment_id);
  const selectedTpl = templates.find((t) => t.id === form.template_id);

  function canNext() {
    if (step === 0) return form.name && form.subject;
    if (step === 1) return form.segment_id > 0;
    if (step === 2) return form.template_id > 0;
    return true;
  }

  return (
    <div className="p-8 max-w-3xl">
      <Link href="/campaigns" className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 mb-6">
        <ArrowLeft size={15} /> Volver
      </Link>

      <h1 className="text-2xl font-bold text-gray-900 mb-6">Nueva campaña</h1>

      {/* Stepper */}
      <div className="flex items-center gap-0 mb-8">
        {STEPS.map((label, i) => (
          <div key={i} className="flex items-center">
            <div className={`flex items-center gap-2 text-sm font-medium ${i === step ? "text-brand-600" : i < step ? "text-green-600" : "text-gray-400"}`}>
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${i === step ? "bg-brand-600 text-white" : i < step ? "bg-green-500 text-white" : "bg-gray-200 text-gray-500"}`}>
                {i < step ? <Check size={12} /> : i + 1}
              </div>
              {label}
            </div>
            {i < STEPS.length - 1 && <div className="w-8 h-px bg-gray-200 mx-3" />}
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        {step === 0 && (
          <div className="space-y-4">
            <h2 className="font-semibold text-gray-900 mb-4">Información de la campaña</h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nombre interno *</label>
              <input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder="Ej: Newsletter mayo 2025" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Asunto del email *</label>
              <input value={form.subject} onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))} placeholder="Ej: ¡Nuevas fechas disponibles, {{nombre}}!" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
              <p className="text-xs text-gray-400 mt-1">Puedes usar {"{{nombre}}"} para personalizar</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Preview text</label>
              <input value={form.preview_text} onChange={(e) => setForm((f) => ({ ...f, preview_text: e.target.value }))} placeholder="Texto de vista previa en el cliente de correo" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1.5"><Calendar size={13} /> Programar envío (opcional)</label>
              <input
                type="datetime-local"
                value={form.scheduled_at}
                onChange={(e) => setForm((f) => ({ ...f, scheduled_at: e.target.value }))}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              <p className="text-xs text-gray-400 mt-1">Si lo dejas vacío se crea como borrador y puedes enviarla manualmente.</p>
            </div>
          </div>
        )}

        {step === 1 && (
          <div>
            <h2 className="font-semibold text-gray-900 mb-4">Seleccionar segmento</h2>
            {segments.length === 0 ? (
              <p className="text-gray-500 text-sm">No hay segmentos. <Link href="/segments/new" className="text-brand-600 underline">Crear uno</Link></p>
            ) : (
              <div className="space-y-2">
                {segments.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => setForm((f) => ({ ...f, segment_id: s.id }))}
                    className={`w-full flex items-center justify-between px-4 py-3 border rounded-xl text-left transition-colors ${form.segment_id === s.id ? "border-brand-500 bg-brand-50" : "border-gray-200 hover:border-gray-300"}`}
                  >
                    <div>
                      <p className="font-medium text-gray-900">{s.name}</p>
                      {s.description && <p className="text-xs text-gray-400">{s.description}</p>}
                    </div>
                    <span className="text-sm font-semibold text-gray-600">{s.contact_count?.toLocaleString()} contactos</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {step === 2 && (
          <div>
            <h2 className="font-semibold text-gray-900 mb-4">Seleccionar plantilla</h2>
            {templates.length === 0 ? (
              <p className="text-gray-500 text-sm">No hay plantillas. <Link href="/templates/new" className="text-brand-600 underline">Crear una</Link></p>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                {templates.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setForm((f) => ({ ...f, template_id: t.id }))}
                    className={`border rounded-xl p-4 text-left transition-colors ${form.template_id === t.id ? "border-brand-500 bg-brand-50" : "border-gray-200 hover:border-gray-300"}`}
                  >
                    <p className="font-medium text-gray-900">{t.name}</p>
                    <p className="text-xs text-gray-400 mt-0.5 truncate">{t.subject_default}</p>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <h2 className="font-semibold text-gray-900 mb-4">Revisar y crear</h2>
            {[
              { label: "Nombre", value: form.name },
              { label: "Asunto", value: form.subject },
              { label: "Segmento", value: selectedSeg ? `${selectedSeg.name} (${selectedSeg.contact_count} contactos)` : "—" },
              { label: "Plantilla", value: selectedTpl?.name ?? "—" },
              { label: "Programada para", value: form.scheduled_at ? new Date(form.scheduled_at).toLocaleString("es-CL") : "Borrador (envío manual)" },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between py-2 border-b border-gray-100 text-sm">
                <span className="text-gray-500">{label}</span>
                <span className="font-medium text-gray-900">{value}</span>
              </div>
            ))}
            <p className="text-xs text-gray-400 mt-4">La campaña se creará como borrador. Podrás enviarla desde la lista de campañas.</p>
          </div>
        )}
      </div>

      {mutation.isError && (
        <p className="text-red-600 text-sm mt-3">Error al crear la campaña. Intenta de nuevo.</p>
      )}

      <div className="flex justify-between mt-6">
        <button
          type="button"
          onClick={() => setStep((s) => s - 1)}
          disabled={step === 0}
          className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-30 transition-colors"
        >
          <ArrowLeft size={14} /> Anterior
        </button>
        {step < 3 ? (
          <button
            type="button"
            onClick={() => setStep((s) => s + 1)}
            disabled={!canNext()}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-60 transition-colors"
          >
            Siguiente <ArrowRight size={14} />
          </button>
        ) : (
          <button
            type="button"
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="flex items-center gap-2 px-5 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-60 transition-colors"
          >
            <Check size={14} /> {mutation.isPending ? "Creando..." : "Crear campaña"}
          </button>
        )}
      </div>
    </div>
  );
}
