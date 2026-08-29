# AJSYSTEM — framework declarativo de listas e formulários

O **ajsystem** é um framework web (Flask) para construir aplicações de gestão
(CRUD) de forma **declarativa**: você define *entidades*, *listas* e *formulários*
em dicionários Python e o framework monta blueprints, rotas, telas, autenticação
e menu automaticamente.

Este README ensina a criar um **novo app do zero** usando o framework e serve de
referência completa de configuração.

---

## Checklist de revisão

Estado de cada propriedade do contrato, validado página a página. A revisão
guia a reorganização deste README ao final: marcas somem e as seções de
referência (§5–§7) passam a refletir somente o contrato aprovado.

Atualização recente: Inclusão da dataclass `Query` em `defs/data.py` estilo SQL (`fields`, `join`, `when`, `groups`, `order`, `limit`) para uso em `List` e `Report`.

Legenda: `✓` aprovada · `✗` desaprovada (deprecada) · `~` quebrada (a corrigir) · `vazio` pendente.

### Field — propriedades de campo (§5)

| Propriedade | Estado | Onde validada |
|---|---|---|
| `agg` | ✗/✓ | **Removida do field** (decisão). A agregação é propriedade do **componente**, não do campo. No **form/table** (sub-tabela de sessão) implementado agora: `table.columns` (lista de nomes de campos resolvidos pela `Entity` da página) e `table.total` (lista de nomes → soma vertical no rodapé); `agg` fica **declarativo por-linha** na coluna (`'pago': {'agg': 'sum'}`), suportado mas sem uso real em pedidos/orcamentos. `ReportColumn.agg` (report) segue e permanece. Migração por componente: **list** — `agg: 'sum'` removido de `movimentos`/`transacao`/`compras` (inerte no HTML); **report** — já via `ReportColumn.agg`. Implementar list/table-aggr em futuras páginas |
| `align` | ✓ | Tipos numéricos (`INT`/`NUM`/`PERCENT`) — células da lista à direita; inputs `number` alinham à direita globalmente (CSS `input[type="number"]`) |
| `attrs` | ✗ | Categorias — substituída por `min`/`max`/`step`; reavaliar se necessário |
| `calc` | ✓ | Campo **calculado virtual** (não persistido): aceita expressão string (`QuoteItem.valor` = `'quantidade * preco_unitario'` — célula ao vivo na sub-tabela) ou **callable** `f(item) -> valor` (Orçamentos — `validade_data` = data de vencimento, exibida na lista e no form como rótulo `readonly`). Substitui a prop `function` (§5.2) |
| `card_path` | ✗ | Substituída por `query.display` (FK — derivado automaticamente no list) ou `calc` (display derivado, ex.: `validade_data`). Sem uso direto nos módulos |
| `decimals` | ✓ | Insumos — `fator`; Carteiras — `taxa_recebimento` (PERCENT) |
| `DK` | ✓ | Insumos — `ingredient_id`/`product_id` (chave da linha-pai; oculto, `in_form=0`); Orçamentos — `quote_id` |
| `filter` | ✗ | Substituída por `in_filter` (0/1/2/3) — o tipo do widget é inferido do campo (`input`/`options`/`query`), com `in_filter` 0/1/2/3 para ocultar/forçar (§5.3) |
| `filter_options` | ✗ | Redundante com `options`/`query` — opções derivadas automaticamente |
| `filter_path` | ✗ | Substituída por `query.display` (derivado automaticamente no filtro select) |
| `function` | ✗ | **Recusada** — substituída por `calc` callable (campo calculado virtual na coluna). Sem uso direto nos módulos |
| `hidden` |  | a validar — campo invisível que submete via `<input type="hidden">` |
| `hide_if` | ✗ | Substituída por `when` (callable `(instance) -> bool`) — Suporta condições complexas (comparações, múltiplos campos) |
| `ID` em coluna FK | ✗ | Insumos — `ingredient_id`/`product_id` eram `ID`; usar `DK` (linha-pai) ou `FK` |
| `in_form` | ✓ | Gate do form (renomeada de `edit`), tri-state: `0` não exibe nem submete (defaults `ID`/`DK`; Orçamentos `total`/`status`/`pedido_id`; Pedidos `cliente`/`carteira`/`transacao`/`quote_id`; Operações `indice`; Produtos `ativo`); `1` edita (padrão); `2` exibe apenas (sem input, não submete) — Orçamentos `data_pedido`/`validade_data`; `3` exibe apenas **se houver valor** (vazio omite o campo) — Orçamentos `data_renovacao` |
| `in_filter` | ✓ | Gate do filtro de lista (renomeada de `filter`): `0` oculta (Orçamentos `data_renovacao`/`validade_data`/`carteira_id`/`pedido_id`; Operações `indice`; Movimentos `previsao`; Pedidos `transacao`/`quote_id`); `1` input (texto/número/data); `2` select (1 opção); `3` checklist multi-seleção (1+ opções) — Orçamentos `status`; `None` = auto do campo (text/number/date→1; select/options/query/boolean→2) |
| `in_list` | ✓ | Coluna na tabela e/ou card: `0` exclui da listagem/card/filtro; `1` coluna na linha (vai p/ o card quando não couber, padrão); `2` sempre no card — Produtos `descricao` (`in_list: 2`; `True`→`1`, `False`→`0`) |
| `label` | ✓ | Insumos — `product_id` → 'Produto'; Carteiras — `prazo_recebimento` → 'Prazo', `taxa_recebimento` → 'Taxa' |
| `link` | ✗ | Removida — navegação resolvida pelo motor via `query.model`, não explicitamente no field |
| `list` | ✓ | Insumos — `tipo`/`unidade_medida` (LIST) e `etapas` (MULT10); Carteiras — `uso`/`gerar` (LIST) |
| `LIST` em campo multivalorado | ✗ | Insumos — `etapa` (valor único) → `MULT10` (`etapas`) |
| `mask` | ✓ | Categorias — `ordem` (`'999'`) |
| `__meta__` | ✗ | **Removida** — label/readonly de sessões derivadas substituídos por `label` explícito na config da sessão; `masterkey` substitui query explícito em DK |
| `masterkey` | ✓ | **FK/DK (opcional)**: chave do `MODEL_MAP` que identifica o field do relacionamento na tabela-mestra (ex.: `'quote'` em `quote_id`) — substitui `__meta__`/query explícito em `DK`. Popula `query` = `Query(model=<chave>)`. **Consolida pares FK**: um campo `*_id` com `masterkey` serve tanto para exibição na lista quanto para dados (Pedidos — `transacao_id`/`movto_id` consolidados de pares `transacao`+`transacao_id`/`movto`+`movto_id`) |
| `total` | ✓ | **Total de session (table)**: prop `total` dentro de `table` na session config. É uma **lista de nomes de fields** da Entity que terão seus valores **somados** na row de rodapé (soma vertical, opcionalmente com `calc`/`currency` derivados da Entity). O rótulo 'Total' é interno ao motor e não deve ser informado pelo usuário. Exemplo: `{'table': {'columns': ['product_id', 'quantidade', 'preco_unitario', 'valor'], 'total': ['quantidade', 'valor']}}`. Se não definido, não exibe row de total. |
| `group_by` (table) | ✓ | **Agrupamento em table readonly**: prop `group_by` dentro de `table` (ex.: `{'table': {'group_by': 'status', 'columns': [...], 'total': ['qtd', 'total'], 'order_by': 'data desc'}}`). Agrupa os registros do relacionamento pelo field (ordenado pelas options da Entity), renderizado pelo macro `item_table_grouped` com **subtotal por grupo e total geral**. Sessão é forçada `readonly`. O subtotal de cada grupo usa o mesmo `table.total` (soma vertical). `order_by` opcional ordena dentro de cada grupo. Contas — `Pedidos` agrupados por `status`. |
| `max` | ✓ | Categorias — `ordem` |
| `min` | ✓ | Categorias — `ordem`; Orçamentos — `validade` (`min: 1`) |
| `MULT10` | ✓ | Insumos — `etapas` (códigos concatenados, máx. 10 opções 0-9; editor genérico abre em modal) |
| `on_set` | ✓ | Produtos — `ingredient_id` (qtd/unidade); Orçamentos — `product_id` (preço); Insumos — `unidade` (fator=1) |
| `percent` | ✓ | Carteiras — `taxa_recebimento` (tipo `PERCENT`); formata `12,5%` na lista e sufixo `%` no input do form |
| `query` | ✓ | `Query` dataclass (aceita `str` = model / `dict` / instância) — model, `field`, `columns`, `display`, `return_field`, `when`, `order`; implícitos derivados do model (§5.4) |
| `query_filter` | ✗ | Substituída por `Query.when` (SQL) — sem uso direto nos módulos |
| `readonly` | ✓ | Pedidos/Recursos — `id`/`total`/`status` (FIELD_* de `app/fields`) |
| `required` | ✓ | Insumos — `product_id`, `unidade_medida`, `fator`, `unidade` |
| `step` | ✓ | Passo do input quando definido na Entidade (ex.: `0.1`; mostra as setinhas do spinner); sem `step` o input emite `step="any"` e não exibe as setinhas |
| `tags` | ✓ | Fields renderizados como badges — Form: nav bar (à direita, flex-wrap); List: substitui texto da célula. Cores inferidas do valor ou por `colors: {valor: 'cor'}`. Orçamentos — `status` |
| `transform` | ✓ | Insumos — `nome` ('title'); Carteiras — `nome` ('title') |
| `type` | ✓ | Categorias — `ID`, `TEXT`, `INT`, `BOOL`; Carteiras — `LIST`, `INT`, `NUM`, `PERCENT` |
| `width` | ✓ | Categorias — `id`; Carteiras — `id` |
| `when` (botão) | ✓ | Condição callable `(instance) -> bool` para exibir o botão (substitui `hide_if`) — Orçamentos `Enviar`: `lambda i: i.pedido_id is None and i.status < 7`; `Converter`: `lambda i: i.pedido_id is None and i.status < 7` |

> Padrão dos inputs numéricos: alinhados à direita (CSS global), conteúdo selecionado
> ao focar (digitar sobrescreve) e sem spinner, a menos que a Entidade defina `step`.

### Page — abas e configuração da listagem (§6)

| Propriedade | Estado | Onde validada |
|---|---|---|
| `tabs.<id>.type` | ✓ | Dados/`List`, Filtros/`Filter` — 7 módulos (Categorias, Carteiras, Insumos, Produtos, Contas, Operações, Orçamentos); `Report`/`Custom` reservados; tipo inválido → `ValueError` |
| `tabs.<id>.type` derivado da chave | ✓ | `Dados`→`List`, `Filtros`→`Filter`, `Relatórios`→`Report`, senão `Custom` |
| `tabs.<id>.max_width` | ✓ | Carteiras — `Filtros.max_width: 80` (painel `max-width:80ch`, centralizado); demais sem max_width |
| `tabs.<id>.template` | ✓ | Propriedade disponível (ex.: aba Dados usa template da página); Orçamentos usava `sys/orcamentos/list.html` e **foi removido** — passou a usar `pages/list.html` do motor (templates custom eliminados do módulo) |
| auto-append de `Filtros` | ✓ | `Page` sem aba `Filter` ganha `Filtros` padrão (módulos migrados declaram explícito) |
| forma legada `List` | ✓ | Módulo com `List` sem `Page` → default `Dados(List)+Filtros(Filter)` |
| `fields` | ✓ | Modelo único expande toda a Entity, com visibilidade via flags: list usa `'Quote'` + `in_list: 0` para ocultar (Orçamentos — `validade`/`forminhas`/`observacao`); form usa `'Quote'` + `in_form: 0`/`2`/`3` para ocultar/exibir (Orçamentos — `total`/`status`/`pedido_id` ocultos; `data_pedido`/`validade_data` exibidos; `data_renovacao` exibido só quando houver). Lista explícita `['Entity.campo', ...]` também suportada |
| `ordering` | ✓ | Categorias — `['ordem', 'nome']`; Carteiras — `['nome']` |
| `title` | ✓ | Categorias |
| página única (`tabs: ''`, `crud: False`) | ✓ | Vitrine (`route: 'vitrine'`), Sobre (markdown), Contato (html custom) |
| `showcase` (§6.5) | ✓ | Vitrine — `fields`/`filter`/`layout`/`show`/`client_fields`/`badge_id`; carrinho `session['cart_items']` + identificação `session['client']` sem criar `Conta`; rotas `add`/`update`/`remove`/`api/cliente` geradas |
| `contacts` (§6.5) | ✓ | Contato — `props` `{título: {type: 'whatsapp'/'email'/'instagram'/'facebook'/'linkedin'/'phone', value}}`; template nativo do motor (`pages/contacts.html`) com ícones e máscara de telefone; sem `template` no módulo |
| `template.type` `markdown` | ✓ | Sobre (markdown, loader do host) |

