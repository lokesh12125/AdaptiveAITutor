# Execution *service* image. It starts sibling sandbox containers through the Docker socket;
# it never runs student code itself. See docs/security.md for the socket trade-off.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends docker-cli && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY pyproject.toml ./
COPY runner_service ./runner_service
RUN pip install --no-cache-dir .
EXPOSE 8102
CMD ["uvicorn", "runner_service.main:app", "--host", "0.0.0.0", "--port", "8102"]
