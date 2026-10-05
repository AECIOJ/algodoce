# AJSYSTEM 1.26.09.30.0001 — Manual do Framework

> Vinculado a `ajsystem/version` (`1.26.10.02.0001`) — formato `1.aa.mm.dd.bbbb` (`aa` ano, `mm` mês, `dd` dia, `bbbb` builder do dia). Incremente `bbbb` **quando o assunto mudar** (mesmo assunto no mesmo dia mantém a versão). Histórico na seção 6. Versão do app hospedeiro em `APP['version']` (`app/config.py`, `{cycle, year, month, number}` → lê-se `1.aa.mm-build`; bump via script de bump do host).

---

## 1. Introdução e Conceitos Básicos

1. **Propósito.** Framework Flask declarativo para gestão. Descreva `Entity`/`Schema`/`Page` em dicts. O motor monta `Blueprint`, rotas, telas e menu.
2. **Problemas que resolve.**
   1. Elimina boilerplate de CRUD.
   2. Centraliza campos em `Entity` (única fonte).
   3. Customiza por página via `Schema` (`Entity ∪ Schema`, Schema vence).
   4. Gera PDF com a mesma fonte de campos.
3. **Conceitos.**
   1. `Entity` — base de campos no `model` (`app/models/*.py`).
   2. `Schema` — overrides por página na `route` (`app/routes/sys/*.py`).
   3. `Page` — tipo de página (`crud`, `redirect`, `cart`, `showcase`, `contacts`, `custom`).
   4. `Field` — `type`, `pos_form/pos_list/pos_filter`, `tag`, `calc`, `lookup`.
4. **Pré-requisitos.**
   1. Python 3.10+ (o app hospedeiro roda em 3.10.12).
   2. `dict`, `class`, `lambda`, `decorator`.
   3. Flask: `Blueprint`, `request`, `url_for`.
   4. SQLAlchemy: `db.Model`, `db.Column`, `relationship`.
   5. Jinja2: `{{ }}`, `{% %}`.

---

## 2. Guia de Instalação (Getting Started)

1. Clone.
   ```bash
   git clone <repo> && cd <seu-projeto>
   ```
