# database-bootstrap

Job que reconstrói o grafo Neo4j `feeddb` a partir do PostgreSQL do `api-core` (`coredb`). O PostgreSQL é a fonte de verdade e o Neo4j é uma projeção descartável: se o cluster for recriado, o grafo volta vazio e este job o repovoa.

Não é um serviço. Não expõe HTTP, não tem Service nem Ingress e só consome CPU e memória enquanto roda. Ele depende apenas do PostgreSQL e do Neo4j, nunca de uma API da aplicação.

## Como funciona

A sincronização é descrita em Cypher (`src/graphs/`). O SQL é só a extração, em um único arquivo (`src/extract.sql`). O Python (`src/main.py`) só liga as pontas: lê as linhas do PostgreSQL, entrega cada lote ao Cypher e chama os passos na ordem certa.

1. `src/extract.sql` extrai os dados do `coredb` em uma transação `REPEATABLE READ` somente leitura, uma consulta por dataset.
2. `src/graphs/schema.cypher` garante constraints e índices.
3. `src/graphs/snapshot/acquire_lock.cypher` toma o lock com lease. Outra execução recebe código de saída 2.
4. `src/graphs/nodes/` e depois `src/graphs/relationships/` gravam o snapshot novo, com `MERGE` e `UNWIND $rows`. Cada arquivo declara na primeira linha o dataset que consome (`// dataset: <nome>`) e devolve `count(*) AS merged`; se uma linha lida não foi gravada (por exemplo, uma relação sem ponta), a execução é recusada.
5. `src/graphs/snapshot/validate.cypher` recusa o snapshot se algum label ou relação encolheu abaixo de `SYNC_MIN_DOMAIN_RETENTION_RATIO` em relação à versão ativa.
6. `src/graphs/snapshot/activate_snapshot.cypher` troca `SyncState.active_version`. O `api-recommendation` só lê a versão ativa, então um rebuild nunca serve um grafo pela metade.
7. As versões antigas são removidas, mantendo a ativa e a anterior.

Se qualquer passo antes da ativação falhar, a versão ativa continua intacta e o staging é descartado.

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

Todas as variáveis estão em [`.env.example`](.env.example). Em desenvolvimento use um `.env` local (ignorado pelo Git). No GKE elas vêm de um Secret criado a partir do Infisical, pastas `/feeddb` e `/database`.

## Estrutura

```text
src/
  main.py               liga PostgreSQL, Cypher e Neo4j; códigos de saída
  extract.sql           extração do PostgreSQL: um dataset por seção
  graphs/
    schema.cypher       constraints e índices
    nodes/              um arquivo por label
    relationships/      um arquivo por tipo de relação
    snapshot/           lock, validação, ativação e limpeza
tests/
  unit/
  integration/          exigem Neo4j e PostgreSQL descartáveis
scripts/                utilitários locais e de CI
docs/                   arquitetura, execução e plano
```

Documentação: [ARCHITECTURE.md](docs/ARCHITECTURE.md), [RUNNING.md](docs/RUNNING.md) e [PLAN.md](docs/PLAN.md).
