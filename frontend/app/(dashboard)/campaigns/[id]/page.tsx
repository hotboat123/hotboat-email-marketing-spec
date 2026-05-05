"use client";

import { useQuery } from "@tanstack/react-query";
import { campaignsApi } from "@/lib/api";
import { Campaign, CampaignStats } from "@/lib/types";
import { ArrowLeft, TrendingUp, Mail, MousePointer, AlertTriangle } from "lucide-react";
import Link from "next/link";
import { formatDateTime, statusColor, statusLabel } from "@/lib/utils";

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

  const { data: campaign } = useQuery<Campaign>({
    queryKey: ["campaign", id],
    queryFn: () => campaignsApi.get(id).then((r) => r.data),
  });

  const { data: stats } = useQuery<CampaignStats>({
    queryKey: ["campaign-stats", id],
    queryFn: () => campaignsApi.stats(id).then((r) => r.data),
    enabled: campaign?.status === "sent" || campaign?.status === "sending",
  });

  if (!campaign) return <div className="p-8 text-gray-400 text-sm">Cargando...</div>;

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
            <StatBar label="Abiertos" value={stats.opened} total={stats.delivered} color="bg-green-500" />
            <StatBar label="Con clics" value={stats.clicked} total={stats.delivered} color="bg-purple-500" />
            <StatBar label="Rebotados" value={stats.bounced} total={stats.sent} color="bg-red-400" />
          </div>
        </div>
      )}
    </div>
  );
}
