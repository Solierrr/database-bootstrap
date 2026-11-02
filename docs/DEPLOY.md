<p align="center">
  <img src="../assets/readme/banners/neo4j.png" alt="Neo4j" width="100%">
</p>

# Execução no cluster

O job não possui Service ou Ingress. Ele executa com acesso aos dois bancos e termina com código de saída. O processo comum de imagens e GitOps está em [produção](https://github.com/Solierrr/docs-warehouse/blob/main/readme/deploy/PROD_GKE_ARGOCD.md).

## Configuração declarada

Os manifestos consultados no repositório de infraestrutura, revisão `2f053a24`, apontam para imagem identificada pelo SHA da main analisada.

| Recurso | Comportamento |
|---|---|
| Job | Hook PostSync do Argo CD, até três retries, limpeza após 3600 segundos |
| CronJob | Diariamente às 06h UTC, concorrência Forbid, prazo de início de 3600 segundos |
| Container | Python 3.14-slim, usuário de execução sem privilégio, comando `python src/main.py` |
| Configuração | Secret `database-bootstrap-secrets` |
| Recursos | Request de 100m CPU e 128 MiB, limite de 500m CPU e 512 MiB |

Forbid vale para o CronJob, sem substituir o lock entre execução inicial e periódica. A carga mantém a ativa e a anterior, portanto precisa de espaço para staging e versões durante a atualização.

O workflow de release publica a imagem a cada push na main, e o Job roda no cluster de produção com o Secret de acesso aos bancos.

Fontes em [Dockerfile](https://github.com/Solierrr/database-bootstrap/blob/main/Dockerfile), [publicação](https://github.com/Solierrr/database-bootstrap/blob/main/.github/workflows/release.yml), [Job](https://github.com/Solierrr/infra-gitops/blob/main/services/feeddb/bootstrap-job.yaml) e [CronJob](https://github.com/Solierrr/infra-gitops/blob/main/services/feeddb/bootstrap-cronjob.yaml).
