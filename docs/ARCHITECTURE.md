<p align="center">
  <img src="../assets/readme/banners/neo4j.png" alt="Neo4j" width="100%">
</p>

# Arquitetura

Job Python 3.14 que lê PostgreSQL por psycopg e grava Neo4j por Bolt. O Python descobre datasets e estágios a partir de SQL e Cypher, sem definir as regras de elegibilidade no orquestrador.

```mermaid
flowchart LR
  P[(PostgreSQL de negócio)] -->|SQL somente leitura e TLS configurado| E[Extrator]
  E --> M[Datasets em memória]
  M -->|Bolt com usuário e senha| S[Snapshot Neo4j em staging]
  S --> V[Validação e ativação]
  V --> G[(Grafo ativo)]
  G -->|Bolt e versão ativa| C[Serviço de recomendação]
  J[Job ou CronJob] --> E
```

## Componentes

| Caminho | Papel |
|---|---|
| `src/main.py` | Configuração, extração, lotes e códigos de saída |
| `src/config.json` | Variáveis, padrões, limites e timeouts |
| `src/extract.sql` | Dez datasets e fragmentos reutilizados |
| `src/graphs/schema.cypher` | Constraints e índices |
| `src/graphs/nodes/` | Dez projeções de nós de domínio |
| `src/graphs/relationships/` | Sete tipos de relação |
| `src/graphs/snapshot/` | Lock, validação, ativação e limpeza |

## Protocolo e dados

O PostgreSQL e o Neo4j recebem as credenciais do ambiente, e a rotina não tem autenticação JWT, chave de serviço nem endpoint HTTP próprio. O contexto integrado está no [feed de recomendações](https://github.com/Solierrr/docs-warehouse/blob/main/docs/flows/RECOMMENDATION_FEED.md).

A conexão PostgreSQL usa REPEATABLE READ e somente leitura. O extrator acumula os dez datasets em memória com fetchall antes de gravar o grafo. `SYNC_BATCH_SIZE` limita o envio ao Neo4j, sem limitar a memória da extração.

As queries ainda usam `users` e colunas `fk_*`, enquanto a main atual do cadastro passou a nomes como `user_account` e referências terminadas em `_id`, e o job não adapta esses nomes. A atualização para o schema atual do `api-core` está pendente.

O modelo está em [NEO4J.md](../database/NEO4J.md), e o `graph_key` inclui a fonte e a versão, o que permite montar o staging sem alterar os nós da versão ativa, com cada execução recebendo um UUID próprio.

## Consistência

O schema é aplicado antes do lock, que fica em `SyncState` com lease e o token da execução e é renovado depois de cada dataset e lote, sem heartbeat durante uma consulta longa. Quem perde a posse do lock não consegue ativar a versão pelo caminho protegido.

Cada estágio devolve quantidade de linhas processadas. Ela deve coincidir com o dataset enviado, inclusive quando múltiplas linhas convergem no mesmo nó por MERGE. Isso detecta relações sem ponta, sem equivaler a contar nós únicos.

A validação compara labels e tipos de relação por volume, não o conteúdo completo, e um domínio sem registros na versão ativa não estabelece um mínimo inicial. Uma queda maior que a proporção configurada bloqueia a troca e exige liberação manual.

A ativação troca `active_version` e registra a anterior, e se a resposta se perde o código tenta reconciliar a troca antes de abortar. A limpeza e a liberação são best effort e podem deixar pendências recuperadas na próxima execução, e o consumidor respeita o ponteiro ativo.

## Observabilidade e versão

Os logs registram a versão, as contagens e as falhas, e a saúde é medida pelo resultado do processo e dos Jobs, já que não há rota de health. A imagem usa Python 3.14-slim com usuário sem privilégio, e o workflow publica a imagem a cada mudança na main.

A main analisada é `0d39bf86`, em 2026-10-30. Fontes em [orquestrador](https://github.com/Solierrr/database-bootstrap/blob/main/src/main.py), [extração](https://github.com/Solierrr/database-bootstrap/blob/main/src/extract.sql), [configuração](https://github.com/Solierrr/database-bootstrap/blob/main/src/config.json) e [ativação](https://github.com/Solierrr/database-bootstrap/blob/main/src/graphs/snapshot/activate_snapshot.cypher).
