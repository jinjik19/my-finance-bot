FROM python:3.12-slim

ENV LANG ru_RU.UTF-8
ENV LANGUAGE ru_RU:en
ENV LC_ALL ru_RU.UTF-8

WORKDIR /app

COPY requirements.txt .

RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system .
RUN uv pip install --system "pytest" "pytest-asyncio" "aiosqlite" "ruff" "bandit"

COPY . .

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]