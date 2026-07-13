import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

// Only append "Z" when the string has no timezone info at all — a naive
// timestamp (no offset) is assumed UTC. Postgres TIMESTAMPTZ columns already
// serialize with a numeric offset (e.g. "...+00:00"); appending "Z" to those
// produces an invalid ISO string ("...+00:00Z") that Date() can't parse.
function _withTz(date: string): string {
  return /[Zz]$|[+-]\d{2}:\d{2}$/.test(date) ? date : date + "Z";
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return "—";
  return new Date(_withTz(date)).toLocaleDateString("es-CL", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function formatDateTime(date: string | null | undefined): string {
  if (!date) return "—";
  return new Date(_withTz(date)).toLocaleString("es-CL", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function statusLabel(status: string): string {
  const map: Record<string, string> = {
    draft: "Borrador",
    scheduled: "Programada",
    sending: "Enviando",
    sent: "Enviada",
    cancelled: "Cancelada",
    queued: "En cola",
    delivered: "Entregado",
    opened: "Abierto",
    clicked: "Clic",
    bounced: "Rebotado",
    complained: "Spam",
  };
  return map[status] ?? status;
}

export function statusColor(status: string): string {
  const map: Record<string, string> = {
    draft: "bg-gray-100 text-gray-700",
    scheduled: "bg-blue-100 text-blue-700",
    sending: "bg-yellow-100 text-yellow-700",
    sent: "bg-green-100 text-green-700",
    cancelled: "bg-red-100 text-red-700",
  };
  return map[status] ?? "bg-gray-100 text-gray-600";
}
