"""
Genera 5 versiones del email Cyber Tardío con estilos completamente distintos.
Ejecutar: python seed_cyber_5versions.py
Abre los 5 previews en el browser automáticamente.
"""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime
from jinja2 import Template as JTemplate
from sqlmodel import Session, select, create_engine
from app.core.config import settings
from app.models.user import User; from app.models.contact import Contact
from app.models.segment import Segment; from app.models.template import Template
from app.models.campaign import Campaign
from app.models.automation import Automation, AutomationRun
from app.models.form import SignupForm

engine = create_engine(settings.DATABASE_URL)

# ─────────────────────────────────────────────────────────────────────────────
# VERSIÓN A — EDITORIAL MINIMALISTA
# Flat Design · Playfair Display · Cyan #0891B2 · Fondo casi blanco
# Sin iconos. Tipografía como protagonista. Mucho espacio en blanco.
# ─────────────────────────────────────────────────────────────────────────────
HTML_A = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,400;1,700&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:0;background:#ecfeff;">
<div style="font-family:'Playfair Display',Georgia,serif;max-width:600px;margin:0 auto;background:#ffffff;">

  <!-- Barra superior cyan -->
  <div style="height:4px;background:#0891b2;"></div>

  <!-- Header -->
  <div style="padding:40px 48px 32px;border-bottom:1px solid #e0f7fa;">
    <img src="https://hotboatchile.com/logo_hotboat_blanco.png" alt="HotBoat"
         style="height:36px;filter:invert(1) sepia(1) saturate(2) hue-rotate(175deg) brightness(0.4);display:block;" />
  </div>

  <!-- Headline -->
  <div style="padding:48px 48px 32px;">
    <p style="margin:0 0 12px;font-size:12px;font-weight:600;letter-spacing:3px;color:#0891b2;text-transform:uppercase;font-family:'Playfair Display',Georgia,serif;">
      Cyber Tardío · Válido hasta el 7 de junio
    </p>
    <h1 style="margin:0;font-size:38px;font-weight:900;color:#164e63;line-height:1.1;letter-spacing:-1px;">
      Llegamos<br>tarde al Cyber.<br>
      <span style="color:#0891b2;">Lo hicimos<br>de todas formas.</span>
    </h1>
  </div>

  <!-- Separador -->
  <div style="margin:0 48px;height:1px;background:#e0f7fa;"></div>

  <!-- Ofertas como lista editorial -->
  <div style="padding:32px 48px;">
    <p style="margin:0 0 28px;font-size:14px;color:#6b7280;font-family:'Playfair Display',Georgia,serif;font-weight:400;">
      Reservá esta semana y te incluimos:
    </p>

    <div style="margin-bottom:24px;">
      <p style="margin:0 0 4px;font-size:22px;font-weight:700;color:#164e63;">Foto con marco</p>
      <p style="margin:0;font-size:14px;color:#6b7280;font-family:'Playfair Display',Georgia,serif;">Tu mejor momento del día, enmarcado y listo para compartir. <span style="color:#22c55e;font-weight:600;">Gratis.</span></p>
    </div>
    <div style="height:1px;background:#f0fdf4;margin-bottom:24px;"></div>

    <div style="margin-bottom:24px;">
      <p style="margin:0 0 4px;font-size:22px;font-weight:700;color:#164e63;">Video de dron</p>
      <p style="margin:0;font-size:14px;color:#6b7280;font-family:'Playfair Display',Georgia,serif;">La experiencia vista desde el cielo, en video profesional. <span style="color:#22c55e;font-weight:600;">Gratis.</span></p>
    </div>
    <div style="height:1px;background:#f0fdf4;margin-bottom:24px;"></div>

    <div style="margin-bottom:8px;">
      <p style="margin:0 0 4px;font-size:22px;font-weight:700;color:#164e63;">10% de descuento</p>
      <p style="margin:0;font-size:14px;color:#6b7280;font-family:'Playfair Display',Georgia,serif;">Directo sobre el precio de tu reserva, sin condiciones.</p>
    </div>
  </div>

  <!-- Gift Card -->
  <div style="margin:0 48px;padding:28px;background:#ecfeff;border-radius:4px;">
    <p style="margin:0 0 16px;font-size:12px;font-weight:600;letter-spacing:3px;color:#0891b2;text-transform:uppercase;font-family:'Playfair Display',Georgia,serif;">Y además llevás</p>
    <img src="https://hotboatchile.com/images/Gift%20Cards/Gift%20Card%20example%201.jpg"
         alt="Gift Card HotBoat" style="width:100%;border-radius:4px;display:block;margin-bottom:14px;" />
    <p style="margin:0;font-size:14px;color:#164e63;font-family:'Playfair Display',Georgia,serif;">
      Una <strong>gift card válida por 1 año.</strong> Para vos o para regalar.
    </p>
  </div>

  <!-- Código -->
  <div style="padding:40px 48px;text-align:center;">
    <p style="margin:0 0 16px;font-size:12px;letter-spacing:2px;color:#9ca3af;text-transform:uppercase;font-family:'Playfair Display',Georgia,serif;">Tu código de reserva</p>
    <div style="display:inline-block;border:2px solid #0891b2;padding:16px 40px;border-radius:2px;">
      <p style="margin:0;font-size:28px;font-weight:900;letter-spacing:6px;color:#0891b2;">CYBERINVIERNO</p>
    </div>
    <p style="margin:12px 0 0;font-size:12px;color:#9ca3af;font-family:'Playfair Display',Georgia,serif;">Válido hasta el domingo 7 de junio de 2026</p>
  </div>

  <!-- CTA -->
  <div style="padding:0 48px 48px;text-align:center;">
    <a href="https://whatsapp.hotboat.cl/booking"
       style="display:inline-block;background:#22c55e;color:#ffffff;font-weight:700;font-size:15px;padding:16px 48px;border-radius:2px;text-decoration:none;letter-spacing:1px;text-transform:uppercase;font-family:'Playfair Display',Georgia,serif;">
      Reservar ahora
    </a>
    <p style="margin:16px 0 0;font-size:12px;color:#9ca3af;font-family:'Playfair Display',Georgia,serif;">
      <a href="https://hotboat.cl" style="color:#0891b2;text-decoration:none;">hotboat.cl</a>
    </p>
  </div>

  <!-- Footer -->
  <div style="height:4px;background:#0891b2;"></div>
  <div style="padding:20px 48px;text-align:center;background:#f9fafb;">
    <p style="margin:0;font-size:11px;color:#9ca3af;font-family:'Playfair Display',Georgia,serif;">
      HotBoat · Experiencias en el agua · Chile &nbsp;·&nbsp;
      <a href="{{ unsubscribe_url }}" style="color:#9ca3af;">Cancelar suscripción</a>
    </p>
  </div>
