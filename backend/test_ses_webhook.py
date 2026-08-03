"""
Test suite for the SES/SNS webhook, adapted from the same templates used for
the sibling hotboat-whatsapp migration (which in turn came from the Happy
Lápiz migration). Covers the cert-host allowlist, real RSA signature
verification (not mocked), SubscribeURL never auto-fetched, and — the part
specific to this repo, since it has real sends-tracking tables unlike the
sibling repos — that a Notification event actually updates the matching
CampaignSend/AutomationRun row by message id.
"""
import base64
import json
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.database import get_session
from app.models.automation import Automation, AutomationRun
from app.models.campaign import Campaign, CampaignSend
# Imported (but not created — Contact.extras_favoritos is a Postgres ARRAY
# column SQLite can't compile) so CampaignSend/AutomationRun's foreign keys
# still resolve against a real Column object at metadata-compile time.
from app.models.contact import Contact  # noqa: F401
from app.models.segment import Segment
from app.models.template import Template
from app.models.user import User
from app.routers.ses_webhook import (
    _build_string_to_sign,
    _is_allowed_cert_host,
    _verify_sns_signature,
    router as ses_router,
)


@pytest.fixture(scope="module")
def signing_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "sns.amazonaws.com")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject).issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime(2020, 1, 1, tzinfo=timezone.utc))
        .not_valid_after(datetime(2099, 1, 1, tzinfo=timezone.utc))
        .sign(private_key, hashes.SHA256())
    )
    return private_key, cert.public_bytes(serialization.Encoding.PEM)


def _sign_message(message: dict, private_key) -> str:
    string_to_sign = _build_string_to_sign(message)
    signature = private_key.sign(string_to_sign, padding.PKCS1v15(), hashes.SHA1())
    return base64.b64encode(signature).decode("ascii")


@pytest.fixture
def db_session():
    # StaticPool: every connection shares the same in-memory DB — without it,
    # each new connection to "sqlite://" gets its own private, empty database.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    # Only the two tables this test actually reads/writes. Several tables
    # they have a foreign_key="..." string pointing at (contacts, templates,
    # etc.) use Postgres-only column types (ARRAY, JSONB) SQLite can't
    # compile — but those models stay imported above purely so SQLAlchemy
    # can resolve the FK reference at metadata-compile time; SQLite doesn't
    # enforce FK constraints by default, so the referenced tables don't
    # actually need to exist for CampaignSend/AutomationRun's own CREATE
    # TABLE (with a REFERENCES clause pointing at them) to succeed.
    SQLModel.metadata.create_all(engine, tables=[
        CampaignSend.__table__, AutomationRun.__table__,
    ])
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(db_session):
    app = FastAPI()
    app.include_router(ses_router, prefix="/api/webhooks")
    app.dependency_overrides[get_session] = lambda: db_session
    return TestClient(app)


class TestCertHostAllowlist:
    @pytest.mark.parametrize(
        "signing_cert_url,should_be_allowed",
        [
            ("https://sns.us-east-2.amazonaws.com/SimpleNotificationService-abc123.pem", True),
            ("https://sns.eu-west-1.amazonaws.com/SimpleNotificationService-abc123.pem", True),
            ("https://evil.com/fake-cert.pem", False),
            ("https://sns.us-east-2.amazonaws.com.evil.com/cert.pem", False),
            ("http://sns.us-east-2.amazonaws.com/cert.pem", False),
            ("https://s3.amazonaws.com/sns.us-east-2.amazonaws.com/cert.pem", False),
        ],
    )
    def test_only_real_sns_hosts_are_allowed(self, signing_cert_url, should_be_allowed):
        assert _is_allowed_cert_host(signing_cert_url) == should_be_allowed


class TestSignatureVerification:
    def test_valid_signature_is_accepted(self, signing_keypair):
        private_key, cert_pem = signing_keypair
        message = {
            "Type": "Notification", "MessageId": "abc-123",
            "Message": json.dumps({"eventType": "Delivery"}),
            "Timestamp": "2026-01-01T00:00:00.000Z",
            "TopicArn": "arn:aws:sns:us-east-2:123:ems-ses-events",
            "SigningCertURL": "https://sns.us-east-2.amazonaws.com/cert.pem",
            "SignatureVersion": "1",
        }
        message["Signature"] = _sign_message(message, private_key)
        with patch("app.routers.ses_webhook._fetch_signing_cert", return_value=cert_pem):
            assert _verify_sns_signature(message) is True

    def test_invalid_signature_is_rejected(self):
        message = {
            "Type": "Notification", "MessageId": "abc-123",
            "Message": json.dumps({"eventType": "Delivery"}),
            "Timestamp": "2026-01-01T00:00:00.000Z",
            "TopicArn": "arn:aws:sns:us-east-2:123:ems-ses-events",
            "SigningCertURL": "https://sns.us-east-2.amazonaws.com/cert.pem",
            "Signature": base64.b64encode(b"not-a-real-signature").decode("ascii"),
            "SignatureVersion": "1",
        }
        with patch("app.routers.ses_webhook._fetch_signing_cert") as mock_fetch:
            mock_fetch.return_value = b"-----BEGIN CERTIFICATE-----\nfake\n-----END CERTIFICATE-----"
            assert _verify_sns_signature(message) is False

    def test_rejects_disallowed_cert_host_without_fetching(self, signing_keypair):
        private_key, _ = signing_keypair
        message = {
            "Type": "Notification", "MessageId": "abc-123",
            "Message": json.dumps({"eventType": "Delivery"}),
            "Timestamp": "2026-01-01T00:00:00.000Z",
            "TopicArn": "arn:aws:sns:us-east-2:123:ems-ses-events",
            "SigningCertURL": "https://evil.com/fake-cert.pem",
            "SignatureVersion": "1",
        }
        message["Signature"] = _sign_message(message, private_key)
        with patch("app.routers.ses_webhook._fetch_signing_cert") as mock_fetch:
            assert _verify_sns_signature(message) is False
            mock_fetch.assert_not_called()


