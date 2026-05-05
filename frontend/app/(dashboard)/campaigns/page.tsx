"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { campaignsApi } from "@/lib/api";
import { Campaign } from "@/lib/types";
import { Plus, Send, Trash2 } from "lucide-react";
import Link from "next/link";
import { formatDateTime, statusColor, statusLabel } from "@/lib/utils";

export default function CampaignsPage() {
  const qc = useQueryClient();
  const { data: campaigns = [], isLoading } = useQuery<Campaign[]>({
    queryKey: ["campaigns"],
    queryFn: () => campaignsApi.list().then((r) => r.data),
  });

  const sendMutation = useMutation({
    mutationFn: (id: number) => campaignsApi.send(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaigns"] }),
  });

  const delMutation = useMutation({
    mutationFn: (id: number) => campaignsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaigns"] }),
  });

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Campañas</h1>
          <p className="text-gray-500 mt-1 text-sm">{campaigns.length} campañas</p>
        </div>
        <Link
          href="/campaigns/new"
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors"
        >
          <Plus size={15} />
          Nueva campaña
        </Link>
      </div>

      <div className="bg-white rounded-xl border border-gray-200">
        {isLoading ? (
          <div className="p-12 text-center text-gray-400 text-sm">Cargando...</div>
        ) : campaigns.length === 0 ? (
          <div className="p-12 text-center">
            <Send size={40} className="mx-auto text-gray-300 mb-3" />
            <p className="text-gray-500 font-medium">No hay campañas</p>
            <p className="text-gray-400 text-sm mt-1">Crea tu primera campaña de email</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Campaña</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estado</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fecha envío</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.map((c) => (
                <tr key={c.id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-6 py-3">
                    <Link href={`/campaigns/${c.id}`} className="hover:underline">
                      <p className="font-medium text-gray-900">{c.name}</p>
                      <p className="text-gray-400 text-xs">{c.subject}</p>
                    </Link>
                  </td>
                  <td className="px-6 py-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColor(c.status)}`}>
                      {statusLabel(c.status)}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-gray-500">{formatDateTime(c.sent_at) || formatDateTime(c.scheduled_at) || "—"}</td>
                  <td className="px-6 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {(c.status === "draft" || c.status === "scheduled") && (
                        <button
                          onClick={() => sendMutation.mutate(c.id)}
                          disabled={sendMutation.isPending}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 text-white rounded-lg text-xs font-medium hover:bg-brand-700 disabled:opacity-60 transition-colors"
                        >
                          <Send size={11} /> Enviar
                        </button>
                      )}
                      {c.status === "sent" && (
                        <Link
                          href={`/campaigns/${c.id}`}
                          className="px-3 py-1.5 border border-gray-300 rounded-lg text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                        >
                          Ver stats
                        </Link>
                      )}
                      {c.status === "draft" && (
                        <button
                          onClick={() => delMutation.mutate(c.id)}
                          className="p-1.5 text-gray-300 hover:text-red-500 transition-colors"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
