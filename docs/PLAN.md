# Plano de implementação futura

Itens que ainda não existem, em ordem de dependência. O que já está pronto e o porquê das decisões estão em [ARCHITECTURE.md](ARCHITECTURE.md).

## 1. Operação do job no cluster

- Usuário somente leitura do PostgreSQL para o job. Hoje ele usa o `DB_POSTGRES_USER` de `/database`, que é o usuário da aplicação.
- Confirmar no banco real que a migração `V10__technician_review_status` (`technician.status`) está aplicada, já que a elegibilidade de técnico depende dela.
- Calibrar `SYNC_BATCH_SIZE` e os limites de memória do Job com o volume real de dados.
- Alerta de falha: enquanto o OTEL não funciona, só o status do Job no ArgoCD mostra uma falha.

## 2. Menos Python

O objetivo é que o Python seja apenas a ponte entre o PostgreSQL e o Neo4j. Falta avaliar se essa ponte pode sair do código.

- Ler o PostgreSQL de dentro do Cypher com `apoc.load.jdbc`. Exige o plugin APOC e o driver JDBC do PostgreSQL no Neo4j, e coloca a credencial do `coredb` no Neo4j. Só vale se o ganho de eliminar `src/main.py` compensar esse acoplamento.
- Manter `src/main.py` e reduzi-lo: mover o que ainda é lógica (a regra de recusa por linha não gravada e a ordem dos estágios) para o próprio Cypher, onde der.

## 3. Camada de contexto por empresa

Prepara os feeds personalizados do `api-recommendation` (ver a spec `feed-architecture`).

- Nós `Company` e relações com unidades, serviços contratados e profissionais contratados.
- Novos datasets em `src/extract.sql` e arquivos em `src/graphs/nodes/` e `src/graphs/relationships/`, seguindo as convenções existentes. Nenhuma mudança em `src/main.py` deve ser necessária.
- Atualizar o contrato do grafo no VersioSpec junto.

## 4. Frescor dos dados

- Cada execução gera um snapshot completo, o que basta para o CronJob diário. Se o frescor virar requisito, avaliar sincronização incremental por `updated_at` ou por evento do `api-core`, sem mudar o contrato do grafo.

## 5. Dependências

- Adicionar o ecossistema `pip` ao `dependabot.yml`: hoje só `github-actions` e `docker` são atualizados, e o `requirements.txt` fica de fora.
- Fixar as dependências com hashes (`pip-compile --generate-hashes`) se o repositório passar a rodar em um ambiente com exigência de supply chain.
