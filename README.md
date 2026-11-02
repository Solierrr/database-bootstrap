<p align="center">
  <img src="./assets/readme/banners/neo4j.png" alt="Neo4j" width="100%">
</p>

<p align="center">
  <img src="./assets/readme/stacks/python.png" width="100" hspace="8" alt="Python" title="Python">
  <img src="./assets/readme/stacks/postgresql.png" width="100" hspace="8" alt="PostgreSQL" title="PostgreSQL">
</p>

# Reconstrução do grafo de recomendações

[![License](https://img.shields.io/github/license/Solierrr/database-bootstrap)](https://github.com/Solierrr/database-bootstrap/blob/main/LICENSE)
[![GitHub Last Commit](https://img.shields.io/github/last-commit/Solierrr/database-bootstrap)](https://github.com/Solierrr/database-bootstrap/commits)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/Solierrr/database-bootstrap)](https://github.com/Solierrr/database-bootstrap/pulls)
[![Release](https://img.shields.io/github/v/release/Solierrr/database-bootstrap)](https://github.com/Solierrr/database-bootstrap/releases)

Esta rotina prepara os dados usados pelas recomendações de profissionais, fornecedores e ofertas. Ela lê o cadastro de negócio e monta uma nova versão do grafo de consulta. Isso permite reconstruir a projeção quando o banco de recomendações é recriado e atualizar suas informações sem expor uma carga incompleta. A rotina atende à operação da plataforma e não oferece uma tela para a pessoa usuária.

Python transporta os dados do PostgreSQL para o Neo4j. SQL define a extração e Cypher define os nós, as relações e a troca de versão. Uma trava coordena as execuções e verificações impedem a ativação de um snapshot que perdeu dados acima do limite configurado. O grafo é uma projeção do cadastro, enquanto o PostgreSQL continua sendo a fonte de negócio.

## Aprofunde-se no Projeto!

- [OVERVIEW.md](./docs/OVERVIEW.md), finalidade e critérios de seleção.
- [ARCHITECTURE.md](./docs/ARCHITECTURE.md), etapas, versões e dependências.
- [RUNNING.md](./docs/RUNNING.md), configuração, execução e códigos de saída.
- [DEPLOY.md](./docs/DEPLOY.md), imagem, Job e CronJob.
- [STATUS.md](./docs/STATUS.md), limitações e diferenças verificadas.
- [Fluxos](./flows/), reconstrução, ativação e recuperação.
- [NEO4J.md](./database/NEO4J.md), modelo, propriedades e índices.
- [PENDENCIAS.md](./PENDENCIAS.md), confirmações do responsável.

## Contribuindo

- [CONTRIBUTING.md](https://github.com/Solierrr/.github/blob/main/.github/CONTRIBUTING.md), convenções de contribuição.
- [CODE_OF_CONDUCT.md](https://github.com/Solierrr/.github/blob/main/CODE_OF_CONDUCT.md), código de conduta.
- [SECURITY.md](https://github.com/Solierrr/.github/blob/main/SECURITY.md), reporte de vulnerabilidade.
