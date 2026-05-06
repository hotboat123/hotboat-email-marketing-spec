"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { contactsApi } from "@/lib/api";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function NewContactPage() {
  const router = useRouter();

  const [form, setForm] = useState({
    email: "",
    name: "",
    phone: "",
    location: "",
    language: "",
    origin_utm: "",
    opted_in: true,
  });

  const mutation = useMutation({
    mutationFn: () => contactsApi.create(form),
    onSuccess: (res) => {
      const id = res.data?.id;
      router.push(id ? `/contacts/${id}` : "/contacts");
    },
  });

  const set = (key: string, value: string | boolean) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const isValid = form.email.trim().length > 0;

  return (
    <div className="p-8 max-w-xl">
      <Link
        href="/contacts"
        className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 mb-6"
      >
        <ArrowLeft size={15} /> Volver a clientes
      </Link>

      <h1 className="text-2xl font-bold text-gray-900 mb-8">Nuevo cliente</h1>

      {mutation.isError && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          {(mutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Error al crear el contacto. ¿El email ya existe?"}
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
        {/* Email */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Email <span className="text-red-500">*</span>
          </label>
          <input
            type="email"
            value={form.email}
            onChange={(e) => set("email", e.target.value)}
            placeholder="cliente@ejemplo.com"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        {/* Nombre */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            placeholder="Juan Pérez"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        {/* Teléfono */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono</label>
          <input
            type="tel"
            value={form.phone}
            onChange={(e) => set("phone", e.target.value)}
            placeholder="+56 9 1234 5678"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        {/* Ubicación */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Ubicación</label>
          <input
            type="text"
            value={form.location}
            onChange={(e) => set("location", e.target.value)}
            placeholder="Santiago, Chile"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* Idioma */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Idioma</label>
            <select
              value={form.language}
              onChange={(e) => set("language", e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="">—</option>
              <option value="es">Español</option>
              <option value="en">English</option>
            </select>
          </div>

          {/* Origen */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Origen / UTM</label>
            <input
              type="text"
              value={form.origin_utm}
              onChange={(e) => set("origin_utm", e.target.value)}
              placeholder="Instagram, Google…"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </div>

        {/* Opt-in */}
        <div className="flex items-center gap-3 pt-1">
          <input
            id="opted_in"
            type="checkbox"
            checked={form.opted_in}
            onChange={(e) => set("opted_in", e.target.checked)}
            className="w-4 h-4 accent-brand-600"
          />
          <label htmlFor="opted_in" className="text-sm text-gray-700">
            Suscrito a emails de marketing
          </label>
        </div>

        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending || !isValid}
          className="w-full py-2.5 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-60 transition-colors mt-2"
        >
          {mutation.isPending ? "Creando…" : "Crear cliente"}
        </button>
      </div>
    </div>
  );
}
