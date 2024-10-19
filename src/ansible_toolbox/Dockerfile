FROM docker.io/alpine:latest

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    PIP_NO_CACHE_DIR=yes \
    VIRTUAL_ENV=/install/.venv \
    PATH="/install/.venv/bin:$PATH"

RUN apk add --no-cache \
    ca-certificates \
    openssh \
    git \
    python3 \
    py3-pip \
    && python3 -m venv $VIRTUAL_ENV \
    && pip install --no-cache-dir ansible requests==2.32.3 docker==7.1.0 \
    && rm -rf /tmp/* /var/cache/apk/* /root/.cache
