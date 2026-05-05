"use client";

import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "@/lib/api";
import { OverviewStats } from "@/lib/types";
import { Users, Send, Filter, FileText, TrendingUp } from "lucide-react";
import { formatDateTime } from "@/lib/utils";

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  color,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-medium text-gray-500">{label}</span>
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${color}`}>
          <Icon size={16} className="text-white" />
        </div>
      </div>
      <p className="text-3xl font-bold text-gray-900">{value}</p>
      {sub && <p className="text-sm text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const { data: overview, isLoading } = useQuery<OverviewStats>({
    queryKey: ["overview"],
    queryFn: () => analyticsApi.overview().then((r) => r.data),
  });

  const { data: recent } = useQuery({
    queryKey: ["recent-campaigns"],
    queryFn: () => analyticsApi.recentCampaigns().then((r) => r.data),
  });

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-48" />
          <div className="grid grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-32 bg-gray-200 rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1 text-sm">Resumen de tu plataforma de email</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Contactos activos"
          value={overview?.contacts.opted_in.toLocaleString() ?? "—"}
          sub={`${overview?.contacts.total.toLocaleString()} total`}
          icon={Users}
          color="bg-blue-500"
        />
        <StatCard
          label="Campañas enviadas"
          value={overview?.campaigns.sent ?? "—"}
          sub={`${overview?.campaigns.total} total`}
          icon={Send}
          color="bg-brand-600"
        />
        <StatCard
          label="Tasa apertura global"
          value={`${overview?.sends.open_rate ?? 0}%`}
          sub={`${overview?.sends.opened.toLocaleString()} aperturas`}
          icon={TrendingUp}
          color="bg-green-500"
        />
        <StatCard
          label="Segmentos"
          value={overview?.segments ?? "—"}
          sub={`${overview?.templates} plantillas`}
          icon={Filter}
          color="bg-purple-500"
        />
      </div>

      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-900">Últimas campañas enviadas</h2>
        </div>
        {!recent || recent.length === 0 ? (
          <div className="px-6 py-12 text-center text-gray-400 text-sm">
            Aún no hay campañas enviadas
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Campaña</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Enviados</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Apertura</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fecha</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((c: { id: number; name: string; total: number; open_rate: number; sent_at: string }) => (
                <tr key={c.id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-6 py-3 font-medium text-gray-900">{c.name}</td>
                  <td className="px-6 py-3 text-gray-600">{c.total.toLocaleString()}</td>
                  <td className="px-6 py-3">
                    <span className="font-semibold text-green-700">{c.open_rate}%</span>
                  </td>
                  <td className="px-6 py-3 text-gray-500">{formatDateTime(c.sent_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
