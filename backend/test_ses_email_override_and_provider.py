"""
La red de seguridad de la migración Resend -> SES. Acá el riesgo es mayor
que en los repos hermanos: un envío de campaña sale a cientos/miles de
contactos de una vez, no a un solo cliente — por eso el test más importante
de este archivo (test_override_is_applied_by_every_send_call_site) no es
opcional.

Adaptado de las plantillas de la migración de Happy Lápiz a SES.
"""
import subprocess
from pathlib import Path

import pytest

from app.email import send_email as send_email_module
from app.core.config import settings

BACKEND_ROOT = Path(__file__).resolve().parent


@pytest.fixture
def fake_provider(monkeypatch):
    calls = []

    def _fake(*, to, subject, html, from_address, bcc, reply_to, headers, tags):
        calls.append(dict(to=to, subject=subject, bcc=bcc, headers=headers, tags=tags))
        return {"id": "fake-id-123", "MessageId": "fake-id-123"}

    monkeypatch.setattr(send_email_module, "_send_via_resend", _fake)
    monkeypatch.setattr(send_email_module, "_send_via_ses", _fake)
    return calls


class TestEmailOverride:
    def test_noop_when_override_not_set(self, monkeypatch, fake_provider):
        monkeypatch.setattr(settings, "EMAIL_ENABLED", True)
        monkeypatch.setattr(settings, "EMAIL_OVERRIDE_TO", "")

        result = send_email_module.send_email(
            to="real@cliente.com", subject="Asunto", html="<p>hola</p>",
            from_address="tomas@hotboat.cl",
        )
        assert result["sent"] is True
        assert fake_provider[0]["to"] == "real@cliente.com"

    def test_redirects_to_and_bcc_when_set(self, monkeypatch, fake_provider):
        monkeypatch.setattr(settings, "EMAIL_ENABLED", True)
        monkeypatch.setattr(settings, "EMAIL_OVERRIDE_TO", "tester@ejemplo.com")

        result = send_email_module.send_email(
            to="real1@cliente.com", subject="Asunto", html="<p>hola</p>",
            from_address="tomas@hotboat.cl", bcc=["admin@hotboat.cl"],
        )
        assert result["sent"] is True
        call = fake_provider[0]
        assert call["to"] == "tester@ejemplo.com"
        assert "real1@cliente.com" in call["subject"]
        assert call["bcc"] is None

    def test_override_applies_to_a_full_campaign_batch_loop(self, monkeypatch, fake_provider):
        """El caso que más importa acá — no un solo email, sino los N
        contactos de un segmento completo — porque send_campaign_sync llama
        _send_one() en loop, y CADA llamada tiene que pasar por el mismo
        override, no solo la primera."""
        monkeypatch.setattr(settings, "EMAIL_ENABLED", True)
        monkeypatch.setattr(settings, "EMAIL_OVERRIDE_TO", "tester@ejemplo.com")

        recipients = [f"cliente{i}@real.com" for i in range(5)]
        for to in recipients:
            send_email_module.send_email(
                to=to, subject="Campaña", html="<p>hola</p>", from_address="tomas@hotboat.cl",
            )
        assert len(fake_provider) == 5
        assert all(c["to"] == "tester@ejemplo.com" for c in fake_provider), (
            "algún envío del batch se escapó del override"
        )

    def test_override_is_applied_by_every_send_call_site(self):
        """Confirma que ningún call site llama al SDK de Resend o boto3
        directo, saltándose send_email() (y por lo tanto el override)."""
        app_dir = str(BACKEND_ROOT / "app")

        result_resend = subprocess.run(
            ["grep", "-rl", "resend.Emails.send(", app_dir],
            capture_output=True, text=True,
        )
        files = [f for f in result_resend.stdout.splitlines() if f]
        assert len(files) == 1, f"resend.Emails.send() se llama desde más de un archivo: {files}"
        assert files[0].replace("\\", "/").endswith("app/email/resend_provider.py")

        result_boto = subprocess.run(
            ["grep", "-rl", "boto3.client(", app_dir],
            capture_output=True, text=True,
        )
        files2 = [f for f in result_boto.stdout.splitlines() if f]
        assert len(files2) == 1, f"boto3.client() se llama desde más de un archivo: {files2}"
        assert files2[0].replace("\\", "/").endswith("app/email/ses_provider.py")


class TestProviderResolution:
    def test_default_provider_stays_resend_until_explicit_opt_in(self, monkeypatch, fake_provider):
        monkeypatch.setattr(settings, "EMAIL_ENABLED", True)
        monkeypatch.setattr(settings, "EMAIL_PROVIDER", "resend")
        monkeypatch.setattr(settings, "EMAIL_OVERRIDE_TO", "")

        result = send_email_module.send_email(
            to="cliente@ejemplo.com", subject="s", html="h", from_address="f@f.com",
        )
        assert result["provider"] == "resend"

    def test_provider_flips_globally_with_the_flag(self, monkeypatch, fake_provider):
        monkeypatch.setattr(settings, "EMAIL_ENABLED", True)
        monkeypatch.setattr(settings, "EMAIL_OVERRIDE_TO", "")
        monkeypatch.setattr(settings, "EMAIL_PROVIDER", "ses")

        result = send_email_module.send_email(
            to="cliente@ejemplo.com", subject="s", html="h", from_address="f@f.com",
        )
        assert result["provider"] == "ses"

    def test_default_from_address_matches_active_provider(self, monkeypatch):
        from app.email.send_email import default_from_address

        monkeypatch.setattr(settings, "EMAIL_PROVIDER", "resend")
        assert default_from_address() == settings.RESEND_FROM_EMAIL

        monkeypatch.setattr(settings, "EMAIL_PROVIDER", "ses")
        assert default_from_address() == settings.SES_FROM_EMAIL

    @pytest.mark.skip(
        reason="No aplica: un solo negocio, no multi-tenant. El corte de "
        "proveedor es un flag global (EMAIL_PROVIDER) — no existe el "
        "concepto de 'entidad migrada' por separado, a diferencia del "
        "proyecto hermano de donde se adaptó esta plantilla."
    )
    def test_migrated_entity_uses_ses_without_affecting_others(self):
        pass
