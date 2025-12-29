FROM python:3.13-slim

# Install system tools
RUN apt-get update && apt-get install -y \
    curl \
    htop \
    procps \
    iproute2 \
    git \
    nano \
    vim \
    tmux \
    && rm -rf /var/lib/apt/lists/*

# Install python tools
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    requests \
    httpx \
    glances \
    httpie \
    psutil

WORKDIR /workspace

# Keep container running
CMD ["tail", "-f", "/dev/null"]
