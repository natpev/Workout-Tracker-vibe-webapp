# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
# Builds a replaceable Flask/Gunicorn image. Compose supplies external storage;
# no database is created during build or normal startup. pip verifies HTTPS.
FROM python:3.12-slim@sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54
WORKDIR /app
COPY requirements.txt ./
# An optional build secret supplies a combined trusted CA bundle in managed
# environments. It stays out of image layers; normal hosts use system trust.
RUN --mount=type=secret,id=pip_ca \
    if [ -f /run/secrets/pip_ca ]; then \
      PIP_CERT=/run/secrets/pip_ca pip install --no-cache-dir -r requirements.txt; \
    else pip install --no-cache-dir -r requirements.txt; fi
COPY workout_tracker ./workout_tracker
# Checkout permissions can be private in cloud workspaces. Make only packaged
# application sources readable/traversable by the unprivileged runtime identity.
RUN chmod -R a+rX /app && groupadd --gid 10001 tracker && useradd --uid 10001 --gid tracker --no-create-home tracker
USER 10001:10001
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "300", "--workers", "1", "--threads", "2", "--access-logfile", "-", "workout_tracker:create_app()"]
