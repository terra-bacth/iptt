# ---- IPTT (FastAPI) container image ----
FROM python:3.12-slim

# Prevents .pyc files, forces unbuffered logs, puts matplotlib config
# in a writable place inside read-only-ish container filesystems.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp \
    PORT=8080

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# OpenShift runs containers with a RANDOM UID in group 0.
# Make the app directory group-0-writable so the app can
# create/write the SQLite DB and any runtime files.
RUN mkdir -p /app/data && \
    chown -R 1001:0 /app && \
    chgrp -R 0 /app && \
    chmod -R g=u /app

USER 1001

EXPOSE 8080

# Single worker: SQLite does not support concurrent writers.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
