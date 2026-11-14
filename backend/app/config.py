"""Environment-based configuration. API credentials stay on the server and are never sent to clients."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    # Later files win. backend/.env may hold provider keys; the root .env holds everything else.
    model_config = SettingsConfigDict(env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"), extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+psycopg://csmasf:csmasf_dev_password@127.0.0.1:5544/csmasf"
    content_path: Path = REPO_ROOT / "content"
    chroma_path: Path = BACKEND_DIR / ".data" / "chroma"

    runner_url: str = "http://127.0.0.1:8102"
    runner_token: str = ""
    runner_timeout_seconds: float = 45.0

    llm_provider: str = "none"
    llm_timeout_seconds: float = 15.0
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-5-5"
    ollama_base_url: str = "http://127.0.0.1:11434/v1"
    ollama_model: str = "qwen2.5-coder:1.5b"

    teacher_invite_code: str = ""
    demo_mode: bool = True
    retrieval_allow_synthetic: bool = True
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    session_days: int = 14
    pipeline_workers: int = 4

    max_code_chars: int = 20000
    rate_run_per_minute: int = 30
    rate_submit_per_minute: int = 15
    rate_hint_per_minute: int = 15
    rate_auth_per_minute: int = 12
    rate_import_per_minute: int = 20
    import_page_fetch: bool = True  # False turns off opening external pages. Paste and official APIs still work.
    import_blocked_domains: str = ""  # comma-separated domains this server will never open

    @property
    def import_blocked_domain_list(self) -> list[str]:
        return [d.strip().lower() for d in self.import_blocked_domains.split(",") if d.strip()]


    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def psycopg_url(self) -> str:
        return self.database_url.replace("postgresql+psycopg://", "postgresql://")


settings = Settings()


def check_production_settings(config: Settings) -> list[str]:
    """Settings that are fine on a laptop but unsafe in production. Production startup refuses them."""
    problems = []
    if config.demo_mode:
        problems.append("DEMO_MODE must be false: demo access creates accounts with no password.")
    if config.retrieval_allow_synthetic:
        problems.append("RETRIEVAL_ALLOW_SYNTHETIC must be false: synthetic records must not influence real learners.")
    if len(config.runner_token) < 16:
        problems.append("RUNNER_TOKEN must be a long random value.")
    if "csmasf_dev_password" in config.database_url:
        problems.append("DATABASE_URL still uses the development password.")
    return problems
