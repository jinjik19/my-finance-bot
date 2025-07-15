FROM python:3.12-slim

ENV LANG ru_RU.UTF-8
ENV LANGUAGE ru_RU:en
ENV LC_ALL ru_RU.UTF-8

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends dnsutils && \
    pip install --no-cache-dir  -r requirements.txt && \
    apt-get remove -y dnsutils && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY . .

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]