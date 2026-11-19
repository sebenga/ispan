# Single image: Ionic/Angular SPA + Django API (Frankfurt / Render).
FROM node:22-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY frontend/ ./
ENV NODE_ENV=production
RUN npx ng build --configuration production

FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    SPA_DIR=/app/spa
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend/ /app/
# Ionic angular.json sets outputPath.base=www with browser=""
COPY --from=frontend /frontend/www /app/spa
RUN date -u +%Y-%m-%dT%H:%M:%SZ > /app/.build-time

ENV DJANGO_SECRET_KEY=collectstatic-build-only \
    SECURE_SSL_REDIRECT=false
RUN python manage.py collectstatic --noinput

COPY scripts/render-docker-start.sh /render-docker-start.sh
RUN chmod +x /render-docker-start.sh

EXPOSE 8000
CMD ["/render-docker-start.sh"]
