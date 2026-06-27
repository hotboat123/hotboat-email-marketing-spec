from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    RESEND_API_KEY: str
    RESEND_FROM_EMAIL: str = "HotBoat <hola@hotboat.cl>"
    RESEND_WEBHOOK_SECRET: str = ""
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
