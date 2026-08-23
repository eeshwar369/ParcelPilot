from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    allowed_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:3000,http://localhost:3000").split(",")
        if origin.strip()
    )
    retrieval_provider: str = os.getenv("RETRIEVAL_PROVIDER", "local")
    pinecone_api_key: str = os.getenv("PINECONE_API_KEY", "")
    pinecone_index: str = os.getenv("PINECONE_INDEX", "")
    pinecone_namespace: str = os.getenv("PINECONE_NAMESPACE", "parcelpilot")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    openai_embedding_dimensions: int = int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "1024"))
    database_url: str = os.getenv("DATABASE_URL", "")
    redis_url: str = os.getenv("REDIS_URL", "")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    def validate_production(self) -> None:
        if not self.is_production:
            return
        missing = []
        if self.retrieval_provider != "pinecone":
            missing.append("RETRIEVAL_PROVIDER=pinecone")
        if not self.pinecone_api_key:
            missing.append("PINECONE_API_KEY")
        if not self.pinecone_index:
            missing.append("PINECONE_INDEX")
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not self.database_url:
            missing.append("DATABASE_URL")
        if not self.redis_url:
            missing.append("REDIS_URL")
        if missing:
            raise RuntimeError(f"Production configuration is incomplete: {', '.join(missing)}")


settings = Settings()
