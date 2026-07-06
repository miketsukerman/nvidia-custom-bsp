FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    build-essential \
    bc \
    git \
    wget \
    kmod \
    libncurses-dev \
    flex \
    bison \
    libssl-dev \
    qemu-user-static \
    python3 \
    python3-pip \
    device-tree-compiler \
    ca-certificates \
    xz-utils \
    xxd \
    cpio \
    rsync \
    file \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/repo
COPY . /workspace/repo
RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    python3 -m pip install --no-cache-dir .

ENTRYPOINT ["/workspace/repo/docker/entrypoint.sh"]