class TestSubscriptionConfirmationNeverAutoConfirms:
    def test_subscription_confirmation_only_logs_does_not_fetch_subscribe_url(self, client, signing_keypair):
        private_key, cert_pem = signing_keypair
        payload = {
            "Type": "SubscriptionConfirmation", "MessageId": "sub-123",
            "Message": "You have chosen to subscribe...",
            "SubscribeURL": "https://sns.us-east-2.amazonaws.com/?Action=ConfirmSubscription&TopicArn=...",
            "Timestamp": "2026-01-01T00:00:00.000Z", "Token": "abcToken",
            "TopicArn": "arn:aws:sns:us-east-2:123:ems-ses-events",
            "SigningCertURL": "https://sns.us-east-2.amazonaws.com/cert.pem",
            "SignatureVersion": "1",
        }
        payload["Signature"] = _sign_message(payload, private_key)
        with patch("app.routers.ses_webhook._fetch_signing_cert", return_value=cert_pem), \
             patch("urllib.request.urlopen") as mock_urlopen:
            response = client.post("/api/webhooks/ses", content=json.dumps(payload),
                                    headers={"content-type": "text/plain"})
            assert response.status_code == 200
            assert response.json()["action"] == "manual_confirmation_required"
            mock_urlopen.assert_not_called()


class TestNotificationUpdatesCorrectRow:
    """El caso que no tiene precedente en los repos hermanos: acá SÍ hay una
    tabla de envíos real que actualizar por message id."""

    def _post_notification(self, client, private_key, cert_pem, inner_message: dict):
        envelope = {
            "Type": "Notification", "MessageId": "notif-1",
            "Message": json.dumps(inner_message),
            "Timestamp": "2026-01-01T00:00:00.000Z",
            "TopicArn": "arn:aws:sns:us-east-2:123:ems-ses-events",
            "SigningCertURL": "https://sns.us-east-2.amazonaws.com/cert.pem",
            "SignatureVersion": "1",
        }
        envelope["Signature"] = _sign_message(envelope, private_key)
        with patch("app.routers.ses_webhook._fetch_signing_cert", return_value=cert_pem):
            return client.post("/api/webhooks/ses", content=json.dumps(envelope),
                                headers={"content-type": "text/plain"})

    def test_delivery_event_updates_campaign_send_by_message_id(self, client, db_session, signing_keypair):
        private_key, cert_pem = signing_keypair
        send = CampaignSend(campaign_id=1, contact_id=1, resend_id="ses-msg-abc", status="sent")
        db_session.add(send)
        db_session.commit()
        db_session.refresh(send)

        resp = self._post_notification(client, private_key, cert_pem, {
            "eventType": "Delivery", "mail": {"messageId": "ses-msg-abc"},
        })
        assert resp.status_code == 200

        updated = db_session.exec(select(CampaignSend).where(CampaignSend.id == send.id)).first()
        assert updated.status == "delivered"
        assert updated.delivered_at is not None

    def test_bounce_event_does_not_touch_automation_run_status(self, client, db_session, signing_keypair):
        """AutomationRun.status significa sent/failed/skipped — nunca se
        pisa con vocabulario de entrega, solo los timestamps."""
        private_key, cert_pem = signing_keypair
        run = AutomationRun(
            automation_id=1, contact_email="cliente@ejemplo.com",
            trigger_key="birthday:1", resend_id="ses-msg-xyz", status="sent",
        )
        db_session.add(run)
        db_session.commit()
        db_session.refresh(run)

        resp = self._post_notification(client, private_key, cert_pem, {
            "eventType": "Bounce", "mail": {"messageId": "ses-msg-xyz"},
        })
        assert resp.status_code == 200

        updated = db_session.exec(select(AutomationRun).where(AutomationRun.id == run.id)).first()
        assert updated.status == "sent"  # unchanged — not "bounced"
        assert updated.bounced_at is not None

    def test_unknown_message_id_is_a_no_op(self, client, db_session, signing_keypair):
        private_key, cert_pem = signing_keypair
        resp = self._post_notification(client, private_key, cert_pem, {
            "eventType": "Delivery", "mail": {"messageId": "does-not-exist"},
        })
        assert resp.status_code == 200  # logged and ignored, not an error
