# AJSYSTEM 1.26.09.16.0009 — Manual do Framework

> Vinculado a `ajsystem/version` (`1.26.09.16.0009`) — formato `1.aa.mm.dd.bbbb` (`aa` ano, `mm` mês, `dd` dia, `bbbb` builder do dia). Incremente `bbbb` **quando o assunto mudar** (mesmo assunto no mesmo dia mantém a versão). Histórico em `README.old`. Versão do app hospedeiro em `app/config.py:APP['version']`.

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
   3. `Page` — tipo de página (`crud`, `custom`, `showcase`, `cart`, `contacts`).
   4. `Field` — `type`, `pos_form/pos_list/pos_filter`, `tag`, `calc`, `lookup`.
4. **Pré-requisitos.**
   1. Python 3.11+.
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
   from ajsystem.defs.constants import POS_EXPLICIT_NOT_EMPTY
   Schema = {'Tarefa':{'feito':{'tag':{'colors':{True:'success'}}},'transacao_id':{'pos_form':POS_EXPLICIT_NOT_EMPTY}}}
   # POS_EXPLICIT_NOT_EMPTY = {'pos':0,'when':{'not_empty':True}} → pos:0 explícito só quando valor<>null (só form)
   ```

3. **Page CRUD com sessão.**
   ```python
   Page={'type':'crud','props':{'list':{'columns':'Tarefa','order':['titulo']},'form':{'fields':'Tarefa','sessions':{'Financeiro':{'fields':['total','carteira_id']}}}}}
   ```

4. **Calc + tag com link.**
   ```python
   # Entity: 'transacao_id':{'type':'INT','calc':lambda row: row.transacao_id}
   # Schema: 'transacao_id':{'pos_form':POS_EXPLICIT_NOT_EMPTY,'pos_list':0,'tag':{'link':'receber.form','color':'info'}}
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

### 5.1 `Field` — `ajsystem/defs/data.py:143` `class Field`

| Prop | Tipo | Valores possíveis | Impacto visual | Impacto processamento |
|---|---|---|---|---|
| `name` | `str` | nome da coluna | — | chave do `Field` |
| `type` | `str` | `TEXT,MEMO,INT,NUM,PERCENT,ID,DK,FK,DATA,DATA_HORA,HORA,BOOL,FONE,CPF,CNPJ,LIST,MULT10,IMAGE` (`FIELD_TYPES:23`) | define `input`, `width` default, máscara | `build_field_config` aplica `FIELD_TYPES`; `DK` força `pos_form:0 pos_filter:0` |
| `label` | `str` | texto ou `None` → `_auto_label(name)` | cabeçalho lista/form/report | — |
| `width` | `int` | `ch` (ex: `6` para `ID`, `12` para `NUM`) | largura input/coluna (`field.width+3 ch`, report mm) | `field_to_column` (`core/list.py:143`) calcula |
| `align` | `str` | `left,center,right` (`NUM`→`right` automático `data.py:217`) | `text-align` célula/input | — |
| `input` | `str` | `text,number,date,select,textarea,boolean,image,multi` | tipo de `<input>` | `_coerce` (`core/form.py:133`) converte |
| `options` | `dict` | `{k:label}` para `LIST/MULT10` | `select` options, `tag` texto | `field_filter_options` |
| `mask` | `str` | `@R 999.999.999-99` (CPF), `dd/mm/aaaa`, `@T` title | máscara display/edição (`formats.js:fmtMask`) | `parse_mask_commands`, `width` derivado |
| `placeholder` | `str` | texto | `placeholder` input | — |
| `decimals` | `int` | `0` int, `2` moeda | `data-num-decimals`, `fmtNumBR` | `parseNum` |
| `min`/`max`/`step` | `num` | limites | `input min/max/step` | validação `required` |
| `currency` | `int` | `0` off, `1` R$ pt-BR, `2` $ , `3` € (`constants.py:CURRENCY`) | `itFmtMoney`, `R$` | `parseNum` remove `R$` antes de `itEval` |
| `percent` | `bool` | `True` → `12%` | ` %` sufixo | — |
| `required` | `bool` | `True` → `*` | `*` no label, `required` attr | bloqueia `POST` se vazio |
| `disabled` | `bool\|callable` | `True` ou `callable(row)->bool` (`_financeiro_gerado`) | `disabled` attr | `form_macros.html:32` avalia `callable` |
| `readonly` | `bool` | `True` → sempre readonly | branch `pos_form==2/3/readonly` (`form_macros.html:43`) | `do_form.py:430` skip no `POST` se `readonly` |
| `hidden` | `bool` | `True` → `<input type=hidden>` | oculto mas enviado | `do_form.py:397` `extra_ctx['hidden']` |
| `pos_form` | `int\|dict` | `0` oculto body (visível só em `fields` explícito), `1` visível, `2` readonly sempre, `3` barra/tag, `5` footer, `dict{pos,when}` (`when:{not_empty,empty,field,callable}`) | `init.py:54` `field_body`, `form_macros.html:473` `is_visible_by_pos` | `do_form.py:430` skip no `POST` se barra/readonly |
| `pos_list` | `int` | `0` oculto lista, `1` coluna, `2` card, `3` barra lista | `list.py:274` `_pos_managed` | `do_list.py` filtra `pos_list` |
| `pos_filter` | `int` | `0` sem filtro, `1` texto, `2` select, `3` checklist, `9` fixo (`WHERE default`, força `pos_form0/pos_list0` `data.py:184`) | sem UI quando `9` | `filters.py:117` `fixed_filters` injeta `WHERE` |
| `default` | `any\|callable` | `date.today`, `lambda:1` | valor inicial | `do_form.py:419` aplica se `None` |
| `rows` | `int` | altura textarea | `rows` attr | — |
| `lookup` | `dict\|Lookup` | `{display,fields,value,when,query,replaces}` | `select` vs modal `lookup-search` | `resolve_lookup` (`data.py:574`) + `apply_lookup_when` |
| `validate` | `str` | `cpf,cnpj,placa` (`validators.js`) | erro client `data-err-for` | `core/validators.py` espelha no `POST` |
| `help` | `str\|list` | texto | botão `?` | — |
| `on_set` | `dict` | `{replaces:{campo:fonte},disables:[...]}` | `data-replaces-map`, `data-disables` | `itOnSetBind` copia `data-*` da option |
| `calc` | `str\|callable\|dict` | `'qtd*preco'`, `lambda row:`, `{'type':'agg','source':'sum(Item.valor)'}`, `{'type':'call','source':'calc_status'}` | `aj-calc` (`data-calc`) ou `readonly` | `calc_value` (`do_form.py:406` `diff` flash), `itEval`/`formCalcRefresh` JS |
| `carry` | `str` | nome campo origem (`carry` map do botão `Gerar`) | — | `do_form.py:550` `carry_get` importa |
| `tag` | `dict\|Tag` | `{colors, color, link, size}` | `tag-pill` (`width:width+3ch`, `badge`) ou `badge` lista | `tags.py:74` `resolve_link` (`callable` ok) |

