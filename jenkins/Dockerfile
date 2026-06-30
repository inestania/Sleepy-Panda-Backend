FROM jenkins/jenkins:lts

USER root

RUN apt-get update && \
    apt-get install -y \
        wget \
        build-essential \
        libssl-dev \
        zlib1g-dev \
        libncurses5-dev \
        libncursesw5-dev \
        libreadline-dev \
        libsqlite3-dev \
        libgdbm-dev \
        libdb5.3-dev \
        libbz2-dev \
        libexpat1-dev \
        liblzma-dev \
        tk-dev \
        libffi-dev \
        uuid-dev \
        curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /tmp

RUN wget https://www.python.org/ftp/python/3.10.18/Python-3.10.18.tgz && \
    tar -xf Python-3.10.18.tgz && \
    cd Python-3.10.18 && \
    ./configure --enable-optimizations && \
    make -j"$(nproc)" && \
    make altinstall && \
    ln -sf /usr/local/bin/python3.10 /usr/bin/python3 && \
    ln -sf /usr/local/bin/pip3.10 /usr/bin/pip3 && \
    cd / && \
    rm -rf /tmp/Python-3.10*

USER jenkins