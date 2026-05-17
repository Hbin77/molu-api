from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Gemini
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-pro"

    # Upload constraints
    max_image_mb: int = 10
    allowed_mime: tuple[str, ...] = (
        "image/jpeg",
        "image/png",
        "image/webp",
    )

    # CORS — comma-separated origins. Defaults cover prod web + local dev.
    cors_origins: str = (
        "https://molu.likelionscnu.site,http://localhost:3000,http://localhost:3300"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
