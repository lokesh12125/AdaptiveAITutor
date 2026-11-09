from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RUNNER_", env_file=Path(__file__).resolve().parents[2] / ".env", extra="ignore")

    # Shared secret with the backend. The service refuses to start without one.
    token: str = ""
    # "docker" is the only isolating backend. "local_dev_unsafe" must be chosen explicitly
    # and is reported to the UI as not secure; there is no automatic fallback between them.
    backend: str = "docker"
    sandbox_image: str = "csmasf-sandbox:py312"
    docker_binary: str = "docker"
    max_concurrent_jobs: int = 3
    max_queued_jobs: int = 12
    container_memory_mb: int = 256
    container_pids: int = 64
    container_cpus: str = "1"
    tmpfs_mb: int = 32
    dev_harness_dir: Path = Path(__file__).resolve().parent.parent / "sandbox"


settings = Settings()
