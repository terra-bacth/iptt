# ---- IPTT (FastAPI) container image ----
# Airgap-friendly: the base image and pip index can be redirected to
# JFrog Artifactory mirrors at build time, e.g.:
#
#   podman build \
#     --build-arg BASE_IMAGE=artifactory.example.com/docker-remote/python:3.12-slim \
#     --build-arg PIP_INDEX_URL=https://artifactory.example.com/artifactory/api/pypi/pypi-remote/simple \
#     -t artifactory.example.com/docker-local/iptt:1.0.0 .
#
ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}

ARG PIP_INDEX_URL=""

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp \
    PORT=8080 \
    HOST="::"

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        ${PIP_INDEX_URL:+--index-url "$PIP_INDEX_URL"} \
        -r requirements.txt

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

# --host "::" is REQUIRED on IPv6 clusters: binding to 0.0.0.0 only opens
# an IPv4 socket and the Service/Route cannot reach the pod.
# "::" also accepts IPv4 clients (dual-stack), so it works everywhere.
# Single worker: SQLite does not support concurrent writers.
CMD ["sh", "-c", "uvicorn main:app --host ${HOST} --port ${PORT} --workers 1"]
