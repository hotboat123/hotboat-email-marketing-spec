"""
Replace the SVG logo URL in all email templates with the hosted PNG.
Run once: python fix_logo_in_templates.py
"""
import os
import re
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL")
BACKEND_PUBLIC_URL = os.environ.get(
    "BACKEND_PUBLIC_URL",
    "https://hotboat-email-marketing-spec-staging.up.railway.app",
)

OLD_PATTERN = r'https?://hotboatchile\.com/LOGO_HOTBOAT\.svg'
NEW_SRC = f"{BACKEND_PUBLIC_URL}/static/logo.png"

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    rows = conn.execute(text("SELECT id, name, html_content FROM templates")).fetchall()
    updated = 0
    for row in rows:
        new_html = re.sub(OLD_PATTERN, NEW_SRC, row.html_content or "")
        if new_html != row.html_content:
            conn.execute(
                text("UPDATE templates SET html_content = :html WHERE id = :id"),
                {"html": new_html, "id": row.id},
            )
            print(f"  Updated template {row.id}: {row.name}")
            updated += 1
    conn.commit()

print(f"\nDone — {updated} template(s) updated.")
print(f"Logo now served from: {NEW_SRC}")