</div></body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
# VERSIÓN B — BOLD BRUTALIST
# Playfair Display · Naranja #F97316 + Verde #22C55E · Fondo oscuro #1F2937
# Sin iconos. Números grandes como decoración. Bloques de color duros.
# ─────────────────────────────────────────────────────────────────────────────
HTML_B = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,400;1,700&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:0;background:#111827;">
<div style="font-family:'Playfair Display',Georgia,serif;max-width:600px;margin:0 auto;background:#1f2937;">

  <!-- Header naranja duro -->
  <div style="background:#f97316;padding:24px 36px;display:flex;align-items:center;justify-content:space-between;">
    <img src="https://hotboatchile.com/logo_hotboat_blanco.png" alt="HotBoat" style="height:32px;display:block;" />
    <span style="color:#1f2937;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">CYBER TARDIO</span>
  </div>

  <!-- Headline brutal -->
  <div style="padding:40px 36px 32px;border-bottom:4px solid #f97316;">
    <p style="margin:0 0 8px;font-size:11px;color:#f97316;letter-spacing:3px;">// LLEGAMOS TARDE</p>
    <h1 style="margin:0;font-size:42px;font-weight:700;color:#f8fafc;line-height:1.05;letter-spacing:-1px;">
      LO HICIMOS<br>DE TODAS<br>FORMAS_
    </h1>
  </div>

  <!-- Bloque intro -->
  <div style="padding:24px 36px;background:#111827;border-bottom:2px solid #374151;">
    <p style="margin:0;font-size:13px;color:#9ca3af;line-height:1.8;">
      [ {{ nombre or 'CLIENTE' }} ] &mdash; VÁLIDO HASTA EL 07.06.2026
    </p>
  </div>

  <!-- Oferta 01 -->
  <div style="padding:28px 36px;border-bottom:2px solid #374151;display:flex;align-items:flex-start;gap:20px;">
    <span style="font-size:48px;font-weight:700;color:#374151;line-height:1;min-width:56px;">01</span>
    <div>
      <p style="margin:0 0 4px;font-size:18px;font-weight:700;color:#f8fafc;">FOTO CON MARCO</p>
      <p style="margin:0;font-size:12px;color:#9ca3af;line-height:1.6;">Tu experiencia capturada y enmarcada.</p>
      <span style="display:inline-block;margin-top:8px;background:#22c55e;color:#1f2937;font-size:10px;font-weight:700;letter-spacing:2px;padding:3px 10px;">GRATIS</span>
    </div>
  </div>

  <!-- Oferta 02 -->
  <div style="padding:28px 36px;border-bottom:2px solid #374151;display:flex;align-items:flex-start;gap:20px;">
    <span style="font-size:48px;font-weight:700;color:#374151;line-height:1;min-width:56px;">02</span>
    <div>
      <p style="margin:0 0 4px;font-size:18px;font-weight:700;color:#f8fafc;">VIDEO DE DRON</p>
      <p style="margin:0;font-size:12px;color:#9ca3af;line-height:1.6;">Vista aérea de tu día en el lago. Profesional.</p>
      <span style="display:inline-block;margin-top:8px;background:#22c55e;color:#1f2937;font-size:10px;font-weight:700;letter-spacing:2px;padding:3px 10px;">GRATIS</span>
    </div>
  </div>

  <!-- Oferta 03 -->
  <div style="padding:28px 36px;border-bottom:2px solid #374151;display:flex;align-items:flex-start;gap:20px;">
    <span style="font-size:48px;font-weight:700;color:#374151;line-height:1;min-width:56px;">03</span>
    <div>
      <p style="margin:0 0 4px;font-size:18px;font-weight:700;color:#f8fafc;">10% DESCUENTO</p>
      <p style="margin:0;font-size:12px;color:#9ca3af;line-height:1.6;">En el precio total de tu reserva.</p>
      <span style="display:inline-block;margin-top:8px;background:#f97316;color:#1f2937;font-size:10px;font-weight:700;letter-spacing:2px;padding:3px 10px;">INCLUIDO</span>
    </div>
  </div>

  <!-- Gift Card -->
  <div style="padding:28px 36px;background:#111827;border-bottom:2px solid #374151;">
    <p style="margin:0 0 14px;font-size:11px;color:#f97316;letter-spacing:3px;">// BONUS</p>
    <img src="https://hotboatchile.com/images/Gift%20Cards/Gift%20Card%20example%201.jpg"
         alt="Gift Card" style="width:100%;display:block;border:2px solid #374151;margin-bottom:12px;" />
    <p style="margin:0;font-size:12px;color:#9ca3af;line-height:1.6;">
      GIFT CARD VÁLIDA 1 AÑO — PARA VOS O PARA REGALAR.
    </p>
  </div>

  <!-- Código -->
  <div style="padding:36px;background:#111827;text-align:center;border-bottom:4px solid #f97316;">
    <p style="margin:0 0 12px;font-size:11px;color:#9ca3af;letter-spacing:3px;">CÓDIGO DE RESERVA</p>
    <div style="border:2px solid #22c55e;display:inline-block;padding:16px 32px;">
      <p style="margin:0;font-size:28px;font-weight:700;color:#22c55e;letter-spacing:4px;">CYBERINVIERNO</p>
    </div>
  </div>

  <!-- CTA -->
  <div style="padding:36px;text-align:center;">
    <a href="https://whatsapp.hotboat.cl/booking"
       style="display:inline-block;background:#f97316;color:#1f2937;font-weight:700;font-size:14px;padding:18px 56px;text-decoration:none;letter-spacing:2px;text-transform:uppercase;border:none;">
      RESERVAR AHORA →
    </a>
  </div>

  <!-- Footer -->
  <div style="background:#111827;padding:20px 36px;text-align:center;border-top:2px solid #374151;">
    <p style="margin:0;font-size:11px;color:#4b5563;">
      HOTBOAT.CL &nbsp;/&nbsp; EXPERIENCIAS EN EL AGUA &nbsp;/&nbsp;
      <a href="{{ unsubscribe_url }}" style="color:#4b5563;text-decoration:underline;">BAJA</a>
    </p>
  </div>

