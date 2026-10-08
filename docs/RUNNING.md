# Rodando localmente

Requisitos: Python 3.14, Docker e `psql`.

## Instalação

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.dev.txt
```

No Windows, use `.venv/Scripts/python`.

## Bancos descartáveis

```bash
docker run -d --name bootstrap-neo4j -p 127.0.0.1:7687:7687 \
  -e NEO4J_AUTH=neo4j/test-password-for-ci \
  -e NEO4J_initial_dbms_default__database=feeddb \
  neo4j:5.26-community

docker run -d --name bootstrap-postgres -p 127.0.0.1:5432:5432 \
  -e POSTGRES_PASSWORD=test-password-for-ci -e POSTGRES_DB=coredb \
  postgres:16
```

Carregue o schema do `api-core` a partir de um checkout de `Solierrr/database-console`:

```bash
PGHOST=127.0.0.1 PGUSER=postgres PGPASSWORD=test-password-for-ci PGDATABASE=coredb \
  sh scripts/load-core-schema.sh ../database-console
```

Se alguma porta já estiver em uso, troque o lado esquerdo do `-p` e ajuste as variáveis abaixo.

## Variáveis

```bash
export DB_POSTGRES_HOST=127.0.0.1 DB_POSTGRES_PORT=5432 DB_POSTGRES_CORE=coredb \
  DB_POSTGRES_USER=postgres DB_POSTGRES_PASSWORD=test-password-for-ci DB_POSTGRES_SSLMODE=disable \
  DB_NEO4J_URI=bolt://127.0.0.1:7687 DB_NEO4J_USER=neo4j \
  DB_NEO4J_PASSWORD=test-password-for-ci DB_NEO4J_FEED=feeddb
```

## Executar o job

```bash
.venv/bin/python src/main.py
```

## Testes

Unitários, sem bancos:

```bash
.venv/bin/python -m pytest tests/unit
```

Integração, com os bancos acima. Eles apagam e recriam dados, então só rodam com a confirmação explícita:

```bash
BOOTSTRAP_TEST_ALLOW_DESTRUCTIVE=true .venv/bin/python -m pytest
```

Nunca aponte essas variáveis para o banco real: os testes truncam as tabelas do `coredb` e apagam todo o grafo.

## Imagem

```bash
docker build -t database-bootstrap .
docker run --rm --env-file .env database-bootstrap
```
