FROM pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime

WORKDIR /workspace
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /workspace/training/requirements.txt
RUN pip install --upgrade pip \
  && pip install --no-cache-dir -r /workspace/training/requirements.txt
