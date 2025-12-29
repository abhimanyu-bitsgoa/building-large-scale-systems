FROM ubuntu:24.04

# Avoid interactive prompts during apt install
ENV DEBIAN_FRONTEND=noninteractive

# Install System Tools + Python
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    htop \
    procps \
    iproute2 \
    git \
    nano \
    vim \
    tmux \
    && rm -rf /var/lib/apt/lists/*

# Symlink python to python3 for convenience
RUN ln -s /usr/bin/python3 /usr/bin/python

# Create Virtual Environment at /opt/venv
RUN python3 -m venv /opt/venv

# Activate venv globally by updating PATH
# This ensures every terminal session uses the venv by default
ENV PATH="/opt/venv/bin:$PATH"

# Install Python Workshop Libraries into the venv
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
