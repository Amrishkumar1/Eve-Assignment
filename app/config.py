from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./eve_healthcare.db"
    jwt_secret_key: str = "development-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    auto_create_tables: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
