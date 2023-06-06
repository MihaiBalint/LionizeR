FROM nvidia/cuda:11.0.3-base-ubuntu20.04

##############################################################################
# Temporary Installation Directory
##############################################################################
ENV STAGE_DIR=/tmp
RUN mkdir -p ${STAGE_DIR}

##############################################################################
# Installation/Basic Utilities
##############################################################################
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
RUN apt-get update && \
        apt-get install -y --no-install-recommends \
        software-properties-common build-essential autotools-dev \
        cmake g++ gcc \
        curl wget vim tmux emacs less unzip \
        htop iftop iotop ca-certificates openssh-client \
        rsync iputils-ping net-tools sudo libgl1 \
        llvm-9-dev


##############################################################################
# Python
##############################################################################
ENV PYTHON_VERSION=3
RUN apt-get install -y python3 python3-dev && \
        rm -f /usr/bin/python && \
        ln -s /usr/bin/python3 /usr/bin/python && \
        curl -O https://bootstrap.pypa.io/get-pip.py && \
        python get-pip.py && \
        rm get-pip.py && \
        pip install --upgrade pip && \
        # Print python an pip version
        python -V && pip -V
RUN pip install pyyaml
RUN pip install ipython

##############################################################################
# Some Packages
##############################################################################
RUN apt-get update && \
        apt-get install -y --no-install-recommends \
        libsndfile-dev \
        libcupti-dev \
        libjpeg-dev \
        libpng-dev \
        screen \
        libaio-dev
RUN pip install psutil \
        yappi \
        cffi \
        ipdb \
        pandas \
        matplotlib \
        py3nvml \
        pyarrow \
        graphviz \
        astor \
        boto3 \
        tqdm \
        sentencepiece \
        msgpack \
        requests \
        pandas \
        sphinx \
        sphinx_rtd_theme \
        scipy \
        numpy \
        sklearn \
        scikit-learn \
        nvidia-ml-py3 \
        cupy-cuda100 \
        accelerate \
        clean-text[gpl] \
        gradio \
        natsort \
        nltk \
        pyspellchecker \
        python-doctr[torch] \
        rapidfuzz==2.13.7 \
        torch \
        tqdm \
        transformers \
        comcrawl \
        fsspec \
        aiohttp \
        loguru \
        fastwarc \
        pysimdjson \
        ipdb
