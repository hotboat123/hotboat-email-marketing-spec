"use client";

import { useState } from "react";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { campaignsApi, contactsApi } from "@/lib/api";
import { Campaign, CampaignStats } from "@/lib/types";
import { ArrowLeft, TrendingUp, Mail, MousePointer, AlertTriangle, Send, Users, CheckCircle, Clock, XCircle, Trash2 } from "lucide-react";
import Link from "next/link";
import { formatDateTime, statusColor, statusLabel } from "@/lib/utils";

interface CampaignSendRow {
  contact_id: number;
  name: string;
  email: string;
  status: string;
  sent_at: string | null;
  delivered_at: string | null;
  opened_at: string | null;
  clicked_at: string | null;
  bounced_at: string | null;
}

function Tick({ date, label }: { date: string | null; label: string }) {
  if (!date) return <span title={`Sin ${label}`} className="text-gray-200">—</span>;
  return (
    <span title={`${label}: ${formatDateTime(date)}`} className="text-green-500 font-semibold">✓</span>
  );
}

interface SendProgress {
  total_in_segment: number;
  already_sent: number;
}

function StatBar({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  const pct = total > 0 ? (value / total) * 100 : 0;
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className="font-semibold text-gray-900">{value.toLocaleString()} <span className="text-gray-400 font-normal">({pct.toFixed(1)}%)</span></span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function CampaignDetailPage({ params }: { params: { id: string } }) {
  const id = parseInt(params.id);
  const queryClient = useQueryClient();
  const [limit, setLimit] = useState(20);
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState("");
  const [deletingIds, setDeletingIds] = useState<Set<number>>(new Set());

  const deleteMutation = useMutation({
    mutationFn: (contactId: number) => contactsApi.delete(contactId),
    onSuccess: (_, contactId) => {
      setDeletingIds((prev) => { const s = new Set(prev); s.delete(contactId); return s; });
      queryClient.invalidateQueries({ queryKey: ["campaign-sends", id] });
      queryClient.invalidateQueries({ queryKey: ["campaign-stats", id] });
    },
  });

  async function deleteContact(contactId: number) {
    setDeletingIds((prev) => new Set(prev).add(contactId));
    deleteMutation.mutate(contactId);
  }

  async function deleteAllBounced() {
    const bounced = sends.filter((s) => s.bounced_at);
    if (!confirm(`¿Eliminar ${bounced.length} contactos rebotados de la base de datos?`)) return;
    for (const s of bounced) await contactsApi.delete(s.contact_id);
    queryClient.invalidateQueries({ queryKey: ["campaign-sends", id] });
    queryClient.invalidateQueries({ queryKey: ["campaign-stats", id] });
  }

  const { data: campaign } = useQuery<Campaign>({
    queryKey: ["campaign", id],
    queryFn: () => campaignsApi.get(id).then((r) => r.data),
  });

  const { data: sends = [] } = useQuery<CampaignSendRow[]>({
    queryKey: ["campaign-sends", id],
    queryFn: () => campaignsApi.sends(id).then((r) => r.data),
    staleTime: 30_000,
  });

  const { data: stats } = useQuery<CampaignStats>({
    queryKey: ["campaign-stats", id],
    queryFn: () => campaignsApi.stats(id).then((r) => r.data),
    enabled: sends.length > 0 || campaign?.status === "sent" || campaign?.status === "sending",
  });

  const { data: progress } = useQuery<SendProgress>({
    queryKey: ["campaign-progress", id],
    queryFn: () => campaignsApi.sendProgress(id).then((r) => r.data),
    enabled: campaign?.status === "draft",
    refetchInterval: campaign?.status === "sending" ? 3000 : false,
  });

  async function handleSend(sendAll: boolean) {
    setSendError("");
    setSending(true);
    try {
      await campaignsApi.send(id, sendAll ? undefined : limit);
      await queryClient.invalidateQueries({ queryKey: ["campaign", id] });
      await queryClient.invalidateQueries({ queryKey: ["campaign-progress", id] });
      await queryClient.invalidateQueries({ queryKey: ["campaign-stats", id] });
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Error al enviar";
      setSendError(msg);
    } finally {
      setSending(false);
    }
  }

  if (!campaign) return <div className="p-8 text-gray-400 text-sm">Cargando...</div>;

  const remaining = progress ? progress.total_in_segment - progress.already_sent : 0;
  const safeLimit = Math.min(limit, remaining);
  const progressPct = progress && progress.total_in_segment > 0
    ? (progress.already_sent / progress.total_in_segment) * 100
    : 0;

  return (
    <div className="p-8 max-w-3xl">
      <Link href="/campaigns" className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 mb-6">
        <ArrowLeft size={15} /> Volver a campañas
      </Link>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{campaign.name}</h1>
          <p className="text-gray-500 text-sm mt-1">{campaign.subject}</p>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusColor(campaign.status)}`}>
          {statusLabel(campaign.status)}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        {[
          { label: "Fecha de envío", value: formatDateTime(campaign.sent_at) },
          { label: "Programada para", value: formatDateTime(campaign.scheduled_at) },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white border border-gray-200 rounded-xl px-5 py-4">
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">{label}</p>
            <p className="text-gray-900 font-medium">{value}</p>
          </div>
        ))}
      </div>

      {/* ── Envío por fases ─────────────────────────────────────────────── */}
      {campaign.status === "draft" && progress && (
        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Users size={16} className="text-gray-400" />
            <h2 className="font-semibold text-gray-900">Envío por fases</h2>
          </div>

          {/* Progreso del segmento */}
          <div className="mb-5">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-600">Contactos enviados</span>
              <span className="font-semibold text-gray-900">
                {progress.already_sent.toLocaleString()}
                <span className="text-gray-400 font-normal"> / {progress.total_in_segment.toLocaleString()}</span>
              </span>
            </div>
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-600 rounded-full transition-all"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            {remaining > 0 && (
              <p className="text-xs text-gray-400 mt-1.5">{remaining.toLocaleString()} contactos pendientes</p>
            )}
          </div>

          {remaining > 0 ? (
            <>
              {/* Input de cantidad */}
              <div className="flex items-center gap-3 mb-4">
                <label className="text-sm text-gray-600 whitespace-nowrap">Enviar a</label>
                <input
                  type="number"
                  min={1}
                  max={remaining}
                  value={limit}
                  onChange={(e) => setLimit(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-24 border border-gray-200 rounded-lg px-3 py-1.5 text-sm text-center font-semibold focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
                <span className="text-sm text-gray-600">contactos</span>
              </div>

              {sendError && (
                <p className="text-sm text-red-600 mb-3">{sendError}</p>
              )}

              <div className="flex items-center gap-3 flex-wrap">
                <button
                  onClick={() => handleSend(false)}
                  disabled={sending}
                  className="inline-flex items-center gap-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-semibold px-5 py-2.5 rounded-lg text-sm transition-colors"
                >
                  <Send size={14} />
                  {sending ? "Enviando..." : `Enviar a ${safeLimit} contactos`}
                </button>

                <button
                  onClick={() => handleSend(true)}
                  disabled={sending}
                  className="text-sm text-gray-500 hover:text-gray-900 underline underline-offset-2 transition-colors disabled:opacity-50"
                >
                  Enviar a todos los restantes ({remaining.toLocaleString()})
                </button>
              </div>
            </>
          ) : (
            <p className="text-sm text-green-700 font-medium">
              ✓ Todos los contactos del segmento ya recibieron esta campaña.
            </p>
          )}
        </div>
      )}

      {/* ── Lista de contactos enviados ──────────────────────────────────── */}
      {sends.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden mb-6">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between gap-3 flex-wrap">
            <h2 className="font-semibold text-gray-900">Contactos</h2>
            <div className="flex items-center gap-3">
              {sends.filter((s) => s.bounced_at).length > 0 && (
                <button
                  onClick={deleteAllBounced}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-red-50 border border-red-200 text-red-600 rounded-lg text-xs font-medium hover:bg-red-100 transition-colors"
                >
                  <Trash2 size={12} />
                  Eliminar {sends.filter((s) => s.bounced_at).length} rebotados
                </button>
              )}
              <span className="text-xs text-gray-400">{sends.length} enviados</span>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  <th className="px-5 py-3 text-left">Contacto</th>
                  <th className="px-4 py-3 text-center">Enviado</th>
                  <th className="px-4 py-3 text-center">Entregado</th>
                  <th className="px-4 py-3 text-center">Abrió</th>
                  <th className="px-4 py-3 text-center">Clic</th>
                  <th className="px-4 py-3 text-center">Rebote</th>
                </tr>
              </thead>
              <tbody>
                {sends.map((s) => (
                  <tr key={s.contact_id} className={`border-b border-gray-100 hover:bg-gray-50 transition-colors ${s.bounced_at ? "bg-red-50/40" : ""}`}>
                    <td className="px-5 py-3">
                      <Link href={`/contacts/${s.contact_id}`} className="hover:text-brand-600 transition-colors">
                        <p className="font-medium text-gray-900">{s.name}</p>
                        <p className="text-xs text-gray-400">{s.email}</p>
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-center"><Tick date={s.sent_at} label="enviado" /></td>
                    <td className="px-4 py-3 text-center"><Tick date={s.delivered_at} label="entregado" /></td>
                    <td className="px-4 py-3 text-center"><Tick date={s.opened_at} label="abierto" /></td>
                    <td className="px-4 py-3 text-center"><Tick date={s.clicked_at} label="clic" /></td>
                    <td className="px-4 py-3 text-center">
                      {s.bounced_at ? (
                        <div className="flex items-center justify-center gap-2">
                          <span title={`Rebotó: ${formatDateTime(s.bounced_at)}`} className="text-red-400 font-semibold">✕</span>
                          <button
                            onClick={() => deleteContact(s.contact_id)}
                            disabled={deletingIds.has(s.contact_id)}
                            title="Eliminar contacto"
                            className="text-red-300 hover:text-red-600 transition-colors disabled:opacity-40"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      ) : <span className="text-gray-200">—</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {stats && (
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <h2 className="font-semibold text-gray-900 mb-5">Estadísticas</h2>

          <div className="grid grid-cols-4 gap-4 mb-6">
            {[
              { label: "Enviados", value: stats.sent, icon: Mail, color: "text-blue-600" },
              { label: "Aperturas", value: `${stats.open_rate}%`, icon: TrendingUp, color: "text-green-600" },
              { label: "Clics", value: `${stats.click_rate}%`, icon: MousePointer, color: "text-purple-600" },
              { label: "Rebotes", value: `${stats.bounce_rate}%`, icon: AlertTriangle, color: "text-red-600" },
            ].map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="text-center">
                <Icon size={20} className={`mx-auto mb-1 ${color}`} />
                <p className="text-2xl font-bold text-gray-900">{value}</p>
                <p className="text-xs text-gray-500">{label}</p>
              </div>
            ))}
          </div>

          <div className="space-y-4">
            <StatBar label="Entregados" value={stats.delivered} total={stats.sent} color="bg-blue-500" />
            <StatBar label="Abiertos"   value={stats.opened}    total={stats.delivered || stats.sent} color="bg-green-500" />
            <StatBar label="Con clics"  value={stats.clicked}   total={stats.delivered || stats.sent} color="bg-purple-500" />
            <StatBar label="Rebotados"  value={stats.bounced}   total={stats.sent} color="bg-red-400" />
          </div>
        </div>
      )}
    </div>
  );
}