</div></body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
# VERSIÓN C — WARM LIFESTYLE / POLAROID FILM
# Playfair Display · Tonos cálidos sepia · Sin iconos · Imagen como protagonista
# Estilo: fotos como si fueran polaroids, textura análoga, calidez
# ─────────────────────────────────────────────────────────────────────────────
HTML_C = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,400;1,700&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:0;background:#1a1209;">
<div style="font-family:'Playfair Display',Georgia,serif;max-width:600px;margin:0 auto;background:#1a1209;">

  <!-- Hero con gradiente lago/atardecer -->
  <div style="background:linear-gradient(180deg,#2d1b00 0%,#1a1209 100%);padding:48px 40px 40px;text-align:center;border-bottom:1px solid #2d1b00;">
    <img src="https://hotboatchile.com/logo_hotboat_blanco.png" alt="HotBoat"
         style="height:52px;width:auto;display:block;margin:0 auto 28px;opacity:0.9;" />
    <h1 style="margin:0;font-family:'Playfair Display',Georgia,serif;font-size:44px;font-weight:700;color:#f5deb3;line-height:1.1;">
      Llegamos tarde al Cyber.
    </h1>
    <h2 style="margin:8px 0 0;font-family:'Playfair Display',Georgia,serif;font-size:32px;font-weight:400;color:#d4956a;line-height:1.2;">
      Lo hicimos de todas formas.
    </h2>
    <p style="margin:20px 0 0;font-size:13px;color:#8b6914;font-weight:500;letter-spacing:1px;">
      {{ nombre or 'Hola' }} &nbsp;·&nbsp; válido hasta el domingo 7 de junio
    </p>
  </div>

  <!-- Intro -->
  <div style="padding:36px 40px 20px;text-align:center;">
    <p style="margin:0;font-size:15px;color:#c8a882;line-height:1.8;font-weight:400;">
      Reservá esta semana y te regalamos estas tres cosas.
    </p>
  </div>

  <!-- Polaroid 1: Foto -->
  <div style="margin:12px 40px;background:#fdf8f0;padding:16px 16px 28px;box-shadow:2px 4px 16px rgba(0,0,0,0.4);transform:rotate(-1.2deg);">
    <div style="background:#e8d8c0;height:140px;display:flex;align-items:center;justify-content:center;margin-bottom:12px;">
      <p style="margin:0;font-family:'Playfair Display',Georgia,serif;font-size:52px;color:#c4a882;">[ foto ]</p>
    </div>
    <p style="margin:0;font-family:'Playfair Display',Georgia,serif;font-size:22px;color:#3d2b1a;text-align:center;">
      Foto con marco &mdash; <span style="color:#b45309;">gratis</span>
    </p>
    <p style="margin:4px 0 0;font-size:12px;color:#8b6914;text-align:center;font-weight:500;">Tu mejor momento del día, enmarcado para siempre.</p>
  </div>

  <!-- Polaroid 2: Dron -->
  <div style="margin:16px 40px;background:#fdf8f0;padding:16px 16px 28px;box-shadow:2px 4px 16px rgba(0,0,0,0.4);transform:rotate(1deg);">
    <div style="background:#c8dce0;height:140px;display:flex;align-items:center;justify-content:center;margin-bottom:12px;">
      <p style="margin:0;font-family:'Playfair Display',Georgia,serif;font-size:52px;color:#5a8fa0;">[ dron ]</p>
    </div>
    <p style="margin:0;font-family:'Playfair Display',Georgia,serif;font-size:22px;color:#3d2b1a;text-align:center;">
      Video de dron &mdash; <span style="color:#b45309;">gratis</span>
    </p>
    <p style="margin:4px 0 0;font-size:12px;color:#8b6914;text-align:center;font-weight:500;">Tu día en el lago, visto desde las alturas.</p>
  </div>

  <!-- Polaroid 3: Descuento -->
  <div style="margin:16px 40px 32px;background:#fdf8f0;padding:16px 16px 28px;box-shadow:2px 4px 16px rgba(0,0,0,0.4);transform:rotate(-0.5deg);">
    <div style="background:#d4e8d0;height:140px;display:flex;align-items:center;justify-content:center;margin-bottom:12px;">
      <p style="margin:0;font-family:'Playfair Display',Georgia,serif;font-size:64px;color:#4a7a42;">10%</p>
    </div>
    <p style="margin:0;font-family:'Playfair Display',Georgia,serif;font-size:22px;color:#3d2b1a;text-align:center;">
      Descuento en tu reserva
    </p>
    <p style="margin:4px 0 0;font-size:12px;color:#8b6914;text-align:center;font-weight:500;">Directo, sin condiciones ni letras chicas.</p>
  </div>

  <!-- Separador -->
  <div style="margin:0 40px;height:1px;background:#2d1b00;"></div>

  <!-- Gift Card -->
  <div style="padding:32px 40px;text-align:center;">
    <p style="margin:0 0 8px;font-family:'Playfair Display',Georgia,serif;font-size:28px;color:#f5deb3;">Y además llevás una gift card</p>
    <p style="margin:0 0 20px;font-size:13px;color:#8b6914;font-weight:500;">válida por 1 año &nbsp;·&nbsp; para vos o para regalar</p>
    <div style="background:#fdf8f0;padding:10px;box-shadow:2px 4px 20px rgba(0,0,0,0.5);display:inline-block;">
      <img src="https://hotboatchile.com/images/Gift%20Cards/Gift%20Card%20example%201.jpg"
           alt="Gift Card HotBoat" style="width:100%;max-width:400px;display:block;" />
    </div>
  </div>

  <!-- Código estilo sello -->
  <div style="padding:0 40px 32px;text-align:center;">
    <p style="margin:0 0 14px;font-size:12px;color:#8b6914;font-weight:600;letter-spacing:2px;text-transform:uppercase;">Tu código</p>
    <div style="display:inline-block;border:2px dashed #8b6914;padding:16px 36px;border-radius:4px;background:#1a1209;">
      <p style="margin:0;font-family:'Playfair Display',Georgia,serif;font-size:34px;color:#f5deb3;letter-spacing:3px;">CYBERINVIERNO</p>
    </div>
    <p style="margin:12px 0 0;font-size:12px;color:#4a3520;font-weight:500;">Válido hasta el domingo 7 de junio de 2026</p>
  </div>

  <!-- CTA -->
  <div style="padding:0 40px 40px;text-align:center;">
    <a href="https://whatsapp.hotboat.cl/booking"
       style="display:inline-block;background:#f5deb3;color:#3d2b1a;font-weight:700;font-size:15px;padding:16px 48px;border-radius:4px;text-decoration:none;font-family:'Playfair Display',Georgia,serif;font-size:22px;letter-spacing:1px;">
      Reservar ahora →
    </a>
  </div>

  <!-- Footer -->
  <div style="background:#110c06;padding:20px 40px;text-align:center;border-top:1px solid #2d1b00;">
    <p style="margin:0;font-size:11px;color:#4a3520;font-weight:500;">
      HotBoat &nbsp;·&nbsp; Experiencias en el agua &nbsp;·&nbsp; Chile<br>
      <a href="{{ unsubscribe_url }}" style="color:#4a3520;">Cancelar suscripción</a>
    </p>
  </div>

