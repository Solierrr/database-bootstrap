<p align="center">
  <img src="../assets/readme/banners/neo4j.png" alt="Neo4j" width="100%">
</p>

# Construção e ativação

O job cria um snapshot sem alterar a versão ativa até a validação terminar.

```mermaid
flowchart TD
  A[Validar configuração e conexão] --> B[Aplicar constraints e índices]
  B --> C{Obteve lock?}
  C -->|Não| X[Sair com código 2]
  C -->|Sim| D[Extrair snapshot PostgreSQL]
  D --> E[Gravar nós em lotes]
  E --> F[Gravar relações em lotes]
  F --> G{Contagens e retenção aceitas?}
  G -->|Não| H[Abortar staging e manter ativa]
  G -->|Sim| I[Ativar nova versão]
  I --> J[Limpar versões antigas]
  J --> K[Liberar lock e terminar]
```

## Falhas e limites

A falta de configuração encerra com código 64, as contagens divergentes, a queda anormal e a perda da posse encerram com 3, e uma exceção inesperada encerra com 1. Uma falha na extração ou no estágio conserva a versão ativa, e o leitor deve seguir o ponteiro da versão em vez de ler todos os nós.

Fonte em [implementação](https://github.com/Solierrr/database-bootstrap/blob/main/src/main.py). O contexto está em [feed de recomendações](https://github.com/Solierrr/docs-warehouse/blob/main/docs/flows/RECOMMENDATION_FEED.md).
