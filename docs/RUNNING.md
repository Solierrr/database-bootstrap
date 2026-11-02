<p align="center">
  <img src="../assets/readme/banners/neo4j.png" alt="Neo4j" width="100%">
</p>

# Execução local

Requer Python 3.14, acesso a PostgreSQL e Neo4j compatíveis com as queries, make e shell. O guia comum está em [Python](https://github.com/Solierrr/docs-warehouse/blob/main/readme/running/PYTHON.md).

## Preparar

Executar no checkout do job.

```bash
make doctor
make vault
make install
```

O `make vault` lê as pastas `/database` e `/recommendation`, conforme o Makefile, mas o orquestrador não carrega o `.env` sozinho, por isso as variáveis precisam ser exportadas no shell ou passadas ao container antes da execução.

```bash
set -a
. ./.env
set +a
make dev
```

O `make dev` executa uma carga real que escreve no Neo4j, e não um servidor de desenvolvimento, por isso deve apontar para destinos descartáveis ou autorizados para essa finalidade.

| Nome | Uso |
|---|---|
| `DB_POSTGRES_HOST`, `DB_POSTGRES_CORE`, `DB_POSTGRES_USER`, `DB_POSTGRES_PASSWORD` | Origem |
| `DB_POSTGRES_PORT`, `DB_POSTGRES_SSLMODE` | Porta e TLS da origem |
| `DB_NEO4J_URI`, `DB_NEO4J_USER`, `DB_NEO4J_PASSWORD`, `DB_NEO4J_FEED` | Destino |
| `SYNC_BATCH_SIZE` | Lote, padrão 500 |
| `SYNC_LOCK_LEASE_SECONDS` | Lease, padrão 900 segundos |
| `SYNC_MIN_DOMAIN_RETENTION_RATIO` | Mínimo relativo por domínio, padrão 0.5 |
| `NEO4J_WAIT_SECONDS` | Espera inicial de conectividade, padrão 300 segundos |

A proporção de queda precisa ficar entre zero e um, e uma configuração numérica inválida impede o início. A conexão com o PostgreSQL usa limite de 15 segundos e TLS `require` por padrão, e a do Neo4j usa limite de 10 segundos e um pool de até cinco conexões.

## Verificações

O `make lint` roda o Ruff, o `make build` compila `src` e o `make test` não tem comando configurado, porque esta main não tem a suíte `tests/` citada nos textos antigos. O CI constrói o container, importa o módulo e confirma a saída 64 sem configuração, o que não substitui um teste integrado do grafo.

Não há `make openapi`, Swagger ou API própria.

| Saída | Significado |
|---|---|
| 0 | Snapshot ativado |
| 1 | Falha inesperada |
| 2 | Outra execução possui o lock |
| 3 | Snapshot inseguro, contagem divergente ou posse perdida |
| 64 | Configuração ausente ou inválida |

Confira se o extrator está alinhado ao schema atual do `api-core` antes de executar. A rotina auxiliar de schema é externa ao carregamento normal e não corrige automaticamente uma incompatibilidade.

Fontes em [Makefile](https://github.com/Solierrr/database-bootstrap/blob/main/Makefile), [CI](https://github.com/Solierrr/database-bootstrap/blob/main/.github/workflows/ci.yml) e [configuração](https://github.com/Solierrr/database-bootstrap/blob/main/src/config.json).