</div></body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
# VERSIÓN D — CLAYMORPHISM
# Playfair Display · Índigo #4F46E5 + Naranja #F97316 · Fondo lavanda #EEF2FF
# Cards con sombras gruesas estilo clay, bordes gruesos, muy redondo
# ─────────────────────────────────────────────────────────────────────────────
HTML_D = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,400;1,700&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:0;background:#dde4ff;">
<div style="font-family:'Playfair Display',Georgia,serif;max-width:600px;margin:0 auto;background:#eef2ff;padding:32px 0;">

  <!-- Header clay -->
  <div style="background:#4f46e5;margin:0 24px 24px;border-radius:20px;padding:32px 32px 28px;text-align:center;box-shadow:0 6px 0 #3730a3,0 8px 24px rgba(79,70,229,0.3);">
    <img src="https://hotboatchile.com/logo_hotboat_blanco.png" alt="HotBoat"
         style="height:52px;display:block;margin:0 auto 20px;" />
    <h1 style="margin:0;font-family:'Playfair Display',Georgia,serif;font-size:28px;font-weight:700;color:#ffffff;line-height:1.25;">
      Llegamos tarde al Cyber. ¡Lo hicimos igual! 🎉
    </h1>
    <p style="margin:12px 0 0;font-size:15px;color:#c7d2fe;font-weight:500;">
      {{ nombre or 'Hola' }}, reservá antes del domingo 7 de junio y te regalamos:
    </p>
  </div>

  <!-- Card 1: Foto (clay azul) -->
  <div style="margin:0 24px 16px;background:#ffffff;border-radius:20px;padding:24px;box-shadow:0 6px 0 #bfdbfe,0 8px 20px rgba(59,130,246,0.15);border:3px solid #bfdbfe;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="width:64px;vertical-align:middle;">
        <div style="width:56px;height:56px;background:#dbeafe;border-radius:16px;border:3px solid #93c5fd;text-align:center;line-height:56px;font-size:28px;">📸</div>
      </td>
      <td style="padding-left:16px;vertical-align:middle;">
        <p style="margin:0;font-family:'Playfair Display',Georgia,serif;font-size:20px;font-weight:600;color:#1e3a8a;">Foto con marco</p>
        <p style="margin:2px 0 0;font-size:13px;color:#6b7280;font-weight:500;">Tu mejor momento del día, enmarcado.</p>
      </td>
      <td style="text-align:right;vertical-align:middle;">
        <div style="background:#22c55e;color:#ffffff;font-family:'Playfair Display',Georgia,serif;font-size:16px;font-weight:600;padding:6px 16px;border-radius:99px;box-shadow:0 4px 0 #15803d;white-space:nowrap;">¡Gratis!</div>
      </td>
    </tr></table>
  </div>

  <!-- Card 2: Dron (clay verde) -->
  <div style="margin:0 24px 16px;background:#ffffff;border-radius:20px;padding:24px;box-shadow:0 6px 0 #bbf7d0,0 8px 20px rgba(34,197,94,0.15);border:3px solid #bbf7d0;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="width:64px;vertical-align:middle;">
        <div style="width:56px;height:56px;background:#dcfce7;border-radius:16px;border:3px solid #86efac;text-align:center;line-height:56px;font-size:28px;">🚁</div>
      </td>
      <td style="padding-left:16px;vertical-align:middle;">
        <p style="margin:0;font-family:'Playfair Display',Georgia,serif;font-size:20px;font-weight:600;color:#14532d;">Video de dron</p>
        <p style="margin:2px 0 0;font-size:13px;color:#6b7280;font-weight:500;">Visto desde el cielo, en video profesional.</p>
      </td>
      <td style="text-align:right;vertical-align:middle;">
        <div style="background:#22c55e;color:#ffffff;font-family:'Playfair Display',Georgia,serif;font-size:16px;font-weight:600;padding:6px 16px;border-radius:99px;box-shadow:0 4px 0 #15803d;white-space:nowrap;">¡Gratis!</div>
      </td>
    </tr></table>
  </div>

  <!-- Card 3: Descuento (clay naranja) -->
  <div style="margin:0 24px 24px;background:#ffffff;border-radius:20px;padding:24px;box-shadow:0 6px 0 #fed7aa,0 8px 20px rgba(249,115,22,0.15);border:3px solid #fed7aa;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="width:64px;vertical-align:middle;">
        <div style="width:56px;height:56px;background:#ffedd5;border-radius:16px;border:3px solid #fdba74;text-align:center;line-height:56px;font-size:28px;">💸</div>
      </td>
      <td style="padding-left:16px;vertical-align:middle;">
        <p style="margin:0;font-family:'Playfair Display',Georgia,serif;font-size:20px;font-weight:600;color:#7c2d12;">10% de descuento</p>
        <p style="margin:2px 0 0;font-size:13px;color:#6b7280;font-weight:500;">En el precio total de tu reserva.</p>
      </td>
      <td style="text-align:right;vertical-align:middle;">
        <div style="background:#f97316;color:#ffffff;font-family:'Playfair Display',Georgia,serif;font-size:16px;font-weight:600;padding:6px 16px;border-radius:99px;box-shadow:0 4px 0 #c2410c;white-space:nowrap;">Incluido</div>
      </td>
    </tr></table>
  </div>

  <!-- Gift Card -->
  <div style="margin:0 24px 24px;background:#ffffff;border-radius:20px;padding:24px;box-shadow:0 6px 0 #e9d5ff,0 8px 20px rgba(167,139,250,0.15);border:3px solid #e9d5ff;text-align:center;">
    <p style="margin:0 0 6px;font-family:'Playfair Display',Georgia,serif;font-size:20px;font-weight:600;color:#581c87;">Y además llevás una gift card 🎁</p>
    <p style="margin:0 0 16px;font-size:13px;color:#6b7280;font-weight:500;">Válida por 1 año &nbsp;·&nbsp; para vos o para regalar</p>
    <img src="https://hotboatchile.com/images/Gift%20Cards/Gift%20Card%20example%201.jpg"
         alt="Gift Card" style="width:100%;border-radius:16px;display:block;border:3px solid #e9d5ff;" />
  </div>

  <!-- Código clay -->
  <div style="margin:0 24px 24px;background:#4f46e5;border-radius:20px;padding:28px;text-align:center;box-shadow:0 6px 0 #3730a3,0 8px 24px rgba(79,70,229,0.3);">
    <p style="margin:0 0 12px;font-size:13px;color:#a5b4fc;font-weight:600;letter-spacing:1px;">Tu código de reserva</p>
    <div style="background:#3730a3;border-radius:16px;padding:16px 24px;border:2px solid #6366f1;display:inline-block;">
      <p style="margin:0;font-family:'Playfair Display',Georgia,serif;font-size:30px;font-weight:700;color:#ffffff;letter-spacing:4px;">CYBERINVIERNO</p>
    </div>
    <p style="margin:12px 0 0;font-size:12px;color:#a5b4fc;font-weight:500;">Válido hasta el domingo 7 de junio de 2026</p>
  </div>

  <!-- CTA clay -->
  <div style="margin:0 24px 32px;text-align:center;">
    <a href="https://whatsapp.hotboat.cl/booking"
       style="display:inline-block;background:#f97316;color:#ffffff;font-family:'Playfair Display',Georgia,serif;font-weight:600;font-size:20px;padding:18px 52px;border-radius:20px;text-decoration:none;box-shadow:0 6px 0 #c2410c,0 8px 20px rgba(249,115,22,0.4);">
      ¡Reservar ahora! 🌊
    </a>
  </div>

  <!-- Footer -->
  <div style="padding:16px 24px;text-align:center;">
    <p style="margin:0;font-size:12px;color:#9ca3af;font-weight:500;">
      HotBoat · Experiencias en el agua · Chile<br>
      <a href="{{ unsubscribe_url }}" style="color:#9ca3af;">Cancelar suscripción</a>
    </p>
  </div>