> **Evolução do contrato `Page`:** a estrutura `tabs` (acima) foi substituída
> pelo formato `type` + `props` (`app/ajsystem/defs/page.py`): `Page['type']`
> define o roteiro (`'crud'`, `'showcase'`, `'cart'`, `'contacts'`, `'redirect'`,
> `'custom'`) e `Page['props']` carrega a config específica do tipo (`tabs`,
> `list`, `form`, `reports` para `crud`; `on_send` para `cart`; etc.). O `Form`
> de módulo migrou para `Page['props']['form']` (funções `_pre_save`/`_post_save`
> reordenadas antes do `Page`). O orquestrador `core/do_page.py` roteia por
> `type` e dispara `Page['events']` (`on_send`, `on_show`).

### Form — configuração do formulário (§7)

| Propriedade | Estado | Onde validada |
|---|---|---|
| `buttons` | ✓ | Categorias — `on_off`; Orçamentos — botão `Enviar` (`action` callable, `when: lambda i: i.pedido_id is None and i.status < 7`, `position: 'nav_right'`), `Converter` (`action`, `when: lambda i: i.pedido_id is None and i.status < 7`) e `Rejeitar` (`action`, `color: 'error'`, `position: 'footer_left'`, `when: lambda i: i.status < 7`); list — botão `Validar` (`action` callable, `color: 'info'`) |
| `delete` | ✓ | Categorias — set `{Product}` + `msg_ok`/`msg_no` (dict); Carteiras — quando multi-model `{Compra, Order, Quote, Previsao}`; Insumos — set `{ProductIngredient, ProducaoInsumo, CompraItem, UnitConversion}`; Orçamentos — callable `lambda q: q.pedido_id is None` |
| `fields` | ✓ | Categorias — `'Category'`; Insumos — `'Ingredient'`; Orçamentos — lista explícita `['cliente_nome', 'cliente_telefone', 'validade', 'forminhas', 'carteira_id', 'observacao']` |
| `form_tail` | ✗ | Removida — sem consumidores ativos |
| `page_scripts` | ✗ | Removida — usada por Transacao; Pedidos migrado (child-table + on_set genéricos) |
| `body_template` | ✗ | Removida — substituída por campos declarativos na Entity + sessões; Pedidos migrado |
| `nav_right_extra` | ✗ | Removida — substituída por `buttons` com `position: nav_right`; Pedidos migrado |
| `footer_left` | ✗ | Removida — substituída por `buttons` com `position: footer_left`; Pedidos migrado |
| `post_save` | ✓ | Categorias — reordenação |
| `pre_get` | ✓ | Carteiras — `em_uso`/`ro_fields` no editar: quando em uso, só `nome` fica readonly com hint |
| `pre_save` | ✓ | Categorias — auto-ordenação `ordem`; Carteiras — guarda de `nome` quando em uso (com `no_autoflush`); Orçamentos — status 0→1 (Pendente→Negociação na 1a edição admin) |
| `readonly` | ✓ | Form/readonly unificado (`False`/`True`/callable) — substitui `readonly_when` |
| `sessions` | ✓ | Insumos — `Conversões` e `Produtos` (dict puro com `table.columns`); Orçamentos — `Itens do Orçamento` e `Evento` |
| `tags` | ✓ | Orçamentos — `[{'field': 'status', 'colors': {9: 'success', 7: 'error', ...}}]` (badges no nav bar, cores inferidas ou por `colors`) |

### Report — configuração de relatórios PDF (§7.7)

Declaração **dict puro** (`ORCAMENTO_REPORT = {...}` em `app/reports/`);
motor resolve via `parse_report()`. **Sem rotas**: a action do botão chama
`print_report(DICT, instance)` e o motor gera o PDF na hora, embutindo-o
no iframe como data URI.

**Fields/columns na pegada List/Form** — dois formatos, resolução automática
da Entity do módulo corrente (via blueprint da request, mesmo `_resolve_cols`
do List/Form):
- **lista** (enxuta): strs puros + dicts para calculados/overrides;
- **mapa** `nome: extras`: quando qualquer campo precisa de extras.

Da Entity vêm **label + apresentação inferida do type** (`NUM`/currency →
`brl` right, `DATA` → `datetime` right, `INT` → center), **FK**
(`product_id` → valor via `product.nome`) e **`calc`** (vira
`function(row)` no PDF). Extras sobrepõem; chave ausente/ambígua passa
direto se trouxer `label`/`function` (senão: erro claro). `width` é sempre
em **ch** — o motor converte para mm pela métrica da fonte.

| Propriedade | Estado | Onde validada |
|---|---|---|
| `label` | ✓ | Título fallback do PDF (`pdf.py`); gravado como `/Title` do PDF (nome exibido pelo viewer) |
| `header.fields` / `table.columns` | ✓ | Dois formatos: **lista enxuta** (strs + dicts calculados) e **mapa** `nome: extras` — resolução automática pela Entity do módulo (via blueprint da request, mesmo `_resolve_cols` de List/Form) |
| inferência type → apresentação | ✓ | `NUM`/currency → `brl` right · `DATA` → `datetime` right · `INT` → center (override explícito vence) |
| FK na Entity | ✓ | `product_id` → label `'Produto'` + valor via `product.nome` (convenção `<base>.nome`) |
| BOOL / LIST na Entity | ✓ | BOOL → `Sim`/`Não` · LIST → label das options (`tipo` → `TIPO_OPERACAO`) |
| auto-label | ✓ | Campo sem `label` na Entity → `_auto_label` (mesmo fallback de List/Form) |
| `groups` (lista/mapa por campo) | ✓ | `'groups': [{'indice': {'left': 2, 'pos': 1, 'skip': True, 'fields': 'nome', 'transform': 'upper', 'bold': False}}]` — agrupa por mudança de valor; lista permite N níveis do mesmo campo; defaults `pos=1` (**0** oculto · **1** linha · **2** titulo), `total=True`, `line=True`, `eject=False`, `bold=True`; opção `left: n` agrupa pelos primeiros **n segmentos** do código; **`text`**: template do título — `{campo}` = valor da linha (LIST→label), `{<field do grupo>}` = código, demais caracteres literais; `fields` (str/list) acrescenta descrição ao título; `transform` ('upper'/'title'/'lower') aplica efeito; `skip=True` consome a linha-âncora (não repete nas colunas); subtotal quando houver col `agg` |
| `calc` na Entity | ✓ | callable usado direto (`quote_validade`); string vira `function(row)` (`_calc_fn`, avaliação restrita) |
| `width` em ch | ✓ | Sempre caracteres; motor converte para mm pela métrica da fonte (`_calc_col_widths`), bloco centrado; parciais dividem o restante |
| chave fora da Entity | ✓ | Passthrough se extras trouxerem `label`/`function`; senão erro claro (guard de typo) |
| `print_fragment_template` | ✓ | Default `'components/print_fragment.html'` (fragmento sem page_layout, injeção via `injectHTML`) |
| `print_erro` (interno) | ✓ | `components/print_erro.html` — falha de impressão exibe `msg` (default `'Erro na impressão do Relatório'`) |
| `logo_path` | ✓ | Default `'static/icons/Logo.png'`; resolvido em runtime por `do_report._resolve_logo()` |
| `print_template` | ✓ | Default `'components/print_default.html'` (página standalone imprimível, p/ rota custom) |
| `before_table` / `after_table` | ✓ | Orçamentos — `_event_after`/`_forminhas_carteira`; Compras — `_report_before`/`_report_after`; Pedidos — `_event_after`/`_forminhas_carteira` |
| `data_attr` | ✓ | Default `'items'`; `print_report(REPORT, instance)` extrai `instance.<data_attr>` quando `data` omitido |

**Botão com pre-controle (action + render):**

```python
# app/routes/sys/orcamentos.py — só o registro; data sai de instance.<data_attr>:
def _btn_enviar_action(instance):
    if not instance.items:
        return ''                                  # não injeta nada
    return print_report(ORCAMENTO_REPORT, instance)

{'label': 'Enviar', 'icon': 'paper-airplane', 'color': 'success',
 'action': _btn_enviar_action, 'render': '#page-content'}

# app/reports/orcamentos.py — header 100% Entity (calc callable ou expressão):
'header': {'fields': [
    'cliente_nome',        # label/texto esquerda
    'data_pedido',         # DATA → right/datetime
    'cliente_telefone',
    'validade_data',       # calc da Entity → label 'Válido até'
]},
'table': {'columns': {
    'product_id':     {'width': 44},               # FK → 'Produto'; product.nome
    'quantidade':     {'width': 8},                # INT → center; label 'Qtd'
    'preco_unitario': {'width': 14},               # NUM brl → right/brl
    'valor':          {'width': 14, 'agg': 'sum'}, # calc da Entity vira function
]},

# app/reports/operacoes.py — grupos por mudança de valor (após header):
PLANO = {
    'label': 'Plano de Contas',
    'header': {...},
    'groups': [
        {'indice': {'left': 1, 'pos': 2,
                    'text': '{indice}. {tipo}'}},   # título: '1. Receitas'
        {'indice': {'left': 2, 'pos': 1, 'skip': True,
                    'text': '{indice} {nome}',
                    'transform': 'upper', 'bold': False}},
    ],
    'table': {'columns': {
        'indice': {'width': 10}, 'id': {'width': 6}, 'nome': {},
        'fator': {'width': 10}, 'ativa': {'width': 8},
    }},
}

# app/routes/sys/operacoes.py — action pura; fonte inferida das colunas:
{'label': 'Plano', 'icon': 'printer', 'color': 'info',
 'action': lambda _: print_report(PLANO), 'render': '#page-content'}

# app/routes/sys/operacoes.py — Entity amarra o cálculo hierárquico:
# Field.code → código hierárquico em uma passada (core/hier.py::codigos):
'indice': {'label': 'Índice', 'code': {'mask': '9.99.99',
                                       'prefix_fields': ['tipo'],
                                       'scope_fields': ['tipo']}},
'indice': {..., 'calc': _indice_calc},
```

Contrato: `action` retorna **HTML** — fragmento do relatório ou conteúdo
alternativo; string vazia/None → container intacto (`injectHTML` guarda).

**Removidas / Desaprovadas (convenção sobre configuração):**
- ~~`edit_endpoint`~~ / ~~`pdf_endpoint`~~ / ~~`endpoint`~~ / rotas `/pdf`,`/print`
  auto-geradas — PDF embutido via data URI, nenhuma rota envolvida
- ~~`mod.REPORT`~~ / mapa de registros / scan do pacote (`report_loader`,
  `REPORTS_PACKAGE`) — resolução vem do blueprint da request
- ~~chave `'print'` no botão~~ — substituída por `action` explícita (pre-controle)
- ~~`redirect_fn`~~ — pre-controle vive na `action` do botão; caso especial de
  rota: `@auto.rota` com mesmo endpoint vence a gerada
- ~~`data_fn`~~ — dados vêm da instância (`data_attr`) ou explícitos na action
- ~~`fallback_url`~~ — erro exibe view interna `print_erro.html` com `msg`;
  Voltar usa `reload()`/`history.back()`

### Module — triggers de UI (§3.3)

| Propriedade | Estado | Onde validada |
|---|---|---|
| `triggers.<ev>.target` | ✓ | `'logo'` — elemento `.brand-logo`; suportado qualquer seletor | 
| `triggers.<ev>.action` | ✓ | `system` (popup login sistema), `admin` (popup admin), `qr` (QR mobile); SITE/SYS/ADMIN no `app/config.py` |
| `triggers.click` | ✓ | 1 clique — SITE→`system`, SYS→`qr`, ADMIN→`system` |
| `triggers.click_dbl` | ✓ | 2 cliques — SITE→`admin`, SYS→`admin` |
| gerado por `auth_triggers.html` | ✓ | Lê `modulo.triggers`, gera handlers/popups condicionais; `auth_logo_modo` removido |

### Layout — header/footer por módulo (§3.4)

| Propriedade | Estado | Onde validada |
|---|---|---|
| `layout.header.logo.rows` | ✓ | Altura do logo em `em` (linhas ≈ altura do caractere) — SITE/SYS `4`; `height:<rows>em` + mobile via `--logo-rows` |
| `layout.header.logo.align` | ✓ | `center` (padrão) — centralização do logo no container |
| `layout.header.title.text` | ✓ | Texto literal (SITE — "O doce sabor do seu evento!"); valor especial `'app_title'` → resolve para `APP.title` (SYS) |
| `layout.header.title.text: None` | ✓ | Não exibe título (campo omitido/None) |
| `layout.header.title.align` | ✓ | `center` (padrão) — alinhamento do título |
| `layout.header.title.font` | ✓ | Nome de fonte (Google Fonts, carregada no `head` via link condicional); `None`/omitido → system default |
| `layout.header.title.color` | ✓ | Cor do texto (ex.: `'var(--rosa)'`); `None`/omitido → herda do tema |
| `layout.footer.font` | ✓ | Fonte do rodapé (Google Fonts); `None`/omitido → system default |
| `layout.footer.color` | ✓ | Cor do rodapé; `None`/omitido → `--bar-txt-rodape` |
| `layout.footer.user` | ✓ | `True` mostra usuário no rodapé (SYS — `DOCEIRA`); `False` oculta (SITE) |

### APP — propriedades (§3.2)

