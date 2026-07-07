from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    FEEGOW_BASE_URL: str = "https://api.feegow.com/v1/api"
    FEEGOW_ACCESS_TOKEN: str
    FEEGOW_DEFAULT_UNIDADE_ID: int = 2
    FEEGOW_DEFAULT_ESPECIALIDADE_ID: int = 4
    FEEGOW_TIMEOUT: int = 20
    FEEGOW_RETRIES: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