</div></body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
# VERSIÓN E — LUXURY MAGAZINE
# Playfair Display · Negro #1C1917 + Dorado #CA8A04 · Fondo crema #FAFAF9
# Sin iconos. Serif elegante. Líneas doradas finas. Editorial de lujo.
# ─────────────────────────────────────────────────────────────────────────────
HTML_E = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,400;1,700&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:0;background:#e8e0d4;">
<div style="font-family:'Playfair Display',Georgia,serif;max-width:600px;margin:0 auto;background:#fafaf9;">

  <!-- Barra dorada superior -->
  <div style="height:2px;background:linear-gradient(90deg,#ca8a04,#fbbf24,#ca8a04);"></div>

  <!-- Header minimal -->
  <div style="padding:40px 56px 32px;text-align:center;border-bottom:1px solid #e7e0d5;">
    <img src="https://hotboatchile.com/logo_hotboat_blanco.png" alt="HotBoat"
         style="height:60px;display:block;margin:0 auto 20px;filter:invert(1) sepia(1) saturate(2) hue-rotate(5deg) brightness(0.25);" />
    <div style="width:32px;height:1px;background:#ca8a04;margin:0 auto;"></div>
  </div>

  <!-- Headline serif -->
  <div style="padding:40px 56px 32px;text-align:center;">
    <p style="margin:0 0 16px;font-size:11px;letter-spacing:4px;color:#ca8a04;text-transform:uppercase;font-weight:500;">
      Una propuesta de invierno
    </p>
    <h1 style="margin:0;font-family:'Playfair Display',Georgia,serif;font-size:48px;font-weight:600;color:#1c1917;line-height:1.1;font-style:italic;">
      Llegamos tarde al Cyber.
    </h1>
    <h2 style="margin:8px 0 0;font-family:'Playfair Display',Georgia,serif;font-size:36px;font-weight:400;color:#44403c;line-height:1.2;">
      Lo hicimos de todas formas.
    </h2>
    <div style="width:48px;height:1px;background:#ca8a04;margin:28px auto 0;"></div>
  </div>

  <!-- Intro -->
  <div style="padding:0 56px 36px;text-align:center;">
    <p style="margin:0;font-size:14px;color:#78716c;line-height:1.8;font-weight:300;">
      {{ nombre or 'Estimado cliente' }}, reservando antes del domingo 7 de junio<br>
      recibís lo siguiente sin costo adicional:
    </p>
  </div>

  <!-- Oferta 1 -->
  <div style="padding:24px 56px;border-top:1px solid #e7e0d5;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="vertical-align:top;padding-right:24px;width:24px;">
        <p style="margin:4px 0 0;font-family:'Playfair Display',Georgia,serif;font-size:20px;color:#ca8a04;font-style:italic;">I.</p>
      </td>
      <td style="vertical-align:top;">
        <p style="margin:0 0 4px;font-family:'Playfair Display',Georgia,serif;font-size:22px;font-weight:600;color:#1c1917;">Fotografía con marco</p>
        <p style="margin:0;font-size:12px;color:#78716c;line-height:1.7;font-weight:300;">Tu experiencia capturada y presentada en un marco de alta calidad, lista para exhibir.</p>
      </td>
      <td style="text-align:right;vertical-align:top;padding-left:16px;white-space:nowrap;">
        <p style="margin:0;font-size:11px;letter-spacing:2px;color:#ca8a04;font-weight:500;text-transform:uppercase;">Sin cargo</p>
      </td>
    </tr></table>
  </div>

  <!-- Oferta 2 -->
  <div style="padding:24px 56px;border-top:1px solid #e7e0d5;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="vertical-align:top;padding-right:24px;width:24px;">
        <p style="margin:4px 0 0;font-family:'Playfair Display',Georgia,serif;font-size:20px;color:#ca8a04;font-style:italic;">II.</p>
      </td>
      <td style="vertical-align:top;">
        <p style="margin:0 0 4px;font-family:'Playfair Display',Georgia,serif;font-size:22px;font-weight:600;color:#1c1917;">Video aéreo con dron</p>
        <p style="margin:0;font-size:12px;color:#78716c;line-height:1.7;font-weight:300;">Producción audiovisual profesional de tu día en el lago, capturada desde las alturas.</p>
      </td>
      <td style="text-align:right;vertical-align:top;padding-left:16px;white-space:nowrap;">
        <p style="margin:0;font-size:11px;letter-spacing:2px;color:#ca8a04;font-weight:500;text-transform:uppercase;">Sin cargo</p>
      </td>
    </tr></table>
  </div>

  <!-- Oferta 3 -->
  <div style="padding:24px 56px;border-top:1px solid #e7e0d5;border-bottom:1px solid #e7e0d5;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="vertical-align:top;padding-right:24px;width:24px;">
        <p style="margin:4px 0 0;font-family:'Playfair Display',Georgia,serif;font-size:20px;color:#ca8a04;font-style:italic;">III.</p>
      </td>
      <td style="vertical-align:top;">
        <p style="margin:0 0 4px;font-family:'Playfair Display',Georgia,serif;font-size:22px;font-weight:600;color:#1c1917;">Diez por ciento de descuento</p>
        <p style="margin:0;font-size:12px;color:#78716c;line-height:1.7;font-weight:300;">Aplicado directamente sobre el valor de tu reserva, sin condiciones ni restricciones.</p>
      </td>
      <td style="text-align:right;vertical-align:top;padding-left:16px;white-space:nowrap;">
        <p style="margin:0;font-size:11px;letter-spacing:2px;color:#ca8a04;font-weight:500;text-transform:uppercase;">Incluido</p>
      </td>
    </tr></table>
  </div>

  <!-- Gift Card -->
  <div style="padding:40px 56px;text-align:center;border-bottom:1px solid #e7e0d5;">
    <p style="margin:0 0 6px;font-size:11px;letter-spacing:4px;color:#ca8a04;text-transform:uppercase;font-weight:500;">Además</p>
    <p style="margin:0 0 24px;font-family:'Playfair Display',Georgia,serif;font-size:26px;font-weight:600;color:#1c1917;font-style:italic;">Una gift card válida por doce meses</p>
    <img src="https://hotboatchile.com/images/Gift%20Cards/Gift%20Card%20example%201.jpg"
         alt="Gift Card HotBoat"
         style="width:100%;max-width:380px;display:block;margin:0 auto;border:1px solid #e7e0d5;" />
    <p style="margin:16px 0 0;font-size:12px;color:#a8a29e;font-weight:300;">Para disfrutarla cuando desees, o para obsequiarla.</p>
  </div>

  <!-- Código -->
  <div style="padding:40px 56px;text-align:center;border-bottom:1px solid #e7e0d5;">
    <p style="margin:0 0 20px;font-size:11px;letter-spacing:4px;color:#78716c;text-transform:uppercase;font-weight:500;">Código de reserva</p>
    <div style="display:inline-block;border:1px solid #ca8a04;padding:20px 48px;">
      <p style="margin:0 0 4px;font-size:10px;letter-spacing:3px;color:#ca8a04;text-transform:uppercase;font-weight:500;">HOTBOAT</p>
      <p style="margin:0;font-family:'Playfair Display',Georgia,serif;font-size:34px;font-weight:600;color:#1c1917;letter-spacing:4px;">CYBERINVIERNO</p>
    </div>
    <p style="margin:16px 0 0;font-size:11px;color:#a8a29e;font-weight:300;letter-spacing:1px;">Válido hasta el domingo 7 de junio de 2026</p>
  </div>

  <!-- CTA -->
  <div style="padding:40px 56px;text-align:center;">
    <a href="https://whatsapp.hotboat.cl/booking"
       style="display:inline-block;background:#1c1917;color:#ca8a04;font-size:16px;font-weight:700;letter-spacing:3px;text-transform:uppercase;padding:20px 52px;text-decoration:none;">
      Aprovechar Cupón
    </a>
    <p style="margin:20px 0 0;font-size:11px;color:#a8a29e;font-weight:300;">
      <a href="https://hotboat.cl" style="color:#78716c;text-decoration:none;">hotboat.cl</a>
    </p>
  </div>

  <!-- Footer -->
  <div style="height:2px;background:linear-gradient(90deg,#ca8a04,#fbbf24,#ca8a04);"></div>
  <div style="padding:20px 56px;text-align:center;background:#f5f0e8;">
    <p style="margin:0;font-size:10px;color:#a8a29e;font-weight:400;letter-spacing:1px;">
      HOTBOAT &nbsp;·&nbsp; EXPERIENCIAS EN EL AGUA &nbsp;·&nbsp; CHILE<br>
      <a href="{{ unsubscribe_url }}" style="color:#a8a29e;text-decoration:underline;">Cancelar suscripción</a>
    </p>
  </div>

