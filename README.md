# quero-midia

Repositório de peças de mídia do Quero Turismo.

## Publicador seguro do Instagram

`instagram_publisher.py` mantém uma fila persistente em SQLite e opera em **dry-run por padrão**. A execução real exige simultaneamente estado `approved`, aprovação registrada por `Arthur`, `INSTAGRAM_PUBLISHING_ENABLED=true` e a opção explícita `run --execute`.

Requisitos: Python 3.11+ e nenhuma dependência externa. As credenciais são lidas somente em tempo de execução:

```bash
export INSTAGRAM_USER_ID='...'
export INSTAGRAM_ACCESS_TOKEN='...'
export INSTAGRAM_PUBLISHING_ENABLED=false
```

Nunca coloque esses valores em arquivos do repositório. O token não é exibido nem armazenado pela ferramenta. `INSTAGRAM_PUBLISHING_ENABLED` ausente ou com qualquer valor diferente de `true` equivale a `false`.

### Regras editoriais permanentes

- Nada é publicado sem aprovação explícita de Arthur.
- Post de navio vendido pelo Quero Abadá convida `queroabada` e `queronavio` como colaboradores.
- Hospedagem de Carnaval convida somente `queroabada`.
- Navio não vendido pelo Quero Abadá convida somente `queronavio`.
- Toda peça de navio MSC inclui o selo `TOP MSC`.
- Toda arte de navio temático apresenta foto do artista principal; prefira fotografia oficial ou autorizada e nunca apresente imagem gerada como fotografia documental.
- As logos seguem o mesmo critério dos colaboradores: navio vendido pelo Quero Abadá usa Quero Turismo + Quero Abadá + Quero Navio; hospedagem de Carnaval usa Quero Turismo + Quero Abadá; navio não vendido pelo Quero Abadá usa Quero Turismo + Quero Navio.
- Toda arte que exibe preço inclui: `* Valores válidos no momento da postagem e podem mudar sem aviso prévio.`
- A segunda linha da ressalva usa a unidade exata da fonte, por exemplo: `Valores por pessoa, sujeitos à disponibilidade.`, `Valores por casal, sujeitos à disponibilidade.` ou `Valores por cabine, sujeitos à disponibilidade.`
- Para produto vendido pelo Quero Abadá, o Story aponta para a página específica do produto. Quando não for vendido pelo Quero Abadá, aponta para o WhatsApp.
- Story não é publicado enquanto o suporte a link clicável pela API não estiver confirmado e não houver autorização específica. O suporte técnico `--placement story` não constitui autorização: ele só pode ser usado em uma exceção expressa de Arthur, não envia link, legenda nem colaboradores e mantém fila/idempotência próprias.
- A arte deve passar por revisão visual final, incluindo logos e selos exigidos pelo produto, antes de Arthur aprová-la.

As regras de colaboradores são codificadas em `--content-policy` para evitar digitação ou fallback silencioso:

| Política | Colaboradores |
| --- | --- |
| `ship_sold_by_quero_abada` | `queroabada`, `queronavio` |
| `carnival_lodging` | `queroabada` |
| `ship_not_sold_by_quero_abada` | `queronavio` |
| `other` | nenhum |

### Fluxo

Crie um rascunho com identificador único, JPEG local ou URL HTTPS, legenda e horário ISO 8601 com fuso:

```bash
python3 instagram_publisher.py enqueue \
  --piece-id carnaval-2027-hospedagens \
  --media carnaval-2027-hospedagens.jpg \
  --caption 'Legenda para revisão' \
  --scheduled-at '2027-01-15T12:00:00-03:00' \
  --content-policy carnival_lodging
```

A aprovação é uma ação separada e registra o responsável, a data/hora e o identificador da peça:

```bash
python3 instagram_publisher.py approve \
  --piece-id carnaval-2027-hospedagens \
  --approved-by Arthur
```

Somente o estado `approved` passa ao preflight. Os estados persistidos são `draft`, `approved`, `published` e `failed`:

```bash
# Dry-run é o padrão: valida e faz no máximo um GET do username.
python3 instagram_publisher.py run --piece-id carnaval-2027-hospedagens

python3 instagram_publisher.py list
python3 instagram_publisher.py audit
```

O dry-run valida o estado, metadados de aprovação, JPEG local ou URL HTTPS, legenda (até 2.200 caracteres), horário com fuso, presença das credenciais, colaboradores derivados da política e a conta esperada `@quero.turismo`. Ele não cria contêiner de mídia e não publica.

Antes de uma execução autorizada, a mídia deve estar em URL HTTPS pública e retornar `image/jpeg` íntegro sem autenticação. Caminho local serve somente ao dry-run. A flag deve ser habilitada apenas no processo autorizado, sem ser gravada em arquivo:

```bash
INSTAGRAM_PUBLISHING_ENABLED=true \
  python3 instagram_publisher.py run --piece-id ID_APROVADO --execute
```

O fluxo real confirma a conta e a mídia, procura uma publicação equivalente para reconciliação, reutiliza um `container_id` persistido quando existir, cria no máximo um contêiner, aguarda `FINISHED` e chama `media_publish` uma única vez. `container_id`, `media_id` e permalink são persistidos. Falha ambígua em `media_publish` muda o item para `failed` e nunca dispara repetição automática. Se a API rejeitar colaboradores, a execução para sem removê-los e sem publicar uma versão degradada. Uma trava com expiração impede duas execuções concorrentes.

Uma nova tentativa após falha exige investigação, reconciliação por leitura e nova aprovação de Arthur. Nunca apague o banco para contornar as proteções de idempotência.

A fila e o log de auditoria ficam em `.instagram/queue.sqlite3`, ignorado pelo Git. O log contém somente eventos e metadados operacionais, nunca credenciais.

### Testes

```bash
python3 -m unittest discover -s tests -v
```

Os testes usam banco, imagem, cliente de API e credenciais fictícios; não acessam a rede. Eles comprovam bloqueios de estado, aprovação e flag; política de colaboradores; persistência dos IDs; reutilização do contêiner; reconciliação sem POST; ausência de fallback degradado; e não repetição de `media_publish` após falha ambígua.
