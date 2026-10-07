# database-bootstrap

Job que reconstrói o grafo Neo4j `feeddb` a partir do PostgreSQL do `api-core` (`coredb`). O PostgreSQL é a fonte de verdade e o Neo4j é uma projeção descartável: se o cluster for recriado, o grafo volta vazio e este job o repovoa.

Não é um serviço. Não expõe HTTP, não tem Service nem Ingress e só consome CPU e memória enquanto roda. Ele depende apenas do PostgreSQL e do Neo4j, nunca de uma API da aplicação.

## Como funciona

1. Lê o PostgreSQL em uma transação `REPEATABLE READ` somente leitura, com as consultas de `src/database_bootstrap/queries/postgres/`.
2. Grava um snapshot novo no Neo4j, com `MERGE` e parâmetros (`UNWIND $rows`), usando os arquivos de `queries/neo4j/`: schema, depois nós, depois relações.
3. Valida o snapshot: contagem exata de nós e relações e retenção mínima por domínio em relação à versão ativa.
4. Ativa o snapshot trocando `SyncState.active_version`. O `api-recommendation` só lê a versão ativa, então um rebuild nunca serve um grafo pela metade.
5. Remove as versões antigas, mantendo a ativa e a anterior.

Se qualquer passo antes da ativação falhar, a versão ativa continua intacta e o staging é descartado. Um lock com lease impede duas execuções simultâneas.

O contrato do grafo (labels, relações e regra de elegibilidade) está documentado na spec do projeto no VersioSpec.

## Códigos de saída

| Código | Significado |
|---|---|
| 0 | snapshot ativado |
| 1 | falha inesperada |
| 2 | outra sincronização em andamento |
| 3 | snapshot recusado por validação |
| 64 | variáveis de ambiente ausentes ou inválidas |

## Configuração

Todas as variáveis estão em [`.env.example`](.env.example). Em desenvolvimento use um `.env` local (ignorado pelo Git). No GKE elas vêm de um Secret criado a partir do Infisical, pasta `/feeddb` e `/database`.

## Estrutura

```text
src/database_bootstrap/
├── main.py          ponto de entrada e códigos de saída
├── config/          leitura das variáveis de ambiente
├── clients/         conexões com PostgreSQL e Neo4j
├── sync/            domínios, extração do PostgreSQL e snapshot em memória
├── bootstrap/       ordem das etapas, lock, validação e ativação no Neo4j
└── queries/
    ├── postgres/    SQL de extração e fragmentos reutilizados
    └── neo4j/       schema, snapshot, nós e relações em Cypher
tests/
├── unit/
└── integration/     exigem Neo4j e PostgreSQL descartáveis
scripts/             utilitários locais e de CI
docs/                arquitetura e execução
```

Documentação: [ARCHITECTURE.md](docs/ARCHITECTURE.md) e [RUNNING.md](docs/RUNNING.md).
