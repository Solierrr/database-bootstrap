FROM python:3.12-slim AS build

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN useradd --system --uid 10001 --no-create-home bootstrap

COPY --from=build /install /usr/local
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

USER bootstrap

ENTRYPOINT ["./entrypoint.sh"]
CMD ["python", "-m", "database_bootstrap"]