### 5.2 `Tag` — `ajsystem/defs/tags.py:62` `class Tag`

| Prop | Tipo | Valores | Visual | Processamento |
|---|---|---|---|---|
| `colors` | `dict` | `{valor:cor}` cor `ghost/primary/success/warning/error/info` ou `0-9` (`COLORS_0_to_9`) | `badge-{cor}` | `_resolve_tag_color` |
| `color` | `str` | cor fixa | idem | — |
| `link` | `str\|callable` | `'pedidos.form'` ou `lambda row:'pagar.form' if tipo=='P'` | `<a href=url_for(link,id)>` | `resolve_link(instance)` |
| `size` | `str` | `sm` (default) | `badge-sm` | — |
| `outline` | `bool` | `True` → outline | `badge-outline` | — |
| `preset` | `str` | `boolean,ativo,status` | — | `parse_tag` aplica `PRESETS` |

### 5.3 `Lookup` — `ajsystem/defs/data.py:102` `class Lookup`

| Prop | Tipo | Valores | Impacto |
|---|---|---|---|
| `display` | `str` | campo exibido (`nome`) | `resolve_lookup` `path: relacao.display` |
| `fields` | `list[str]` | `['nome','telefone']` | `1`→`select`, `>1`→modal busca |
| `value` | `str` | `id` | valor gravado |
| `when` | `dict\|str` | `{'ativo':True}`, `'tipo IN (0,1)'` | `apply_lookup_when` filtra options |
| `query` | `str` | `'PREVISOES'` | modal `lookup-search` (`ajsystem.lookup_search`) |

### 5.4 `Page` — `ajsystem/defs/pages.py:17` `class Page`

