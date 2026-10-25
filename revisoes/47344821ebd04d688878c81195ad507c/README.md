# Quero Entregas 2.0 — Fluxo completo de entrega

## Nova versão: tablet e celular — 25/10/2026

**[Abrir o fluxo v9 no tablet de 8 polegadas e no celular](v9-tablet-celular/README.md)** — 31 etapas no tablet e 21 no celular, com fotos, documentos consolidados e estoque.


19 telas reais do protótipo, com dados fictícios. Acompanhe a leitura do voucher, check-in, impressão, montagem, entrega e relatórios. Toque em uma imagem para ampliar.

**Pedido de demonstração #41001:** Ana Demonstração · 1 Camarote Horizonte + 2 Bloco Aurora.

[Baixar todos os prints em ZIP](fluxo-completo.zip) · [Ver resumo visual](00-resumo-do-fluxo.png)

## Atualização: telas por função, sem menu lateral

A interface atual abre diretamente a função do usuário. Atendimento, impressão, estoque, montagem e entrega têm acessos próprios, com permissões verificadas no servidor. Administradores usam um menu compacto. Os exemplos abaixo são fictícios.

- [Atendimento no computador](atendimento-sem-menu.png)
- [Impressão no computador](impressao-sem-menu.png)
- [Atendimento no celular](atendimento-celular-sem-menu.png)

![Atendimento com interface limpa](atendimento-sem-menu.png)

Os relatórios agora executam em outro processo, com conexão SQLite somente leitura. O ensaio interrompeu os relatórios durante check-in, montagem e entrega e publicou/retornou um modelo de impressão sem reiniciar o núcleo. Testes de carga e impressoras reais continuam pendentes. As capturas abaixo preservam versões anteriores do protótipo.

## Nova etapa: conferência consolidada dos documentos

Depois de selecionar os pedidos, o atendente abre **Conferir documentos**. O resumo reúne os documentos exigidos sem repetir o que for comum: uma identidade e, neste exemplo, dois cartões de pagamento distintos. Cada documento mostra os pedidos que o exigem. É necessário conferir todos antes de confirmar a solicitação. A troca de seleção ou de exigências invalida a conferência anterior.

[Ampliar a nova tela](conferencia-documentos.png) · [Ver no celular](conferencia-documentos-celular.png)

![Conferência documental consolidada: uma identidade e dois cartões com seus pedidos](conferencia-documentos.png)

Os documentos e cartões exibidos são fictícios. As regras reais de pagamento/titularidade ainda precisam ser integradas e homologadas. Os painéis gerais abaixo preservam as capturas anteriores a esta nova etapa.

## Imagens em alta resolução

