#!/bin/sh
# Opens a docker shell to facilitate experimentation within the container environment

volume=`pwd`

docker run --gpus all --rm -i -t --shm-size 1g \
    -e DISABLE_FLASH_ATTENTION=True \
    -v $volume:/app-src laionizer-pdf-ocr:latest /bin/bash
