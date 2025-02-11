from string import Template


class DockerFileTemplate(Template):
    """Custom template class that uses % as delimiter instead of $."""

    delimiter = "%"


DEFAULT_IMAGE_NAME = "ansible-toolbox:latest"

DEFAULT_PYTHON_PACKAGES = [
    "requests==2.32.3",
    "docker==7.1.0",
]

DOCKERFILE_TEMPLATE = DockerFileTemplate("""
FROM docker.io/alpine:latest

ENV PYTHONUNBUFFERED=1 \\
    PYTHONIOENCODING=UTF-8 \\
    PIP_NO_CACHE_DIR=yes \\
    VIRTUAL_ENV=/install/.venv \\
    PATH="/install/.venv/bin:$PATH"

RUN apk add --no-cache \\
    ca-certificates \\
    openssh \\
    git \\
    python3 \\
    py3-pip \\
    && python3 -m venv $VIRTUAL_ENV \\
    && pip install --no-cache-dir ansible %additional_packages \\
    && rm -rf /tmp/* /var/cache/apk/* /root/.cache
""")
