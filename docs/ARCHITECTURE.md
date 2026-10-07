# Arquitetura

## Papel no sistema

```text
Aiven PostgreSQL (coredb)        fonte de verdade
        |
        | SQL, somente leitura
        v
database-bootstrap (Job k8s)     extrai, transforma e projeta
        |
        | Bolt, Cypher parametrizado
        v
Neo4j feeddb (GKE)               projeção descartável
        |
        | Bolt, somente leitura
        v
api-recommendation
```

O GKE é efêmero. Quando o cluster é recriado, o Neo4j volta vazio e o bootstrap reconstrói o grafo. Depois disso, um CronJob no cluster reexecuta o mesmo código periodicamente, cada vez gerando um snapshot completo novo.

## Fases de uma execução

1. Schema: constraints e índices, todos com `IF NOT EXISTS`.
2. Lock: `SyncState` com lease renovada a cada lote. Outra execução recebe exit code 2.
3. Extração: uma transação `REPEATABLE READ` somente leitura, uma consulta por dataset (`sync/domains.py`).
4. Nós, depois relações, em lotes de `SYNC_BATCH_SIZE`.
5. Validação e ativação, conforme o README.
6. Limpeza das versões que não são a ativa nem a anterior.

## Decisões

- Dados reais nunca ficam em `.cypher`. O Cypher descreve só a projeção e recebe `$rows`.
- `MERGE` em vez de `CREATE`, com `graph_key = source|sync_version|id`. Cada execução usa uma `sync_version` própria, então duas execuções nunca disputam os mesmos nós.
- A regra de elegibilidade de técnicos vive em um único fragmento SQL (`queries/postgres/fragments/eligible_technician.sql`), incluído pelas consultas que dependem dela. Usuário ativo e `technician.status = 'APPROVED'`.
- O SQL segue o schema real do `database-console/db/core`. Os testes de integração rodam contra esse schema carregado em um PostgreSQL de teste.
- Os campos `name` de técnicos são anonimizados (`Profissional <início do id>`), como no sync original.

## Limites conhecidos

- O Neo4j Community tem um único banco de usuário. O nome `feeddb` vem de `initial.dbms.default_database=feeddb` na primeira subida do Neo4j.
- `dimension` do modelo de painel é calculada como `width * length`. O schema atual não tem coluna `dimension`.
- `professional_review` guarda a avaliação do técnico, mas o texto do comentário não entra no grafo.
