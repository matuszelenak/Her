from pydantic_settings import BaseSettings


class Config(BaseSettings):
    OPENAI_MODEL: str
    OPENAI_API_URL: str

    TAVILY_API_TOKEN: str

    LOGFIRE_TOKEN: str

    class Config:
        case_sensitive = True
        env_file = ".env"


config = Config()
