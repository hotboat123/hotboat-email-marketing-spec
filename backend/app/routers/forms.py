import json
import textwrap
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import PlainTextResponse
from sqlmodel import Session, select

from app.core.config import settings
from app.core.deps import get_current_user, require_editor
from app.database import get_session
from app.models.contact import Contact
from app.models.form import (
    FormSubmission, FormSubmitPayload,
    SignupForm, SignupFormCreate, SignupFormRead, SignupFormUpdate,
)
from app.models.user import User

router = APIRouter()

# ── Authenticated CRUD ────────────────────────────────────────────────────────

@router.get("", response_model=List[SignupFormRead])
def list_forms(session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    return session.exec(select(SignupForm).order_by(SignupForm.created_at.desc())).all()


@router.post("", response_model=SignupFormRead, status_code=201)
def create_form(
    payload: SignupFormCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_editor),
):
    form = SignupForm(**payload.model_dump(), created_by=current_user.id)
    session.add(form)
    session.commit()
    session.refresh(form)
    return form


@router.get("/{form_id}", response_model=SignupFormRead)
def get_form(form_id: int, session: Session = Depends(get_session), _: User = Depends(get_current_user)):
    f = session.get(SignupForm, form_id)
    if not f:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")
    return f


@router.patch("/{form_id}", response_model=SignupFormRead)
def update_form(
    form_id: int,
    payload: SignupFormUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_editor),
):
    f = session.get(SignupForm, form_id)
    if not f:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(f, k, v)
    f.updated_at = datetime.utcnow()
    session.add(f)
    session.commit()
    session.refresh(f)
    return f


@router.delete("/{form_id}", status_code=204)
def delete_form(
    form_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_editor),
):
    f = session.get(SignupForm, form_id)
    if not f:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")
    session.delete(f)
    session.commit()


@router.get("/{form_id}/submissions")
def list_submissions(
    form_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    subs = session.exec(
        select(FormSubmission)
        .where(FormSubmission.form_id == form_id)
        .order_by(FormSubmission.created_at.desc())
        .limit(200)
    ).all()
    total = session.exec(
        select(FormSubmission).where(FormSubmission.form_id == form_id)
    ).all()
    return {"total": len(total), "submissions": subs}


# ── Public endpoints (no auth — called from embedded popup) ──────────────────

def _cors_headers() -> dict:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }


@router.options("/{form_id}/submit")
def submit_preflight(form_id: int):
    return Response(status_code=204, headers=_cors_headers())


@router.post("/{form_id}/submit")
def submit_form(
    form_id: int,
    payload: FormSubmitPayload,
    response: Response,
    session: Session = Depends(get_session),
):
    for k, v in _cors_headers().items():
        response.headers[k] = v

    f = session.get(SignupForm, form_id)
    if not f or f.status != "active":
        raise HTTPException(status_code=404, detail="Formulario no disponible")

    email = payload.email.lower().strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="Email inválido")

    # Upsert contact with opted_in
    contact = session.exec(select(Contact).where(Contact.email == email)).first()
    if contact:
        if not contact.opted_in:
            contact.opted_in = True
            contact.opted_in_at = datetime.utcnow()
            contact.opted_out_at = None
        if payload.name and not contact.name:
            contact.name = payload.name.strip() or None
        if payload.phone and not contact.phone:
            contact.phone = payload.phone.strip() or None
        contact.updated_at = datetime.utcnow()
        session.add(contact)
    else:
        session.add(Contact(
            email=email,
            name=(payload.name or "").strip() or None,
            phone=(payload.phone or "").strip() or None,
            opted_in=True,
            opted_in_at=datetime.utcnow(),
        ))

    session.add(FormSubmission(
        form_id=form_id,
        email=email,
        name=(payload.name or "").strip() or None,
        phone=(payload.phone or "").strip() or None,
        source_url=payload.source_url,
    ))
    session.commit()
    return {"ok": True}


