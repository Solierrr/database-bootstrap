<p align="center">
  <img src="../assets/readme/banners/neo4j.png" alt="Neo4j" width="100%">
</p>

# Visão de produto

As recomendações precisam de informações sobre ofertas disponíveis, fornecedores, profissionais e serviços já realizados. A rotina prepara essa projeção a partir do cadastro de negócio para que o serviço de recomendação possa consultá-la.

## Dados selecionados

- Ofertas com modelo aprovado, características físicas válidas, preço e estoque positivos e fornecedor ativo.
- Fornecedores com assinatura paga e ainda vigente, sem exigir data final quando ela não existe.
- Profissionais aprovados ligados a contas ativas.
- Profissões com nome preenchido e registros profissionais dentro da validade.
- Vínculos, turnos, serviços, atribuições e experiência em serviços concluídos.
- Médias e contagens de avaliações ativas, sem copiar o comentário para o grafo.

A disponibilidade efetiva de uma oferta é o menor valor entre a oferta e o estoque. O nome do profissional é substituído por um rótulo derivado do identificador. Isso não torna todo o conjunto anônimo, pois identificadores, registro profissional e localização continuam presentes.

## Atualização

Cada execução constrói uma versão separada e, antes de ativá-la, compara o volume de cada domínio com a versão ativa, bloqueando a troca quando a queda passa da proporção configurada, que por padrão é metade do volume anterior. Uma queda legítima ou uma primeira carga vazia exigem liberação manual.

A troca aponta para a versão nova e mantém a anterior, enquanto a limpeza remove as versões mais antigas quando possível. Uma falha antes da ativação conserva a versão ativa, e uma falha na limpeza depois da ativação não desfaz a publicação.

## Limite de integração

O serviço de recomendação consulta somente a versão ativa, e a rotina não controla a decisão final de ranqueamento nem atende pedidos HTTP. O extrator ainda precisa ser atualizado para o schema atual do cadastro.
