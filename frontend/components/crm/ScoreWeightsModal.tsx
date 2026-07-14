"use client";

import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { X, RotateCcw } from "lucide-react";
import { crmApi } from "@/lib/api";
import { ScoreWeight } from "@/lib/types";

export function ScoreWeightsModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const { data: weights = [], isLoading } = useQuery<ScoreWeight[]>({
    queryKey: ["score-weights"],
    queryFn: () => crmApi.scoreWeights().then((r) => r.data),
  });

  const [points, setPoints] = useState<Record<string, number>>({});

  useEffect(() => {
    if (weights.length) {
      setPoints(Object.fromEntries(weights.map((w) => [w.key, w.points])));
    }
  }, [weights]);

  const saveMutation = useMutation({
    mutationFn: () =>
      crmApi.updateScoreWeights(
        Object.entries(points).map(([key, pts]) => ({ key, points: pts }))
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["score-weights"] });
      onClose();
    },
  });

  function resetToFetched() {
    setPoints(Object.fromEntries(weights.map((w) => [w.key, w.points])));
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-lg w-full max-w-lg">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div>
            <h3 className="font-semibold text-gray-900">Configurar score de reserva</h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Puntos por señal — se aplican en la próxima sincronización, no de inmediato.
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        <div className="px-5 py-3 max-h-[60vh] overflow-y-auto">
          {isLoading ? (
            [...Array(8)].map((_, i) => (
              <div key={i} className="h-10 bg-gray-100 rounded animate-pulse my-2" />
            ))
          ) : (
            weights.map((w) => (
              <div
                key={w.key}
                className="flex items-center justify-between gap-4 py-2.5 border-b border-gray-50 last:border-0"
              >
                <div className="min-w-0">
                  <p className="text-sm text-gray-800 truncate">{w.label}</p>
                  <p className="text-[11px] text-gray-400 font-mono">{w.key}</p>
                </div>
                <input
                  type="number"
                  value={points[w.key] ?? w.points}
                  onChange={(e) =>
                    setPoints((prev) => ({ ...prev, [w.key]: Number(e.target.value) }))
                  }
                  className="w-20 shrink-0 px-2.5 py-1.5 border border-gray-200 rounded-lg text-sm text-right tabular-nums focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
            ))
          )}
        </div>

        <div className="flex items-center justify-between px-5 py-4 border-t border-gray-100">
          <button
            onClick={resetToFetched}
            disabled={isLoading}
            className="flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 disabled:opacity-40"
          >
            <RotateCcw size={12} /> Deshacer cambios
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-3.5 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 rounded-lg"
            >
              Cancelar
            </button>
            <button
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending || isLoading}
              className="px-3.5 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-50"
            >
              {saveMutation.isPending ? "Guardando..." : "Guardar"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
