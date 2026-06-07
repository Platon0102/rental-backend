from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/rental_db"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 20

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    TELEGRAM_TOKEN: str = "8477878496:AAHgLi-6FmbVjy0xHmD-iY4PzlUgg5uhnSk"
    TELEGRAM_CHAT_ID: str = ""  # заполняется через настройки

    class Config:
        env_file = ".env"

settings = Settings()
