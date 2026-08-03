"""
Envío directo vía SES (cliente sesv2), mockeado — nunca toca AWS real.

A diferencia del repo hermano hotboat-whatsapp (que manda Content={"Simple":
...} porque ningún call site necesita headers), acá List-Unsubscribe y tags
de campaña están en uso real hoy — así que send_ses_email() SIEMPRE arma
MIME crudo, y estos tests lo verifican de punta a punta: el header sigue
presente, la dirección del From no se corrompe con tildes/ñ, y los tags
llegan como EmailTags (parámetro de primer nivel, no dentro de Content).

Adaptado de las plantillas de la migración de Happy Lápiz a SES.
"""
import email
from email.utils import parseaddr
from unittest.mock import MagicMock, patch

import pytest

from app.email.ses_provider import _safe_from_header, send_ses_email


@pytest.fixture()
def fake_ses_client():
    client = MagicMock()
    client.send_email.return_value = {"MessageId": "fake-message-id-123"}
    return client


class TestFromHeaderEncoding:
    def test_accented_display_name_keeps_address_bare(self):
        result = _safe_from_header("HotBoat Ñañá <tomas@hotboat.cl>")
        assert result.endswith("<tomas@hotboat.cl>")
        assert "tomas@hotboat.cl" in result

    def test_accented_display_name_reaches_raw_mime_intact(self, fake_ses_client):
        with patch("app.email.ses_provider._get_client", return_value=fake_ses_client):
            send_ses_email(
                to="destino@ejemplo.com", subject="Promo", html="<p>Hola</p>",
                from_address="HotBoat Ñañá <tomas@hotboat.cl>",
                access_key="fake", secret_key="fake", region="us-east-2",
            )
        call_kwargs = fake_ses_client.send_email.call_args.kwargs
        raw = call_kwargs["Content"]["Raw"]["Data"]
        msg = email.message_from_bytes(raw)
        _, addr = parseaddr(msg["From"])
        assert addr == "tomas@hotboat.cl"


class TestCustomHeaders:
    def test_list_unsubscribe_header_is_included(self, fake_ses_client):
        headers = {
            "List-Unsubscribe": "<https://ems.hotboat.cl/unsub?email=a>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }
        with patch("app.email.ses_provider._get_client", return_value=fake_ses_client):
            send_ses_email(
                to="destino@ejemplo.com", subject="Promo", html="<p>Hola</p>",
                from_address="tomas@hotboat.cl",
                access_key="fake", secret_key="fake", region="us-east-2",
                headers=headers,
            )
        call_kwargs = fake_ses_client.send_email.call_args.kwargs
        raw = call_kwargs["Content"]["Raw"]["Data"]
        msg = email.message_from_bytes(raw)
        assert msg["List-Unsubscribe"] == headers["List-Unsubscribe"]
        assert msg["List-Unsubscribe-Post"] == headers["List-Unsubscribe-Post"]

    def test_raw_mime_is_always_used_even_without_headers(self, fake_ses_client):
        """A diferencia del repo hermano: acá se usa MIME crudo para TODO
        envío por SES, incluidos los avisos internos sin headers/tags — un
        solo camino de envío, no dos."""
        with patch("app.email.ses_provider._get_client", return_value=fake_ses_client):
            send_ses_email(
                to="admin@hotboat.cl", subject="Aviso interno", html="<p>Hola</p>",
                from_address="tomas@hotboat.cl",
                access_key="fake", secret_key="fake", region="us-east-2",
            )
        call_kwargs = fake_ses_client.send_email.call_args.kwargs
        assert "Raw" in call_kwargs["Content"]
        assert "FromEmailAddress" not in call_kwargs, (
            "con Content=Raw, el From ya va dentro del MIME — no debe "
            "pasarse también como FromEmailAddress (SES lo rechaza)"
        )


class TestTags:
    def test_tags_are_forwarded_as_email_tags(self, fake_ses_client):
        with patch("app.email.ses_provider._get_client", return_value=fake_ses_client):
            send_ses_email(
                to="destino@ejemplo.com", subject="Promo", html="<p>Hola</p>",
                from_address="tomas@hotboat.cl",
                access_key="fake", secret_key="fake", region="us-east-2",
                tags={"campaign_id": "42", "contact_id": "7"},
            )
        call_kwargs = fake_ses_client.send_email.call_args.kwargs
        assert call_kwargs["EmailTags"] == [
            {"Name": "campaign_id", "Value": "42"},
            {"Name": "contact_id", "Value": "7"},
        ]
        # EmailTags is a top-level kwarg on send_email, not nested in Content.
        assert "EmailTags" not in call_kwargs.get("Content", {})


class TestErrorHandling:
    def test_ses_error_propagates_to_caller(self, fake_ses_client):
        fake_ses_client.send_email.side_effect = Exception("Email address is not verified")
        with patch("app.email.ses_provider._get_client", return_value=fake_ses_client):
            with pytest.raises(Exception, match="Email address is not verified"):
                send_ses_email(
                    to="destino@ejemplo.com", subject="s", html="h",
                    from_address="tomas@hotboat.cl",
                    access_key="fake", secret_key="fake", region="us-east-2",
                )

    def test_missing_credentials_raises_before_any_network_call(self, fake_ses_client):
        with patch("app.email.ses_provider._get_client", return_value=fake_ses_client):
            with pytest.raises(ValueError, match="AWS SES credentials"):
                send_ses_email(
                    to="destino@ejemplo.com", subject="s", html="h",
                    from_address="tomas@hotboat.cl",
                    access_key="", secret_key="", region="us-east-2",
                )
        fake_ses_client.send_email.assert_not_called()
