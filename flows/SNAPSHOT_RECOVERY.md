<p align="center">
  <img src="../assets/readme/banners/neo4j.png" alt="Neo4j" width="100%">
</p>

# Recuperação de snapshots

A rotina reconcilia ativação ambígua e tenta limpar versões descartadas sem remover ativa ou anterior.

```mermaid
flowchart TD
  A[Ativar snapshot] --> B{Resposta confirma ativação?}
  B -->|Sim| C[Registrar anterior e limpeza]
  B -->|Não| D[Consultar estado para reconciliar]
  D -->|Ativação confirmada| C
  D -->|Não confirmada| E[Abortar staging]
  C --> F[Limpar versões elegíveis]
  F -->|Falha| G[Manter pendência para próxima execução]
  F -->|Sucesso| H[Remover pendência]
  E --> I[Tentar limpar e liberar lock]
  G --> J[Preservar ativa e anterior]
  H --> J
```

## Falhas e limites

As etapas de limpeza e liberação toleram falhas e registram log, e uma ativação confirmada não é revertida por falha posterior de limpeza. A recuperação não dispensa a revisão manual de um snapshot legítimo com queda grande.

Fonte em [implementação](https://github.com/Solierrr/database-bootstrap/blob/main/src/graphs/snapshot/reconcile_activation.cypher). O contexto está em [feed de recomendações](https://github.com/Solierrr/docs-warehouse/blob/main/docs/flows/RECOMMENDATION_FEED.md).
