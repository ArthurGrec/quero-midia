---
name: quero-instagram-intelligence
description: Analisa desempenho e referências do Carnaval, identifica oportunidades e prepara pautas semanais para Quero Turismo, Quero Abadá e Quero Navio, sempre com aprovação antes da criação e da publicação.
---

# Inteligência editorial do Instagram — Grupo Quero

Use esta skill quando Arthur pedir análise de perfil, benchmark, tendências, pauta, calendário ou ideias para Instagram.

## Fontes obrigatórias

1. Leia `references/source-registry.json`.
2. Para métricas próprias, use somente leitura na API e mantenha `INSTAGRAM_USER_ID` e `INSTAGRAM_ACCESS_TOKEN` apenas em runtime. Nunca imprima o token.
3. Para concorrentes e referências, use somente conteúdo publicamente acessível, links, capturas ou exportações fornecidas por Arthur.
4. Se a API não entregar métricas de terceiros, declare a limitação. Nunca estime curtidas, alcance, salvamentos, compartilhamentos ou retenção.
5. Separe fatos confirmados, sinais observados e hipóteses editoriais.

## Classificação das fontes

- `owned`: perfis do Grupo Quero.
- `direct_competitor`: vende Carnaval para o mesmo público.
- `partial_competitor`: considerar apenas o recorte de Carnaval.
- `artist`, `block`, `camarote`: fontes de agenda, colaboração e tendências.
- `influencer`: referência de linguagem, alcance e possíveis parcerias.

Não trate artista, bloco, camarote ou influenciador como concorrente comercial direto.

## Método de análise

Para o perfil próprio, compare ao menos:

- visualizações, alcance e interações;
- curtidas, comentários, compartilhamentos e salvamentos;
- formato, tema, abertura, CTA, data e horário;
- desempenho por alcance, não apenas números absolutos;
- conteúdo recente versus base histórica.

Considere viral um conteúdo que fique claramente acima da mediana do próprio perfil. Quando houver dados suficientes, use múltiplos de mediana e velocidade nas primeiras 24 e 72 horas. Não chame de viral apenas por ter muitas curtidas.

No benchmark público, observe formato, frequência, tema, oferta, linguagem, identidade, velocidade aparente, comentários e sinais públicos de compartilhamento. Inspire-se no mecanismo; nunca copie arte, texto ou conceito distintivo.

## Saída editorial

Entregue primeiro:

1. diagnóstico curto;
2. oportunidades e riscos;
3. pauta de sete dias;
4. justificativa de cada ideia;
5. formato, horário, CTA, fonte e colaboração sugerida.

O padrão semanal é de três peças por dia:

- 09h: alcance, emoção, notícia ou entretenimento;
- 15h: utilidade, produto ou conversão;
- 19h: Story interativo que aprende com a audiência.

Varie Reels, carrosséis, fotos e Stories. Evite três ofertas diretas no mesmo dia.

## Aprovações e publicação

1. Apresente as ideias antes de criar imagens ou vídeos.
2. Só produza as peças que Arthur aprovar.
3. Apresente as peças e legendas finais para nova conferência.
4. Não publique sem autorização explícita de Arthur para aquela peça ou lote.
5. Use o publicador seguro existente, com fila, dry-run, idempotência e colaboração obrigatória conforme as regras do repositório.

## Regras de conteúdo

- Priorize Salvador real, multidão, trio, artistas e experiências humanas.
- Linguagem baiana pode aparecer com naturalidade, sem caricatura.
- Títulos devem ser curtos, grandes e legíveis no celular.
- Conteúdo comercial precisa informar condições, unidade do preço e disponibilidade.
- Confirme agendas, atrações, datas, preços, hotéis e viradas de lote na fonte oficial antes de criar ou publicar.
- Fotografia de artista deve ser oficial ou autorizada; não apresente imagem gerada como registro documental.
- Respeite as regras permanentes de logos, colaboradores, TOP MSC e Stories do README.

## Memória e melhoria contínua

Após cada semana, compare previsto versus realizado e registre:

- três vencedores;
- três conteúdos abaixo da mediana;
- temas que geraram compartilhamento, salvamento e conversa;
- aprendizados para a próxima pauta.

Nunca transforme um resultado isolado em regra permanente.
