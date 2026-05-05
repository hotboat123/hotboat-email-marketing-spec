"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { campaignsApi, segmentsApi } from "@/lib/api";
import { Campaign, Segment } from "@/lib/types";
import { Plus, Send, Trash2, FlaskConical, Users, CheckCircle, Clock } from "lucide-react";
import Link from "next/link";
import { formatDateTime, statusColor, statusLabel } from "@/lib/utils";

function CampaignSkeleton() {
  return (
    <tr className="border-b border-gray-50">
      <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-48 animate-pulse" /><div className="h-3 bg-gray-100 rounded w-64 mt-1.5 animate-pulse" /></td>
      <td className="px-6 py-4"><div className="h-5 bg-gray-100 rounded-full w-16 animate-pulse" /></td>
      <td className="px-6 py-4"><div className="h-4 bg-gray-100 rounded w-28 animate-pulse" /></td>
      <td className="px-6 py-4"><div className="h-4 bg-gray-100 rounded w-20 animate-pulse" /></td>
      <td className="px-6 py-4" />
    </tr>
  );
}

export default function CampaignsPage() {
  const qc = useQueryClient();
  const [testSentTo, setTestSentTo] = useState<string | null>(null);

  const { data: campaigns = [], isLoading, isError } = useQuery<Campaign[]>({
    queryKey: ["campaigns"],
    queryFn: () => campaignsApi.list().then((r) => r.data),
    staleTime: 2 * 60_000,
  });

  const { data: segments = [] } = useQuery<Segment[]>({
    queryKey: ["segments"],
    queryFn: () => segmentsApi.list().then((r) => r.data),
    staleTime: 5 * 60_000,
  });

  const segMap = Object.fromEntries(segments.map((s) => [s.id, s]));

  const sendMutation = useMutation({
    mutationFn: (id: number) => campaignsApi.send(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaigns"] }),
  });

  const testMutation = useMutation({
    mutationFn: (id: number) => campaignsApi.sendTest(id),
    onSuccess: (res) => {
      setTestSentTo(res.data?.sent_to || "tu correo");
      setTimeout(() => setTestSentTo(null), 8000);
    },
  });

  const delMutation = useMutation({
    mutationFn: (id: number) => campaignsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaigns"] }),
  });

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Campanas</h1>
          <p className="text-gray-500 mt-1 text-sm">{campaigns.length} campanas</p>
        </div>
        <Link
          href="/campaigns/new"
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors"
        >
          <Plus size={15} />
          Nueva campana
        </Link>
      </div>

      {testSentTo && (
        <div className="mb-4 bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg px-4 py-3 flex items-center gap-2">
          <CheckCircle size={15} />
          <span>Email de prueba enviado a <strong>{testSentTo}</strong>. Si no aparece en tu bandeja, revisa la carpeta de <strong>Spam</strong>.</span>
        </div>
      )}

      {isError && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
          Error al cargar campanas.
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200">
        {isLoading ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Campana</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estado</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Segmento</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fecha</th>
                <th className="px-6 py-3" />
              </tr>
            </thead>
            <tbody>{[...Array(4)].map((_, i) => <CampaignSkeleton key={i} />)}</tbody>
          </table>
        ) : campaigns.length === 0 ? (
          <div className="p-12 text-center">
            <Send size={40} className="mx-auto text-gray-300 mb-3" />
            <p className="text-gray-500 font-medium">No hay campanas</p>
            <p className="text-gray-400 text-sm mt-1">Crea tu primera campana de email</p>
            <Link href="/campaigns/new" className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 transition-colors">
              <Plus size={14} /> Crear campana
            </Link>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Campana</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estado</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Segmento / Alcance</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fecha envio</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.map((c) => {
                const seg = segMap[c.segment_id];
                return (
                  <tr key={c.id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <Link href={`/campaigns/${c.id}`} className="hover:underline">
                        <p className="font-medium text-gray-900">{c.name}</p>
                        <p className="text-gray-400 text-xs mt-0.5 truncate max-w-xs">{c.subject}</p>
                      </Link>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColor(c.status)}`}>
                        {c.status === "scheduled" && <Clock size={10} className="mr-1" />}
                        {statusLabel(c.status)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {seg ? (
                        <div>
                          <p className="text-gray-700 text-xs font-medium truncate max-w-[160px]">{seg.name}</p>
                          {seg.contact_count != null && (
                            <p className="text-gray-400 text-xs mt-0.5 flex items-center gap-1">
                              <Users size={10} /> {seg.contact_count.toLocaleString()} contactos
                            </p>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-400 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-gray-500 text-xs">
                      {formatDateTime(c.sent_at) || formatDateTime(c.scheduled_at) || "—"}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-1.5">
                        {(c.status === "draft" || c.status === "scheduled") && (
                          <>
                            <button
                              onClick={() => testMutation.mutate(c.id)}
                              disabled={testMutation.isPending}
                              title="Enviar prueba a mi email"
                              className="flex items-center gap-1 px-2.5 py-1.5 border border-gray-300 text-gray-600 rounded-lg text-xs font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors"
                            >
                              <FlaskConical size={11} /> Prueba
                            </button>
                            <button
                              onClick={() => {
                                if (confirm(`Enviar "${c.name}" ahora?`)) sendMutation.mutate(c.id);
                              }}
                              disabled={sendMutation.isPending}
                              className="flex items-center gap-1 px-2.5 py-1.5 bg-brand-600 text-white rounded-lg text-xs font-medium hover:bg-brand-700 disabled:opacity-60 transition-colors"
                            >
                              <Send size={11} /> Enviar
                            </button>
                          </>
                        )}
                        {c.status === "sent" && (
                          <Link
                            href={`/campaigns/${c.id}`}
                            className="px-2.5 py-1.5 border border-gray-300 rounded-lg text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                          >
                            Ver stats
                          </Link>
                        )}
                        {c.status === "draft" && (
                          <button
                            onClick={() => {
                              if (confirm("Eliminar esta campana?")) delMutation.mutate(c.id);
                            }}
                            className="p-1.5 text-gray-300 hover:text-red-500 transition-colors"
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
