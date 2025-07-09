from pydantic_settings import BaseSettings


class Config(BaseSettings):
    ASSISTANT_API_URL: str

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432

    WHISPER_API_URL: str | None = None
    KOKORO_API_URL: str | None = None
    ORPHEUS_API_URL: str | None = None
    CHATTERBOX_API_URL: str | None = None

    class Config:
        env_file = ".env"


config = Config()
