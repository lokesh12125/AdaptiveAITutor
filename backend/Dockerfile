FROM python:3.12-slim
WORKDIR /srv/backend
COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/alembic.ini ./
COPY content /srv/content
RUN pip install --no-cache-dir .
ENV CONTENT_PATH=/srv/content
EXPOSE 8101
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8101"]
