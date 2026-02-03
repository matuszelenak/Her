from pydantic_settings import BaseSettings


class Config(BaseSettings):
    OPENAI_MODEL: str
    OPENAI_API_URL: str

    TAVILY_API_TOKEN: str | None = None

    LOGFIRE_TOKEN: str | None = None

    class Config:
        case_sensitive = True


config = Config()
