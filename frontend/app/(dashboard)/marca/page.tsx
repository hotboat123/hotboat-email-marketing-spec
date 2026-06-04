"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { marcaApi } from "@/lib/api";
import { BrandAsset } from "@/lib/types";
import { Plus, Pencil, Trash2, Check, X, Copy } from "lucide-react";
import { cn } from "@/lib/utils";

// ── Categorías ────────────────────────────────────────────────────────────────

const CATEGORIAS = [
  { key: "color",      label: "Colores",      emoji: "🎨" },
  { key: "tipografia", label: "Tipografía",   emoji: "✍️" },
  { key: "logo",       label: "Logos",        emoji: "🏷️" },
  { key: "url",        label: "URLs",         emoji: "🔗" },
  { key: "espaciado",  label: "Espaciado",    emoji: "📐" },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function isHex(val: string) {
  return /^#[0-9a-fA-F]{3,8}$/.test(val.trim());
}

function isUrl(val: string) {
  return val.startsWith("http") || val.startsWith("https");
}

function isImageUrl(val: string) {
  return isUrl(val) && /\.(png|jpg|jpeg|webp|svg|gif)/i.test(val);
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).catch(() => {});
}

// ── Valor visual ─────────────────────────────────────────────────────────────

function ValorDisplay({ valor, categoria }: { valor: string; categoria: string }) {
  if (categoria === "color" && isHex(valor)) {
    return (
      <div className="flex items-center gap-2">
        <div
          className="w-6 h-6 rounded-md border border-gray-200 flex-shrink-0 shadow-sm"
          style={{ backgroundColor: valor }}
        />
        <span className="font-mono text-sm text-gray-800">{valor}</span>
      </div>
    );
  }
  if (categoria === "logo" && isImageUrl(valor)) {
    return (
      <div className="flex items-center gap-3">
        <div className="w-16 h-9 bg-gray-900 rounded-md flex items-center justify-center overflow-hidden flex-shrink-0">
          <img src={valor} alt="" className="h-6 object-contain" />
        </div>
        <span className="text-xs text-gray-400 truncate max-w-[200px]" title={valor}>{valor}</span>
      </div>
    );
  }
  if (isUrl(valor)) {
    return (
      <a href={valor} target="_blank" rel="noreferrer"
         className="text-brand-600 text-sm hover:underline truncate max-w-[300px] block" title={valor}>
        {valor}
      </a>
    );
  }
  return <span className="text-sm text-gray-800 font-medium">{valor}</span>;
}

// ── Row editable ─────────────────────────────────────────────────────────────

function AssetRow({ asset, onDelete }: { asset: BrandAsset; onDelete: () => void }) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ nombre: asset.nombre, valor: asset.valor, descripcion: asset.descripcion ?? "" });
  const [copied, setCopied] = useState(false);

  const updateMut = useMutation({
    mutationFn: () => marcaApi.update(asset.id, form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["marca"] }); setEditing(false); },
  });

  const deleteMut = useMutation({
    mutationFn: () => marcaApi.remove(asset.id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["marca"] }); onDelete(); },
  });

  function handleCopy() {
    copyToClipboard(asset.valor);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  if (editing) {
    return (
      <tr className="border-b border-gray-100 bg-blue-50">
        <td className="px-4 py-2">
          <input
            className="w-full border border-gray-300 rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
            value={form.nombre}
            onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))}
          />
        </td>
        <td className="px-4 py-2">
          <input
            className="w-full border border-gray-300 rounded-md px-2 py-1 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-400"
            value={form.valor}
            onChange={(e) => setForm((f) => ({ ...f, valor: e.target.value }))}
          />
        </td>
        <td className="px-4 py-2">
          <input
            className="w-full border border-gray-300 rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
            value={form.descripcion}
            onChange={(e) => setForm((f) => ({ ...f, descripcion: e.target.value }))}
            placeholder="Descripción..."
          />
        </td>
        <td className="px-4 py-2">
          <div className="flex gap-1">
            <button
              onClick={() => updateMut.mutate()}
              className="p-1.5 rounded-md bg-green-500 text-white hover:bg-green-600 transition-colors"
            >
              <Check size={13} />
            </button>
            <button
              onClick={() => setEditing(false)}
              className="p-1.5 rounded-md bg-gray-200 text-gray-600 hover:bg-gray-300 transition-colors"
            >
              <X size={13} />
            </button>
          </div>
        </td>
      </tr>
    );
  }

  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50 transition-colors group">
      <td className="px-4 py-3 text-sm font-medium text-gray-800">{asset.nombre}</td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <ValorDisplay valor={asset.valor} categoria={asset.categoria} />
          <button
            onClick={handleCopy}
            className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600"
            title="Copiar valor"
          >
            {copied ? <Check size={12} className="text-green-500" /> : <Copy size={12} />}
          </button>
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-gray-500">{asset.descripcion ?? "—"}</td>
      <td className="px-4 py-3">
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={() => setEditing(true)}
            className="p-1.5 rounded-md text-gray-400 hover:text-brand-600 hover:bg-brand-50 transition-colors"
          >
            <Pencil size={13} />
          </button>
          <button
            onClick={() => { if (confirm("¿Eliminar este asset?")) deleteMut.mutate(); }}
            className="p-1.5 rounded-md text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </td>
    </tr>
  );
}