@router.get("/{form_id}/embed.js", response_class=PlainTextResponse)
def embed_js(form_id: int, session: Session = Depends(get_session)):
    f = session.get(SignupForm, form_id)
    if not f or f.status != "active":
        return PlainTextResponse("/* form not found */", media_type="application/javascript")

    cfg = {
        "id": f.id,
        "title": f.title,
        "description": f.description or "",
        "button_text": f.button_text,
        "success_message": f.success_message,
        "collect_name": f.collect_name,
        "collect_phone": f.collect_phone,
        "trigger": f.popup_trigger,
        "delay_seconds": f.popup_delay_seconds,
        "scroll_pct": f.popup_scroll_pct,
        "api": settings.BACKEND_PUBLIC_URL,
    }

    js = _build_embed_js(cfg)
    return PlainTextResponse(
        js,
        media_type="application/javascript",
        headers={**_cors_headers(), "Cache-Control": "no-cache"},
    )


def _build_embed_js(cfg: dict) -> str:
    cfg_json = json.dumps(cfg, ensure_ascii=False)
    return textwrap.dedent(f"""
    (function() {{
      var C = {cfg_json};
      var STORE_KEY = 'hb_form_' + C.id;

      // Only show once per browser session (not if already submitted or dismissed)
      if (sessionStorage.getItem(STORE_KEY)) return;

      var STYLES = `
        @keyframes hbSlideUp {{
          from {{ transform: translateY(100px); opacity: 0; }}
          to   {{ transform: translateY(0);    opacity: 1; }}
        }}
        #hb-popup-overlay {{
          position: fixed; bottom: 0; left: 0; right: 0;
          display: flex; justify-content: center; padding: 16px;
          z-index: 2147483647; pointer-events: none;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}
        #hb-popup-box {{
          background: #fff; border-radius: 16px; overflow: hidden;
          box-shadow: 0 20px 60px rgba(0,0,0,0.2);
          max-width: 420px; width: 100%;
          pointer-events: all;
          animation: hbSlideUp 0.4s cubic-bezier(0.34,1.56,0.64,1);
          border: 1px solid #e2e8f0;
        }}
        #hb-popup-header {{
          background: linear-gradient(135deg,#0369a1 0%,#0ea5e9 100%);
          padding: 20px 48px 20px 24px; position: relative;
        }}
        #hb-popup-close {{
          position: absolute; top: 12px; right: 12px;
          background: rgba(255,255,255,0.2); border: none; color: #fff;
          width: 28px; height: 28px; border-radius: 50%;
          cursor: pointer; font-size: 18px; line-height: 28px; text-align: center;
          transition: background .2s;
        }}
        #hb-popup-close:hover {{ background: rgba(255,255,255,0.35); }}
        #hb-popup-brand {{
          margin: 0 0 4px; color: rgba(255,255,255,0.7);
          font-size: 11px; letter-spacing: 2px; text-transform: uppercase; font-weight: 700;
        }}
        #hb-popup-title {{
          margin: 0; color: #fff; font-size: 19px; font-weight: 700; line-height: 1.3;
        }}
        #hb-popup-body {{ padding: 20px 24px; }}
        #hb-popup-desc {{
          margin: 0 0 16px; color: #64748b; font-size: 14px; line-height: 1.5;
        }}
        .hb-input {{
          width: 100%; padding: 10px 14px; border: 1.5px solid #e2e8f0;
          border-radius: 8px; font-size: 14px; color: #1e293b;
          margin-bottom: 10px; box-sizing: border-box; outline: none;
          transition: border-color .2s;
        }}
        .hb-input:focus {{ border-color: #0ea5e9; }}
        #hb-popup-btn {{
          width: 100%; padding: 12px; background: linear-gradient(135deg,#0369a1,#0ea5e9);
          color: #fff; border: none; border-radius: 10px; font-size: 15px;
          font-weight: 700; cursor: pointer; transition: opacity .2s; margin-top: 4px;
        }}
        #hb-popup-btn:hover {{ opacity: 0.88; }}
        #hb-popup-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
        #hb-popup-success {{
          display: none; text-align: center; padding: 8px 0 4px;
        }}
        #hb-popup-fine {{
          margin: 12px 0 0; color: #94a3b8; font-size: 11px; text-align: center;
        }}
      `;

      // Inject styles
      var style = document.createElement('style');
      style.textContent = STYLES;
      document.head.appendChild(style);

      // Build HTML
      var nameField   = C.collect_name  ? '<input class="hb-input" id="hb-inp-name"  type="text"  placeholder="Tu nombre" />' : '';
      var phoneField  = C.collect_phone ? '<input class="hb-input" id="hb-inp-phone" type="tel"   placeholder="Tu teléfono" />' : '';
      var descHtml    = C.description   ? '<p id="hb-popup-desc">' + C.description + '</p>' : '';

      var html = [
        '<div id="hb-popup-overlay">',
        '  <div id="hb-popup-box">',
        '    <div id="hb-popup-header">',
        '      <button id="hb-popup-close" aria-label="Cerrar">&#x2715;</button>',
        '      <p id="hb-popup-brand">HotBoat</p>',
        '      <h2 id="hb-popup-title">' + C.title + '</h2>',
        '    </div>',
        '    <div id="hb-popup-body">',
        '      ' + descHtml,
        '      <form id="hb-popup-form" novalidate>',
        '        ' + nameField,
        '        <input class="hb-input" id="hb-inp-email" type="email" placeholder="Tu email *" required />',
        '        ' + phoneField,
        '        <button id="hb-popup-btn" type="submit">' + C.button_text + '</button>',
        '      </form>',
        '      <div id="hb-popup-success">',
        '        <div style="font-size:40px;margin-bottom:8px;">&#x2705;</div>',
        '        <p style="color:#166534;font-weight:700;font-size:15px;margin:0">' + C.success_message + '</p>',
        '      </div>',
        '      <p id="hb-popup-fine">Respetamos tu privacidad. Puedes darte de baja cuando quieras.</p>',
        '    </div>',
        '  </div>',
        '</div>',
      ].join('\\n');

      var container = document.createElement('div');
      container.innerHTML = html;

      function closePopup() {{
        var el = document.getElementById('hb-popup-overlay');
        if (el) el.parentNode.removeChild(el);
        sessionStorage.setItem(STORE_KEY, '1');
      }}

      function showPopup() {{
        if (document.getElementById('hb-popup-overlay')) return;
        document.body.appendChild(container.firstChild);

        document.getElementById('hb-popup-close').addEventListener('click', closePopup);

        document.getElementById('hb-popup-form').addEventListener('submit', function(e) {{
          e.preventDefault();
          var email = document.getElementById('hb-inp-email').value.trim();
          if (!email) return;
          var btn = document.getElementById('hb-popup-btn');
          btn.disabled = true;
          btn.textContent = 'Enviando...';

          var data = {{ email: email, source_url: window.location.href }};
          var nameEl  = document.getElementById('hb-inp-name');
          var phoneEl = document.getElementById('hb-inp-phone');
          if (nameEl  && nameEl.value.trim())  data.name  = nameEl.value.trim();
          if (phoneEl && phoneEl.value.trim()) data.phone = phoneEl.value.trim();

          fetch(C.api + '/api/forms/' + C.id + '/submit', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(data),
          }})
          .then(function(r) {{ return r.json(); }})
          .then(function() {{
            document.getElementById('hb-popup-form').style.display = 'none';
            document.getElementById('hb-popup-success').style.display = 'block';
            sessionStorage.setItem(STORE_KEY, 'submitted');
            setTimeout(closePopup, 3500);
          }})
          .catch(function() {{
            btn.disabled = false;
            btn.textContent = C.button_text;
            btn.style.background = '#dc2626';
            btn.textContent = 'Error — intenta de nuevo';
          }});
        }});
      }}

      // Trigger logic
      if (C.trigger === 'delay') {{
        setTimeout(showPopup, C.delay_seconds * 1000);
      }} else if (C.trigger === 'exit_intent') {{
        document.addEventListener('mouseleave', function handler(e) {{
          if (e.clientY <= 0) {{
            showPopup();
            document.removeEventListener('mouseleave', handler);
          }}
        }});
      }} else if (C.trigger === 'scroll') {{
        window.addEventListener('scroll', function handler() {{
          var pct = (window.scrollY / Math.max(1, document.body.scrollHeight - window.innerHeight)) * 100;
          if (pct >= C.scroll_pct) {{
            showPopup();
            window.removeEventListener('scroll', handler);
          }}
        }});
      }}
    }})();
    """).strip()
