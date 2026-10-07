# Arquitetura

## Papel no sistema

```text
Aiven PostgreSQL (coredb)        fonte de verdade
        |
        | SQL, somente leitura
        v
database-bootstrap (Job k8s)     lê as linhas e as entrega ao Cypher
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

## Divisão de responsabilidades

| Camada | Responsável por |
|---|---|
| `src/extract.sql` | o que sai do PostgreSQL, incluindo as regras de elegibilidade |
| `src/graphs/` | a projeção em grafo, o lock, a validação, a ativação e a limpeza |
| `src/config.json` | valores de configuração (fonte, defaults e limites das variáveis, timeouts) |
| `src/main.py` | ler as variáveis de ambiente, mover as linhas do PostgreSQL para o Neo4j em lotes, chamar os arquivos Cypher na ordem e traduzir falhas em códigos de saída |

Toda regra de negócio fica em SQL ou Cypher. O Python não conhece labels, relações nem colunas: ele descobre os datasets pelas seções de `src/extract.sql` e os estágios pelos arquivos de `src/graphs/nodes/` e `src/graphs/relationships/`.

## Convenções dos arquivos

- `src/extract.sql` reúne todas as consultas em um arquivo. `-- dataset: <nome>` abre a consulta de um dataset e `-- fragment: <nome>` abre um trecho reutilizável; linhas `-- include: <nome>` dentro de um dataset são substituídas pelo fragmento.
- Cada arquivo de `src/graphs/nodes/` e `src/graphs/relationships/` começa com `// dataset: <nome>` e termina com `RETURN count(*) AS merged`. Adicionar um label ou uma relação é adicionar um arquivo (e, para nós, a constraint em `src/graphs/schema.cypher`).
- Os nós rodam antes das relações. Dentro de cada grupo a ordem é alfabética, o que não importa porque os arquivos do mesmo grupo são independentes.

## Fases de uma execução

1. Schema: constraints e índices, todos com `IF NOT EXISTS`.
2. Lock: `SyncState` com lease renovada a cada lote. Outra execução recebe código de saída 2.
3. Extração: uma transação `REPEATABLE READ` somente leitura, uma consulta por dataset.
4. Nós, depois relações, em lotes de `SYNC_BATCH_SIZE`, com verificação de que cada linha lida foi gravada.
5. Validação de retenção por domínio contra a versão ativa, e ativação.
6. Limpeza das versões que não são a ativa nem a anterior.

## Decisões

- Dados reais nunca ficam em `.cypher`. O Cypher descreve só a projeção e recebe `$rows`.
- `MERGE` em vez de `CREATE`, com `graph_key = source|sync_version|id`. Cada execução usa uma `sync_version` própria, então duas execuções nunca disputam os mesmos nós.
- A regra de técnico elegível vive em um único fragmento SQL (`eligible_technician`, em `src/extract.sql`), incluído pelas consultas que dependem dela: usuário ativo e `technician.status = 'APPROVED'`.
- O SQL segue o schema real do `database-console/db/core`. Os testes de integração rodam contra esse schema carregado em um PostgreSQL de teste.
- Os campos `name` de técnicos são anonimizados (`Profissional <início do id>`), como no sync original.
- O repositório não é um pacote Python instalável: roda como `python src/main.py` com dependências em `requirements.txt`. Não há `setup.py`, `pyproject` de build nem metadados `.egg-info`.

## Limites conhecidos

- O Neo4j Community tem um único banco de usuário. O nome `feeddb` vem de `initial.dbms.default_database=feeddb` na primeira subida do Neo4j.
- `dimension` do modelo de painel é calculada como `width * length`. O schema atual não tem coluna `dimension`.
- `professional_review` guarda a avaliação do técnico, mas o texto do comentário não entra no grafo.