| Propriedade | Estado | Onde validada |
|---|---|---|
| `APP.title` | ✓ | Título do app (ex.: "Sistema Gerenciador de Doceria"); referenciado por `title.text: 'app_title'` |

### Motor / CSS — contratos de renderização

| Propriedade | Estado | Onde validada |
|---|---|---|
| CSS inline via `{% include %}` | ✓ | `page_layout.html` inclui `components/motor_style.css` como `<style>` — sem `<link>` para `app/static/css/style.css`. Motor é única fonte |
| `#page-content` como container de largura | ✓ | `max-width: 100%` (mobile), `calc(100vw - 4rem)` (desktop ≥992px), `margin-inline: auto` — controla largura de todas as páginas |
| `.page-list-inner` deprecated | ✗ | Removida — largura controlada por `#page-content` |
| `#page-content` min-height | ✓ | `200px` — garante área mínima de conteúdo |
| `fitListColumns()` greedy (todas viewports) | ✓ | Mede `.overflow-auto` parent; colunas que não cabem vão para detail card — funciona desktop E mobile |
| `.container` max-width | ✓ | Breakpoints: 540px/720px/960px/1140px — override de DaisyUI |

---

## Índice

1. [Visão geral do framework](#1-visão-geral-do-framework)
2. [Criando um novo app do zero](#2-criando-um-novo-app-do-zero)
3. [Definições do App — APP, modules e Temas](#3-definições-do-app)
4. [Módulos (rotas declarativas)](#4-módulos-rotas-declarativas)
5. [Entity — definição de campos](#5-entity--definição-de-campos)
6. [List — configuração](#6-list--configuração)
7. [Form — configuração](#7-form--configuração)
8. [Exemplo completo do zero](#8-exemplo-completo-do-zero)

---

## 1. Visão geral do framework

### 1.1 O que ele faz

A partir de três dicionários declarativos por módulo:

| Declaração | Para que serve |
|---|---|
| `Entity` | Define os **campos** (nome, tipo, máscara, referências, validação) |
| `Page` | Define a **página** com abas; a aba `Dados` (type `List`) carrega a configuração da **listagem** |
| `Form` | Define o **formulário** (campos, tabelas filhas, exclusão, hooks, botões) |

O framework cuida de todo o resto:

- Rotas de listagem, criação, edição, exclusão e *toggle* (ativa/desativa);
- Formulários com validação, máscaras, upload de imagens e campos de referência (FK);
- Autenticação (login, logout, "lembrar-me") e proteção `login_required` em todas as rotas CRUD;
- Menu dinâmico (site público, sistema e admin) com submenus e ícones;
- Templates prontos (Tailwind + DaisyUI + Heroicons) para página, lista e formulário;
- **Temas** de cores centralizados em um único dicionário;
- Filtros Jinja e globals utilitários (`fmtdate`, `brl`, `mask`, `deep_attr`, `CONECTORES`, `aj_uploads_endpoint`, ...).

### 1.2 O que você precisa fornecer (o "contrato")

O framework não conhece sua aplicação. Ele recebe tudo através de um **adaptador**
(`adapter.py`) e da declaração `APP` (com `modules`). Você deve entregar:

1. **O app Flask** criado (`create_app`) — o framework apenas faz `init_app(app)`.
2. **Um adaptador** `adapter.py` expondo `db`, `login_manager`, `User`, `Setting`, `APP` e o endpoint de uploads.
3. **Models SQLAlchemy** em `app/models/` (um por entidade).
4. **Módulos declarativos** em `app/routes/sys/` (Entity + List + Form).
5. **`app/config.py`** com `Temas` e `APP` (incluindo `modules`).

### 1.3 Estrutura de pastas do framework

O framework é a pasta `app/ajsystem/`:

```
 ajsystem/
 ├── __init__.py           # exports (init_app; blueprint ajsystem; filtro heroicon)
 ├── init.py               # init_app(app): wiring de tudo
 ├── core/                 # motor/runtime do framework
 │   ├── adapter.py         # ADAPTADOR — único ponto de acoplamento com o app
 │   ├── auto.py           # auto.rota, montar_blueprint, registrar_modulos
 │   ├── menu.py           # url_do_item: resolve menus → endpoints
 │   ├── utils.py          # helpers (item_ref, deep_get, ...)
 │   ├── filters.py        # comportamento de filtros (resolve/apply_*)
 │   ├── form.py           # Form; sessions; hooks; handle_form
 │   ├── list.py           # listagem/colunas; usa defs.entities
  │   ├── query.py          # consultas (Query): agregação/ordenação/grupos
 │   └── edits.py          # assets de editores (rich text)
 ├── defs/                 # definições declarativas (sem lógica de request)
 │   ├── constants.py      # CONECTORES (conectivos de títulos)
  │   ├── fields.py         # dataclass Field; FIELD_TYPES; VALIDATORS; fmt_mask
  │   ├── query.py          # dataclass Query (referência); _resolve_query
  │   ├── buttons.py        # Button/ConfirmModal; presets BTN_*
  │   ├── filters.py        # constantes FILTER_*/MODE_*
  │   ├── report.py         # config de relatórios PDF (Report/ReportColumn)
   │   └── entities.py       # Entity; build_field_config; register_model; MODEL_MAP
 ├── handles/              # ações de request (handlers)
 │   ├── render_list.py    # render_list + resolvers de colunas/ordenação
 │   └── auth.py           # init_auth + blueprints auth e seguranca (login/logout/chave)
 ├── templates/
 │   ├── pages/            # sys.html, list.html, form.html, construcao.html, ...
 │   └── components/       # page_layout.html, form_macros.html, item_table.html, ...
 ```

 O bloco `defs/` contém as definições declarativas (estrutura de entidades,
 tipos, filtros e botões); `handles/` concentra os pontos de entrada de request
 (render_list, auth); `core/` reúne o motor/runtime. **Nenhum** deles deve ser
 importado diretamente pelo seu código de módulo — use apenas os exports de
 alto nível descritos aqui (em geral via `core`).

---

## 2. Criando um novo app do zero

### 2.1 Requisitos

- Python 3.10+
- PostgreSQL (o framework usa `psycopg2`)
- Node.js (apenas se você precisar rebuildar o CSS — ver §2.6)

Dependências mínimas (`requirements.txt`):

```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.0.5
Flask-WTF==1.2.1
WTForms==3.1.1
psycopg2-binary==2.9.9
python-dotenv==1.0.0
markdown==3.5.1
requests==2.31.0
Flask-Login
```

### 2.2 Estrutura de pastas do novo app

```
meu_app/
├── app/
│   ├── __init__.py          # create_app(): bootstrap + init_app(app)
│   ├── extensions.py        # db = SQLAlchemy(); login_manager; migrate
│   ├── config.py            # Config: SQLALCHEMY_DATABASE_URI, SECRET_KEY, ...
│   ├── ajsystem/            # o framework (esta pasta)
│   ├── adapter.py           # ADAPTADOR (dentro de ajsystem/ — edite)
│   ├── config.py            # Temas + APP (com modules)  ← comece aqui
│   ├── models/              # SQLAlchemy models (1 arquivo por entidade)
│   │   ├── __init__.py      # importa todos os models
│   │   ├── user.py          # User (obrigatório p/ autenticação)
│   │   ├── setting.py       # Setting (obrigatório p/ sessão/senha do painel)
│   │   ├── category.py
│   │   └── product.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── sys/             # módulos CRUD declarativos
│   │   │   ├── categorias.py
│   │   │   └── produtos.py
│   │   └── site/            # páginas públicas (opcional)
│   ├── templates/           # templates custom da app
│   │   └── sys/             # sessões/templates de módulos (ver §7.4)
│   ├── static/              # css, js, img (logo, favicon)
│   └── migrations/          # geradas pelo Flask-Migrate
├── dados/
│   ├── uploads/             # imagens enviadas (upload_path)
│   └── paginas/             # páginas markdown (render_pagina)
├── requirements.txt
├── .env                     # variáveis de ambiente
└── run.py                   # app = create_app(); app.run()
```

> **Ordem recomendada de implementação:** (1) `config.py` → (2) `models/` →
> (3) `app/routes/sys/` com os 3 dicionários → (4) `app/__init__.py` →
> (5) `adapter.py`. As seções 3 a 7 explicam cada passo em detalhe.

### 2.3 Bootstrap — `app/__init__.py`

```python
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config.from_object('app.config.Config')

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    from app.ajsystem import init_app as init_ajsystem
    init_ajsystem(app)

    from app import models  # noqa: garante registro dos models
    from app.ajsystem.core.list import register_model
    from app.models.user import User
    from app.models.category import Category
    register_model('user', User)
    register_model('category', Category)

    return app
```

`init_app(app)` (em `app/ajsystem/init.py`) faz todo o wiring: registra os
blueprints (`ajsystem`, `auth`, `seguranca`), configura o `login_manager` com o
loader a partir do seu `User`, injeta filtros/globals no Jinja, registra os
módulos a partir de `SYS['menus']` e configura os endpoints de upload.

> O `register_model` registra a chave usada nas referências (`'category'`).
> Se você **não** registrar, o framework tenta importar automaticamente
> `app.models.<chave>` (§4.6).

### 2.4 Adaptador — `adapter.py`

Este é o **único ponto de acoplamento** entre o framework e a sua app. O
framework importa tudo daqui, nunca diretamente de `app.models` etc.:

```python
from app.extensions import db, login_manager
from app.models.user import User
from app.models.setting import Setting
from app.config import APP, SYS, Temas   # que você define (seção 3)
from flask import url_for


def get_uploads_endpoint(app):
    """Endpoint usado para servir as imagens enviadas."""
    return app.config.get('AJ_UPLOADS_ENDPOINT') or 'uploads.uploaded_file'
```

O que o adaptador deve expor:

| Nome | Tipo | Para que serve |
|---|---|---|
| `db` | `SQLAlchemy` | queries feitas pelo motor |
| `login_manager` | `LoginManager` | autenticação |
| `User` | Model | login (deve ter `username`, `check_password`, `set_password`) |
| `Setting` | Model | armazenamento de `Setting.get('chave')` (painel, sessão) |
| `APP` | dict | definições do app (name, logo, version, tema, modules) |
| `get_uploads_endpoint(app)` | callable | endpoint das imagens |
| `set_tunnel_url_provider(fn)` | callable | registra o provedor da URL pública (QR de acesso) |

O `get_uploads_endpoint` retorna `'uploads.uploaded_file'` por padrão. Você pode
mudar para um endpoint seu (ex.: `'media.serve'`) ou usar a config
`AJ_UPLOADS_ENDPOINT`. Os templates usam o global `aj_uploads_endpoint()` para
montar as URLs das imagens.

O hook `set_tunnel_url_provider(fn)` recebe um callable que devolve a URL pública
do app (usada no QR de acesso pelo endpoint `GET /api/tunnel-url`). Se nenhum
provedor for registrado, o endpoint usa `request.host_url` como fallback.
Registre-o no bootstrap do seu app, ex.:

```python
from app.ajsystem.core import adapter
adapter.set_tunnel_url_provider(lambda: get_tunnel_url(force=True))
```

### 2.5 API genérica do framework (`/api/*`)

O framework expõe blueprints de API reutilizáveis em `app/ajsystem/core/do_api.py`
(`Blueprint api`, prefixo `/api`), já registrados pelo `init_app`:

| Endpoint | Métodos | Auth | Uso |
|---|---|---|---|
| `/api/consulta` | GET | login | consulta genérica: `?campo=product&valor=5&retorno=preco,qtd_minima` |
| `/api/on_set` | GET | login | executa o `on_set` da FK de uma Entity (`?ent=&fk=&valor=&mod=`) |
| `/api/transformar-texto` | POST | login | normalização em massa `lower`/`upper`/`title` de uma coluna |
| `/api/tunnel-url` | GET | público | URL pública do app para QR de acesso (via adapter) |

`consulta` resolve o modelo pelo nome no `MODEL_MAP` do framework (case-insensitive);
com um único campo de retorno devolve `{ok, valor}`, com vários devolve
`{ok, valores: {campo: valor}}` — é o que o helper `window.consulta(campo, valor,
retorno, cb)` de `app/static/js/itens.js` usa para auto-preenchimento de preços.

### 2.6 Variáveis de ambiente (`.env`)

```
SECRET_KEY=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_DB=...
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
ADMIN_PASSWORD=...            # senha padrão do usuário admin (primeiro login)
ADMIN_EMAIL=...
UPLOAD_PATH=dados/uploads     # pasta das imagens (upload_path)
```

> Variáveis de leitura adicional: `FLASK_APP=app`, `FLASK_DEBUG=1`.

### 2.7 Estáticos e CSS

Os templates usam **Tailwind CSS** e **DaisyUI**. Há dois caminhos:

**A. Com build (tema próprio)** — as cores vêm de `Temas` no `app/config.py`:
classes novas ou cores alteradas exigem rebuild:

```
npm install
npm run build:css          # prebuild:css roda core/do_themes.py automaticamente
```

**B. Sem build (CSS pré-compilado)** — o `app/ajsystem/static/` é a fonte
canônica dos estáticos prontos. Copie para o `app/static/` da sua app:

```bash
cp app/ajsystem/static/css/tailwind.css    app/static/css/tailwind.css     # tema padrão do framework
cp app/ajsystem/static/css/multi-ctl.css   app/static/css/multi-ctl.css
cp app/ajsystem/static/js/multi-ctl.js     app/static/js/multi-ctl.js
cp -r app/ajsystem/static/lib/             app/static/lib/                 # htmx, alpine, bootstrap-icons, qrcode
```

> **`style.css` do motor é inline** — o CSS genérico do framework (`motor_style.css`)
> é incluído via `{% include %}` no `page_layout.html`, tornando-se parte do
> HTML renderizado. Não precisa ser copiado para `app/static/`. O motor é a
> única fonte de verdade para este CSS.

O `tailwind.css` pré-compilado usa o **tema padrão do framework** (`ajsystem`),
neutro. Para um tema próprio, use o caminho A (rebuild gera
`app/static/css/tailwind.css` do próprio app). Para regenerar o CSS do framework:

```
npm run build:css:framework   # core/do_themes.py --framework → tailwind.css do framework
```

Os ícones (logo/favicon) são específicos de cada app e vêm do próprio
`app/static/icons/`. Os ícones de interface vêm de `components/heroicons.svg`
(sprite inline, ícones por nome — ex.: `trash`, `pencil-square`, `arrow-path`,
`paper-airplane`, `check`, `xmark`, ...).

---

## 3. Definições do App

Todo o app é descrito em `app/config.py`, começando pelos **temas** e depois
pelo dicionário `APP` (com a lista `modules`). A estrutura desses dicts é
tipada pelo framework em `defs/config.py` (`App`, `Module`, `MenuItem`, `Tema`)
e coage via `build_*` no adaptador (`core/adapter.py`); consumidores do
framework acessam por atributo (`APP.module('system').menus`, `TEMAS['algodoce'].base`).

### 3.1 Temas (tokens de cor)

`app/config.py` é a **fonte única de cores** do app:

```python
Temas = {
    'algodoce': {
        'base': 'algodoce',            # nome do tema DaisyUI compilado (data-theme)
        'rotulo': 'AlgoDoce',
        'marca': {                     # primary / secondary (CTAs, links, destaque)
            'primary': '#26A69A', 'primary-content': '#FFFFFF',
            'secondary': '#E91E63', 'secondary-content': '#FFFFFF',
        },
        'neutras': {                   # superfícies, bordas, textos
            'base-100': '#f5f5f5', 'base-200': '#e0e0e0', 'base-300': '#bdbdbd',
            'base-content': '#212121', 'neutral': '#37474F', 'neutral-content': '#FFFFFF',
        },
        'feedback': {                  # estado semântico (mensagens, botões, badges)
            'success': '#43A047', 'success-content': '#FFFFFF',
            'warning': '#FB8C00', 'warning-content': '#000000',
            'error': '#E53935', 'error-content': '#FFFFFF',
            'info': '#0288D1', 'info-content': '#FFFFFF',
        },
        'apoio': {                     # accent (destaque, sem erro/sucesso)
            'accent': '#FFB300', 'accent-content': '#000000',
        },
        'barras': {                    # chrome do app (runtime — vars --bar-*)
            'altura': 5,
            'menu':    {'fundo': '#e91e63', 'texto': '#FFFFFF'},
            'submenu': {'fundo': '#FFFFFF', 'texto': '#e91e63'},
            'form':    {'fundo': '#FFFFFF', 'texto': '#e91e63'},
            'rodape':  {'fundo': '#FFFFFF', 'texto': '#e91e63'},
        },
    },
}
```

| Grupo | Uso |
|---|---|
| `marca` | `primary`/`secondary` (+`-content`) — CTAs, links, botões principais |
| `neutras` | `base-100/200/300`, `base-content`, `neutral` — fundos, cards, bordas, textos |
| `feedback` | `success`/`warning`/`error`/`info` (+`-content`) — flash, botões, badges, hints |
| `apoio` | `accent` (+`-content`) — destaque |
| `barras` | Chrome do app (runtime): `menu`, `submenu`, `form`, `rodape` → vars `--bar-*` via `components/theme.html` |

**Como as cores chegam ao CSS** — duas vias:

- `marca`/`neutras`/`feedback`/`apoio` alimentam o **tema DaisyUI compilado**:
  `app/ajsystem/core/do_themes.py` (tooling do framework) lê `Temas` de
  `app/config.py` e gera `tailwind.daisyui.json` (consumido por
  `tailwind.config.js`). A compilação gera `app/static/css/tailwind.css`
  (`npm run build:css`). **Mudou uma cor? Altere em `app/config.py` e rode
  `npm run build:css`** — propaga para o app inteiro.
- `barras` é lido em runtime por `components/theme.html` e **propaga sem rebuild**.

> **Não edite `tailwind.daisyui.json` à mão** — ele é gerado (`npm run gen:theme`,
> executado automaticamente como `prebuild:css`/`prewatch:css`). A chave `APP.tema`
> (abaixo) seleciona qual tema de `Temas` está ativo (`data-theme`).

### 3.2 `APP` — as propriedades e o que pode ser inserido

O dicionário `APP` descreve a aplicação. **Cada propriedade** abaixo indica o que
pode ser inserido e a referência para a definição completa:

```python
APP = {
    'name': 'Algodocê',          # nome exibido no topo/menu
    'title': 'Sistema de ...',   # título do app (§3.4 — title.text: 'app_title')
    'logo': 'logo.png',          # arquivo em app/static/
    'version': '1.0.0',          # versão exibida no rodapé
    'tema': 'doceira',           # chave do dicionário Temas  →  §3.1
    'modules': [                 # módulos (áreas) do app     →  §3.3
        {'type': 'public', 'default_path': 'produtos', 'menus': {...}},
        {'type': 'system', 'default_path': 'cadastro/categorias', 'menus': {...}},
        {'type': 'admin',  'default_path': 'seguranca.painel',   'menus': {}},
    ],
}
```

| Propriedade | Tipo | O que pode ser inserido | Ver § |
|---|---|---|---|
| `name` | str | Nome do app exibido no cabeçalho e nos títulos | — |
| `title` | str | Título descritivo do app (ex.: `'Sistema Gerenciador de Doceria'`); usado no header quando `layout.header.title.text = 'app_title'` | [§3.4](#34-layout--header-e-footer-por-módulo) |
| `logo` | str | Nome do arquivo em `app/static/` (ex.: `'logo.png'`). Vazio para não exibir | — |
| `version` | str | Versão mostrada no rodapé (ex.: `'1.0.0'`). Se omitida, lê o arquivo `app/versao.py` (`YEAR`/`MONTH`/`SEQUENCE` → `'v1.YY.MM-SEQ'`) | — |
| `tema` | str | Chave do dicionário `Temas`; define todas as cores | [§3.1](#31-temas-tokens-de-cor) |
| `modules` | list | Módulos do app. Cada um tem `type` (único), `default_path` e `menus` | [§3.3](#33-menus-modules) |

> Cada módulo tem um `type` que o identifica (`'public'` por padrão) e deve ser
> único. O framework seleciona por tipo: `APP.module('system')` (área após
> login), `APP.module('public')` (visitante) e `APP.module('admin')`
> (painel de segurança). Tipos além de `public`/`system`/`admin` são permitidos.
> Se o tipo pedido não existir, `APP.module()` retorna o **primeiro módulo da
> lista** (módulo padrão); retorna `None` apenas se a lista estiver vazia.

### 3.3 Menus (modules)

A estrutura de cada módulo é um dict com `type`, `default_path` e `menus`:

```python
# dentro de APP['modules'] — ex.: módulo 'system'
{'type': 'system',
 'default_path': 'cadastro/categorias',   # destino após login (caminho de menu)
 'triggers': {                            # §3.4 — interações de UI
     'click':     {'target': 'logo', 'action': 'qr'},
     'click_dbl': {'target': 'logo', 'action': 'admin'},
 },
 'layout': {                              # §3.4 — header/footer
     'header': {
         'logo': {'rows': 6, 'align': 'center'},
         'title': {'text': 'app_title', 'align': 'center'},
     },
     'footer': {'user': True},
 },
 'menus': {
     'Categorias': {'icon': 'bi-journal'},        # sem submenu → módulo 'categorias'
     'Estoque': {'icon': 'bi-box', 'submenus': {  # com submenu
         'Insumos':   {'icon': 'bi-box-seam'},
         'Produtos':  {'icon': 'bi-gift'},
         'Operações': {'icon': 'bi-tags', 'page': 'opr'},  # rótulo ≠ arquivo
     }},
     'Sobre': {'url': 'site.sobre', 'icon': 'bi-info-circle'},   # endpoint nomeado
     'Manual': {'url': '/manual', 'icon': 'bi-book'},            # caminho literal
 },
}
```

Propriedades de um item de menu:

| Propriedade | Obrigatória | O que é |
|---|---|---|
| `label` | sim* | Rótulo exibido; usado para derivar o slug do módulo |
| `icon` | não | Nome do ícone Bootstrap (ex.: `'bi-tag'`, `'bi-box'`) |
| `submenus` | não | Dict de itens-filhos com `label`/`icon`/`page`/`url` |
| `page` | não | Arquivo do módulo quando o rótulo ≠ arquivo (ex.: menu `'Operações'` → `app.routes.sys.opr`). Ainda monta o módulo |
| `url` | não | **Escape de navegação** (não monta módulo): endpoint nomeado (`'orcamentos.list'`) ou caminho literal (`'/manual'`, `'https://...'`) |

> **Regra de ouro:** itens sem `url` viram módulos. O **slug** (derivado do
> `page` — ou do `label`, normalizado sem acentos) define o módulo Python em
> `app.routes.sys.<slug>` — veja §4.4. Por isso itens com `submenus` ou sem
> `page` precisam de `label`. Use `url` apenas para endpoints registrados fora
> do menu (blueprints com `bp` próprio, páginas custom) ou caminhos literais —
> nunca para um módulo automático sem `bp`, pois ele não seria montado.

### 3.4 Layout e triggers — header/footer e interações por módulo

Além de `type`, `default_path` e `menus`, um módulo pode declarar **`layout`**
(header/footer) e **`triggers`** (interações de UI). Ambas são opcionais — sem
elas o módulo usa os padrões do motor.

#### `layout` — header e footer

```python
'layout': {
    'header': {
        'logo':  {'rows': 3.5, 'align': 'center'},
        'title': {'text': 'O doce sabor do seu evento!',
                  'align': 'center',
                  'font': 'Poppins',
                  'color': 'var(--rosa)'},
    },
    'footer': {'font': None, 'color': None, 'user': False},
}
```

O **header é um container dinâmico**: a altura acompanha o conteúdo — apenas o
logo, ou logo + título empilhados. O `<img>` do logo usa `height: <rows>em`
(linhas ≈ altura do caractere); no mobile escala via variável CSS `--logo-rows`.

| Propriedade | Tipo | Padrão | O que configura |
|---|---|---|---|
| `header.logo.rows` | float | `5` | Altura do logo em `em` (≈ número de linhas de texto) |
| `header.logo.align` | str | `'center'` | Alinhamento horizontal do logo |
| `header.title.text` | str/`None` | `None` | Texto do título. `None`/omitido → não exibe. `'app_title'` (constante `TEXTO_APP`) → resolve para `APP.title` |
| `header.title.align` | str | `'center'` | Alinhamento do título |
| `header.title.font` | str/`None` | `None` | Nome da fonte (Google Fonts; carregada condicionalmente no `head`). `None` → font do tema |
| `header.title.color` | str/`None` | `None` | Cor do texto (CSS color). `None` → herda do tema |
| `footer.font` | str/`None` | `None` | Fonte do rodapé (Google Fonts) |
| `footer.color` | str/`None` | `None` | Cor do texto do rodapé (sobrepõe `--bar-txt-rodape`) |
| `footer.user` | bool | `True` | Exibe o usuário logado no rodapé (`versao | <usuario>`) |

> `font: None` e `color: None` não precisam ser declarados — os defaults já são
> `None`. Fonte em `header`/`footer` que não seja `None` dispara o `<link>` ao
> Google Fonts no `page_layout.html`.

#### `triggers` — interações de UI

```python
'triggers': {
    'click':     {'target': 'logo', 'action': 'system'},
    'click_dbl': {'target': 'logo', 'action': 'admin'},
}
```

O motor (`components/auth_triggers.html`) lê `modulo.triggers` e gera os
handlers no elemento `target`. Substituiu o antigo `auth_logo.html`/`auth_logo_modo`.

| Propriedade | Tipo | O que configura |
|---|---|---|
| `triggers.click.target` | str | Seletor do elemento (ex.: `'logo'` → `.brand-logo`) |
| `triggers.click.action` | str | Ação de 1 clique: `'system'` (login sistema), `'admin'` (login admin), `'qr'` (QR mobile) |
| `triggers.click_dbl.target` | str | Seletor do elemento (duplo clique) |
| `triggers.click_dbl.action` | str | Ação de 2 cliques (mesmos valores de `click.action`) |

> Módulos da aplicação: `SITE` usa `click→system` / `click_dbl→admin`;
> `SYS` usa `click→qr` / `click_dbl→admin`; `ADMIN` usa `click→system`.

---

## 4. Módulos (rotas declarativas)

### 4.1 O que é um módulo

Um módulo é um arquivo Python em `app/routes/sys/` que declara os dicionários
`Entity`, `Page` (com a listagem aninhada) e (opcionalmente) `Form`:

```python
# app/routes/sys/categorias.py
Entity = {
    'Category': {
        'id':    {'type': 'ID'},
        'nome':  {'type': 'TEXT'},
        'ativo': {'type': 'BOOL'},
    },
}

Page = {
    'tabs': {
        'Dados': {
            'type': 'List',
            'fields': ['Category'],
            'ordering': ['nome'],
        },
        'Filtros': {'type': 'Filter'},
    },
}

Form = {
    'fields': 'Category',
    'buttons': ['on_off'],
}
```

Sem `bp = Blueprint(...)` o framework **monta o blueprint automaticamente** e
cria, protegidas por `login_required`:

| Rota | Endpoint | Método | Quando |
|---|---|---|---|
| `/<slug>/` | `<slug>.list` | GET | sempre |
| `/<slug>/novo` e `/<slug>/<id>/editar` | `<slug>.form` | GET/POST | sempre |
| `/<slug>/<id>/excluir` | `<slug>.delete` | POST | se `Form['delete']` (≠ `False`) |
| `/<slug>/<id>/toggle` | `<slug>.toggle` | GET | se houver botão `on_off` em `Form['buttons']` |

### 4.2 Modo declarativo vs modo legado

| Modo | Como | Quando usar |
|---|---|---|
| Declarativo | Apenas `Entity`/`List`/`Form` (+ `@auto.rota` para rotas extras) | módulos novos — recomendado |
| Legado | Definir `bp = Blueprint('x', __name__)` e rotas próprias | integrar módulos existentes; o menu continua apontando para `x.list` |

Se você definir `bp`, o framework **respeita o blueprint e não sobrescreve** as
suas rotas.

### 4.3 As três declarações

- **`Entity`** — mapa `nome_da_entidade → campos`. Cada campo é um dict de
  propriedades ([§5](#5-entity--definição-de-campos)). Pode ter **várias
  entidades** no mesmo módulo (ex.: `Product` e `ProductIngredient`).
- **`Page`** — dict com `tabs`: cada aba tem `type`, `max_width` opcional e, na
  aba `Dados` (`type: 'List'`), a configuração da listagem (`fields`,
  `ordering`, `title`, ... — [§6](#6-list--configuração)).
- **`Form`** — dict com `fields`, `sessions`, `delete`, `buttons` e hooks
  ([§7](#7-form--configuração)). Também pode ser `Form(...)` da dataclass
  (`app.ajsystem.core.form`); `handle_form` aceita ambos.

> Forma **legada**: módulos antigos declaram `List = {...}` no topo (sem `Page`).
> O framework monta o default `Dados(List) + Filtros(Filter)` automaticamente,
> preservando o comportamento — os módulos do projeto já foram migrados para
> `Page`.

### 4.4 Registro do módulo (menu → blueprint)

O framework percorre `SYS['menus']` (via `registrar_modulos(app, menus)`) e, para
cada item sem `url`:

1. Deriva o slug (do `page`, ou do `label` normalizado);
2. Importa o módulo `app.routes.sys.<slug>`;
3. Se o módulo **não** tem `bp`, monta o blueprint declarativo e o registra com
   `url_prefix = '/' + slug`.

> O menu e o blueprint usam o mesmo slug, então a ordem das seções **3.3 → 4.4**
> é consistente: `label`/`page` no menu, `Entity`/`List`/`Form` no módulo.

### 4.5 Rotas custom — `@auto.rota`

```python
from app.ajsystem.core.auto import auto
from flask import jsonify

@auto.rota("/search")
def search():
    q = request.args.get("q", "").strip()
    items = Product.query.filter(Product.nome.ilike(f"%{q}%")).limit(10).all()
    return jsonify([{"id": p.id, "nome": p.nome} for p in items])
```

O decorator registra a rota no blueprint **do módulo atual** (detectado pelo
arquivo). O `endpoint` padrão é o nome da função.

> Você pode **substituir uma rota gerada** declarando-a com o mesmo endpoint —
> ex.: `@auto.rota('/<int:id>/excluir', methods=['POST'], endpoint='delete')`
> implementa a exclusão manualmente (a rota gerada é ignorada).

### 4.6 Modelos e `MODEL_MAP`

O framework resolve a model de uma entidade em duas etapas:

1. **`MODEL_MAP`** — registro explícito via `register_model('category', Category)`
   em `app/__init__.py` (recomendado);
2. **Fallback** — importa `app.models.<chave>` e busca a classe com o nome da
   entidade.

> Use `register_model` para evitar import dinâmico (mais rápido e sem erro de
> circular import).

---

## 5. Entity — definição de campos

### 5.1 Tipos de campo (`FIELD_TYPES`)

Cada campo é `{'type': '<TIPO>', ...}` — **sempre em maiúsculas**. Tipos
disponíveis (`app/ajsystem/defs/fields.py`):

| Tipo | input | Props base aplicadas |
|---|---|---|
| `TEXT` | `text` | — |
| `MEMO` | `textarea` | `rows` p/ altura |
| `INT` | `number` | `align: right`, `width: 5`, `decimals: 0` |
| `NUM` | `number` | `align: right`, `width: 10`, `decimals: 2` |
| `PERCENT` | `number` | Percentual 0–100, `decimals: 1`, `min: 0`, `max: 100`; exibe com `%` (ex.: `12,5%`) |
| `ID` | `number` | PK da tabela; `in_form: 0`, `label: '#'`, `in_filter: 0` |
| `DK` | `number` | Ligação filho→pai (sessão); `in_form: 0`, `in_filter: 0`, preenchido pelo motor |
| `DATA` | `date` | filtro por data (`in_filter` 1) |
| `DATA_HORA` | `datetime-local` | filtro por data (`in_filter` 1) |
| `HORA` | `time` | — |
| `BOOL` | `boolean` | filtro Sim/Não (`in_filter` 2) |
| `FONE` | `text` | `mask: '(99) 99999-9999'`, `digits_only: True` |
| `CPF` | `text` | `mask: '999.999.999-99'`, `digits_only`, `validate: 'cpf'` |
| `CNPJ` | `text` | `mask: '99.999.999/9999-99'`, `digits_only`, `validate: 'cnpj'` |
| `FK` | `select` | filtro select (`in_filter` 2); referência a outra entidade — `masterkey` opcional, veja §5.2. **Nunca duplicar** (par display+data): um campo `*_id` serve para ambos |
| `LIST` | `select` | filtro select (`in_filter` 2) ou checklist (`in_filter` 3); opções fixas via `list`/`options` |
| `MULT10` | `multi` | Opções fixas via `list`/`options` (máx. 10, códigos 0-9); editor genérico em modal; persiste códigos concatenados |
| `IMAGE` | `image` | `in_filter: 0`, widget de preview/upload |

> As props base do tipo são **mescladas** com as da entidade e do form — você
> pode sobrescrever/estender qualquer uma (ex.: `{'type': 'BOOL', 'in_form': 0}`).
> `required` é sempre **opt-in** (`'required': True`), nunca herdado do tipo.
> No formulário, a referência de um campo `*_id` pode ser **derivada da relação**
> do model (em vez de `masterkey`) — veja §5.4.

### 5.2 Referência de propriedades de campo

| Propriedade | Tipo | Uso |
|---|---|---|
| `type` | str | O tipo, da tabela §5.1, em maiúsculas. **Obrigatória** |
| `label` | str | Rótulo exibido (auto-derivado do nome se ausente) |
| `width` | int | Largura em caracteres (colunas/listagem) |
| `align` | str | `'left'` (padrão) \| `'right'` \| `'center'` (células da lista; inputs numéricos já alinham à direita por padrão) |
| `input` | str | Sobrescreve o widget (`text`, `textarea`, `number`, `date`, `boolean`, `select`, `image`, ...) |
| `required` | bool | Obrigatório (validação de presença) |
| `help` | str/dict | Ajuda do campo: `str` → texto no modal (quebras com `\n`); `dict` `{entrada: descrição}` → tabela "Entrada \| Descrição" no modal. Aparece um botão-ícone ao lado do label que abre o modal (Carteiras — `prazo_recebimento` com formatos de prazo) |
| `in_form` | int | Gate do form: `0` não exibe nem submete; `1` edita (padrão); `2` exibe apenas o valor (sem input, não submete — ex.: datas exibidas antes da validade); `3` exibe apenas **se houver valor** (vazio omite o campo — ex.: `data_renovacao`). `True`→`1`, `False`→`0` |
| `in_list` | int | `0` exclui o campo da listagem, do card e do filtro; `1` coluna na linha (vai p/ o card quando não couber); `2` sempre no card; padrão `1`. `True`→`1`, `False`→`0` |
| `readonly` | bool | Exibe o valor como texto estático no form (sem edição); o valor é submetido via `<input type="hidden">` (preserva valores preenchidos por `on_set`). Equivalente a `in_form: 2` — porém com submit via hidden |
| `hidden` | bool | Invisível no form; submete o valor via `<input type="hidden">` (controle interno) |
| `default` | any | Valor inicial de novos registros |
| `attrs` | dict | Atributos HTML do input (ex.: `{'min': 0, 'step': 1}`) |
| `mask` | str | Máscara de formatação (ex.: `'999.999'`) |
| `digits_only` | bool | Remove não-dígitos antes de aplicar a máscara |
| `decimals` | int | Casas decimais (gera máscara se `mask` ausente) |
| `currency` | bool | Formata como moeda (`brl`) |
| `percent` | bool | Formata como percentual (`percent` — ex.: `12,5%`); setado pelo tipo `PERCENT` |
| `derived` | dict | Campo **virtual** (sem coluna no banco): `{'sum': '<caminho>'}` soma as folhas do caminho, atravessando coleções (ex.: `'items.quantidade'`). Calculado na renderização (células, colunas e agregados) |
| `hide_zero` | bool | Ocultar valores zero na listagem (padrão `True`) |
| `masterkey` | str | **FK/DK (opcional)**: chave do `MODEL_MAP` que identifica o field do relacionamento na tabela-mestra (ex.: `'quote'` em `quote_id`) — popula `query` = `Query(model=<chave>)`. Sem ele, a referência é derivada da relação do model (§5.4). Em campos `DK` o padrão é a **primeira tabela da `Entity`** |

> **Regra FK: um campo só, nunca par.** Um campo `*_id` com `type: 'FK'` serve
> tanto para exibição na lista quanto para dados. Use `masterkey` (sem `when`)
> ou `query` dict (com `when`) — nunca crie dois campos para a mesma FK.
> O motor deriva `card_path` automaticamente via `_rel_name_for_field()`.
>
> ```python
> # ✓ CORRETO — campo único
> 'transacao_id': {'type': 'FK', 'label': 'Faturado', 'width': 10,
>                  'masterkey': 'transacao', 'in_filter': 0, 'in_form': 0}
>
> # ✓ CORRETO — com query.when (filtra opções do form/select)
> 'client_id': {'type': 'FK', 'label': 'Cliente', 'width': 20,
>               'query': {'model': 'conta', 'when': 'ativo = true'}, 'required': True}
>
> # ✗ ERRADO — par desnecessário
> 'transacao':    {'type': 'FK', 'label': 'Faturado', ...},  # display duplicado
> 'transacao_id': {'type': 'FK', 'query': {'model': 'transacao'}, ...}
> ```

| `list` | dict | **LIST/MULT10**: opções fixas `{valor: rótulo}` (alias de `options`) |
| `options` | dict | Opções do select (estáticas, ou preenchidas pelo motor via `query`) |
| `query` | str/dict/Query | Referência de consulta: `str` = chave do `MODEL_MAP` (default `display='nome'`), `dict`/`Query` = `model`, `field`, `columns`, `display`, `return_field`, `when`, `order` (§5.4) |
| `in_filter` | int | Filtro de lista: `0` oculta; `1` input; `2` select (1 opção); `3` checklist (1+ opções); `None` = inferido do `input`/`options`/`query` (text/number/date→1, select/boolean→2) |
| `validate` | str/callable | `'cpf'`/`'cnpj'` ou função `(valor) -> bool` |
| `transform` | str/callable | Transformação ao salvar: `'title'` (padrão em textos editáveis), `'cap'` (só o 1º caractere maiúsculo), `'upper'`, `'lower'`, `'none'` ou callable `(val, field)` |
| `rows` | int | Altura do textarea (MEMO) |
| `upload_path` | str | Pasta relativa dos uploads de IMAGE |
| `link` | str | Endpoint p/ link da célula (ex.: `'produtos.list'`) |
| `calc` | str/callable | Campo **calculado virtual** (não persistido): string = expressão aritmética (célula ao vivo na sub-tabela do form); callable = `f(item) -> valor` renderizado na coluna (lista) e como rótulo `readonly` no form — substitui a prop `function` |

### 5.3 Filtros de lista

Campos com filtro habilitado ganham widget na tela de lista. O tipo é inferido
do `input` do campo (text → busca, number → intervalo, date → período,
boolean/select → Sim/Não/listas) e pode ser forçado/ocultado com `in_filter`:

```python
{'type': 'TEXT', 'in_filter': 1}          # input de texto (explícito)
{'type': 'MEMO', 'in_filter': 0}          # oculta do filtro
{'type': 'LIST', 'in_filter': 3}          # checklist multi-seleção (1+ opções)
```

No checklist, cada opção vira um checkbox; a seleção é enviada como valores
separados por vírgula (`?status=Pendente&status=Negociação`) e filtrada por
inclusão no valor do registro (SQL `IN` para listas de objetos).

Referências (`FK`/`masterkey`) geram select com as opções do banco
automaticamente. O rótulo de cada filtro na aba **Filtros** segue o
`label`/`display_label` do campo (não o nome cru — ex.: `carteira_id` →
"Carteira").

### 5.4 `Query`, chave reservada `__meta__`, referências derivadas e `agg`

**`Query` — referência declarativa de consulta.** Todo campo `*_id` de select
pode usar `str` (chave do `MODEL_MAP`), `dict` ou a dataclass `Query`:

```python
# dict (idêntico à dataclass)
'carteira_id': {'type': 'FK', 'query': {'model': 'carteira', 'when': 'uso IN (0, 1)'}}
'product_id':  {'type': 'FK', 'query': {'model': 'product', 'display': 'preco', 'return_field': 'preco'}}
```

Campos **implícitos** — derivados automaticamente do model consultado:

| Campo | Derivação | Ex.: `carteira_id` | Ex.: `preco` (product) |
|---|---|---|---|
| `model` | **obrigatório** | `'carteira'` | `'product'` |
| `field` | PK do model (coluna de busca) | `'id'` | `'id'` |
| `columns` | 1º campo string após a PK | `'nome'` | `'nome'` |
| `display` | 1º campo string após a PK | `'nome'` | `'preco'` (informado) |
| `return_field` | PK do model | `'id'` | `'preco'` (informado) |
| `when` | — | `'uso IN (0, 1)'` | — |
| `order` | `display` | `'nome'` | `'preco'` |

- `display` — coluna exibida no select, na listagem (`card_path` derivado:
  `carteira_id` + model `carteira` → exibe `carteira.nome`) e no filtro;
- `return_field` — coluna submetida após a seleção (default: PK). Ex.: buscar o
  produto pela FK e retornar o `preco` (em vez do id);
- `when` — cláusula SQL `WHERE` (substitui a antiga `query_filter`).

**Chave reservada `__meta__`** — toda entrada da `Entity` é um dict de campos;
chaves que começam com `__` são **reservadas** e não viram campos. `__meta__`
(`label`/`readonly` de sessões derivadas) foi **substituída por `label`
explícito na config da sessão** e `masterkey` para DK — removida de novos
módulos (Pedidos usa `table: ['Entity']` + `label` na sessão). Motor ainda
lê para compatibilidade com módulos legado.

**Referência derivada da relação** — um campo `*_id` sem `masterkey`/`query` tem
o `query` resolvido automaticamente pelo motor a partir da relação do model do
filho (ex.: `product_id` em `quote_item` → `query=Query(model='product')`). Vale
para campos de sessões **e** do form principal (ex.: `category_id` em `Product`).
O alvo precisa estar em `MODEL_MAP` (§4.6).

**Selects `LIST` com valor fora do padrão** — o select e o rótulo aceitam o
valor salvo mesmo que a caixa/maiúscula não bata com a chave da `list`
(ex.: `'kg'` salvo → mostra a opção `'Kg'` selecionada). Ao salvar o registro,
o valor é normalizado para a chave padrão.

**Campo `DK` (detail key)** — marca a coluna que liga a linha filha à **tabela
principal da `Entity`** (a primeira chave da `Entity`, ex.: `ingredient_id` na
sessão "Conversões" de um Insumo). É `in_form: 0`, não participa de validação
e é preenchido automaticamente pelo motor ao salvar (FK para o pai). Se
`masterkey`/`query` não forem dados, o padrão é a chave `MODEL_MAP` da primeira
tabela da `Entity`:

```python
'UnitConversion': {
    'id':            {'type': 'ID'},   # PK
    'ingredient_id': {'type': 'DK'},   # ligação com o Insumo (pai)
    ...
}
```

**Campo `MULT10`** — múltiplas opções fixas (`list`/`options`), limitadas a
**10 opções com códigos de 1 caractere (0-9)**; o valor persistido é a
concatenação dos códigos marcados, sem separador (ex.: `"01"` = etapas 0 e 1).
Na exibição, os códigos são traduzidos para os rótulos
(ex.: `"01"` → "Preparação, Montagem"). O limite é validado em runtime
(`build_field_config`): mais de 10 opções ou código multichar lança `ValueError`.

O editor é **genérico e incluso no framework**: em campos do form e em células
de sessões editáveis, o `MULT10` é um controle `multi-ctl` (rótulo + lápis que
aparece no hover); o clique abre o modal `multiModal` com as opções verticais
e botões Cancelar/OK. O modal grava o valor concatenado (ordenado) num hidden
único — o servidor recebe o mesmo contrato de antes (códigos concatenados).
Em sessões `readonly`, o campo é renderizado apenas como texto, sem editor.

**`agg` dict no form** — além do `'sum'` de rodapé na listagem/relatório, `agg`
aceita um dict para o motor **recalcular o campo do pai ao salvar** os filhos:

```python
'total': {'type': 'NUM', 'currency': 'brl',
          'agg': {'table': 'items', 'sum': 'preco_unitario * quantidade'}},
```

O motor soma a expressão (avaliada com namespace restrito aos atributos de cada
filho) e atribui ao campo do pai após persistir as sessões.

---

## 6. List — configuração

A configuração da listagem vive na aba `Dados` (`type: 'List'`) de `Page`.

### 6.1 Exemplo

```python
Page = {
    'tabs': {
        'Dados': {
            'type': 'List',
            'fields': ['Product'],
            'ordering': ['nome'],
            'title': 'Produtos cadastrados',
            'new_endpoint': None,     # esconde o botão "Novo" (sem criação)
        },
        'Filtros': {'type': 'Filter'},
    },
}
```

### 6.2 `Page` — abas da página

`Page` é um dict com `tabs` (`{id_da_aba: {cfg}}`). A **chave é o rótulo** exibido
no botão da aba (ex.: `'Dados'`, `'Filtros'`, `'Relatórios'`). Cada aba aceita:

| Propriedade | Tipo | O que configura | Padrão |
|---|---|---|---|
| `type` | str | Renderização do painel: `List`, `Filter`, `Report` ou `Custom` | derivado da chave (`Dados`→`List`, `Filtros`→`Filter`, `Relatórios`→`Report`, senão `Custom`) |
| `max_width` | int | Largura máxima do **painel** (conteúdo) em `ch`, centralizada | largura da página |
| `template` | str | Template alternativo da página (aba `List`) ou do painel (tipos `Report`/`Custom`) | `pages/list.html` |

- O tipo de uma aba é **validado** — valor fora de `List/Filter/Report/Custom`
  lança `ValueError`.
- Sem `max_width`, o painel ocupa a largura da página (com a pequena margem
  padrão). Com `max_width`, o conteúdo do painel fica centralizado e limitado
  a `max_width` caracteres (`max-width: Nch; margin-inline: auto`).
- Se o `Page` declarado não incluir aba `type: 'Filter'`, o framework acrescenta
  uma aba `Filtros` padrão (para não perder a filtragem da listagem).
- Tipos `Report`/`Custom` são **reservados**: renderizam `template` quando
  informado, senão ficam vazios. Relatórios PDF são gerados por `do_report`
  (§7.7) com dados da instância (`data_attr`) ou passados diretamente.

Exemplo com largura de painel:

```python
Page = {
    'tabs': {
        'Dados': {
            'type': 'List',
            'fields': 'Carteira',
            'ordering': ['nome'],
        },
        'Filtros': {
            'type': 'Filter',
            'max_width': 80,        # painel de filtros limitado a 80ch, centralizado
        },
    },
}
```

### 6.3 Referência de propriedades da aba `List`

| Propriedade | Tipo | O que configura | Padrão |
|---|---|---|---|
| `fields` | list[str]/dict | Colunas da tabela. Formato `'Entity'` (todos os campos), `'Entity.campo'` (campo específico), nome simples (resolvido via entity principal) ou `{'name': ..., 'label': ...}` (override); campos com `in_list: 0` são omitidos e com `in_list: 2` vão direto para o card | `[entidade]` |
| `card` | list[str] | Campos do card de destaque (primeira coluna, com id + imagem) | — |
| `linha` | list[str] | Campos destacados nas linhas (utilizado com filtros) | — |
| `detail` | list[str] | Campos de detalhe expandível; o framework busca itens na relação `<entity>_items` (viewonly) do model | — |
| `ordering` | list[str] | Nomes de **atributos** da model p/ `ORDER BY` (ex.: `['ordem', 'nome']`) | — |
| `title` | str | Título da página | nome da entidade |
| `template` | str | Template alternativo da página | `pages/list.html` |
| `tags` | list | Fields renderizados como badges coloridos nas células — `[{'field': 'status', 'colors': {9: 'success', ...}}]` ou `['status']` (cores inferidas) | — |
| `new_endpoint` | str/None | Endpoint do botão "Novo". Ausente → `'<blueprint>.form'`; `None` → esconde; string → usa esse endpoint | — |
| `edit_endpoint` | str/None | Endpoint do link de edição da linha. Ausente → `'<blueprint>.form'`; `None` → esconde | — |
| `edit_id_field` | str | Campo usado no `id=` do link de edição | `'id'` |
| `buttons` | list | Botões no cabeçalho, à esquerda de "Incluir" (quebram para a próxima linha se não couber). Mesma sintaxe de `Form['buttons']` (§7.5): preset `ACTIONS` (ex.: `['on_off']`), `{nome: {overrides}}` ou dict `{label, endpoint, icon, color, ...}`. `on_off` é botão de linha (precisa de instância) e **não** é renderizado no cabeçalho | — |

### 6.4 Semântica de endpoints (importante)

O padrão "ausente → default" permite comportamento por omissão, e o `None`
explícito **esconde** o botão/link:

```python
Page = {
    'tabs': {
        'Dados': {
            'type': 'List',
            'fields': ['Category'],
            'edit_endpoint': None,   # listagem somente-leitura
        },
        'Filtros': {'type': 'Filter'},
    },
}
```

> Quando `new_endpoint`/`edit_endpoint` são `None`, o respectivo botão/link não é
> renderizado. Útil para módulos de consulta ou detalhe.

### 6.5 Página única e Vitrine declarativa (`showcase`)

Página única: `Page` com `tabs: ''` descreve uma página **sem abas nem CRUD**,
renderizada pelo motor via `do_page`. Declare `crud: False` (a rota `list` é
gerada automaticamente). O `template` define o tipo de renderização:

| `template.type` | `file` | Renderiza |
|---|---|---|
| `html` | opcional (omitido = `'index'`) | Template do módulo (`site/vitrine/index.html`) com contexto da função `context()` |
| `markdown` | nome (`'sobre'`) ou caminho | Conteúdo markdown (loader do host) na template padrão `pages/markdown.html` |
| `showcase` | — | Vitrine declarativa (abaixo) na template padrão `pages/showcase.html` |

`Page['type']` também aceita `'contacts'` e `'cart'`, ambos com template nativo
do motor (`pages/contacts.html` e `pages/cart.html`): contato renderiza
`props` `{título: {type, value}}` (ícones whatsapp/email/instagram/facebook/
linkedin, telefone mascarado), e carrinho renderiza `session['cart_items']`
com envio em `Page['events']['on_send']`. Nenhum template no módulo é
necessário nesses casos.

A **vitrine** (`Page['showcase']`) gera vitrine + carrinho de sessão +
identificação do cliente sem nenhuma rota ou template custom. Exemplo completo:

```python
# app/routes/site/produtos.py — só declaração, sem funções
Entity = {
    'Product': {
        'nome':        {'type': 'TEXT'},
        'descricao':   {'type': 'MEMO', 'rows': 4},
        'imagem':      {'type': 'IMAGE'},
        'qtd_minima':  {'type': 'INT'},
        'category_id': {'type': 'FK', 'query': 'category'},
    },
    'Category': {'nome': {'type': 'TEXT'}},
}
Page = {
    'crud': False,
    'tabs': '',
    'route': 'vitrine',
    'max_width': '48rem',           # largura da página; a vitrine dimensiona o resto proporcionalmente
    'showcase': {
        'fields': 'Product',        # entidade dos itens (chave do Entity)
        'filter': 'Category',       # entidade do filtro de categoria
        'layout': 'carousel',       # carousel | grid | list
        'show': {'nome': 'title', 'imagem': 'left',
                 'descricao': 'right', 'qtd_minima': 'qty'},
        'client_fields': ['nome', 'telefone'],   # termos nome/telefone/email (aliases fone/mail)
        'badge_id': 'bnOrcamentoBadge',          # id do contador do carrinho no shell
    },
}
```

A largura da página é declarada no **`Page`** (`max_width`: `int` → `{n}ch` ou
string CSS, ex. `'48rem'`); a vitrine usa essa largura e dimensiona os demais
elementos (filtro, card e navegador) proporcionalmente a ela.

Propriedades da showcase:

| Propriedade | Obrigatória | O que configura | Padrão |
|---|---|---|---|
| `fields` | sim | Entidade dos itens (chave do `Entity` do módulo) | — |
| `filter` | não | Entidade do filtro de categoria (exibe badges + seletor) | — |
| `layout` | não | `carousel`, `grid` ou `list` | `carousel` |
| `show` | não | `{campo: posição}` dos campos do card (`title`, `left`, `right`, `qty`); a posição do campo `IMAGE` no `Entity` renderiza a imagem | — |
| `client_fields` | não | Lista de termos pedidos no modal de identificação (`nome`, `telefone`, `email`; aliases `fone`, `mail`). Ativa o modal e a rota `POST /<rota>/api/cliente` | — |
| `badge_id` | não | `id` do elemento-contador do carrinho no shell do host | — |

Convenções: carrinho em `session['cart_items']` com itens `{entidade}_id` /
`quantidade` / `observacao`; cliente identificado em `session['client']` (em
memória, **sem** persistir em banco); itens e categorias filtrados pela coluna
`ativo`/`active` quando existir; imagem servida por
`adapter.get_uploads_endpoint()` (default `uploads.uploaded_file`). Rotas
geradas: `POST /<rota>/<id>/add|update|remove` — o `add` valida a quantidade
mínima (`qty` do produto) e responde `401` quando há `client_fields` e o
cliente ainda não foi identificado (o JS abre o modal) — e
`POST /<rota>/api/cliente` (valida os campos obrigatórios). Os endpoints
(`adicionar`, `atualizar`, `remover`, `identificar`) são sobrescritos se o
módulo os declarar com `@auto.rota`.

> O fluxo do algodoce é o caso de uso padrão: identificar → adicionar ao
> carrinho → `orcamento.py` monta o `Quote` a partir de `session['client']` +
> `session['cart_items']` (uma `Conta` só nasce na conversão orçamento→pedido).

---

## 7. Form — configuração

O `Form` é um dict em `Page['props']['form']` com a configuração **declarativa**
do formulário. O **motor** resolve o resto a partir de `fields` + o `Schema` da
página (rota) + as entitys associadas (imports do módulo): ele **lembra de nada
do host** — apenas lẽ a página e resolve via `columns`/`fields`.

```python
Form = {                     # dentro de Page['props']['form']
    'fields': 'Category',    # nome da entidade (source de verdade)
    'delete': {Product},     # set de classes/models → bloqueia se houver referência
    'buttons': ['on_off'],
    'pre_save': _pre_save,
}
```

### 7.1 Formato de `fields`

`fields` é a **única fonte** de model + schema + colunas. O motor resolve o model
via `_resolve_model` (`MODEL_MAP`), faz o merge do `Schema` da página com o
`Entity` do model e monta os campos resolvidos.

| Formato | Sintaxe | Quando usar |
|---|---|---|
| string | `'fields': 'Category'` | todos os campos da entidade `Category` |
| lista | `'fields': ['nome', 'preco']` | campos específicos (por nome) |
| dict de campo | `'fields': [{'name': 'nome', 'label': 'N.ome'}]` | sobreposições de campo |

> Não existe mais `model`, `entity_name`, `schema` ou `field_overrides` como
> props: tudo é derivado de `fields` pelo motor.

### 7.2 Referência de propriedades

| Propriedade | Tipo | O que configura | Padrão |
|---|---|---|---|
| `fields` | str/list/dict | Campos do form (§7.1) — resolve model+schema+colunas | — |
| `sessions` | dict | Tabelas/seções filhas (§7.3) | — |
| `template` | str | **1ª prop**: se setada, as demais são ignoradas | `pages/form.html` |
| `readonly` | bool/callable | Form read-only: `False` (padrão), `True`, ou `(instance)->bool` | `False` |
| `delete` | bool/callable/set/dict | Exclusão (§7.4) | `False` |
| `pre_save` | callable | `(instance, request, is_new) -> bool` (§7.6) | — |
| `post_save` | callable | `(instance, changed, old_vals)` (§7.6) | — |
| `buttons` | list | Botões (§7.5) | — |
| `tags` | list | Badges no nav bar (§2) | — |
| `flash_ok` | str | Mensagem de sucesso (criação) | `'{label} incluído!'` |
| `flash_update` | str | Mensagem de sucesso (atualização) | `'{label} atualizado!'` |
| `spacing` | int | Espaçamento do grid de campos | `2` |

**Props removidas** (o motor resolve/deriva — comportamento padrão):
`model`, `module_name`, `entity_name`, `schema`, `field_overrides`, `redirect`
(derivado do blueprint), `label`/`new_label`/`new_title` (derivados de `fields`),
`back_url`, `edit_endpoint`, `nav`, `nav_right_extra`, `body_template`,
`form_tail`, `footer_left`, `page_scripts`, `tag` (→ `tags`), `delete_when`
(→ `delete`), `readonly_when` (→ `readonly`), `defaults` (default resolve no
campo), `toggle` (→ via `buttons: ['on_off']`), `flash_deny`, `flash_excluido`,
`flash_toggle`.

### 7.3 `sessions` — seções filhas (dict puro)

**Derivação automática (recomendado)** — se `sessions` não for declarado, o motor
deriva as sessões dos **relacionamentos** do model do form (as relações
ONETOMANY/ONETOONE cujo model alvo tenha `Entity`):

```python
Form = {
    'fields': 'Product',
    # sem 'sessions' → o motor gera a sessão 'ingredients'
}
```

**Sessões explícitas** — dict, com `template`, `fields`, `query` ou `table`:

```python
Form = {
    'fields': 'Ingredient',
    'sessions': {
        'Conversões': {                       # chave = rótulo da seção
            'table': {'columns': ['UnitConversion'], 'allow_add': True, 'allow_delete': True},
        },
        'Produtos': {
            'table': {'columns': ['ProductIngredient'], 'allow_add': False, 'allow_delete': False},
        },
        'Obs': {'template': 'sys_insumos/_obs.html'},   # template só (1ª prop)
    },
}
```

Propriedades de cada sessão (dict):

| Propriedade | Tipo | O que configura |
|---|---|---|
| `template` | str | **1ª prop**; se setada, as demais são ignoradas (template parcial) |
| `fields` | str/list/dict | Campos não-tabulares (form simples, mesmo formato de `Form.fields`) |
| `query` | dict | **Somente-leitura** (mini-relatório) com `columns` e demais props de `Query` (§12) |
| `table` | dict | Tabela editável com `columns`, `allow_add`, `allow_delete`, `order` |
| `name` | str | Rótulo explícito da seção (senão usa a chave do dict) |

> `query` e `table` são **mutuamente exclusivos** — o motor lança erro se ambos
> forem declarados. `columns` aceita o nome da entidade (expande todos os campos)
> ou lista de campos específicos. O vetor de colunas é resolvido contra o `Entity`
> + `Schema` da entidade filha e preserva a **ordem de definição**.

### 7.4 `delete` — exclusão com proteção

`delete` aceita os seguintes formatos (o motor normaliza todos):

```python
'delete': False,                # sem exclusão (padrão)
'delete': True,                 # sempre permite
'delete': lambda i: i.status < 7,        # callable (instance) -> bool
'delete': {Product, Order, Quote},       # set de classes/models → bloqueia se houver referência
'delete': {'when': {Product}, 'msg_ok': 'Categoria excluída.', 'msg_no': 'Em uso.'},
```

| Formato | O que configura |
|---|---|
| `False` | sem exclusão — a rota `/<id>/excluir` não é criada |
| `True` | permite excluir sempre |
| callable | `(instance)->bool` — `True` permite |
| set/list/tuple de classes | checa FK nos models dados; se houver referência, bloqueia |
| dict | `{'when': <qualquer formato acima>, 'msg_ok': ..., 'msg_no': ...}` |

> O motor monta o modal de confirmação e cria a rota `/<id>/excluir`. O botão
> **Excluir** no rodapé do form só aparece no modo edição quando há `delete`
> habilitado. Para limpeza/callback extra, declare uma rota `delete` custom
> (veja §4.5).

### 7.5 Botões (`buttons`)

Os botões vêm de `app/ajsystem/defs/buttons.py` (presets `BTN_*`) ou `Button(...)`.
Três formas no `Form`:

```python
'buttons': ['on_off'],                      # ação padrão (toggle ativo/inativo)
'buttons': [{'on_off': {'field': 'publicado'}}],   # ação padrão com campo custom
'buttons': [BTN_SALVAR, Button(label='Imprimir', icon='printer', color='info')],
```

| Propriedade de `Button` | Tipo | Uso |
|---|---|---|
| `label` | str | Texto do botão |
| `icon` | str | Nome do ícone (Heroicon) |
| `color` | str | `success`, `danger`, `primary`, `secondary`, `info`, `warning`, ... |
| `outline` | bool | Estilo outline |
| `size` | str | `sm`/`md`/`lg` |
| `endpoint` / `url` | str | Destino do link |
| `action` | callable | `(instance) → url` ou, com `render`, `(instance) → html` — Orçamentos `Enviar`; Pedidos `Enviar` (render fragment) |
| `render` | str | CSS selector do container que recebe HTML retornado por `action` via `injectHTML` (ex: `'#page-content'`) — Pedidos `Enviar` |
| `method` | str | `GET`/`POST` (para ações) — Pedidos `Cancelar Pedido` (POST com confirm) |
| `confirm_msg` | str | Mensagem do modal de confirmação |
| `on_off` | bool | Botão de toggle ativo/inativo |
| `field` | str | Campo booleano do toggle (padrão `'ativo'`) |
| `label_off`/`icon_off` | str | Rótulo/ícone no estado "off" |
| `when` | callable | `(instance) → bool`; oculta o botão quando retorna `False` |
| `show_if` | tuple | Mostrar conforme condição `(campo, valor)` (legado) |
| `position` | str | `nav_right`, `nav_left`, `footer_left`, `footer_right` |
| `extra_params` | dict | Parâmetros extras na URL |

> ~~`hide_if`~~ removido — usar `when`.

Presets: `BTN_SALVAR`, `BTN_ENVIAR`, `BTN_EXCLUIR`, `BTN_NOVO`, `BTN_VOLTAR`,
`BTN_EDITAR`, `BTN_CANCELAR`, `BTN_CONVERTER`, `BTN_LISTA`, `BTN_IMPRIMIR`,
`BTN_DETALHES`, `BTN_ADICIONAR`, `BTN_ADICIONAR_ITEM`, `BTN_FINALIZAR`,
`BTN_ATUALIZAR`, `BTN_REMOVER`, `BTN_RELATORIO`, etc.

> O `buttons: ['on_off']` gera a rota `/<id>/toggle` (campo `'ativo'` por
> convenção) — o mesmo efeito de `Form['toggle'] = 'ativo'`.

### 7.6 Hooks de ciclo de vida

```python
def _pre_save(instance, request, is_new):
    if instance.ordem is None and is_new:
        last = db.session.query(db.func.max(Category.ordem)).scalar() or 0
        instance.ordem = last + 1
    return True            # False cancela o salvamento (rollback + redirect)

def _post_save(instance, changed, old_vals):
    if 'ordem' not in changed:
        return
    # reordena demais registros após a mudança
    ...
```

| Hook | Assinatura | Quando | Retorno |
|---|---|---|---|
| `pre_save` | `(instance, request, is_new)` | antes do commit | `False` cancela |
| `post_save` | `(instance, changed, old_vals)` | depois do commit | — |
| `pre_get` | `(mod, id)` | ao abrir o form de edição | dict mesclado no contexto do template |

> `changed` é o conjunto de nomes de campos cujo valor mudou (inclui imagens).
> `old_vals` é o mapa `campo → valor_anterior`.

`pre_get` também pode devolver **`ro_fields`**: um dict `{campo: mensagem}` —
campos listados renderizam como readonly (texto + `<input type="hidden">`) e
mostram `mensagem` como hint discreto. Ex. (Carteiras): quando em uso, só o
`nome` fica travado:

```python
def _carteira_pre_get(mod, id):
    carteira = Carteira.query.get(id)
    if carteira and em_uso(carteira, [Compra, Order, Quote, Previsao]):
        return {'em_uso': True,
                'ro_fields': {'nome': 'Carteira já utilizada — o nome não pode ser alterado.'}}
    return {'em_uso': False}
```

### 7.7 Relatórios PDF (`do_report` / `print_report`)

Relatórios são **dicts declarativos** (igual a `Entity`/`Page`) em
`app/reports/*.py`; o motor resolve para `Report` via `parse_report`.
**Nenhuma rota envolvida**: a action do botão constrói os dados, chama
`print_report(DICT, data=...)`, o motor gera os bytes do PDF e embute-os
no iframe como **data URI** — N relatórios por página sem conflito de URLs.

```python
# app/reports/orcamentos.py — declaração pura:
ORCAMENTO_REPORT = {
    'label': 'Orçamento',                 # display (título do PDF)
    'header': {...}, 'table': {...}, 'after_table': _event_after,
}

# app/routes/sys/orcamentos.py — botão com pre-controle no form:
def _btn_enviar_action(instance):
    if not instance.items:
        return ''                          # não injeta nada
    return print_report(ORCAMENTO_REPORT, data=instance.items, instance=instance)

{'label': 'Enviar', 'icon': 'paper-airplane', 'color': 'success',
 'action': _btn_enviar_action, 'render': '#page-content',
 'when': lambda i: i.pedido_id is None and i.status < 7}

# app/routes/sys/operacoes.py — fonte inferida; Field.code na Entity:
{'label': 'Plano', 'icon': 'printer', 'color': 'info',
 'action': lambda _: print_report(PLANO), 'render': '#page-content'}
```

**Report (dict)** — propriedades:

| Propriedade | Tipo | Descrição | Padrão |
|---|---|---|---|
| `logo_path` | str | Path da logo (relativo a `root_path`); resolvido em runtime | `'static/icons/Logo.png'` |
| `print_template` | str | Página standalone imprimível (p/ rota custom) | `'components/print_default.html'` |
| `print_fragment_template` | str | Fragmento HTML p/ injeção via `injectHTML` | `'components/print_fragment.html'` |

**Header/Table:**

- `header.title`: str ou dict `{label, font_size, font_style, align}` ·
  `header.line`: True → linha horizontal após o cabeçalho
- `table.rows_after` / `table.rows_before`: espaçamento (default **1**)

**Fonte de dados (inferência):** sem `data`/`instance`, o motor localiza o
**model da Entity que contém todas as colunas** da tabela (`_resolve_model`),
consulta-o e ordena pelo **calc callable** de uma das colunas (ex.: índice
hierárquico via `core/hier.py::codigos` (Field.code)). Ambíguo/ausente → erro com
orientação.

**`do_report(report, data=None, instance=None, filename, as_response=True)`**

- `report` — dict ou Report (resolvido por `parse_report`)
- `data` — itens/rows do relatório (sempre explícitos)
- `instance` — instância do model (para `{id}` no título)
- `filename` — nome do arquivo PDF no Content-Disposition
- `as_response=False` → retorna objeto FPDF (para testes)

**`print_report(report, data=None, instance=None, msg=None)`** — fragmento
HTML com PDF embutido (data URI), sem page_layout; usado nas actions.

**`print_report_page(report, data=None, instance=None, msg=None)`** — mesma
view como página completa; para views standalone via rota custom.

> **Contrato de erro:** qualquer falha de geração renderiza a view interna
> `components/print_erro.html` com `msg`
> (default `'Erro na impressão do Relatório'`). Sem URLs de fallback —
> o botão Voltar das views usa `reload()` (fragmento) / `history.back()`
> (página cheia).
>
> ~~`edit_endpoint`~~ / ~~`pdf_endpoint`~~ / ~~`endpoint`~~ / rotas `/pdf`,
> `/print` geradas / ~~`mod.REPORT`~~ / mapa ou scan de pacote /
> chave `'print'` / ~~`redirect_fn`~~ / ~~`data_fn`~~ / ~~`data_attr`~~:
> removidos — tudo vive na action da app + data URI.

### 7.8 Templates custom

Você pode sobrescrever partes sem recriar a página inteira:

- `template` — página completa;
- `body_template` — só a área de campos;
- `form_tail` — HTML antes dos botões de ação;
- `footer_left` — rodapé à esquerda (ex.: status);
- `page_scripts` — JS extra da página;
- `nav_right_extra` — HTML extra na barra de navegação.

Componentes reutilizáveis: `components/form_macros.html` (`fm.render_fields`,
`fm.render_widget`, ...), `components/item_table.html`,
`components/image_widget.html`.

---

## 8. Exemplo completo do zero

### Passo 1 — Model (categoria)

```python
# app/models/category.py
from app.extensions import db


class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    ordem = db.Column(db.Integer, default=0)
    ativo = db.Column(db.Boolean, default=True)
```

### Passo 2 — Módulo declarativo

```python
# app/routes/sys/categorias.py
from app.extensions import db
from app.models.category import Category
from app.models.product import Product


def _pre_save(instance, request, is_new):
    if instance.ordem is None and is_new:
        last = db.session.query(db.func.max(Category.ordem)).scalar() or 0
        instance.ordem = last + 1


Entity = {
    'Category': {
        'id':    {'type': 'ID'},
        'nome':  {'type': 'TEXT'},
        'ordem': {'type': 'INT', 'attrs': {'min': 0, 'max': 99}},
        'ativo': {'type': 'BOOL'},
    },
}

Page = {
    'tabs': {
        'Dados': {
            'type': 'List',
            'fields': ['Category'],
            'ordering': ['ordem', 'nome'],
            'title': 'Categorias',
        },
        'Filtros': {'type': 'Filter'},
    },
}

Form = {
    'fields': 'Category',
    'delete': {
        'when': {Product},
        'msg_ok': 'Categoria excluída!',
        'msg_no': 'Não é possível excluir — está em uso.',
    },
    'buttons': ['on_off'],
    'pre_save': _pre_save,
}
```

> `delete['when'] = {Product}` bloqueia a exclusão enquanto existirem produtos
> referenciando a categoria (checagem automática de FKs).

### Passo 3 — registrar o módulo no menu

```python
# app/config.py
'modules': [
    {'type': 'system',
     'default_path': 'cadastro/categorias',
     'menus': {
         'Cadastro': {'submenus': {'Categorias': {'icon': 'bi-journal'}}},
     }},
],
```

### Passo 4 — rodar

```bash
flask db init
flask db migrate -m "initial"
flask db upgrade
python run.py
```

Acesse `/categorias/` (listagem), `/categorias/novo` (form) e o menu. Para uma
entidade com referência, imagem, tabela filha e rotas custom, veja o padrão de
`Product` em `app/routes/sys/produtos.py` (tipos `FK`, `LIST`, `IMAGE`, `NUM`,
sessão `ingredients` **derivada automaticamente** dos relacionamentos e
`@auto.rota`).

---

## 9. Referências rápidas

### Globals do Jinja (injetados por `init_app`)

| Nome | Descrição |
|---|---|
| `aj_uploads_endpoint()` | endpoint de uploads (do adaptador) |
| `SYS` / `APP` / `Temas` | definições do app |
| `CONECTORES` | conectivos usados na geração de títulos |
| `current_user` | usuário logado (flask-login) |

### Filtros úteis

| Filtro | Uso |
|---|---|
| `fmtdate` | formata data/hora |
| `brl` | formata moeda brasileira |
| `mask` | aplica máscara (com `digits_only`) |
| `deep_attr` | acessa atributo aninhado (ex.: `item|deep_attr('Encomenda.id')`) |
| `title_case` | transforma nome em título (usando `CONECTORES`) |

### Convenções importantes

- **Tipos em maiúsculas** (`TEXT`, `NUM`, `FK`, `LIST`, `IMAGE`, ...).
- **Referências** usam `masterkey: '<chave do MODEL_MAP>'` (FK) ou são derivadas
  da relação do model no form; opções fixas com `list`/`options` (LIST).
- **Sessões** derivadas dos relacionamentos quando `Form['sessions']` ausente
  (§7.3); chaves `__*` na `Entity` são reservadas (`__meta__`).
- **Slug do menu** = slug do módulo (`label`/`page` → módulo em
  `app.routes.sys.<slug>`).
- **Endpoints gerados**: `<slug>.list`, `<slug>.form`, `<slug>.delete`,
  `<slug>.toggle`.
- **`None` desliga** (`new_endpoint`, `edit_endpoint`, `delete`, `toggle`).
- **`ordering` usa atributos da model**, não `'Entity.campo'`.
- **`login_required`** em todas as rotas CRUD geradas.

---

## 12. Consultas nomeadas (`Query`), campos derivados e agregados

### `Query` — consultas em um só lugar

Uma `Query` é um **dict nomeado** (mesmo estilo de `Entity`/`List`/`Form`), sem
função de definição, que descreve uma consulta agrupada reutilizável. O rótulo
padrão vem do nome da chave (`label` opcional para sobrescrever).

```python
Query = {
    'pedidos': {
        'fields': ['Order'],              # strings = entidades; dicts = campos explícitos
        'group_by': 'status',
        'order_by': 'data_pedido desc',
        'totals': {
            'Qtd':          {'sum': 'qtd'},
            'Valor':        {'sum': 'total', 'currency': True},
            'Média/Pedido': {'avg': 'total', 'currency': True},
            'Média/Item':   {'avg': 'total', 'by': 'qtd', 'currency': True},
        },
        # fonte SQL global (fase 2): join / where / raw ('with x as (...) select ...')
    },
}

Form = {
    'fields': 'Conta',
    'sessions': {'Pedidos': {'query': 'pedidos'}},
}
```

- `query` aceita **string = chave da `Query`** (dict nomeado do mesmo módulo, ver
  §12) ou **lista/string de entidades** (formato legado, §7.3). O valor string
  é resolvido no registro `Query` do módulo — `KeyError` se a chave não existir.
- `fields`: **strings = nomes de Entity** (campos vêm da Entity, sem redefinição);
  **dicts = campos explícitos** (`{'name': 'conta.nome', 'label': 'Cliente'}` —
  caminhos dotted funcionam via `deep_attr`).
- `group_by`: campo de agrupamento (ordem das `options` quando houver).
- `order_by`: ordem das linhas (`'campo'`, `'campo desc'` ou lista).
- `totals`: agregados por grupo/geral (ver spec abaixo).
- O motor (`app/ajsystem/core/query.py`) é consumido por sessões de Form; na fase 2
  também por List/PDF. Sessões de form buscam os itens por **relacionamento**; a
  fonte SQL global (`join`/`where`/`raw`) é extensão futura.
- O formato inline legado (§7.3, `'query': ['Order']` + `group_by`/`group_totals`)
  continua suportado pelo motor.

### Campo calculado (`Field.calc`)

Campo **virtual** (sem coluna no banco) — o valor **não é persistido**, é
calculado sob demanda na renderização:

```python
# callable — função `f(item) -> valor` renderizada na coluna da lista e como
# rótulo `readonly` no form (substitui a antiga prop `function`):
'validade_data': {'label': 'Válido até', 'calc': quote_validade,
                  'width': 14, 'readonly': True, 'in_filter': 0},

# string — expressão aritmética avaliada por linha, com namespace restrito
# aos atributos; renderiza ao vivo a célula da sub-tabela no form
# (ex.: `QuoteItem.valor`):
'valor': {'type': 'NUM', 'calc': 'quantidade * preco_unitario', 'in_form': 0},
```

- Callable: recebe o registro (`item`) e devolve o valor final da célula
  (texto/`Markup` incluso). Avaliado no servidor pelo global Jinja `calc_value`
  (`init.py`).
- String: usa o mesmo avaliador restrito do `agg` (`eval` com `__builtins__`
  vazio) no servidor e o `itEval` (JS) ao vivo no form.
- `calc` não participa de save/filtro — é exibição apenas. No form, campos com
  `calc` são renderizados como rótulo `readonly` (sem input) e não são
  persistidos.

### Campo derivado (`Field.derived`)

Campo **virtual** (sem coluna no banco) calculado por item pelo motor:

```python
'qtd': {'type': 'INT', 'derived': {'sum': 'items.quantidade'}},
```

- `{'sum': '<caminho>'}` — soma das folhas do caminho, percorrendo coleções
  (`items.quantidade` = soma das quantidades dos itens do registro).
- Resolvido por `field_value` (global Jinja e helper Python) em renderização e
  em agregados.

### Spec de agregados (`totals` / `group_totals`)

| Spec | Resultado |
|---|---|
| `'count'` | número de itens (linhas) |
| `{'sum': 'campo'}` | soma (resolve derivados e dotted) |
| `{'avg': 'campo'}` | média sobre itens com valor (soma ÷ nº de itens com valor) |
| `{'avg': 'campo', 'by': 'divisor'}` | soma(campo) ÷ soma(divisor) — média ponderada (ex.: Valor ÷ Qtd) |

- `'currency': True` — formata como BRL na renderização.
- Divisor zero ou valor ausente → renderiza `—`.

### Summary

- Definir campos **uma vez** na Entity (incl. derivados) e referenciá-los na
  `Query` — sem redefinição.
- `Query` nomeada = mesma definição para Form hoje, List/PDF depois.
- Agregação/agrupamento rodam **em Python** sobre as linhas buscadas (preserva
  derivados, média ponderada e formatação da Entity).
- A sessão referenciada por `query` (dict `Query` ou lista/string de entidades)
  vira `readonly` e não é persistida pelo motor.
