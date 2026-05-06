"""
Limpieza de segmentos duplicados en Railway DB.
Ejecutar: python cleanup_segments.py
"""
import sys, psycopg2

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB = "postgresql://postgres:mcxQvhpGaatBzcZNCbVqnGWGBjQpCNYJ@turntable.proxy.rlwy.net:48129/railway"

conn = psycopg2.connect(DB)
cur = conn.cursor()

# ── Listar todos los segmentos ────────────────────────────────────────────────
cur.execute("SELECT id, name, created_at FROM segments ORDER BY id")
rows = cur.fetchall()

print("=== Segmentos actuales ===")
for sid, name, created_at in rows:
    print(f"  [{sid}] {name!r}  ({created_at})")

cur.execute("SELECT DISTINCT segment_id FROM campaigns WHERE segment_id IS NOT NULL")
used_ids = {r[0] for r in cur.fetchall()}
print(f"\nIDs usados en campanas: {sorted(used_ids)}")

# ── Pares duplicados: (keep_id, delete_id) ───────────────────────────────────
# keep_id: el que se mantiene (campaigns apuntaran a este)
# delete_id: el que se elimina
DUPLICATES = [
    # "Hablan ingles" (17, sin tilde) es copia de "Hablan ingles" (7, con tilde)
    # 7 ya esta en campanas; 17 no
    (7, 17),
    # "VIP — 3 o mas visitas" (13) y "Clientes VIP" (5) son el mismo concepto
    # 5 y 13 ambos usados en campanas -> unificar campanas de 13 hacia 5, borrar 13
    (5, 13),
    # "Sin visita registrada" (18) y "Sin experiencia aun" (8) son el mismo concepto
    # ninguno usado en campanas -> borrar 18
    (8, 18),
]

print("\n=== Plan de limpieza ===")
for keep_id, del_id in DUPLICATES:
    keep_name = next((n for sid, n, _ in rows if sid == keep_id), "?")
    del_name  = next((n for sid, n, _ in rows if sid == del_id), "?")
    affected = "usados en campanas" if del_id in used_ids else "no usados"
    print(f"  Mantener [{keep_id}] {keep_name!r}")
    print(f"  Eliminar [{del_id}] {del_name!r}  ({affected})")
    print()

if "--yes" not in sys.argv:
    confirm = input("Confirmar? (s/N): ").strip().lower()
    if confirm != "s":
        print("Cancelado.")
        conn.close()
        sys.exit(0)

for keep_id, del_id in DUPLICATES:
    # Redirigir campanas que apuntaban al segmento eliminado
    cur.execute(
        "UPDATE campaigns SET segment_id = %s WHERE segment_id = %s",
        (keep_id, del_id),
    )
    updated = cur.rowcount
    if updated:
        print(f"  Redirigidas {updated} campana(s) de [{del_id}] -> [{keep_id}]")
    cur.execute("DELETE FROM segments WHERE id = %s", (del_id,))
    print(f"  Eliminado segmento [{del_id}]")

conn.commit()
print("\nListo.")
conn.close()
