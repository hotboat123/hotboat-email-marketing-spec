"""
Adds the web_* activity summary columns to contacts_crm (Railway DB).
Safe to run multiple times (uses IF NOT EXISTS logic).
Uso: cd backend && python migrate_add_web_summary_columns.py

SQLModel.metadata.create_all() (run at app startup) only creates missing
tables, not new columns on existing tables — same reason migrate_add_columns.py
exists for the `contacts` table.
"""
import sys
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.core.config import settings  # noqa: E402

conn = psycopg2.connect(settings.DATABASE_URL)
cur = conn.cursor()

migrations = [
    "ALTER TABLE contacts_crm ADD COLUMN IF NOT EXISTS web_classification VARCHAR",
    "ALTER TABLE contacts_crm ADD COLUMN IF NOT EXISTS web_classification_desc VARCHAR",
    "ALTER TABLE contacts_crm ADD COLUMN IF NOT EXISTS web_last_seen_at TIMESTAMP",
    "ALTER TABLE contacts_crm ADD COLUMN IF NOT EXISTS web_session_count INTEGER DEFAULT 0",
]

for sql in migrations:
    try:
        cur.execute(sql)
        print(f"  OK: {sql}")
    except Exception as e:
        print(f"  ERR: {e}")
        conn.rollback()
        continue

conn.commit()
conn.close()
print("\nMigracion completada.")
