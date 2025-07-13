FROM python:3.12-slim

RUN apt-get update && apt-get install -y locales && \
    sed -i -e 's/# ru_RU.UTF-8 UTF-8/ru_RU.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales

ENV LANG ru_RU.UTF-8
ENV LANGUAGE ru_RU:en
ENV LC_ALL ru_RU.UTF-8

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system .
RUN uv pip install --system "pytest" "pytest-asyncio" "aiosqlite" "ruff" "bandit"

COPY . .

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]