| Prop | Tipo | Valores | Impacto |
|---|---|---|---|
| `label` | `str` | `'Orçamento'` | título, `flash_ok` |
| `type` | `str` | `crud` (lista+form), `custom` (`template`), `showcase`, `cart`, `contacts`, `redirect` | `auto.py:_generated_crud` vs `_page_single` |
| `crud` | `bool` | `False` desliga CRUD | não gera `list/form/delete/toggle` |
| `route` | `str` | subpasta `custom` | `do_page` prefix |
| `template` | `dict` | `{'type':'markdown','file':'nome'}` | `do_page` render |
| `props` | `dict` | `form/list/tabs` | resolvido em `Form`/`List` |
| `upload` | `dict` | `{'path':'','max_size':5MB}` | herda `APP['upload']` |

### 5.5 `Form` — `ajsystem/defs/form.py:37` `class Form`

| Prop | Tipo | Valores | Impacto |
|---|---|---|---|
| `fields` | `str\|list\|dict` | Formatos unificados (resolvidos por `normalize_fieldspec`):<br/>`'Entidade'` — expande todos (pos_managed=True)<br/>`['campo1','campo2']` — explícitos (pos_managed=False)<br/>`['Entidade.campo1','Outra.campo2']` — multi-entidade com prefixo<br/>`{'Entidade':['c1','c2'],'Outra':['c3']}` — **NOVO**: multi-entidade agrupado | `normalize_fieldspec` centraliza resolução; `_pos_managed` controla se `pos_form/pos_list` filtram |
| `sessions` | `dict` | `{Nome:{fields,table,query,buttons}}` (`fields` 1:1 child vs pai, `table` editável, `query` readonly) | `form.html: sessions` + `item_table.html` |
| `template` | `str` | path | se setado, ignora `fields` |
| `readonly` | `bool\|callable` | `lambda q: q.pedido_id is not None` | `do_form.py:79` `_is_readonly` desabilita tudo |
| `delete` | `bool\|dict\|callable` | `True`, `{'when':[Model]}`, `lambda` | `_resolve_delete` + `_when_allows` |
| `pre_save/post_save` | `callable` | `f(instance,request,is_new)` | `do_form.py:446` valida/salva |
| `buttons` | `list` | `['on_off']` ou `{label,endpoint,when,render,js}` | `form.html:nav`/`footer` |
| `spacing/max_width` | `num` | `2`, `130` | `render_fields` gap, `resolve_max_width` |

### 5.6 `Report` — `ajsystem/defs/report.py:114` `class Report`

| Prop | Tipo | Valores | Impacto |
|---|---|---|---|
| `label` | `str` | título | cabeçalho PDF |
| `header` | `dict` | `{logo, title, fields:[...]}` | `do_report.py:_apply_entity` resolve `label` via `Entity` |
| `body.source` | `str\|dict` | `'Tarefa'` ou `{'entity':'Operacao','order':'indice'}` | `_infer_source` + `_auto_data` query |
| `body.table.columns` | `dict` | `{'titulo':{'width':50},'PedidoItem.valor':{'width':20,'agg':'sum'}}` | `_apply_entity` herda `label`/`calc` da `Entity` (Schema vence); `width` do report |
| `body.table.hierarchy` | `list` | `[{'indice':{'left':1,'pos':2,'text':'{indice}. {tipo}'}}]` | `pos:2` título fora tabela, `1` linha, `0` oculto |
| `filter` | `dict\|callable` | `filter_select('tipo')` | modal `choice_modal` + `WHERE` |

### 5.7 `ReportColumn` — `defs/report.py:35`

| Prop | Tipo | Valores | Impacto |
|---|---|---|---|
| `field` | `str` | `'qtd'` ou `'produto.nome'` | `data_key` |
| `width` | `float` | `ch`/`mm` | coluna PDF |
| `align` | `str` | `left,center,right` | `Form` `align` herdado (`NUM→right`) |
| `agg` | `str` | `sum` | totaliza |
| `function` | `callable` | `lambda row:` | usa `Entity.calc` se ausente |

### 5.8 `normalize_fieldspec` — Especificação Unificada de Fields/Columns

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

### 5.9 Constantes `ajsystem/defs/constants.py`

| Constante | Valor | Impacto |
|---|---|---|
| `CURRENCY {0:None,1:R$}` | `currency:1` | `itFmtMoney`/`money` |
| `POS_EXPLICIT_NOT_EMPTY` | `{'pos':0,'when':{'not_empty':True}}` | `pos:0` explícito só quando valor≠vazio (só `form`, `ajsystem/defs/data.py:234` `is_visible_by_pos`) |

> **Versionamento:** toda mudança em `Field`/`Form`/`Report` exige bump em `app/config.py:APP['version']` e neste README. `FIELD_TYPES`/`_FIELD_KEYS` (`data.py:286`) valida chaves (`FieldConfigError`).
