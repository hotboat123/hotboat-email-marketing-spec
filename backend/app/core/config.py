from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    # Optional once EMAIL_PROVIDER can be "ses" — no longer a hard requirement to boot the app.
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "HotBoat <hola@hotboat.cl>"
    RESEND_WEBHOOK_SECRET: str = ""

    # Which provider app/email/send_email.py uses: "resend" or "ses". Global
    # flag, not per-campaign/per-segment — see app/email/send_email.py.
    EMAIL_ENABLED: bool = True
    EMAIL_PROVIDER: str = "resend"
    # Non-negotiable staging safety valve: when set, ALL outgoing mail (any
    # provider, including full campaign sends) is redirected to this single
    # address instead of the real recipients/bcc. Must never be set in production.
    EMAIL_OVERRIDE_TO: str = ""

    # AWS SES (sesv2) — alternate provider, gradual cutover from Resend.
    # hotboat.cl is DKIM-verified in this AWS account/region (same account
    # used for the sibling hotboat-whatsapp project's reservas.hotboat.cl).
    # tomas@hotboat.cl chosen so replies land in a real, monitored mailbox
    # (Hostinger) — reservas.hotboat.cl's mail plan only supports @hotboat.cl.
    SES_FROM_EMAIL: str = "HotBoat <tomas@hotboat.cl>"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-2"
    # Required for SES to publish Bounce/Complaint/Delivery/Open/Click events to SNS.
    SES_CONFIGURATION_SET: str = ""

    FRONTEND_URL: str = "http://localhost:3000"
    # Public URL of THIS backend — used in embed.js to point the form submit call
    BACKEND_PUBLIC_URL: str = "http://localhost:8000"
    # Si los datos fuente están en otra DB, ponla aquí; si no, usa la misma DATABASE_URL
    HOTBOAT_DATABASE_URL: str = ""
    NOTIFY_EMAIL: str = ""  # Email del admin que recibe alertas (desuscripciones, etc.)
    # WooCommerce REST API — necesario para generar links de pago directo en carrito abandonado
    WOO_URL: str = "https://hotboatchile.com"
    WOO_CK: str = ""   # consumer key  (WooCommerce → Ajustes → Avanzado → REST API)
    WOO_CS: str = ""   # consumer secret

    class Config:
        env_file = ".env"


settings = Settings()