// ── Formulario de nuevo asset ─────────────────────────────────────────────────

function NewAssetRow({ categoria, onDone }: { categoria: string; onDone: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({ nombre: "", valor: "", descripcion: "" });

  const createMut = useMutation({
    mutationFn: () => marcaApi.create({ categoria, ...form }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["marca"] }); onDone(); },
  });

  return (
    <tr className="border-b border-brand-100 bg-brand-50">
      <td className="px-4 py-2">
        <input
          autoFocus
          placeholder="Nombre del asset"
          className="w-full border border-brand-300 rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
          value={form.nombre}
          onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))}
        />
      </td>
      <td className="px-4 py-2">
        <input
          placeholder="#hex, URL, font name..."
          className="w-full border border-brand-300 rounded-md px-2 py-1 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-brand-400"
          value={form.valor}
          onChange={(e) => setForm((f) => ({ ...f, valor: e.target.value }))}
        />
      </td>
      <td className="px-4 py-2">
        <input
          placeholder="Descripción opcional"
          className="w-full border border-brand-300 rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
          value={form.descripcion}
          onChange={(e) => setForm((f) => ({ ...f, descripcion: e.target.value }))}
        />
      </td>
      <td className="px-4 py-2">
        <div className="flex gap-1">
          <button
            onClick={() => createMut.mutate()}
            disabled={!form.nombre || !form.valor}
            className="p-1.5 rounded-md bg-brand-600 text-white hover:bg-brand-700 transition-colors disabled:opacity-40"
          >
            <Check size={13} />
          </button>
          <button onClick={onDone} className="p-1.5 rounded-md bg-gray-200 text-gray-600 hover:bg-gray-300 transition-colors">
            <X size={13} />
          </button>
        </div>
      </td>
    </tr>
  );
}

// ── Tabla por categoría ───────────────────────────────────────────────────────

function CategoriaTable({ cat, assets }: { cat: typeof CATEGORIAS[0]; assets: BrandAsset[] }) {
  const [adding, setAdding] = useState(false);

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">{cat.emoji}</span>
          <h2 className="text-base font-semibold text-gray-800">{cat.label}</h2>
          <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">{assets.length}</span>
        </div>
        <button
          onClick={() => setAdding(true)}
          className="flex items-center gap-1.5 text-xs text-brand-600 hover:text-brand-700 font-medium px-2.5 py-1.5 rounded-lg hover:bg-brand-50 transition-colors"
        >
          <Plus size={13} />
          Agregar
        </button>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50">
              <th className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide w-48">Nombre</th>
              <th className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Valor</th>
              <th className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Descripción</th>
              <th className="px-4 py-2.5 w-20" />
            </tr>
          </thead>
          <tbody>
            {assets.map((a) => (
              <AssetRow key={a.id} asset={a} onDelete={() => {}} />
            ))}
            {adding && (
              <NewAssetRow categoria={cat.key} onDone={() => setAdding(false)} />
            )}
            {assets.length === 0 && !adding && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-gray-400 text-sm">
                  Sin assets todavía.{" "}
                  <button onClick={() => setAdding(true)} className="text-brand-600 hover:underline">
                    Agregar el primero
                  </button>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function MarcaPage() {
  const { data: assets = [], isLoading } = useQuery<BrandAsset[]>({
    queryKey: ["marca"],
    queryFn: () => marcaApi.list().then((r) => r.data),
    staleTime: 5 * 60_000,
  });

  const byCategoria = CATEGORIAS.reduce<Record<string, BrandAsset[]>>((acc, cat) => {
    acc[cat.key] = assets.filter((a) => a.categoria === cat.key);
    return acc;
  }, {});

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Plantillas de la marca</h1>
        <p className="text-sm text-gray-500 mt-1">
          Colores, tipografía, logos y URLs oficiales de HotBoat. Usá estos valores en todos los emails para mantener consistencia.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-32 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : (
        CATEGORIAS.map((cat) => (
          <CategoriaTable key={cat.key} cat={cat} assets={byCategoria[cat.key] ?? []} />
        ))
      )}
    </div>
  );
}