</div></body></html>"""


VERSIONS = [
    {"label": "A — Editorial Minimalista", "name": "Cyber Tardío v.A — Editorial Minimalista", "html": HTML_A, "file": "preview_cyber_A.html"},
    {"label": "B — Bold Brutalist",        "name": "Cyber Tardío v.B — Bold Brutalist",        "html": HTML_B, "file": "preview_cyber_B.html"},
    {"label": "C — Lifestyle Polaroid",    "name": "Cyber Tardío v.C — Lifestyle Polaroid",    "html": HTML_C, "file": "preview_cyber_C.html"},
    {"label": "D — Claymorphism",          "name": "Cyber Tardío v.D — Claymorphism",          "html": HTML_D, "file": "preview_cyber_D.html"},
    {"label": "E — Luxury Magazine",       "name": "Cyber Tardío v.E — Luxury Magazine",       "html": HTML_E, "file": "preview_cyber_E.html"},
]


def main():
    print("\n=== 5 versiones Cyber Tardío HotBoat ===\n")
    base = os.path.dirname(__file__)

    with Session(engine) as session:
        for v in VERSIONS:
            # Template en BD
            existing = session.exec(select(Template).where(Template.name == v["name"])).first()
            if existing:
                existing.html_content = v["html"]
                existing.updated_at = datetime.utcnow()
                session.add(existing)
                session.flush()
                tid = existing.id
                print(f"  Actualizado  ID {tid:3d}  {v['label']}")
            else:
                t = Template(
                    name=v["name"],
                    subject_default="Llegamos tarde al Cyber. Lo hicimos de todas formas.",
                    preview_text="Foto + dron + 10% off. Código CYBERINVIERNO hasta el domingo.",
                    html_content=v["html"],
                )
                session.add(t)
                session.flush()
                tid = t.id
                print(f"  Creado       ID {tid:3d}  {v['label']}")

            # Preview HTML
            rendered = JTemplate(v["html"]).render(nombre="Tomas", unsubscribe_url="#")
            path = os.path.join(base, v["file"])
            with open(path, "w", encoding="utf-8") as f:
                f.write(rendered)

        session.commit()

    # Abrir todos los previews
    print("\n  Abriendo previews en el browser...")
    for v in VERSIONS:
        path = os.path.join(base, v["file"])
        subprocess.Popen(["cmd", "/c", "start", "", path])

    print("\n=== Listo — 5 versiones abiertas ===\n")


if __name__ == "__main__":
    main()
