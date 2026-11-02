<p align="center">
  <img src="../assets/readme/banners/neo4j.png" alt="Neo4j" width="100%">
</p>

# Situação

Levantamento da main `0d39bf86`, em 2026-10-30.

- Há extrator consistente somente leitura, snapshots, lock com lease, contagem por estágio, validação de retenção e recuperação de limpeza (2026-10-30).
- O SQL usa o schema antigo, incluindo `users` e as referências `fk_*`, e a atualização para o schema atual do `api-core` está pendente (2026-10-30).
- A retenção mínima padrão de 0.5 protege o volume relativo, sem verificar qualidade nem mínimo absoluto na primeira carga, e uma queda legítima exige liberação manual (2026-10-30).
- Os consumidores filtram a versão ativa, e o Job roda no cluster de produção (2026-10-30).
- O extrator guarda todos os datasets em memória. Lote de escrita não limita essa alocação (2026-10-30).
- Renovação do lock acontece entre consultas e lotes. Consulta longa pode ultrapassar a lease e permitir disputa por outra execução (2026-10-30).
- Falha de limpeza após ativação não desfaz a versão ativa e pode deixar versões pendentes (2026-10-30).
- A árvore atual não contém os testes descritos nos READMEs antigos. O CI faz smoke do container e configuração, sem validar integração de dados (2026-10-30).
