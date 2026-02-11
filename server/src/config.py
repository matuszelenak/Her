from pydantic_settings import BaseSettings


class Config(BaseSettings):
    ASSISTANT_API_URL: str
    OPENAI_MODEL: str

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432

    #STT
    WHISPER_API_URL: str | None = None
    NEMOTRON_API_URL: str | None = None

    #TTS
    KOKORO_API_URL: str | None = None
    ORPHEUS_API_URL: str | None = None
    CHATTERBOX_API_URL: str | None = None


config = Config()
