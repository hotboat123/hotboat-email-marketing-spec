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
    # Si los datos fuente están en otra DB, ponla aquí; si no, usa la misma DATABASE_URL
    HOTBOAT_DATABASE_URL: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