**[Abrir o painel completo em resolução original — 7.680 × 13.975 pixels (4,3 MB)](https://raw.githubusercontent.com/ArthurGrec/quero-midia/main/revisoes/47344821ebd04d688878c81195ad507c/fluxo-completo-alta-resolucao.png)**

Abra o link da imagem original e amplie com os dedos para ler as telas. O painel foi refeito a partir dos prints originais, com as telas inteiras. Para carregar mais rápido no celular, abra uma etapa por vez:

- [1. Atendimento e check-in](https://raw.githubusercontent.com/ArthurGrec/quero-midia/main/revisoes/47344821ebd04d688878c81195ad507c/fluxo-etapa-01-alta-resolucao.png)
- [2. Impressão e preparação](https://raw.githubusercontent.com/ArthurGrec/quero-midia/main/revisoes/47344821ebd04d688878c81195ad507c/fluxo-etapa-02-alta-resolucao.png)
- [3. Estoque e montagem](https://raw.githubusercontent.com/ArthurGrec/quero-midia/main/revisoes/47344821ebd04d688878c81195ad507c/fluxo-etapa-03-alta-resolucao.png)
- [4. Entrega ao cliente](https://raw.githubusercontent.com/ArthurGrec/quero-midia/main/revisoes/47344821ebd04d688878c81195ad507c/fluxo-etapa-04-alta-resolucao.png)
- [5. Relatórios e consulta rápida](https://raw.githubusercontent.com/ArthurGrec/quero-midia/main/revisoes/47344821ebd04d688878c81195ad507c/fluxo-etapa-05-alta-resolucao.png)
- [6. Proteção contra duplicidade](https://raw.githubusercontent.com/ArthurGrec/quero-midia/main/revisoes/47344821ebd04d688878c81195ad507c/fluxo-etapa-06-alta-resolucao.png)

## Visão geral

![Fluxo completo em alta resolução; abra o link acima para ampliar](fluxo-completo-alta-resolucao.png)

## 1. Atendimento e check-in

### 01 · Leitura do voucher do cliente

O QR do cliente identifica Ana e permite consultar todos os pedidos vinculados ao cadastro.

![Leitura do voucher do cliente](01-leitura-do-voucher.png)

### 02 · Pedidos encontrados e elegibilidade

O cliente possui cinco pedidos: dois liberados, um aguardando pagamento, um cancelado e outro destinado ao aeroporto. O pedido #41001 contém dois produtos.

![Pedidos encontrados e elegibilidade](02-pedidos-do-cliente.png)

### 03 · Documentação conferida e solicitação

O operador confere os documentos e solicita os dois pedidos liberados para montagem. Check-in ainda não é entrega.

![Documentação conferida e solicitação](03-documentacao-conferida.png)

### 04 · Um voucher de 52 mm por pedido

A prévia apresenta dois comprovantes, um por pedido liberado. O cliente leva esses vouchers ao setor de montagem.

![Um voucher de 52 mm por pedido](04-vouchers-de-checkin-52mm.png)

## 2. Impressão e preparação

### 05 · Pedidos na fila de impressão de 80 mm

As solicitações chegam à fila do setor de montagem, ainda aguardando que um operador assuma a impressão.

![Pedidos na fila de impressão de 80 mm](05-fila-de-impressao-80mm.png)

### 06 · Pedido reservado para um posto

O pedido #41001 fica reservado para o operador de impressão. A reserva evita que dois postos assumam o mesmo pedido.

![Pedido reservado para um posto](06-operador-assume-impressao.png)

### 07 · Impresso de montagem com QR de entrega

A prévia de 80 mm mostra os dois produtos e suas quantidades: 1 Camarote Horizonte e 2 Bloco Aurora. O QR dedicado será lido na entrega.

![Impresso de montagem com QR de entrega](07-pedido-completo-80mm.png)

### 08 · Impressão confirmada para a montagem

A impressão do pedido #41001 foi confirmada. O pedido #41002 permanece na fila. Nenhuma peça saiu do estoque por imprimir.

![Impressão confirmada para a montagem](08-impressao-confirmada.png)

## 3. Estoque e montagem

### 09 · Peças disponíveis no estoque central

Entrada fictícia de 10 camisas e 10 cartões do camarote, além de 10 camisas e 10 pulseiras do bloco: 40 peças físicas.

![Peças disponíveis no estoque central](09-estoque-central-recebido.png)

### 10 · Abastecimento das araras

Cinco unidades de cada componente vão do central para as araras. O total continua em 40 peças: 20 no central e 20 nas araras.

![Abastecimento das araras](10-araras-abastecidas.png)

### 11 · Conferência antes de montar

A tela lista os componentes exigidos pelo pedido #41001: uma camisa e um cartão do camarote, duas camisas e duas pulseiras do bloco.

![Conferência antes de montar](11-conferencia-dos-componentes.png)

### 12 · Pacote montado e pronto para retirada

A confirmação da montagem transfere seis peças das araras para o pacote do pedido. O total sob custódia permanece igual; a entrega ainda está pendente.

![Pacote montado e pronto para retirada](12-pedido-montado.png)

## 4. Entrega ao cliente

### 13 · Leitura do QR do pedido de 80 mm

No momento da entrega, o operador lê o QR dedicado. O código do cliente e o voucher de 52 mm não confirmam retirada.

![Leitura do QR do pedido de 80 mm](13-leitura-do-qr-de-entrega.png)

### 14 · Entrega confirmada com operador e horário

O pedido #41001 foi entregue integralmente. A tela mostra Ana, os dois produtos, a unidade, o horário e o operador Rafael.

![Entrega confirmada com operador e horário](14-entrega-confirmada.png)

### 15 · Baixa física do pacote entregue

As seis peças do pacote saíram da custódia: restam 34 peças, sendo 20 no central e 14 nas araras. O saldo de pedidos montados voltou a zero.

![Baixa física do pacote entregue](15-baixa-de-estoque-na-entrega.png)

## 5. Relatórios e consulta rápida

### 16 · Entrega registrada no relatório

O relatório apresenta um pedido entregue e três unidades comerciais: 1 camarote e 2 blocos. Esses números são diferentes das seis peças físicas controladas no estoque.

![Entrega registrada no relatório](16-relatorio-de-entregas.png)

### 17 · Quem retirou e quem ainda falta retirar

No Camarote Horizonte, o pedido #41001 aparece retirado, com data, hora e operador. O pedido #41003 permanece pendente, aguardando pagamento.

![Quem retirou e quem ainda falta retirar](17-detalhamento-por-produto.png)

### 18 · Pedido inteiro, mesmo com filtro de produto

A janela rápida mostra Ana e os dois produtos do pedido, incluindo o Bloco Aurora, embora o relatório esteja filtrado pelo Camarote Horizonte.

![Pedido inteiro, mesmo com filtro de produto](18-abertura-rapida-pedido-completo.png)

## 6. Proteção contra duplicidade

### 19 · Nova leitura preserva a entrega original

Uma segunda leitura informa que o pedido já foi entregue. Data, operador e baixa originais permanecem preservados; não há outra saída de estoque.

![Nova leitura preserva a entrega original](19-protecao-contra-entrega-duplicada.png)

---

Capturas de 24/10/2026. Demonstração isolada; impressoras e leitores físicos ainda dependem de validação. O QR do cliente e o voucher de 52 mm identificam o atendimento. Somente o QR dedicado no pedido de 80 mm confirma a entrega.