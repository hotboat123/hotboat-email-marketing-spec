"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { contactsApi } from "@/lib/api";
import { Contact } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import { Plus, Upload, Search, Users } from "lucide-react";
import Link from "next/link";

export default function ContactsPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [importing, setImporting] = useState(false);

  const { data: contacts = [], isLoading } = useQuery<Contact[]>({
    queryKey: ["contacts", search],
    queryFn: () => contactsApi.list({ search: search || undefined, limit: 100 }).then((r) => r.data),
  });

  const importMutation = useMutation({
    mutationFn: (file: File) => contactsApi.importCsv(file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contacts"] });
      setImporting(false);
    },
  });

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) importMutation.mutate(file);
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Contactos</h1>
          <p className="text-gray-500 mt-1 text-sm">{contacts.length.toLocaleString()} contactos</p>
        </div>
        <div className="flex gap-3">
          <label className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-50 cursor-pointer transition-colors">
            <Upload size={15} />
            Importar CSV
            <input type="file" accept=".csv" className="hidden" onChange={handleFileChange} />
          </label>
          <Link
            href="/contacts/new"
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors"
          >
            <Plus size={15} />
            Nuevo contacto
          </Link>
        </div>
      </div>

      {importMutation.data && (
        <div className="mb-4 bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg px-4 py-3">
          Importados: {importMutation.data.data.created} nuevos · {importMutation.data.data.skipped} omitidos
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200">
        <div className="p-4 border-b border-gray-100">
          <div className="relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por email o nombre..."
              className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-gray-400 text-sm">Cargando...</div>
        ) : contacts.length === 0 ? (
          <div className="p-12 text-center">
            <Users size={40} className="mx-auto text-gray-300 mb-3" />
            <p className="text-gray-500 font-medium">No hay contactos</p>
            <p className="text-gray-400 text-sm mt-1">Importa un CSV o agrega contactos manualmente</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nombre / Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Experiencias</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Origen</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Opt-in</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Creado</th>
              </tr>
            </thead>
            <tbody>
              {contacts.map((c) => (
                <tr key={c.id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-6 py-3">
                    <Link href={`/contacts/${c.id}`} className="hover:underline">
                      <p className="font-medium text-gray-900">{c.name || "Sin nombre"}</p>
                      <p className="text-gray-400 text-xs">{c.email}</p>
                    </Link>
                  </td>
                  <td className="px-6 py-3 text-gray-700">{c.veces_hotboat}x</td>
                  <td className="px-6 py-3 text-gray-500">{c.origin_utm || "—"}</td>
                  <td className="px-6 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${c.opted_in ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                      {c.opted_in ? "Activo" : "Baja"}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-gray-500">{formatDate(c.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