2. Ambiente.
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   ```
3. Dependências Python.
   ```bash
   pip install -r requirements.txt  # Flask==3.0.0, Flask-SQLAlchemy==3.1.1, psycopg2-binary, fpdf2==2.8.7
   ```
4. Dependências CSS.
   ```bash
   npm install && npm run build:css  # gera tailwind.daisyui.json de app/config.py
   ```
5. Env.
   ```bash
   cp .env.example .env  # DATABASE_URL, SECRET_KEY
   ```
6. Banco.
   ```bash
   docker compose up -d db
   flask db upgrade
   ```
7. Rode.
   ```bash
   flask run  # http://localhost:5000/categorias
   ```
8. Crie um CRUD.
   1. `app/models/tarefa.py` — `class Tarefa(db.Model)` + `Entity`.
   2. `app/routes/sys/tarefas.py` — `Schema={}` + `Page={'type':'crud','props':{'list':{'columns':'Tarefa'},'form':{'fields':'Tarefa'}}}`.
   3. `app/config.py` — `SYS.menus.Cadastro.submenus['Tarefas']={'icon':'bi-check'}`.
   4. Reinicie. Acesse `GET /tarefas/`, `/tarefas/novo`, `/tarefas/<id>/editar`.

---

## 3. Arquitetura e Padrões

1. **Padrão: Declarativo sobre MVC.**
   1. `Model` (`app/models/*.py` + `Entity`) → dados.
   2. `View` (`ajsystem/templates/pages/*.html` + `form_macros.html`) → renderiza `Field`.
   3. `Controller` (`ajsystem/core/auto.py` + `do_list.py` + `do_form.py`) → monta `Blueprint` de `Page`/`Schema`.
2. **Injeção via registro.**
   1. `app/__init__.py:register_model('pedido',Pedido)` → `ajsystem/defs/data.py:MODEL_MAP`.
   2. `resolve_entity_fields(schema, model, entity)` → `{**Entity, **Schema}`.
3. **Fluxo.**
   ```
   config.py:menus → auto.py:registrar_modulos → Page/Schema → resolve_entity_fields → Field → form/list/report
   ```
4. **Camadas.**
   ```
   ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
   │ app/models  │────▶│ ajsystem/defs│────▶│ ajsystem/core│
   │ Entity      │     │ Field/Schema │     │ do_list/form │
   └─────────────┘     └──────────────┘     └──────┬───────┘
          ▲                    ▲                    │
          │                    │                    ▼
   app/routes/sys/Page+Schema──┘            ┌──────────────┐
                                            │  templates   │
                                            └──────────────┘
   ```
5. **Merge.**
   ```
   Entity ──┐
            ├─► {**Entity, **Schema} ──► Field ──► column/form/report
   Schema ──┘          (Schema vence)
   ```
6. **Ciclo form.**
   ```
   GET /novo ──▶ Page.fields='Entidade' ──▶ resolve_column_configs ──▶ render_fields
       ▲                                                              │
       └──────── POST ──▶ _coerce ──▶ calc(agg/call) ──▶ db.commit ──┘
   ```

---

## 4. Exemplos Práticos (Snippets)

1. **Model + Entity.**
   ```python
   class Tarefa(db.Model):
       id = db.Column(db.Integer, primary_key=True)
       titulo = db.Column(db.String(100), nullable=False)
   Entity = {'id':{'type':'ID'},'titulo':{'type':'TEXT','required':True,'width':20},'feito':{'type':'BOOL'}}
   ```

2. **Schema override exclusivo.**
   ```python
   from ajsystem.defs.constants import POS_0_NOT_EMPTY
   Schema = {'Tarefa':{'feito':{'tag':{'colors':{True:'success'}}},'transacao_id':{'pos_form':POS_0_NOT_EMPTY}}}
   # POS_0_NOT_EMPTY = {'pos':0,'when':{'not_empty':True}} → pos:0 explícito só quando valor<>null (só form)
   ```

3. **Page CRUD com sessão.**
   ```python
   Page={'type':'crud','props':{'list':{'columns':'Tarefa','order':['titulo']},'form':{'fields':'Tarefa','sessions':{'Financeiro':{'fields':['total','carteira_id']}}}}}
   ```

4. **Calc + tag com link.**
   ```python
   # Entity: 'transacao_id':{'type':'INT','calc':lambda row: row.transacao_id}
   # Schema: 'transacao_id':{'pos_form':POS_0_NOT_EMPTY,'pos_list':0,'tag':{'link':'receber.form','color':'info'}}
   # total: 'total':{'type':'NUM','calc':'valor + acrescimo - desconto','pos_form':0}
   ```

5. **Pos condicional dict.**
   ```python
   'pedido_id':{'pos_form':{'pos':0,'when':{'not_empty':True}},'tag':{'link':'pedidos.form'}}
   # when: {'not_empty':True} | {'empty':True} | {'field':'valor','op':'not_empty'} | callable(row,val) | 'not_empty'/'empty'
   ```

6. **Menu.**
   ```python
   SYS={'menus':{'Cadastro':{'icon':'bi-journal','submenus':{'Tarefas':{'icon':'bi-check'}}}}}
   ```

7. **Relatório.**
   ```python
   REL={'label':'Tarefas','body':{'source':'Tarefa','table':{'columns':{'titulo':{'width':50},'PedidoItem.valor':{'width':20,'agg':'sum'}}}}}
   {'label':'Imprimir','action':lambda _: print_report(REL, filter_select('feito'))}
   ```

---

## 5. Referência de API

### 5.1 `Field` — `ajsystem/defs/data.py:156` `class Field`

| Prop | Tipo | Valores possíveis | Impacto visual | Impacto processamento |
|---|---|---|---|---|
| `name` | `str` | nome da coluna | — | chave do `Field` |
| `type` | `str` | `TEXT,MEMO,INT,NUM,PERCENT,PK,ID,DK,FK,DATA,DATA_HORA,HORA,BOOL,FONE,CPF,CNPJ,LIST,MULT10,IMAGE` (`FIELD_TYPES`, **19** entradas) | declara qual **input** do catálogo o campo usa (`BOOL`→`checkbox`, `CPF`→`cpf`, `CNPJ`→`cnpj`, `FONE`→`tel`), e o input traz `width`/máscara/validador | `build_field_config` aplica `FIELD_TYPES`; `DK` força `pos_form:0 pos_filter:0` |
| `label` | `str` | texto ou `None` → `_auto_label(name)` | cabeçalho lista/form/report | — |
| `width` | `int` | `ch` (ex: `6` para `ID`, `12` para `NUM`) | largura input/coluna (`field.width+3 ch`, report mm) | `field_to_column` (`core/list.py:184`) calcula |
| `align` | `str` | `left,center,right` (`NUM`→`right` automático `data.py:260`) | `text-align` célula/input | — |
| `input` | `str` | **nome de um tipo** de `ajsystem/defs/inputs.py` (`text,number,date,select,textarea,email,tel,password,checkbox,multi,image,toggle,…`) | resolve o `Input`; o `Field` passa a ler as props dele | `Field.__post_init__` instancia o `Input` — o `core` lê **`f.inp.*`**, nunca `f.input` por string |
| `input_props` | `dict` | override parcial do input **neste campo** (`{'cls':'x','size':9}`) | última camada do merge, acima do app e da rota | `resolve_input(..., overrides)`; chave desconhecida **levanta erro** |
| `options` | `dict` | `{k:label}` para `LIST/MULT10` | `select` options, `tag` texto | `field_filter_options` |
| `mask` | `str` | `@R 999.999.999-99` (CPF), `dd/mm/aaaa`, `@T` title | máscara display/edição (`formats.js:fmtMask`) | `parse_mask_commands`, `width` derivado |
| `placeholder` | `str` | texto | `placeholder` input | — |
| `decimals` | `int` | `0` int, `2` moeda | `data-num-decimals`, `fmtNumBR` | `parseNum` |
| `min`/`max`/`step` | `num` | limites | `input min/max/step` | validação `required` |
| `currency` | `int` | `0` off, `1` R$ pt-BR, `2` $ en-US, `3` € pt-BR (`constants.py:CURRENCY`; ver 5.14) | `itFmtMoney`, símbolo | `normalize_currency` remove o símbolo antes de `itEval` |
| `percent` | `bool` | `True` → `12%` | ` %` sufixo | — |
| `required` | `bool` | `True` → `*` | `*` no label, `required` attr | bloqueia `POST` se vazio |
| `disabled` | `bool\|callable` | `True` ou `callable(row)->bool` (`_financeiro_gerado`) | `disabled` attr | `form_macros.html:55` avalia `callable` |
| `readonly` | `bool` | `True` → sempre readonly | branch `pos_form==2/3/readonly` (`form_macros.html:66`) | `do_form.py:485` skip no `POST` se `readonly` |
| `hidden` | `bool` | `True` → `<input type=hidden>` | oculto mas enviado | `do_form.py:457` `extra_ctx['hidden']` |
| `pos_form` | `int\|dict` | `0` oculto body (visível só em `fields` explícito), `1` visível, `2` readonly sempre, `3` barra/tag, `5` footer, `dict{pos,when}` (`when:{not_empty,empty,field,callable}`) | `init.py:75` `field_body`, `form_macros.html:405` `is_visible_by_pos` | `do_form.py:485` skip no `POST` se barra/readonly |
| `pos_list` | `int` | `0` oculto lista, `1` coluna, `2` card, `3` barra lista | `do_list.py:68` filtra `pos_list != 0` | `do_list.py` filtra `pos_list` |
| `pos_filter` | `int` | `0` sem filtro, `1` texto, `2` select, `3` checklist, `9` fixo (`WHERE default`, força `pos_form0/pos_list0` `data.py:214`) | sem UI quando `9` | `filters.py:114` `fixed_filters` injeta `WHERE` |
| `default` | `any\|callable` | `TODAY` (`date.today`), `lambda:1` | valor inicial | `do_form.py:479` aplica se `None` |
| `rows` | `int` | altura textarea | `rows` attr | — |
| `lookup` | `bool\|dict\|Lookup` | `True` (defaults) ou `{display,fields,value,when,query}` — **sem `model`**, o alvo vem do FK | `select` (1 campo) vs modal busca (>1) | `resolve_lookup` (`data.py:810`) + `apply_lookup_when` |
| `validate` | `str` | `cpf,cnpj,placa` (`validators.js`) | erro client `data-err-for` | `core/validators.py` espelha no `POST` |
| `help` | `str\|list` | texto | botão `?` | — |
| `on_set` | `dict` | `{replaces:{campo:fonte},disables:[...]}` | `data-replaces-map`, `data-disables` | `itOnSetBind` copia `data-*` da option |
| `calc` | `str\|callable\|dict` | `'qtd*preco'`, `lambda row:`, `{'type':'agg','source':'sum(Item.valor)'}`, `{'type':'call','source':'calc_status'}` | `aj-calc` (`data-calc`) ou `readonly` | `calc_value` (`do_form.py:471` `diff` flash), `itEval`/`formCalcRefresh` JS |
| `carry` | `str` | nome campo origem (`carry` map do botão) | — | `do_form.py:618` `carry_get` importa |
| `memory` | `bool` | `True` → campo só de memória: renderiza/editável, **não persiste** e não entra em expansão automática (form principal/list/filtro); só aparece onde citado explicitamente (ex.: `session.fields`) | select FK normal | `_save_session_masters` skip; alvo vem do FK em `resolve_lookup`/`_build_lookup` |
| `tag` | `dict\|Tag` | `{colors, color, link, size, preset, text_field, outline, cls}` | `tag-pill` (`width:width+3ch`, `badge`) ou `badge` lista | `tags.py:86` `resolve_link` (`callable` ok) |
| `_pos_form_when` | `dict` | **interno** — preenchido pelo motor a partir de `pos_form['when']`; não declarar à mão | — | `is_visible_by_pos` |

> `on_set.replaces` alimenta o `lookup` no `resolve_lookup` — é a prop `replaces` do dicionário de lookup, mas **não** uma prop de `Lookup`. Por isso `lookup.model` também não existe: o model alvo é inferido de `fk_target_model` (`data.py:810`).

### 5.2 `Tag` — `ajsystem/defs/tags.py:62` `class Tag`

| Prop | Tipo | Valores | Visual | Processamento |
|---|---|---|---|---|
| `colors` | `dict` | `{valor:cor}` cor `ghost/primary/success/warning/error/info` ou `0-9` (`COLORS_0_to_9`) | `badge-{cor}` | `_resolve_tag_color` |
| `color` | `str` | cor fixa | idem | — |
| `link` | `str\|callable` | `'pedidos.form'` ou `lambda row:'pagar.form' if tipo=='P'` | `<a href=url_for(link,id)>` | `resolve_link(instance)` |
| `size` | `str` | `sm` (default) | `badge-sm` | — |
| `outline` | `bool` | `True` → outline | `badge-outline` | — |
| `preset` | `str` | `boolean,ativo,status` | — | `parse_tag` aplica `PRESETS` |
| `text_field` | `str` | campo de onde vem o rótulo do tag | texto exibido | `parse_tag` |
| `cls` | `str` | classe CSS extra | concatenada ao badge | — |

### 5.3 `Lookup` — `ajsystem/defs/data.py:114` `class Lookup`

| Prop | Tipo | Default | Impacto |
|---|---|---|---|
| `fields` | `str\|list` | `[display]` | `1`→`select`, `>1`→modal busca |
| `display` | `str` | 1º campo após `id` do alvo | `resolve_lookup` monta `path: relacao.display` |
| `value` | `str` | `'id'` | valor retornado e gravado |
| `when` | `str\|dict\|callable` | `None` | `apply_lookup_when` filtra as opções |
| `query` | `str` | `None` | nome de busca declarada na rota (ex.: `'PREVISOES'`) → renderiza display + hidden + botão que abre modal alimentado pelo endpoint do motor, em vez de `<select>` |

> **Não existe `Lookup.model`.** O model alvo é inferido do FK do campo (`fk_target_model`). Para campo `memory`, sem FK, aponte a origem pelo `lookup` do próprio `Field` — não por um `model` no `Lookup`.

### 5.4 `Page` — `ajsystem/defs/pages.py:17` `class Page`

| Prop | Tipo | Default | Impacto |
|---|---|---|---|
| `label` | `str` | `None` | título, `flash_ok` |
| `type` | `str` | `'crud'` | `crud` (lista+form) \| `redirect` \| `cart` \| `showcase` \| `contacts` \| `custom` (`template`) |
| `crud` | `bool` | `True` | `False` não gera `list/form/delete/toggle` |
| `route` | `str` | `None` | subpasta / endpoint; prefixo de `do_page` |
| `template` | `dict\|str` | `None` | `custom`; ex.: `{'type':'markdown','file':'nome'}` |
| `props` | `dict` | `{}` | `form` / `list` / `tabs` / `auth_target` / `on_send` / `target` / **`scripts`** |
| `on_show` | `callable` | `None` | hook executado ao renderizar a página |
| `upload` | `dict` | `None` | política de upload da página; ausente = herda `App.upload` |

**`props.scripts`** (novo) — spec declara só o **nome** do arquivo e o motor monta o caminho:

```python
Page = {'type': 'crud', 'props': {'scripts': ['previsoes', 'rel/gerar']}}
```

→ `static/js/previsoes.js` e `static/js/rel/gerar.js`, resolvidos por `page_scripts` (`data.py:644`) e injetados no ctx como `page_scripts=[{'name','url'}]`. A URL leva **cache-buster por mtime**, então editar o JS dispensa limpeza de cache. Subpastas são permitidas de propósito: é o mesmo caminho de código e evita uma prop separada quando um grupo de helpers crescer.

### 5.5 `Form` — `ajsystem/defs/form.py:55` `class Form`

| Prop | Tipo | Default | Valores | Impacto |
|---|---|---|---|---|
| `fields` | `str\|list\|dict` | `None` | Formatos unificados (resolvidos por `normalize_fieldspec`, 5.13):<br/>`'Entidade'` — expande todos (pos_managed=True)<br/>`['campo1','campo2']` — explícitos (pos_managed=False)<br/>`['Entidade.campo1','Outra.campo2']` — multi-entidade com prefixo<br/>`{'Entidade':['c1','c2'],'Outra':['c3']}` — multi-entidade agrupado | `_pos_managed` controla se `pos_form/pos_list` filtram |
| `sessions` | `dict` | `None` | `{Nome:{fields,table,query,totals,buttons}}` (`fields` 1:1 child vs pai, `table` editável, `query` readonly) | `form.html: sessions` + `item_table.html` |
| `template` | `str` | `None` | path | se setado, ignora `fields` |
| `flash_ok` | `str` | `None` | mensagem de sucesso do save | flash pós-submit |
| `flash_update` | `str` | `None` | mensagem quando o save só atualiza | flash pós-submit |
| `readonly` | `bool\|callable` | `False` | `lambda q: q.pedido_id is not None` | `core/form.py:77` `_is_readonly` desabilita tudo |
| `delete` | `bool\|dict\|callable` | `False` | `True`, `{'when':[Model]}`, `lambda` | `_resolve_delete` + `_when_allows`; `msg_ok`/`msg_no` |
| `pre_save`/`post_save` | `callable` | `None` | `f(instance,request,is_new)` | `do_form.py:536` valida/salva |
| `buttons` | `str\|Button\|list` | `None` | nome de tipo (`'on_off'`, `'delete'`), `{tipo: {overrides}}`, instância `Button` (`BTN_SAVE`, `BTN_PRINT`, `BTN_SEND`…) ou lista de qualquer um | `resolve_buttons` (`defs/buttons.py`); `form.html:nav`/`footer` |
| `spacing` | `num` | `2` | gap entre campos | `render_fields` |
| `max_width` | `num` | `None` | largura máxima do form | `resolve_max_width` |

### 5.5.1 `totals` em sessões `table`/`query`

Totalização opcional da tabela da sessão — editável (`table`) ou readonly (`query`). Aceita:

- **lista de nomes** `['qtd', 'valor']` — soma as colunas na linha de totais;
- **lista mista** `['qtd', {'valor': 'total'}]` — o item string soma só a coluna; o item `dict {coluna: campo_master}` soma **e** grava no `<input name="campo_master">` do master (ex.: `total`);
- **string única** `'valor'` — soma a coluna.

A linha de totais é renderizada no `<tfoot>` da tabela desktop. Colunas `calc` (ex.: `valor = qtd * preco`) usam a própria expressão no total; campos monetários usam a moeda da coluna (`data-total-currency`).

```python
# Orcamento — sessão 'Itens do Orçamento' (table editável)
'Itens do Orçamento': {
    'table': {
        'columns': ['OrcamentoItem'],          # qtd, preco editáveis; valor = calc
        'totals': ['qtd', {'valor': 'total'}], # qtd soma; valor soma e grava no master `total`
    },
},

# Conta — sessão 'Pedidos' (query readonly com grupos)
'Pedidos': {
    'query': {
        'columns': {'Pedido': ['id', 'pedido_em', 'total', 'status']},
        'groups': 'status',                    # agrupa por status (subtotais)
        'totals': ['total',],                  # + total geral no rodapé
    },
},
```

### 5.6 `List` — `ajsystem/defs/list.py:15` `class List`

| Prop | Tipo | Default | Impacto |
|---|---|---|---|
| `fields` | `list[Field]` | — | colunas; o motor resolve via `normalize_fieldspec` antes de criar o `List` |
| `fields_master` | `list[int]` | — | **computado** — índices de `fields` que são colunas da linha (as demais vão para o card) |
| `edit_endpoint` | `str` | `None` | endpoint do ícone de editar; `None` esconde a ação |
| `edit_id_field` | `str` | `'id'` | campo usado na URL de edição |
| `detail_data` | `str` | `None` | fonte dos campos de detalhe do card |
| `buttons` | `str\|Button\|list` | `None` | mesmos formatos de `Form.buttons` | `List.resolve_buttons` |
| `template` | `str` | `None` | template alternativo |
| `master` | `list` | `None` | colunas da linha mestre |
| `linha` | `list[int]` | `None` | **computado** — o autor declara `linha: ['nome','data']` com **nomes**; `do_list.py:300` converte para índices |
| `card_idx` | `list[int]` | `None` | **computado** — índices de `fields` que caem no card |

> `fields_master`, `linha` e `card_idx` saem do `do_list.py` (`list_obj = List(...)`, `do_list.py:312`). **Não** os declare à mão: a engine sobrescreve. `linha` é a única que aceita nomes na spec, porque a conversão acontece no meio do caminho.

> `columns` da página (`Page.props.list`) aceita query dict no lugar da entidade (`columns=QPLANO`, ver 5.10.1): os dados vêm do `qrun` e `pos_list` da entrada vale (Schema vence). Com ordem própria, a query entra como item da lista (`columns=[QPLANO, 'id', 'indice', ...]` — no máximo uma query por lista; strings autoritativas, fora do `select` quebra nomeando). Nesse modo `field_id` é exigido para editar (ausente = só-leitura; declarado tem que estar no `select` e ser pk, senão quebra nomeando). Sem query, `edit_id_field` (`'id'`) e o resto seguem como antes.

### 5.7 `Report` — `ajsystem/defs/report.py:135` `class Report`

| Prop | Tipo | Default | Valores | Impacto |
|---|---|---|---|---|
| `label` | `str` | — | título | cabeçalho do PDF |
| `page_size` | `str` | `'A4'` | `'A4'`, `'Letter'`… | `fpdf` |
| `orientation` | `str` | `'portrait'` | `'portrait'`, `'landscape'` | `fpdf` |
| `orientation_mutable` | `bool` | `False` | `True` → o usuário gira a página na tela | página de impressão |
| `header` | `dict\|list` | `None` | `{logo, title, fields:[...]}` (legado) ou `[...]` (5.8.1, `LOGO`/`TITLE`/`FIELD`/…) | `do_report.py:_apply_entity` resolve `label` via `Entity`; dict legado sintetiza a lista |
| `body` | `dict\|ReportBody` | `None` | ver 5.8 | fonte dos dados |
| `footer` | `dict` | `None` | `{show_user, show_datetime, show_page_number}` | rodapé do PDF |
| `texts` | `dict\|list` | `None` | `ReportText` — ver 5.8 | blocos de texto avulso |
| `print_template` | `str` | `'components/print_default.html'` | caminho | página standalone (`print_report_page`) |
| (fragmento) | — | overlay do framework (`print_overlay.html`) | fixo no motor | `print_report` injeta sempre com alternância do container; a chave legada `print_fragment_template` é ignorada no parse |
| `logo_path` | `str` | `'static/icons/Logo.png'` | caminho | logo do cabeçalho |
| `margin_top`/`margin_bottom`/`margin_left`/`margin_right` | `num` | `10` / `20` / `10` / `10` | mm | margens do PDF |
| `auto_page_break` | `bool` | `True` | quebra automática de página | `fpdf` |
| `show_table_lines` | `bool` | `False` | grade da tabela | `fpdf` |

Chaves de `body` e `filter` (usadas no exemplo abaixo) resolvem contra o `Entity` do módulo:

| Chave | Tipo | Valores | Impacto |
|---|---|---|---|
| `body.source` | `str\|dict` | `'Tarefa'`, `{'entity':...}` (legado) ou query dict `{select,dist,from,...}` (5.10.1) | `_infer_source` + `_auto_data`; query numera tudo e filtra depois (índice global estável) |
| `body.table.columns` | `dict\|list` | `{'titulo':{'width':50}}` ou `['indice','nome',{'id':{'width':6}}]` (forma enxuta igual ao `select`) | `_apply_entity` herda `label`/`calc` da `Entity` (Schema vence); coluna computada na query usa o attr direto |
| `body.table.groups` | `dict\|list` | `{'tipo':{action:1,print:3,text:'{tipo:d}. {tipo}'}}` | control-break: `action` (quando: 1 abre, 2 fecha, ausente = toda linha) × `print` (onde: 0 nunca, 1 coluna, 2 linha, 3 fora da tabela). Legado `{print,place}` traduzido via shim. `order` da fonte tem que abrir com as quebras (senão quebra nomeando). `totals` no grupo = subtotal (`{'label','align','span'}`; ausente = não totaliza) |
| `when` (item) | `str` | `{'TEXT': {'text': '…', 'when': 'evento.tipo'}}` | imprime só se o path (pontilhado ok) for truthy; ausente = sempre |
| templates | — | `'{total:brl}'`, `'{a.b}'`, `'{?c:…}'`, `'{x\|dflt}'` | `:brl` moeda; path pontilhado com navegação segura; `\|dflt` fallback; labels LIST da Entity |
| fluxo | — | `FIELD`/`TEXT` seguem na linha | `PCOL` avança pela largura; `pcol+largura>ncol` envolve; maior que a linha trunca; quebra por `rows_after/before` ou posicionamento; sem âncora volta à margem |
| `body.table.totals` | `dict` | `{'label':'TOTAL GERAL','align':'R','span':3}` | linha de total geral (sempre). `agg` na coluna diz O QUÊ; sem `totals` não totaliza. Legado `footer/footer_label` via shim |
| `body.table.hierarchy` | `list\|dict` | legado (derivado de `groups` quando ausente) | mantido por compat; prefira `groups` |
| `body.filter` | `dict\|callable` | `filter_select('tipo')` | modal `choice_modal` + `WHERE` com cast tipado; critério aplicado **antes** da ordenação |

### 5.8 `ReportColumn` e amigos — `ajsystem/defs/report.py`

**`ReportColumn`** (`:34`) — 9 props (novas: `text`, `suppress`):

| Prop | Tipo | Default | Valores | Impacto |
|---|---|---|---|---|
| `field` | `str` | — | `'qtd'` ou `'produto.nome'` | `data_key` |
| `label` | `str` | `None` | texto; sem ela, `_auto_label`/Entity/entrada do `select` | cabeçalho da coluna |
| `width` | `float` | `None` | `ch`/`mm` | coluna no PDF |
| `align` | `str` | `'left'` | `left,center,right` | herdado do `Field.align` (`NUM`→`right`) |
| `format` | `str` | `None` | formato de data/número | render da célula. Sem `format` declarado nem inferido, a `mask` da Entity/catálogo manda (genérico: tel/CPF/data) — `format` do relatório vence a máscara, máscara vence inferência |
| `agg` | `str` | `None` | `sum/count/avg/min/max` | O QUÊ somar (só impressão; o ONDE vai em `totals`) |
| `function` | `callable` | `None` | `lambda row:` | usa `Entity.calc` se ausente (coluna computada na query usa o attr) |
| `text` | `str` | `None` | template `'{campo}'`/`{x:02d}`/`{?cond:…}` (6, `core/text.py`) | monta a célula (ex. código) |
| `suppress` | `bool` | `False` | repete valor só na 1ª linha do grupo | `place:0` do `groups` |

**`ReportField`** (`:13`) — 5 props, spec de campo solto (fora de `columns`): `field`, `label`, `align` (`left`), `format`, `function`.

**`ReportGroup`** (`:66`) — 7 props: `field`, `label`, `position` (`titulo`), `subtotal` (`True`), `total` (`True`), `fecha_tabela` (`False`), `nova_pagina` (`False`). Agrupa linhas por campo; `position` decide se o rótulo entra como título de página (`titulo`) ou como linha da tabela.

**`ReportText`** (`:78`) — 5 props: `text` (obrigatório), `font_size` (`10`), `font_style` (`''`), `align` (`'L'`), `when` (`end_of_report`; também `start_of_report`/similar). Bloco de texto avulso, usado por `Report.texts`.

**`ReportBody`** (`:88`) — 8 props: `source`, `form`, `table`, `before`, `after`, `filter`, `levels`, `items`. `before`/`after` inserem blocos ao redor da tabela; `levels` é numeração hierárquica legada (prefira `select` com `over` + `table.groups`); `items` = lista unificada abaixo.

#### 5.8.1 Items de impressão (`header=[...]`, `body.items`)

String pura ou dict unitário = `FIELD`; MAIÚSCULA = elemento (`None` = nu). Factories puras (`defs/report.py`, tradução 1:1 validada pelo mesmo normalizador):

| factory | equivale a | exemplo |
|---|---|---|
| `'nome'` / `{'total': {...}}` / `FIELD(nome, props?)` | `FIELD` | `'cliente_nome'`, `FIELD('data_pedido', {'tab': 2})` |
| `TITLE(texto?, props?)` | `{'TITLE': {'text': texto, ...}}` | `TITLE()` = nu (texto = `label`, sempre centrado salvo `align`); `width` em cols (sem = até o fim da linha) |
| `TEXT(texto, props?)` | `{'TEXT': {'text': texto, ...}}` | `TEXT('Obs: …', {'before': 1})` |
| `LOGO(ancora, linhas)` | `{'LOGO': {'location': [ancora, linhas]}}` | `LOGO('C', 4)` (âncoras `C/L/R`; ausente não renderiza) |
| `TABS(*paradas)` | `{'TABS': [...]}` | `TABS(PCOL, PCOL+20)` (crescente; com `tab:N` no item) |
| `POS(col, lin)` | salto avulso do cursor | `POS(22, 0)` |
| `PROW`/`PCOL` | constantes (`defs/report.py`) | posição corrente em grade, em `pos`/`location`/`TABS` (só literais; `PCOL±N` só em `TABS`) |
| `LINE/BOX/CIRCLE(loc, props?)` | `{'LINE': {'location': loc, ...}}` | `LINE([10, 5, 20])` (horizontal; `[c,r,0,h]` vertical) |
| `IMAGE(campo, props?)` | `{'IMAGE': {'field': campo, ...}}` | `IMAGE('foto', {'location': [...]})` |
| `FIELDS(modelo\|lista, when?)` | expande em `FIELD`s (relação navegada ou instância) | `FIELDS('Evento', when='evento')` (sem lista = todos da Entity; `when` = path truthy, ausente = sempre) |

### 5.9 `Button` — `ajsystem/defs/buttons.py:85` `class Button`

O destino do clique é **exatamente um** entre `action`, `url` ou `render`.

| Prop | Tipo | Default | Valores | Impacto |
|---|---|---|---|---|
| `label` | `str` | — | constante de `ajsystem.locales` | **texto final** do locale ativo; `btn.text()` é pass-through |
| `title` | `str` | `''` | constante de `ajsystem.locales` | nome acessível e tooltip; `title_or_label()` cai no `label` quando vazio |
| `icon` | `str` | `None` | nome de ícone | ícone do botão |
| `color` | `str` | `'secondary'` | `primary/secondary/success/warning/error/info` | `btn-{color}` |
| `variant` | `str` | `'outline'` | `outline`, `solid`, `ghost` | `btn-outline` / `btn-{color}` / `btn-ghost` (o `ghost` **ignora** a cor) |
| `size` | `str` | `'sm'` | `xs,sm,md…` | `btn-{size}` |
| `cls` | `str` | `''` | classe extra; **anula** `color`/`variant`/`size` | `btn.btn_cls()` |
| `visible` | `bool\|callable\|tuple\|dict` | `True` | | decide a renderização, **no servidor, 1×** |
| `enabled` | `bool\|list\|dict` | `True` | | decide o `disabled`; reavaliado **no cliente** a cada `input`/`change` |
| `enabled_fields` | `list` | `[]` | nomes dos campos observados | `enabled_mode` |
| `enabled_mode` | `str` | `'all_filled'` | `all_filled`, `any_filled`… | regra de habilitação |
| `action` | `str` | `''` | nome de função JS global | `onclick="fn(this)"` |
| `url` | `str\|callable` | `''` | nome de endpoint, ou callable que devolve URL | `url_for(...)` |
| `render` | `callable` | `None` | devolve HTML | injetado em `into` |
| `into` | `str` | `''` | seletor/alvo | vazio = `REPORT_CONTENT` (ver `target_into`) |
| `url_params` | `dict\|callable` | `None` | query params | `url_for(..., **params)` |
| `method` | `str` | `'GET'` | `GET`/`POST` | método do form gerado |
| `confirm_msg` | `str` | `None` | constante de `ajsystem.locales` | modal de confirmação; `btn.confirm_text()` é pass-through |
| `carry` | `dict` | `None` | `{campo_destino: campo_origem}` | importa valores do form ao navegar |
| `serialize` | `bool` | `False` | | serializa o form antes de enviar |
| `position` | `str` | `'top_right'` | `POSITION_CONTEXT` — `left`, `right`, `before`, `after`, `top_left`, `top_right`, `bottom_left`, `bottom_right` | ver abaixo |

`resolve_buttons(specs, bp_name, *, where, valid_fields, sess, ctx)` recebe uma **lista** de specs; cada item pode ser instância `Button` (os tipos derivados e `BTN_PRINT`/`BTN_SEND` já são `Button`), nome de tipo (`'delete'`), `{nome: {overrides}}` ou dict custom. Toda chave é validada — chave desconhecida, destino ambíguo (`action`+`url`) ou campo inexistente em `enabled` **levanta erro** em vez de ser descartado em silêncio. Instâncias são copiadas com `replace()` porque a validação normaliza `enabled`/`field`/`url` in-place: sem a cópia, o preset compartilhado seria contaminado pelo primeiro registro que o usasse.

**Catálogo de tipos** — a aparência mora num só lugar, e `resolve_buttons` monta o resultado em camadas:

```
GENERICOS[base]  <  app.botoes.Buttons  <  Buttons da rota  <  spec do uso
```

- **`BUTTON_TYPES`** (`ajsystem/defs/buttons.py:330`) tem 40 entradas, **todas genéricas** — o framework não conhece nenhum botão de app. Cada entrada é a aparência completa de um tipo (dict literal).
- **`type`** — a entrada do host declara de qual genérico diverge. Sem `type`, a base é o tipo de **mesmo nome** (o caso de sobrescrever `delete`); com `type`, o app nomeia um botão seu e declara só o que muda. `type` apontando para tipo inexistente **levanta erro dizendo o nome** — não vira `label faltando` mais tarde.
- **override parcial** — a entrada do host é parcial de propósito. `{'delete': {'color': 'warning'}}` troca a cor e **mantém** o `label`/`icon`/`confirm_msg` do tipo.
- **`build_catalogo(*camadas)`** é a função que faz o merge, com um argumento por camada do host, cada uma sobrepondo a anterior; `None`/`{}` são ignorados. Nenhuma camada muta `GENERICOS`.
- **`Buttons` da rota** é a variável de módulo que a rota declara, lida por `module_buttons` — o mesmo papel que o `Schema` dela tem sobre os campos. É onde vive o botão que só aquela rota usa, e é o que permite a spec ser **uma lista de nomes**. A camada entra depois do app, então a rota também pode sobrescrever um botão do app só naquele form.
- **`report` + `filter_field`** na entrada do catálogo substituem as factories `BTN_PRINT`/`BTN_SEND` no ponto de uso: `render`, `into` e o `guard` padrão (`_has_items`) saem sozinhos, e o que fica escrito é só a aparência que diverge do tipo `print`. `BTN_PRINT`/`BTN_SEND` continuam existindo para o `guard` customizado e para compatibilidade.
- **`enabled`/`carry`/`url`/`position` não moram no catálogo genérico nem no do app**: dependem do form e do registro, então ficam no ponto de uso. No `Buttons` da rota eles podem — a rota já é o ponto de uso.

```python
# framework — só genéricos
BUTTON_TYPES = {'generate': {'label': i18n.GENERATE, 'color': 'success', 'variant': 'solid'}, …}

# framework — o que o motor procura pelo nome (hoje: o toggle)
Buttons = {'on_off': {'label': i18n.ACTIVATE, 'icon': 'check', 'on_off': True, …}}

# app/extends/buttons.py — o que o app repete em 2+ forms
Buttons = {'gerar_financeiro': {'type': 'generate', 'icon': 'currency-dollar', 'variant': 'outline'}}

# route — o `Buttons` dela (mesmo papel do `Schema` dela)
Buttons = {
    'enviar_orcamento': {'type': 'print', 'report': ORCAMENTO, 'label': i18n.SEND,
                         'icon': 'paper-airplane', 'color': 'success',
                         'position': 'top_right', 'visible': _editavel},
}

# route — e a spec vira só a lista dos nomes que este form usa
'buttons': ['enviar_orcamento', 'renovar_orcamento']
```

Toda entrada de `GENERICOS` ganha sua constante `BTN_<NOME>` por loop, e as globais Jinja saem daí por varredura de prefixo (`BTN_*`, `CONFIRM_*` em `ajsystem/init.py`) — por isso um tipo novo não toca lista de importação. `print` vira `BTN_PRINT_STYLE`, porque `BTN_PRINT` é nome da factory de relatório.

**`position`** — são 8 nomes, e o *mesmo* nome se comporta de forma diferente conforme o contexto que vai renderizar o botão. `_check_position` valida contra a tabela do contexto e **levanta erro** em valor fora dela (nada de sumir em silêncio). O contexto da sessão é decidido pelo formato dela: havendo `fields`, o botão pertence ao bloco de `fields` (mesmo que a sessão também traga `table`/`query`, como em `Financeiro`); sem `fields`, pertence à tabela.

| `position` | form | sessão com `fields` | sessão só com `table`/`query` |
|---|---|---|---|
| `left` | erro | mesma linha, à esquerda dos fields | erro |
| `right` | erro | mesma linha, à direita dos fields | erro |
| `before` | erro | faixa acima dos fields | faixa acima da tabela |
| `after` | erro | faixa abaixo dos fields | faixa abaixo da tabela |
| `top_left` | barra de cima, à esquerda | faixa acima, à esquerda | faixa acima da tabela, à esquerda |
| `top_right` | barra de cima, à direita | faixa acima, à direita | faixa acima da tabela, à direita |
| `bottom_left` | rodapé do form, à esquerda | faixa abaixo, à esquerda | **faixa de ação: `+ Adicionar` primeiro, depois o botão** |
| `bottom_right` | rodapé do form, à direita | faixa abaixo, à direita | faixa de ação, encostado à direita |

`before`/`after` são os atalhos sem alinhamento de `top_left`/`bottom_left`. A **faixa de ação** fica dentro do `.child-table-wrap` e **fora** do `<tfoot>` (a tabela pode ter linha de totais, e a largura de colunas do Adicionar não é a delas) e **fora** de `.it-desktop`/`.it-mobile` — por isso o `Adicionar` é renderizado uma vez só e `btn.closest('.child-table-wrap')` funciona nos dois tamanhos de tela. Listagem não usa `position`.

Presets são registrados automaticamente como globais Jinja por varredura de prefixo (`BTN_*`, `CONFIRM_*` em `ajsystem/init.py`).

**`ConfirmModal`** (`:253`) — 6 props: `title` e `message` (constantes de `ajsystem.locales`, obrigatórios), `confirm_label` (`CONFIRM`), `confirm_color` (`'danger'`), `cancel_label` (`CANCEL`), `icon` (`'trash'`). Lectores: `text()`, `message_text()`, `confirm_button_text()`, `cancel_button_text()` — todos pass-through (ver 5.12). Presets: `CONFIRM_DELETE`, `CONFIRM_REMOVE_ITEM`.

**Factories** — duas, mesma assinatura `(report, *, filter_field='', guard=None, **overrides)`:

```python
BTN_PRINT(report, filter_field=None, guard=None)   # ícone printer, cor info
BTN_SEND(report,  filter_field=None, guard=None)   # BTN_PRINT com ícone paper-airplane, cor success

# No spec — report é o dict/Report, não um id:
'buttons': [BTN_PRINT(PEDIDO)]
'buttons': [BTN_PRINT(PLANO, filter_field='tipo', label='Plano')]
'buttons': [BTN_SEND(COMPRA), BTN_SEND(ORCAMENTO, guard=lambda c: c.finalizado)]
```

Sem `filter_field`, imprime para a instância (shape documento). Com `filter_field='tipo'`, imprime o relatório da seleção de filtro corrente (shape listagem) e o `guard` não se aplica. `**overrides` chega ao `Button` e o `replace` recria `cls` a partir da nova cor via `btn_style()`. `print_report` entra por import tardio dentro da closure — é o que mantém `defs/buttons.py` livre do **motor de renderização** (`core/do_report`, `core/pdf`) no import de módulo.

Substituem o antigo `app/utils.btn_enviar_report` e a constante `REPORT_CONTENT`, que foram removidos do app. `REPORT_CONTENT` (`'#report-content'`) agora vive no framework e é o destino padrão de `Button.into`.

O par mora em `ajsystem/defs/report.py` (`REPORT_ID` cru + `REPORT_CONTENT` derivado), não em `defs/buttons.py` — a constante descreve o container do relatório, e o botão só a consome como default. `init.py` expõe as duas como globals Jinja, então `sys.html` e `print_overlay.html` leem `{{ REPORT_ID }}` / `{{ REPORT_CONTENT }}` em vez de repetir o literal. Isso fecha o contrato de três lados (Python, HTML e JS): se o id divergisse em algum deles, o botão renderizaria o HTML sem o JS reconhecer o destino, e o relatório apareceria sem esconder a página nem reexecutar os scripts do fragmento.

### 5.9.1 `Input` — `ajsystem/defs/inputs.py` `class Input`

Gêmeo de `Button`, para o outro lado do formulário: enquanto o botão descreve *o que acontece*, o input descreve *como o valor entra e volta*. Antes, cada editor era um `if field.input == '...'` espalhado por `core/list.py`, `core/form.py`, `core/do_form.py`, `core/do_upload.py` e `defs/transformers.py` — o `core` conhecia os nomes do catálogo, e adicionar um editor era editar cinco arquivos. Agora a escolha do editor é uma prop, e o `core` só lê `f.inp.*`.

| Prop | Tipo | Default | Papel |
|---|---|---|---|
| `html_type` | `str` | `''` | atributo `type` do `<input>` (vazio = o template escolhe) |
| `inputmode` | `str` | `''` | dica de teclado no mobile (`decimal`, `numeric`) |
| `cls` | `str` | `'input input-bordered input-sm'` | classe do controle |
| `size` | `int` | `18` | largura em `ch`; vira `Field.width` quando o campo não declara |
| `align` | `str` | `'left'` | `text-align`; `'right'` do input vence o `'left'` do campo |
| `slot` | `str` | `'body'` | `body` no corpo do form, `bar` na barra — `bar` **exige** `pos_form: 3` |
| `boolean` | `bool` | `False` | valor é booleano; ausência no POST = `False` |
| `number` | `bool` | `False` | formatado por `fmt_num`/`fmt_id` |
| `multi` | `bool` | `False` | lista de opções marcadas |
| `masked` | `bool` | `False` | o texto passa por `mask`/`mask_cmd` |
| `textual` | `bool` | `True` | texto livre — só isso aceita transform `@U/@L/@C/@T` |
| `filter_kind` | `str` | `'text'` | editor de filtro da listagem: `text/boolean/date/number/select` |
| `upload` | `bool` | `False` | o valor é o nome de um arquivo enviado |
| `mask` | `str` | `''` | máscara default; o `Field` vence |
| `validate` | `str\|list` | `None` | validador default; o `Field` vence |
| `mask_group` | `str` | `'text'` | comandos `@X` liberados: `text` (`ULCTR`), `number` (`BX`), `*` |
| `route` | `str` | `''` | sufixo do endpoint — `''` grava no POST do form |
| `method` | `str` | `'GET'` | verbo do endpoint |
| `label_on`/`label_off` | `str` | `''` | rótulos do toggle (title/`aria-label`) |
| `badge_off` | `str` | `''` | badge mostrada quando o valor é falso |
| `endpoint` | `str` | `''` | **interno** — resolvido no `Form.resolve` (blueprint + `route`) |

**Camadas** — mesma regra e mesma mensagem de erro dos botões:

```
INPUTS[base]  <  app.inputs.Inputs  <  Inputs da rota  <  input_props do campo
```

- **`INPUT_TYPES`** (`ajsystem/defs/inputs.py:129`) tem 13 entradas genéricas (`text`, `textarea`, `email`, `tel`, `password`, `number`, `select`, `checkbox`, `multi`, `date`, `datetime-local`, `time`, `image`). O framework não conhece `cpf` nem `cnpj` — são domínio.
- **`Inputs`** (mesmo arquivo) é a camada do **motor**: só o `toggle`. A entrada diverge de `checkbox` declarando `type: 'checkbox'`, e acrescenta `slot: 'bar'`, `route: 'toggle'`, `method: 'POST'`, `label_on`/`label_off` e `badge_off`. `INPUTS` é a soma das duas, já com o `type` resolvido.
- **`type`** é metadado de qual base usar e sai do merge. Base inexistente **levanta erro dizendo o nome**; entrada sem `type` e com nome novo **também**, porque todo tipo do app diverge de um genérico.
- **`App.inputs`** (`app/config.py` → `build_app(inputs=…)`) é a camada do app, lida por `core/adapter.py` e fixada como default de processo por `definir_camadas_padrao` no `init.py` — antes de `registrar_modulos`, porque o `Entity` já é expandido no import do model. É onde `cpf`/`cnpj` e a máscara do telefone BR ganham forma: `app/extends/inputs.py`, gêmeo de `app/extends/buttons.py`.
- **`Inputs` da rota** é a variável de módulo lida por `module_inputs`, no mesmo papel que `Schema` e `Buttons` têm na sua rota. A listagem resolve as mesmas camadas por `_camadas_inputs`.
- **`input_props`** é a última camada e vale só para aquele campo: `{'type': 'BOOL', 'input_props': {'cls': 'meu-toggle'}}`. Chave que não existe em `Input` **levanta erro** com a lista das válidas.

**Resolução** — `Field.input` continua sendo `str` (o *nome* do tipo, porque é isso que o `Schema` e o spec referenciam); o objeto resolvido é `Field.inp`. A resolução é **eager**, no `Field.__post_init__`, e não preguiçosa: `mask`, `validate`, `width` e `align` são computados ali, e um input resolvido depois deixaria a máscara de fora. O `Field` ainda valida três pares que não podem divergir: input de `slot='bar'` sem `pos_form: 3`, comando de máscara não liberado pelo `mask_group`, e `@U/@L/@C/@T` combináveis entre si (são exclusivos).

**Toggle** — `{'type': 'BOOL', 'input': 'toggle', 'pos_form': 3}` no model. Renderiza no rodapé do form (`form_macros.html:render_toggle_field`), **fora** do `<form id="main-form">`, porque cada um é um POST próprio. O endpoint é genérico — um por módulo, em `POST /<rota>/<id>/toggle/<campo>` — e valida o `<campo>` da URL contra `Form.toggle_fields` (os campos cujo input declara `route`), então um POST não escolhe coluna arbitrária do model para inverter. É POST e não GET porque muda dados: GET mutante quebra o cache do navegador, o prefetch de link e o back/forward. Respondendo a HTMX, devolve `204` + `HX-Refresh`; fora dela, `302` para o form.

Presets `IN_TEXT`, `IN_TOGGLE`… são gerados em loop a partir de `INPUTS` e publicados como globals Jinja no `init.py` (mesma ideia dos `BTN_*`). São o preset do **framework**; quem customiza escreve `input_props` no campo, que é a última camada do merge e por isso não pode ser enganado por um global.

### 5.9.2 Predicados de valor — `ajsystem/core/utils.py`
O que decide se um campo "tem valor" são três funções, e confundir duas delas quebra formulário. Todas em `core/utils.py` (dependência permitida de `defs/`, por `defs/__init__.py`).

| Função | True para | Usada por |
|---|---|---|
| `is_null(v)` | só `None` (o NULL do banco) | base das outras duas |
| `is_empty(v)` | `None`, `''`, só espaços, coleção vazia | `required` (`do_form.py`), condição de campo `when` (`defs/data.py`) |
| `is_zero_or_empty(v)` | `is_empty` **mais** qualquer número com `\|v\| <= ZERO_EPS` | `Button.enabled` (`defs/buttons.py`, `init.py`) |

`ZERO_EPS = 0.005` existe para que um total de `0,004` vindo de arredondamento não habilite "Enviar relatório". `as_num(v)` é o leitor que faz `'0,00'` → `0.0`; espelha o `parseNum` de `static/js/formats.js` para que Python e JS leiam o mesmo texto.

**Por que `0` não é vazio em `is_empty`:** um campo preenchido com `0` é um valor deliberado, não ausência. Dar a tolerância a `is_empty` quebraria `do_form.py`: a linha 220 grava `False` no checkbox da linha nova e a 221 usa `is_empty` para detectar a linha em branco — com `False` contando como vazio, a linha nunca seria salva. Daí `is_zero_or_empty` ser função separada, e não uma fusão.

O lado do cliente espelha `is_zero_or_empty` em `sys.html` (`IT_EPS`, `itZeroOrEmpty`, `itFilled`, `itEnabledEval`). `IT_EPS` e `ZERO_EPS` são dois literais acoplados: mudar um sem o outro deixa o `disabled` do servidor e o do cliente discordarem.

Em `init.py`, os dois nomes viram filtros Jinja para não tocar nos templates: `btn_empty` = `is_zero_or_empty` e `btn_filled` = a negação. Não há predicado "preenchido" — é `not is_zero_or_empty(v)`.

### 5.10 `Query`, `Table` e `Session` — `ajsystem/defs/data.py`

**`Query`** (`:95`) — 6 props, fonte de dados **readonly** de sessão ou relatório: `columns`, `join`, `when`, `groups`, `order`, `totals`.

**`Table`** (`:106`) — 3 props, variante **editável**: `columns`, `order`, `totals`.

**`Session`** (`:136`) — 4 props: `template`, `fields`, `query`, `table`. É a spec da sessão dentro de `Form.sessions`; `fields` é a relação 1:1 child↔pai e `query`/`table` o corpo.

### 5.10.1 QSpec — query declarativa SQL-like (`ajsystem/defs/qspec.py`, `core/qrun.py`, `core/text.py`)

`QuerySpec` com as props na ordem do SQL — `select, dist, from, join, where, groups, order, limit` — executada por `qrun.run_query`: WHERE/ORDER/LIMIT/GROUP BY no banco, `OVER` em passo único (1 query, sem N+1), `calc` depois, ordenação final incluindo computados, com cast tipado e nulo-primeiro no asc. Entrada do `select` espelha o `Field` (`field/agg/func/over/calc/pos_list/label/width/align/format`, sem sub-dict); `over` exige `func` explícito do catálogo (`rownumber/rank/denserank/…`) e `order` aceita expressão do registro `EXPR_FUNCS` (só `coalesce` liberado). Templates (`calc`, coluna `text`, `group text`) falam a mesma língua (`core/text.py`): `'{campo}'` label, `'{x:02d}'` cru, `'{?campo:literal}'` ternário sem `else`. `PivotSpec` (`src/lines/columns/aggs/filters`) declarado, executor pendente.

### 5.11 `App`, `Module`, `MenuItem`, `Tema`, `Layout*` — `ajsystem/defs/config.py`

> **Exceção à convenção:** `config.py` é o único módulo do framework com props em **português** (`Tema.rotulo/marca/neutras/...`, `Module.default_path`, `MenuItem.submenus`, `Layout*.rows/align/text/font/color/logo/title/user`). Todo o resto do framework é em inglês.

**`App`** (`:138`) — 9 props:

| Prop | Default | Impacto |
|---|---|---|
| `name` | — | nome do app |
| `logo` | — | caminho do logo |
| `tema` | — | `Tema` |
| `title` | `None` | título padrão de página |
| `version` | `None` | sub-dict `{cycle, year, month, number}` (ex.: `{'cycle': 1, 'year': 26, 'month': 10, 'number': 10}` → `'1.26.10-010'`); `build_version` valida as partes, `Version.text()` compõe no rodapé |
| `upload` | `None` | política padrão de upload (páginas herdam) |
| `botoes` | `None` | catálogo do host (`app.extends.buttons.Buttons`); `None` = só genéricos |
| `inputs` | `None` | catálogo do host (`app.extends.inputs.Inputs`); `None` = só genéricos |
| `modules` | `[]` | `Module`s do menu |

**`Module`** (`:120`) — `type` (`'public'`), `default_path`, `menus` (`MenuItem`s), `triggers`, `layout`.
**`MenuItem`** (`:67`) — `page`, `url`, `icon`, `submenus`.
**`Tema`** (`:16`) — `base`, `rotulo`, `marca`, `neutras`, `feedback`, `apoio`, `barras`, `modal` (paleta daisyUI/Tailwind).
**`Layout`** (`:60`) — `header` (`LayoutHeader`), `footer` (`LayoutFooter`); `LayoutHeader` tem `logo` (`LayoutLogo`: `rows` 5, `align` center) e `title` (`LayoutTitle`: `text`, `align`, `font`, `color`); `LayoutFooter` tem `font`, `color`, `user` (`True`).

### 5.11.1 Overrides do host — `app/extends/`

O que estende ou sobrescreve o framework mora numa pasta exclusiva do app, com os **mesmos nomes do framework em inglês**: `buttons.py` espelha `ajsystem/defs/buttons.py`, `inputs.py` espelha `ajsystem/defs/inputs.py`, `constants.py` espelha `ajsystem/defs/constants.py`, `utils.py` espelha `ajsystem/core/utils.py`. `app/config.py` fica na raiz (documento-raiz do app, lido pelo adapter e pelos models).

O motor **antecipa** esses arquivos: `core/adapter.py:_override_ou(caminho, atributo, default)` verifica a existência com `find_spec` **sem executar nada** e só importa havendo arquivo. As três situações:

| Situação | Comportamento |
|---|---|
| arquivo ausente | `default` do framework, boot normal |
| arquivo presente | vale o atributo do host |
| arquivo presente mas com erro interno | o erro original propaga — `find_spec` distingue "não existe" de "existe e quebrou", então um `except ImportError` genérico (que engoliria um typo e bootaria com default em silêncio) não é usado |
| arquivo presente sem o atributo | `ImportError` nomeando o que falta (fail-fast; silêncio esconderia variável renomeada) |

Só `extends/buttons.py` (`Buttons`) e `extends/inputs.py` (`Inputs`) passam pelo loader — são os únicos que o framework importa. `extends/constants.py` e `extends/utils.py` são só do app (o framework nunca os importa), e `app.config` + models continuam obrigatórios: sem eles não há boot.


### 5.12 Locales — `ajsystem/locales/`

Cada idioma é um módulo irmão com os **mesmos nomes** de constante. O app declara o ativo e o pacote importa o catálogo **na carga**: não existe chave de tradução nem função de tradução no caminho.

| Peça | Papel |
|---|---|
| `APP['locale']` (`app/config.py`) | declara o idioma (`'pt'` por padrão); **não** é prop do `App` |
| `locales/__init__.py` | lê a declaração, importa o catálogo e reexporta as constantes |
| `locales/en.py` / `locales/pt.py` | 146 constantes, mesmos nomes, **mesma ordem** |
| `i18n = locales` | o módulo: `i18n.SAVE` → `'Salvar'` |
| `locales.LOCALE` | o idioma ativo, congelado na carga |
| `locales.disponiveis()` | lista os catálogos que acompanham o framework |
| `locales.herdar_catalogo(globals())` | API de "superset" do motor p/ host que quiser texto próprio: copia as constantes e permite redeclarar as que diferem (opcional) |

Nos templates, `init.py` injeta **um** global `i18n` (o catálogo): `{{ i18n.SAVE }}`. Um global só, em vez das ~146 constantes soltas, porque nomes em caixa alta no namespace do Jinja podem sombrear variável de contexto. A contagem de 158 da versão anterior flutuou: nomes repetidos foram mesclados (`UI_SIGN_OUT`→`EXIT`…), o prefixo `UI_` saiu, e a storefront (vitrine/carrinho/nav) entrou como parte do motor — o catálogo é a coisa única de texto do Page que o framework entrega.

**Por que "no import" e não "na tradução".** Um catálogo importado congela na carga. Nenhum texto é traduzido durante a execução, então nada pode capturar a linguagem cedo demais e virar literal solto por acidente — o bug de `t()` em nível de módulo, que a versão anterior proibia por regra. O preço é que **o idioma não muda em runtime**: o app é monolingue, e trocar é uma linha em `app/config.py` mais um reinício, não um fork.

**Consequências práticas:**

1. `Button.label`, `ConfirmModal.title/message/confirm_label/cancel_label` e `Button.confirm_msg` **já são o texto final** do locale ativo. `btn.text()` e `btn.confirm_text()` viraram pass-through (`return self.label`): o método sobrevive porque `label` é o contrato — o app pode escrever o texto dele direto (`label='Plular'`) e o template não precisa saber a diferença.
2. **Paridade é obrigatória.** Nome que existe em `en.py` e falta em `pt.py` estoura `ImportError` na carga. É o comportamento desejado: erro alto, em vez de degradar silenciosamente.
3. Locale sem catálogo levanta `ValueError` na carga, listando o que existe.
4. `FILTER_MODES` voltou a ser **constante de módulo** (`core/list.py`): o catálogo já vem resolvido, então não há mais o que adiar. A primeira chave de cada par `(modo, rótulo)` continua sendo identificador de máquina e vai para o backend sem tradução.

**Fora do catálogo, de propósito:** as mensagens de diagnóstico de developer (`ERR_INVALID_PARAMS`, `ERR_UNKNOWN_PAGE`, `ERR_INVALID_BUTTON`, `ERR_NO_RENDER`, `ERR_NEED_IDENTIFY`…) são literais em português no código. O leitor é quem desenvolve, não quem usa o app — traduzi-las só criaria uma constante que existe para ser lida uma vez. Já os `ERR_*` exibidos ao usuário (`ERR_BAD_CREDENTIALS`, `ERR_USER_NOT_FOUND`, `ERR_INVALID_FILE`…) **permanecem** no catálogo.

**O app não é obrigado a usar locale:** basta escrever o texto direto no spec (`label='Plular'`), que é o idioma dele. O que **mudou** é que o catálogo customizado por dicionário (`t('Plurar', MEU_CATALOGO)`) não existe mais — o app que quiser texto próprio declara a constante dele.

**A storefront é do motor — não depende do host.** Os textos da vitrine/do carrinho/da nav (`SITE_*`, `CART_TITLE`, `CART_SENT`, `ALL`, `ALL_CATEGORIES`, `CATEGORIES`, `IDENTIFY`, `YOUR_DATA`, `CONTINUE`, `EMPTY_BAG`, `SELECT`, `NO_ITEMS`, `SEND_QUOTE`, `ADD_MORE_ITEMS`, `VIEW_PRODUCTS`) estão no catálogo do framework, junto com o Page `type='showcase'`. Um host mínimo renderiza o carrossel e o carrinho __sem nenhum arquivo de i18n próprio__. Quem quiser voz própria reconstrói via `locales.herdar_catalogo(globals())`: o módulo do host herda o catálogo e redeclara só os nomes que diferem — sem duplicar a rotina de cópia (ela mora no motor). `core/cart.py` lê `i18n.CART_TITLE`/`i18n.CART_SENT` direto; não há ponte de superset. **Regra:** nomes novos de catálogo entram **na mesma posição alfabética** em `en.py` e `pt.py`, senão o diff fica ilegível.

### 5.13 `normalize_fieldspec` — Especificação Unificada de Fields/Columns

**Localização:** `ajsystem/defs/data.py`

Função interna que centraliza a resolução de `fields`/`columns` em **todos** os componentes (List, Form, Query, Report body). O usuário declara o formato bruto; o motor normaliza internamente.

#### Formatos Suportados

| Formato | Exemplo | Comportamento | `pos_managed` |
|---|---|---|---|
| **Entidade única** | `'Orcamento'` | Expande todos os campos da entidade (respeita `pos_form/pos_list` da Entity) | `True` |
| **Lista explícita** | `['data', 'total', 'cliente_id']` | Inclui exatamente os campos listados (ignora `pos_*`) | `False` |
| **Lista com prefixo** | `['Orcamento.data', 'Cliente.nome']` | Campos de entidades diferentes via prefixo `Entidade.campo` | `False` |
| **Multi-entidade (novo)** | `{'Orcamento': ['data', 'total'], 'Cliente': ['nome', 'telefone']}` | Agrupa por entidade; resolve cada grupo contra seu Schema merged | `False` |

#### Regras

1. **Schema é fonte única de overrides** — Entity (model) + Schema (rota) = merged config. Inline dicts em lista são ignorados (warning).
2. **`pos_managed=True`** (expansão por entidade) → `pos_form=0`/`pos_list=0` ocultam o campo.
3. **`pos_managed=False`** (lista explícita) → campos aparecem mesmo com `pos_*=0`; a declaração é autoritativa.
4. **Multi-entidade** — cada entidade resolve contra seu próprio `full_schema[entidade]`. Requer que o Schema da página tenha as entidades declaradas.

#### Exemplo Prático

```python
# routes/orcamento.py
Schema = {
    'Orcamento': {'data': {'label': 'Data'}, 'total': {}},
    'Cliente': {'nome': {'width': 30}, 'telefone': {}},
    'OrcamentoItem': {'produto': {}, 'qtd': {}, 'valor': {}},
}

Page = {
    'type': 'crud',
    'props': {
        'form': {
            'fields': {                    # NOVO: multi-entidade no form
                'Orcamento': ['data', 'total', 'cliente_id'],
                'Cliente': ['nome', 'telefone'],
            },
            'sessions': {
                'Itens': {
                    'table': {
                        'columns': {       # Multi-entidade na tabela de sessão
                            'OrcamentoItem': ['produto', 'qtd', 'valor']
                        }
                    }
                }
            }
        },
        'list': {
            'columns': {                   # Multi-entidade na listagem
                'Orcamento': ['data', 'total'],
                'Cliente': ['nome'],
            }
        }
    }
}
```

### 5.14 Constantes `ajsystem/defs/constants.py`

| Constante | Valor | Impacto |
|---|---|---|
| `CURRENCY` | `{0: None, 1: {'symbol':'R$','locale':'pt-BR'}, 2: {'symbol':'$','locale':'en-US'}, 3: {'symbol':'€','locale':'pt-BR'}}` | `money`/`itFmtMoney` |
| `DEFAULT_CURRENCY` | `1` | código usado quando `Field.currency` é `None`/`True`/`'brl'` |
| `POS_0_NOT_EMPTY` | `{'pos':0,'when':{'not_empty':True}}` | `pos:0` explícito só quando valor≠vazio (só `form`, `ajsystem/defs/data.py:338` `is_visible_by_pos`) |
| `TODAY` | `date.today` (callable) | default de `Field.data` em forms novos |
| `CONNECTORS` | `frozenset` de 40 preposições PT | normalização de busca textual |

> **Sobre `CURRENCY`:** o `locale` só tem **um valor com efeito real** — `core/formats.py:438` `_fmt_number` faz `if locale == 'pt-BR'`, e qualquer outro valor cai no formato `en-US`. Por isso `3` (`€`) usa `pt-BR`: o agrupamento `1.234,56` é o correto para pt-PT/es-ES/it-IT/de-DE, e o símbolo é prefixado em todos os códigos. Não troque `3` por `de-DE`: o Python passaria a emitir `€ 1,234.56` (errado para Alemanha) enquanto o `toLocaleString` do `formats.js` emitiria `1.234,56` — cliente e servidor divergiriam no mesmo campo.
>
> **Limitação conhecida:** `formats.js:259` (`itMoneyInfo`) duplica a tabela `CURRENCY` à mão. Alterar só o Python dessincroniza os dois em silêncio. E `normalize_currency` só aceita `'brl'` como string — `currency:'eur'` devolve `None` e **desliga** a formatação em vez de escolher o código 3.

> **Versionamento:** toda mudança em `Field`/`Form`/`Report` exige bump em `ajsystem/version` e neste README. A versão do **app hospedeiro** é separada, em `APP['version']` (`app/config.py`, `{cycle, year, month, number}`) — sem arquivo próprio; bump via script de bump do host. `FIELD_TYPES`/`_FIELD_KEYS` (`data.py:413`) valida chaves (`FieldConfigError`).

---

## 6. Histórico de versões

### 1.26.10.02.0001
- **Fonte de dados declarativa SQL-like (`defs/qspec.py`, novo).** `QuerySpec` com as props na ordem do SQL — `select, dist, from, join, where, groups, order, limit` (`levels` legado aceito como alias) — e `PivotSpec` (`src, lines, columns, aggs, filters`; executor pendente). Cada entrada do `select` espelha o `Field`: dado (`field/agg/func/over/calc`) + apresentação (`label/width/align/format/pos_list`) lado a lado, sem sub-dict `display` (que existiu numa fase e foi removido por duplicar props do `Field`). Formas por campo: `'nome'` puro, `{'alias': {agg, field}}` (GROUP BY fora de `over`), `{func, over}` (janela, `func` explícito, `over` nunca vazio), `{over={agg,...}}` (agregado em janela), `{calc}` (template montado pós-`over`). `aggs` no dual curto/longo (`{'id':'count'}` | `{'qtd':{'id':'count'}}`). Tudo com `fail-fast` nomeando (função desconhecida, chave estranha, `groups` sem `agg`, `calc` referenciando campo inexistente). Detecção `is_query_dict` (`select+from`) para a `columns` polimórfica da listagem.
- **Catálogo de window functions + registro de expressões.** `OVER_FUNCS` cobre `rownumber/rank/denserank/percentrank/cumedist/ntile/lag/lead/firstvalue/lastvalue/nthvalue/sum/avg/min/max/count`; `order` aceita campo, `'campo desc'`, `{field, direction}` e expressão do registro `EXPR_FUNCS` — hoje só `coalesce` liberado (`{coalesce: [...]}`), resto entra um por vez (função fora do registro = erro listando as liberadas; campo inexistente = erro).
- **Executor genérico (`core/qrun.py`, novo).** `run_query(model, spec)`: WHERE/ORDER/LIMIT/GROUP BY no SQL, `OVER` avaliado em passo único em Python (1 query, sem N+1), `calc` depois, ordenação final incluindo computados. Cast tipado via Entity (`LIST/INT` str→int, então `filter_select` chega string e filtra `Integer` certo). Convenção de nulo igual a `core/query._cmp_value` (None antes no asc — raiz com `pai_id` null abre o grupo), espelhada no SQL com `nullsfirst/nullslast`. `build_levels` (numeração hierárquica com `sortpath` numérico e guarda `maxdepth`) segue no motor com alias `build_hierarchy`, hoje sem uso ativo.
- **Avaliador único de templates (`core/text.py`, novo).** Sintaxe compartilhada por `select.calc`, coluna `text` e `group text`: `'{campo}'` aplica label do catálogo (LIST→options), `'{campo:02d}'` usa o valor cru, `'{?campo:literal}'` é ternário sem `else` (inclui só se não-None/vazio — ex. código da raiz omite o 3º segmento). `_cell_text_fn` e `pdf._group_title` viraram delegação (a segunda reescrita por substituição por placeholder, que também corrigiu o sombreamento `ns[field]` que imprimia `1. 1` em vez de `1. Receitas`).
- **`Report` emagreceu para apresentação + `table.groups` (control-break por coluna).** `Report` ganhou `page/session/shapes` (passthrough) e `ReportBody` ganhou `levels`; `ReportColumn` ganhou `text` (monta a célula via template) e `suppress` (branco no repetido). Quebras declaradas onde quebram: `table.groups=[{field, print, place, text}]` — `print: 0` sempre, `1` abre, `2` fecha (com `footer_text`); `place: 0` na célula (exige o campo em `columns`), `1` título antes da tabela, `2` linha da tabela. `columns` lista só o que imprime e aceita forma enxuta (`'nome'`, `{'alias': cfg}` igual ao `select`). `body.source` aceita query dict (índice global estável: numera tudo, filtra depois); coluna computada usa o attr direto (fim do N+1 por célula e do `calc` da Entity sombreando a query); `body.filter` com cast; `_infer_source`/`_module_entity` entendem `from` (str ou lista); `order` em lista no legado é ignorado com segurança em vez de `TypeError` no `hasattr`.
- **Listagem bebe da mesma fonte (`columns=QPLANO`, `field_id`).** `do_list_normal` aceita query dict em `columns`: `pos_list` da entrada vale (Schema da página vence), `pos_list=0` filtra num ponto único, `field_id` ausente = só-leitura e declarado tem que estar no `select` e ser pk (senão quebra nomeando). Sem query, comportamento intacto.
- **Dependência declarada, executor futuro.** `requirements.txt` ganha `pandas==2.2.2` para o `pivot` (só declarado; o executor `pivot_table` é a próxima fatia). Débito registrado e assumido: a condição de precedência `Schema` × `pos_list` da entrada está sempre-verdadeira (a entrada sempre vence; o correto é a página vencer) — corrigir junto da próxima fatia.

### 1.26.10.01.0004
- **Script de bump do framework removido.** O host já tem bump em bash, então `scripts/bump_version.py` saiu (com a pasta `scripts/`). As refs viraram neutras ("script de bump do host"): docstring de `Version`, `App.version`, comentário do `APP['version']` e as duas notas de versionamento do README. Mecânica intacta — `Version`/`build_version`/`text()` e a validação não mudaram.

### 1.26.10.01.0003
- **`APP['version']` virou `{cycle, year, month, number}` + script de bump.** A string direta durou um commit: sem consumidor para as partes, ela era certa — mas o bump manual da string (`010`→`011` à mão) é o erro de digitação esperando acontecer, então as partes voltaram **com** o consumidor que faltava: `scripts/bump_version.py` (default `number+1`; `--month/--year` viram o período e resetam para 1; `--number` explícito). `defs/config.py` ganhou `Version` (frozen, valida tipos + mês 1–12) e `build_version`; `text()` compõe `'1.26.10-010'` com padding num lugar só. `inject_versao` é o único leitor além do rodapé. Sumiram a regex `_VERSAO_OK` e o param `version=` string do `build_app`. Valor exibido idêntico antes/depois (`1.26.10-010`), provado no rodapé.

### 1.26.10.01.0002
- **Overrides do host ganharam pasta exclusiva, com os nomes do framework em inglês.** `app/botoes.py`, `app/inputs.py`, `app/constantes.py` e `app/utils.py` viraram `app/extends/buttons.py|inputs.py|constants.py|utils.py` (`git mv`, histórico preservado). `app/config.py` fica na raiz. Seção nova 5.11.1 documenta o contrato.
- **O motor antecipa os overrides em vez de exigir.** `core/adapter.py:_override_ou(caminho, atributo, default)` checa com `find_spec` sem executar: arquivo ausente → default do framework; presente → vale o host; presente com erro interno → o erro original propaga (nunca engolido por `except ImportError`); presente sem o atributo → `ImportError` nomeando. Vale para `extends/buttons.py` (`Buttons`) e `extends/inputs.py` (`Inputs`) — os únicos que o framework importa. Verificado nos 3 cenários: boot normal, `inputs.py` ausente (app sobe, `type: 'CPF'` falha alto nomeando o tipo) e `buttons.py` com `SyntaxError` (o erro original aparece com arquivo/linha).
- **`App.version` virou string direta `1.26.10-009`.** É chave do próprio dict (`APP['version']`, em `app/config.py`) — sem arquivo separado; `build_app` valida o formato `1.aa.mm-build` com erro nomeando. Sumiram `app/versao.py`, o trio `YEAR`/`MONTH`/`SEQUENCE`, a composição `v1.26.10-009` e o `_versao_de_arquivo` — que engolia toda exceção com `except Exception: return ''`. O rodapé exibe como veio.

### 1.26.10.01.0001
- **A aparência de input virou um catálogo por tipo, gêmeo do de botão.** `ajsystem/defs/inputs.py` traz `Input` (dataclass), `INPUT_TYPES` (13 genéricos) e a camada do motor `Inputs` (só o `toggle`). As camadas, na ordem: `INPUTS` < `app.extends.inputs.Inputs` < `Inputs` da rota < `input_props` do campo — mesma merge, mesma mensagem de erro de `build_catalogo`. `App.inputs` entrou no `build_app` ao lado de `botoes`, e `app/extends/inputs.py` é o novo gêmeo de `app/extends/buttons.py`.
- **`Field.input` continua `str`, e `Field.inp` é o `Input` resolvido.** A escolha do tipo (checkbox, moeda, data) passou a ser prop, não nome. Isso levou `textual`, `filter_kind` e `upload` ao catálogo: eram três `if field.input == '...'` no `core` que só existiam para distinguir editores, e agora são atributos. **O `core` não compara mais `f.input` com string** — sobraram só quatro pontos, todos de data/hora (`date`/`time`/`datetime-local`), que precisam do nome porque cada um tem formatação própria.
- **`FIELD_TYPES` virou o ponto único de default.** `BOOL`→`checkbox` (o nome `boolean` saiu do catálogo — era um alias que três arquivos usavam), `FONE`→`tel`, `CPF`→`cpf`, `CNPJ`→`cnpj`. A máscara e o validador do CPF/CNPJ e do telefone BR saíram do `Schema` do model para `app/extends/inputs.py`, escritas uma vez.
- **A resolução do input é eager** (`Field.__post_init__`, não property preguiçosa): `mask`, `validate`, `width` e `align` são computados ali, e resolver depois deixaria a máscara de fora. Três pares passaram a ser validados com erro: input de `slot='bar'` sem `pos_form: 3`, comando `@X` não liberado pelo `mask_group`, e `@U/@L/@C/@T` combos (são exclusivos).
- **O `on_off` saiu do catálogo de botão e virou input `toggle`.** Era o único botão cujo comportamento era do motor, não da CRUD. As 4 rotas que o usavam (`produtos`/`contas`/`categorias` com `ativo`, `operacoes` com `ativa`) declararam `{'type': 'BOOL', 'input': 'toggle', 'pos_form': 3}` no model e apagaram `'buttons': ['on_off']`.
- **O toggle virou POST, e a URL passou a declarar o campo.** Antes: `GET /<rota>/<id>/toggle` mutava dados (quebra cache, prefetch e back/forward) e o campo era fixo por módulo, sem o POST poder escolher. Agora: `POST /<rota>/<id>/toggle/<campo>`, validado contra `Form.toggle_fields` (os campos cujo input declara `route`) — `404` para campo que não é toggle, `405` para GET. Respondendo a HTMX devolve `204` + `HX-Refresh`; fora dela, `302` para o form. O CSRF vem do header que `page_layout.html` já mandava.
- **O toggle renderiza fora do `<form id="main-form">`**, no rodapé, porque cada um é um POST próprio — um form aninhado seria HTML inválido. Só aparece com instância (`id` é a URL), então o form de criação não mostra.
- **`Inputs` da rota entrou no mesmo caminho de `Buttons`.** `module_inputs` lê a variável de módulo, `Form.resolve` recebe `inputs_tipos`/`inputs_page` e `_camadas_inputs` propaga para a listagem — uma coluna é um `Field` como outro qualquer, e sem as duas camadas a mesma entidade mostraria coluna de um jeito no form e de outro na grade.
- **`definir_camadas_padrao` fixa o catálogo do app como default de processo.** `Field` é construído em 6 lugares e nem todos passam pelo `Form`, então o `App.inputs` não podia chegar só por parâmetro. O `init.py` chama antes de `registrar_modulos`, porque o `Entity` já é expandido no import do model — um `type: 'CPF'` resolveria o input antes de a camada existir. Mesmo princípio do catálogo de locales, pelo mesmo motivo (resolvido no import e congelado).

### 1.26.09.30.0001
- **A aparência de botão virou um catálogo por tipo, em 4 camadas.** `BUTTON_TYPES` (40 entradas, todas genéricas — o framework não conhece nenhum botão de app) é a base; `build_catalogo(*camadas)` faz o merge e `resolve_buttons` monta o resultado. As camadas, na ordem: `BUTTON_TYPES` < `Buttons` do motor < `app.extends.buttons.Buttons` < `Buttons` da rota < a spec do uso. A entrada do host declara `type` (de qual genérico diverge; sem `type`, a base é o tipo de mesmo nome) e é **parcial de propósito** — `{'delete': {'color': 'warning'}}` troca a cor e herda o resto. `type` apontando para tipo inexistente levanta erro dizendo o nome, em vez de virar "label faltando" no render.
- **O `Buttons` da rota é a 4ª camada, e é a que mais importa na prática.** É uma variável de módulo lida por `module_buttons`, no mesmo papel que o `Schema` da rota tem sobre os campos — e é o que permite a spec ser **só a lista de nomes** que o form usa. Com ela, `BTN_ORC_ENV`/`BTN_ORC_APROVAR`/`BTN_ORC_RENOVAR` e os helpers `_editavel`/`_expirado` saíram de `app/extends/buttons.py` (um catálogo global para a regra de uma tela) e foram para `app/routes/sys/orcamentos.py`; compras, pedidos e operações trocaram as calls de factory por nomes. `enabled`/`carry`/`url`/`position` seguem fora do catálogo genérico e do do app porque dependem do form e do registro — no `Buttons` da rota eles podem, já que a rota é o ponto de uso.
- **`Button.report` tornou o relatório uma declaração, não uma chamada.** `{'type': 'print', 'report': REL}` sintetiza `render`, `into` e o guard padrão (`_has_items`), então o que fica escrito é só a aparência que diverge. Nenhum tipo `send` foi criado: `BTN_PRINT`/`BTN_SEND` continuam existindo para o guard customizado e para compatibilidade. O container de relatório (`REPORT_ID`/`REPORT_CONTENT`) saiu de `defs/buttons.py` para `defs/report.py`, e os predicados de valor (`is_zero_or_empty`, `calc_value`) foram para `core/utils.py`, para o Python e o JS avaliarem a mesma regra.
- **O `on_off` saiu do catálogo de botão e virou input `toggle`.** Era o único botão cujo *comportamento* (ligar/desligar um booleano) era do motor e não da CRUD, e ele morava no meio da aparência por isso. Agora é um tipo do catálogo de inputs (`ajsystem/defs/inputs.py`), declarado no model como `{'type': 'BOOL', 'input': 'toggle', 'pos_form': 3}` e resolvido por um endpoint genérico `POST /<rota>/<id>/toggle/<campo>`. Três ganhos: o `core` deixou de comparar `f.input` por string, o GET mutante virou POST, e a URL passou a declarar qual campo alterna (validado contra o form, então um POST não escolhe coluna arbitrária).
- **Bug corrigido que a comparação de HTML não pegava:** `/list-action` re-resolvia `lista['buttons']` só com o catálogo do app, enquanto a listagem desenha com as duas camadas. Um botão de listagem declarado no `Buttons` da rota era desenhado e dava **500** no clique — `/operacoes/` respondia `KeyError: imprimir_plano`. O endpoint passou a chamar o mesmo `_camadas_botoes` que `do_list` usa, para as duas resoluções não poderem divergir. Botão de *form* não passa por endpoint (o `render` vai inline em `<template>`), então não tinha o mesmo caminho.
- **A navegação de registro saiu do template.** `Lista`, `Primeiro`, `Anterior`, `Próximo` e `Último` resolviam destino com `url_for` inline, cada um com um caso especial (Anterior/Próximo viravam `btn_off` sem vizinho; Primeiro/Último viravam link com `'#'`). `_nav_grupos` em `core/do_form.py` declara os 4 como `(preset, atributo do nav, opcional)` e devolve os 2 grupos com o destino resolvido; o template só escolhe `btn` vs `btn_off` pelo `on`. E o `back_url` do botão Lista passou a vir resolvido (`form._back_url`).
- **Correções de rótulo.** `Button.label` ganhou default `'Button'` com fallback **só** na renderização — `label=''` continua sendo botão só-ícone, e ausência não vira erro. E o botão de incluir voltou a ser o rótulo do tipo `new` (`Incluir`/`Include`) em vez da composição `Incluir <Entity>`.
- **Verificação que vale registrar:** comparar 14 páginas byte a byte contra o HEAD **não prova nada** se os registros escolhidos esconderem os botões — a primeira rodada comparou orçamento vinculado a pedido e aprovada, onde nenhum botão migrado aparece, e deu "idêntico". Refeita com orçamento avulso e editável (com itens), `Enviar` e `Aprovar` aparecem, e foi aí que o 500 do `list-action` apareceu. `Renovar` (status 7) não é exercitado por nenhum registro do banco e está coberto só por teste unitário.

### 1.26.09.29.0001
- **`Button.position` virou vocabulário de 8 nomes** (`left`, `right`, `before`, `after`, `top_left`, `top_right`, `bottom_left`, `bottom_right`), com default `top_right`. O mesmo nome muda de sentido conforme o contexto, e `_check_position` **levanta erro** fora dele — nada de sumir em silêncio no render. Contexto: form (só as 4 barras), sessão que tem `fields` (o `fields` decide, mesmo com `table`/`query` junto, como em `Financeiro`), sessão só com `table`/`query` (a faixa da tabela), listagem (ignora `position`).
- **`Adicionar` saiu do `<tfoot>`:** a tabela pode ter linha de totais e a largura de colunas do botão não é a delas. Virou faixa única de ação embaixo da tabela, dentro do `.child-table-wrap` e **fora** de `.it-desktop`/`.it-mobile` (por isso renderiza uma vez só e `closest('.child-table-wrap')` funciona nos dois tamanhos). `bottom_left` põe o botão depois dele; o pager continua dentro de `.it-mobile` porque `itmApplyPage` o resolve por `closest('.it-mobile, .it-display')`.
- **Bug pré-existente corrigido em `btn_enabled_init`:** o `{% macro %}` não tinha `-%}`, então o `\n` do comentário seguinte entrava no corpo e a macro devolvia `'\n'` — que é *truthy* em Python. Ou seja, **nenhum** botão ficava desabilitado no primeiro render, e `enabled=False` também era ignorado. O `disabled` inicial só aparecia depois que o JS rodava. Affectava `Gerar` (pedidos/compras) e o gate de `Aprovar` (orçamento).
- **Bugs de render corrigidos junto:** no ramo `fields` + `table`/`query` de `render_sessions`, os botões `left`/`right` eram montados no namespace e nunca renderizados (some silencioso) — agora recebem `head`/`tail`, como nos outros ramos.

### 1.26.09.27.0004
- **Storefront do motor não depende mais do host.** As 18 strings da vitrine/carrinho/nav (`SITE_*`, `CART_TITLE`, `CART_SENT`, `ALL`, `ALL_CATEGORIES`, `CATEGORIES`, `IDENTIFY`, `YOUR_DATA`, `CONTINUE`, `EMPTY_BAG`, `SELECT`, `NO_ITEMS`, `SEND_QUOTE`, `ADD_MORE_ITEMS`, `VIEW_PRODUCTS`) entraram no catálogo do framework (128 → **146**). `CART_ITEMS` saiu (era morto). O Page `type='showcase'` renderiza e o carrinho envia sem nenhum arquivo de i18n do host — um host mínimo funciona.
- **Superset do host desativado no algodoce:** `app/templates/i18n.py` removido e o override em `app/__init__.py` junto; o global `i18n` volta a ser o catálogo do motor (`init.py`). O encaminhador perdeu a utilidade e saiu: `_cat()` em `core/cart.py` voltou a ser `i18n.CART_TITLE`/`i18n.CART_SENT` direto, e `adapter.set_i18n()/get_i18n()` foram removidos. A API de extensão permanece: `locales.herdar_catalogo(globals())` + redeclaração para host que quiser texto próprio.
- **Pendência registrada (rotas da storefront):** `site.html` ainda quebra links `/sobre /vitrine /orcamento /contato`, faz polling no endpoint do app `/orcamento/api/orcamento-count` (badge) e `defs/cart.py` fixa `CART_MORE_ITEMS_LINK='/vitrine/'`. As strings não se prendem mais ao app; a estrutura de rotas/nav, sim — próxima iteração.

### 1.26.09.27.0003
- **Catálogo enxugado:** 154 → 128 constantes no framework, +19 no superset do host. Nomes repetidos mesclados (`UI_SIGN_OUT`→`EXIT`, `UI_SIGN_IN`→`LOGIN`, `UI_MONTH`→`FILTER_MONTH`, `UI_YEAR`→`FILTER_YEAR`, `UI_FILE_INVALID`→`ERR_INVALID_FILE`, `UI_YES`→`FILTER_YES`, `UI_TOGGLE`→`{{ i18n.ACTIVATE }}/{{ i18n.DEACTIVATE }}`), prefixo `UI_` removido, seções removidas: `en.py`/`pt.py` ficaram **alfabéticos na mesma ordem** (paridade agora checa ordem também).
- **Textos de domínio moveram para o host:** `CART_TITLE`, `CART_SENT`, `CART_ITEMS` e os 16 da vitrine/storefront vivem agora em `app/templates/i18n.py` (superset que **herda** as 128 do framework via `locales.herdar_catalogo(globals())` — a rotina de cópia mora no motor). O app injeta o superset no global `i18n` do Jinja (depois de `init_app`) e registra no `adapter.set_i18n()`, que o motor Python usa (`core/cart.py` via `_cat()`). Dependência assumida: `site.html`, `showcase.html` e `cart.html` leem nomes do host (ver 5.12).
- **Bug pré-existente corrigido:** `pages/list.html` referenciava `FILTER_MONTH_RANGE`/`FILTER_YEAR_RANGE` (inexistentes; renderizavam placeholder vazio) — agora `MONTH_RANGE`/`YEAR_RANGE`.

### 1.26.09.27.0002
- **Locale resolvido na importação, não na tradução.** `t()`, `catalogo()`, `locale_ativo()`, `_mapa_en()` e `_CACHE` saíram: `locales/__init__.py` agora lê `APP['locale']` de `app/config.py`, importa o catálogo e reexporta as constantes (`from ajsystem import locales as i18n`). 86 call sites em 11 arquivos migrados. O bug de `t()` congelado em nível de módulo deixa de existir por construção, em vez de ser proibido por regra.
- **`App.locale` saiu do dataclass** (8 props → 7). A chave `'locale'` continua em `app/config.py` — única fonte. Lê-la de lá é seguro porque aquele módulo **não tem nenhum import** (dados puros), então não há ciclo possível. Trocar de idioma é uma linha + reinício, não um fork; o idioma é congelado no boot.
- **Diagnóstico de developer fora do catálogo:** `ERR_INVALID_PARAMS`, `ERR_UNKNOWN_PAGE`, `ERR_UNKNOWN_SEARCH`, `ERR_INVALID_PAGE_PARAM`, `ERR_INVALID_BUTTON`, `ERR_NO_RENDER` e `ERR_NEED_IDENTIFY` viraram literais em português no código. Os `ERR_*` mostrados ao usuário (`ERR_BAD_CREDENTIALS`, `ERR_BAD_KEY`, `ERR_USER_NOT_FOUND`, `ERR_USER_REQUIRED`, `ERR_NO_IMAGE`, `ERR_INVALID_FORMAT`, `ERR_FORMAT_NOT_ALLOWED`, `ERR_INVALID_FILE`, `ERR_INVALID_QTY`) **permanecem** no catálogo.
- **Templates migrados (limitação da 0001 encerrada):** 69 referências `i18n.*` em 13 templates, 58 constantes novas com prefixo `UI_` (rótulo de controle de tela), catálogo 100 → 158 pareados. `init.py` injeta **um** global `i18n` em vez de ~158 nomes soltos. Os 3 pontos delicados foram `components/auth_triggers.html` (HTML montado dentro de string JS, com escapes `\u00e1` → `|tojson`), `components/item_table.html` (`onclick` com `tojson`devolve aspas duplas: o atributo passou para aspas simples) e `components/site.html` (nav do algodoce hardcoded no template do framework — registrado abaixo, não corrigido).
- **`Button.text()`/`confirm_text()` e os leitores do `ConfirmModal` viraram pass-through** (`return self.label`). O método sobrevive porque `label` é o contrato: o app pode escrever o texto dele direto e o template não precisa saber a diferença. `FILTER_MODES` voltou a ser constante de módulo em `core/list.py`.
- **Falha agora é alta:** nome faltando em `pt.py` estoura `ImportError` na carga (antes degradava para inglês em silêncio) e locale sem catálogo levanta `ValueError` listando o que existe. A regra de unicidade dos valores em `en.py` saiu junto — ela só existia porque o texto inglês era chave de dicionário.
- **Perdido de propósito:** o catálogo customizado por dicionário (`t('Plurar', MEU_CATALOGO)`) não existe mais. Nenhum call site usava; o app que quiser texto próprio declara a constante dele.

### 1.26.09.27.0001
- **Locale fecha os furos que ainda ignoravam `App.locale`:** 24 constantes novas em `ajsystem/locales/{en,pt}.py` (23 de rótulo de filtro + `CHOOSE`), catálogo de 76 → 100 pareados, valores únicos garantidos.
- **`t()` em nível de módulo descongelado** (3 pontos): `core/form.py` (`MSG_DELETED`, `MSG_CANNOT_DELETE`) e `core/do_report.py:33` (`ERRO_MSG_PADRAO`) resolviam o texto **uma vez, na importação**, e ignoravam `App.locale` depois. As três viraram chamada em tempo de render.
- **`FILTER_MODES` virou `filter_modes()`** (`core/list.py:243`): os 24 rótulos de filtro estavam em português dentro do dicionário de módulo. Função é interna (uso único em `build_filter_config`), então nada de API pública quebra.
- **Defaults de `def` também congelavam:** `choice_modal(label='Escolha', confirm_label='Ok')` era avaliado no `def`, não na chamada. Viraram `None` + resolução interna; `choice_modal.html` recebeu `all_label`/`cancel_label` em vez de `'— Todos —'`, `'Cancelar'` e `{{ confirm_label or 'Ok' }}` fixos.
- **Outros literais sem `t()`:** `core/list.py` (opções booleanas `Sim`/`Não`) e `core/do_report.py` (coluna `BOOL`).
- **Documentação:** props auditadas contra as dataclasses. Corrigidos `POS_EXPLICIT_NOT_EMPTY` (constante que **só existia no README** — o nome real é `POS_0_NOT_EMPTY`), `Lookup.model` (prop inexistente: o model alvo é inferido do FK), `FIELD_TYPES` (23 → 19, `PK` faltando), `CURRENCY`, `Form.buttons` e as referências à versão do app. Seções novas para `Button`, `ConfirmModal`, `List`, `Query`, `Table`, `Session`, `App`/`Module`/`Tema`/`Layout*`, `locales`, `ReportGroup`/`ReportText`/`ReportField` e `Page.props.scripts`.
- **Limitação registrada (corrigida em 0002):** nesta versão a migração de locale cobria valores de retorno em Python, e os **~62 trechos em português fixo nos templates** ficaram para entrega própria. Tudo migrado — ver 1.26.09.27.0002.

### 1.26.09.21.0001
- **`totals` em sessões `table`/`query`:** linha de totais no `<tfoot>` da tabela editável (corrige regressão em que só sessões `query` renderizavam) e **total geral** na tabela agrupada (`session['totals']` via `aggregate_rows`).
- **Refactor de duplicação:** helpers de slug/blueprint/mapper/FK centralizados em `ajsystem/core/utils.py` (`normalizar_slug`, `snake_case`, `is_empty`, `module_blueprint`, `model_columns`, `fk_column_to`, `fk_target`, `rel_for_column`, `has_back_rel`, `protect_blueprint`) — eliminadas cópias em `auto.py`, `menu.py`, `do_list.py`, `do_auth.py`, `cart.py`, `showcase.py`, `form.py`, `pdf.py`, `filters.py`, `defs/cart.py`, `defs/showcase.py`, `defs/data.py`, `do_form.py`, `init.py`. Rede **−66 linhas** (158+/224−).
- **`is_empty` unificado** em `core/utils.py` (substitui `_empty_value`/`_is_empty` locais de `form.py`, `do_form.py` e `defs/data.py`); `protect` → `protect_blueprint` (3×).
- Dead code removido: `_deep_attr` sem uso em `pdf.py` e `filters.py`.
