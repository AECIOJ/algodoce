# AJSYSTEM 1.26.10.24.0001 — Manual do Framework

> Vinculado a `ajsystem/version` (`1.26.10.24.0001`) — formato `ciclo.ano.mes.dia.seq`: ciclo `1`, ano `aa`, mês `mm`, dia `dd` e **seq no dia** `bbbb` (4 dígitos). O bump vem de cada assunto que muda código de `ajsystem/` (não só os dataclasses desta referência; `app/` não entra) — ver **Versionamento** em 5.14.1. O dia vem do calendário e o `seq` reinicia em `0001` a cada dia novo; no mesmo dia, só o `seq` sobe. A versão do **app hospedeiro** é outra, em `APP['version']` (`app/config.py`), e é o dev que bumpa na mão com o comando `versao` (ver 5.14.1).

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
   4. `Field` — `type`, `tag`, `calc`, `lookup`. Onde o campo
      aparece **na tela** não é do `Field`: são os slots da **página** — na
      listagem `line`/`card`/`hidden` (§5.6), no form `bar`/`footer`/`body`/
      `hidden` (§5.5).
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
5. **Merge (declaração de props).**
   ```
   tipo (FIELD_TYPES+INPUT_TYPES)  ─┐
   Entity ──────────────────────────┤ (cada camada sobrescreve a anterior)
   Schema ──────────────────────────┤
   Query  ──────────────────────────┘
            └─► build_field ─► Field ─► column/form/report
   list/form: consomem o Field (sem override)
   report:    consomem o Field + override de props de display (format/mask)
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
   Schema = {'Tarefa':{'feito':{'tag':{'colors':{True:'success'}}}}}
   # Posição/visibilidade são prop da PÁGINA, não do Schema — ver 5.5 (form) e 5.6 (lista)
   ```

3. **Page CRUD com sessão.**
   ```python
   Page={'type':'crud','props':{'list':{'columns':'Tarefa','order':['titulo']},'form':{'fields':'Tarefa','sessions':{'Financeiro':{'fields':['total','carteira_id']}}}}}
   ```

4. **Calc + tag com link.**
   ```python
   # Entity: 'transacao_id':{'type':'INT','calc':lambda row: row.transacao_id}
   # Schema: 'transacao_id':{'tag':{'link':'receber.form','color':'info'}}
   # total: 'total':{'type':'NUM','calc':'valor + acrescimo - desconto'}
   # Onde ele aparece — lista (`hidden`) e form (`positions.hidden`) — é prop da página, não do Schema (5.5/5.6)
   ```

5. **`visible` — visibilidade condicional (prop da página).**
   ```python
   # form: {'visible': {'pedido_id': NOT_EMPTY}}
   # cond: NOT_EMPTY | EMPTY | NOT_NULL | NULL           (sentinelas de defs.constants)
   #     | {'not_empty':True} | {'empty':True} | {'field':'valor','op':'not_empty'} | callable(row,val)
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
| `type` | `str` | `TEXT,MEMO,INT,NUM,PERCENT,PK,ID,DK,FK,DATA,DATA_HORA,HORA,BOOL,FONE,CPF,CNPJ,LIST,MULT10,IMAGE` (`FIELD_TYPES`, **19** entradas) | declara qual **input** do catálogo o campo usa (`BOOL`→`checkbox`, `CPF`→`cpf`, `CNPJ`→`cnpj`, `FONE`→`tel`), e o input traz `width`/máscara/validador | `build_field_config` aplica `FIELD_TYPES`; `DK` não é eixo de filtro nem campo de tela (regra de tipo, §5.5/§5.6) |
| `label` | `str` | texto ou `None` → `_auto_label(name)` | cabeçalho lista/form/report | — |
| `width` | `int` | `ch` (ex: `6` para `ID`, `12` para `NUM`) | largura input/coluna (`field.width+3 ch`, report mm) | `field_to_column` (`core/list.py:184`) calcula |
| `align` | `str` | `left,center,right` (`NUM`→`right` automático `data.py:260`) | `text-align` célula/input | — |
| `input` | `str` | **nome de um tipo** de `ajsystem/defs/inputs.py` (`text,number,date,select,textarea,email,tel,password,checkbox,multi,image,toggle,…`) | resolve o `Input`; o `Field` passa a ler as props dele | `Field.__post_init__` instancia o `Input` — o `core` lê **`f.inp.*`**, nunca `f.input` por string |
| `input_props` | `dict` | override parcial do input **neste campo** (`{'cls':'x','size':9}`) | última camada do merge, acima do app e da rota | `resolve_input(..., overrides)`; chave desconhecida **levanta erro** |
| `options` | `dict` | `{k:label}` para `LIST/MULT10` | `select` options, `tag` texto | `field_filter_options` |
| `mask` | `str` | `@R 999.999.999-99` (CPF), `dd/mm/aaaa`, `@M(BRL) 999,999.99`, `@T` | máscara **de exibição**; default do tipo/catálogo (data/hora/cpf), senão numérico de `decimals`. Numérica canônica (`0`=pad, `9`=opcional, `,`=milhar, `.`=decimal) — o motor troca por `THOUSAND`/`DECIMAL` | `parse_mask`, `width` derivado; precedência `explícita > catálogo > numérico` |
| `placeholder` | `str` | texto | `placeholder` input | — |
| `decimals` | `int` | `0` int, `2` moeda | **entrada** (`data-num-decimals`, `fmtNumBR`), default da máscara numérica e arredondamento no POST | `parseNumField` (JS) / `fmt_num`+`_coerce` (Python), ver 5.14 |
| `min`/`max`/`step` | `num` | limites | `input min/max/step` | validação `required` |
| `percent` | `bool` | `True` → `12%` | ` %` sufixo | — |
| `required` | `bool` | `True` → `*` | `*` no label, `required` attr | bloqueia `POST` se vazio |
| `disabled` | `bool\|callable` | `True` ou `callable(row)->bool` (`_financeiro_gerado`) | `disabled` attr | `form_macros.html:55` avalia `callable` |
| `readonly` | `bool` | `True` → sempre readonly | renderiza rótulo + `<input type=hidden>` (o valor **continua** indo no `POST`) | `form_macros.html:66`; **não** pula o save — quem pula é o `Form.readonly` (callable), em `do_form.py` |
| `hidden` | `bool` | `True` → `<input type=hidden>` | oculto mas enviado | `do_form.py:457` `extra_ctx['hidden']` |
| `default` | `any\|callable` | `TODAY` (`date.today`), `lambda:1` | valor inicial | `do_form.py:536` aplica se `None` |
| `rows` | `int` | altura textarea | `rows` attr | — |
| `lookup` | `bool\|dict\|Lookup` | `True` (defaults) ou `{display,fields,value,when,query}` — **sem `model`**, o alvo vem do FK | `select` (1 campo) vs modal busca (>1) | `resolve_lookup` (`data.py:810`) + `apply_lookup_when` |
| `validate` | `str` | `cpf,cnpj,placa` (`validators.js`) | erro client `data-err-for` | `core/validators.py` espelha no `POST` |
| `help` | `str\|list` | texto | botão `?` | — |
| `on_set` | `dict` | `{replaces:{campo:fonte},disables:[...]}` | `data-replaces-map`, `data-disables` | `itOnSetBind` copia `data-*` da option |
| `calc` | `str\|callable\|dict` | `'qtd*preco'`, `lambda row:`, `{'type':'agg','source':'sum(Item.valor)'}`, `{'type':'call','source':'calc_status'}` | `aj-calc` (`data-calc`) ou `readonly` | `calc_value` (`do_form.py:471` `diff` flash), `itEval`/`formCalcRefresh` JS |

> **`calc` de coluna que é `property` do model tem de ser virtual.** O motor decide o que é gravável pelo que a config **declara**, não pelo que existe no banco: se o `calc` vier como expressão avaliável de aggregate (`{'type':'agg', 'source': 'sum(Item.valor)'}`), ele é tratado como coluna real e entra no `POST` — num campo que **não é coluna** isso é `setattr` num atributo inexistente, e o registro morre no commit. A forma virtual (`lambda row:`, `string`, `{'type':'call', ...}`) é o que `do_form._calc_virtual` reconhece para pular o save (`do_form.py:63`). Vale para qualquer campo derivado: **ou é `memory`, ou o `calc` é virtual** — nunca os dois. Um `property` que também é `memory` é redundante (o `memory` já o resolve); um `property` com `calc` de aggregate sem `memory` grava onde não há coluna.
| `carry` | `str` | nome campo origem (`carry` map do botão) | — | `do_form.py:618` `carry_get` importa |
| `memory` | `bool` | `True` → campo só de memória: renderiza/editável, **não persiste** e não entra em expansão automática (form principal/list/filtro); só aparece onde citado explicitamente — `session.fields` ou um bloco `MEMORY` do Schema (**5.5.3**) | select FK normal | `_save_session_masters` e o save do mestre pulam o campo; alvo vem do `lookup.model` (nome de entidade) em `resolve_lookup` |
| `tag` | `dict\|Tag` | `{colors, color, link, size, preset, text_field, outline, cls}` | `tag-pill` (`width:width+3ch`, `badge`) ou `badge` lista | `tags.py:86` `resolve_link` (`callable` ok) |
| `_slot` | `str` | **interno** — posto por `core/resolve.resolve_slots` a partir dos slots da página; não declarar à mão | — | render + predicado de save (§5.5) |
| `_visible_when` | `dict` | **interno** — posto por `core/resolve.resolve_visible` a partir de `visible`; não declarar à mão | — | `is_visible_by_pos` |

> `on_set.replaces` alimenta o `lookup` no `resolve_lookup` — é a prop `replaces` do dicionário de lookup, mas **não** uma prop de `Lookup`. Por isso `lookup.model` também não existe: o model alvo é inferido de `fk_target_model` (`data.py:810`).

> **Moeda não é prop de `Field`.** Não existe `currency` no dataclass (Entity/Schema que declarar `currency` levanta `FieldConfigError`). A moeda sai da `mask` — comando `@M(id)` (ex.: `@M(BRL)`). `Field.currency` é **derivada pelo motor** (`mask_money_id`) para lista/form/report/totais; em qualquer editável, declare `mask: MVALOR` (ver 5.14).

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

**Rota fora do CRUD gerado.** `type: 'crud'` gera `list`/`form` (e `delete`/`toggle`) sozinho — mas a **função** do handler é da rota, não do motor. Quando a página precisa de um endpoint que o CRUD não gera (aprovar, renovar, estornar, um POST que dispara uma rotina), o padrão é: a função vive no arquivo da rota, e o `create_app` do host só a registra, porque o motor já registrou o blueprint:

```python
# app/__init__.py, dentro de create_app()
from app.routes.sys import orcamentos as _mod
app.add_url_rule('/orcamentos/<int:id>/aprovar', endpoint='orcamentos.aprovar',
                 view_func=login_required(_mod.aprovar), methods=('GET', 'POST'))
```

O `endpoint` é o do blueprint (`rota.ação`) e o prefixo da URL é o do blueprint — `url_for('orcamentos.aprovar', id=…)` funciona de qualquer lugar. Quem chama de dentro do form é um `Button` com `url`/`action` (§5.9), não a spec da Page: a Page descreve a tela, a rota descreve a ação.

### 5.5 `Form` — `ajsystem/defs/form.py:55` `class Form`

| Prop | Tipo | Default | Valores | Impacto |
|---|---|---|---|---|
| `fields` | `str\|list\|dict` | `None` | Formatos unificados (resolvidos por `normalize_fieldspec`, 5.13):<br/>`'Entidade'` — expande todos<br/>`['campo1','campo2']` — explícitos<br/>`['Entidade.campo1','Outra.campo2']` — multi-entidade com prefixo<br/>`{'Entidade':['c1','c2'],'Outra':['c3']}` — multi-entidade agrupado | define **quais** campos e a **ordem**; a posição vem de `positions` (abaixo) |
| `positions` | `dict` | `None` | `{bar:[...], footer:[...], body:[...], hidden:[...]}` — mesma família de formatos de `columns`/`line` (§5.6) | onde cada campo vai na tela — ver **Slots do form**, abaixo |
| `visible` | `dict` | `None` | `{campo: cond}`, `cond` = `NOT_EMPTY`/`EMPTY`/`NOT_NULL`/`NULL` (sentinelas), `{'not_empty'/'empty'[:bool]}`, `{'field','op','value'}`, `callable` | visibilidade condicional — **não** é slot; o campo continua no save |
| `sessions` | `dict` | `None` | `{Nome:{fields,table,query,totals,buttons,defaults,on_new,positions,visible}}` (`fields` 1:1 child vs pai, `table` editável, `query` readonly, `defaults`/`on_new` em 5.5.2, `positions`/`visible` próprios da sessão) | `form.html: sessions` + `item_table.html` |
| `template` | `str` | `None` | path | se setado, ignora `fields` |
| `flash_ok` | `str` | `None` | mensagem de sucesso do save | flash pós-submit |
| `flash_update` | `str` | `None` | mensagem quando o save só atualiza | flash pós-submit |
| `readonly` | `bool\|callable` | `False` | `lambda q: q.pedido_id is not None` | `core/form.py:77` `_is_readonly` desabilita tudo |
| `delete` | `bool\|dict\|callable` | `False` | `True`, `{'when':[Model]}`, `lambda` | `_resolve_delete` + `_when_allows`; `msg_ok`/`msg_no` |
| `pre_save`/`post_save` | `callable` | `None` | `f(instance,request,is_new)` | `do_form.py:536` valida/salva |
| `buttons` | `str\|Button\|list` | `None` | nome de tipo (`'on_off'`, `'delete'`), `{tipo: {overrides}}`, instância `Button` (`BTN_SAVE`, `BTN_PRINT`, `BTN_SEND`…) ou lista de qualquer um | `resolve_buttons` (`defs/buttons.py`); `form.html:nav`/`footer` |
| `spacing` | `num` | `2` | gap entre campos | `render_fields` |
| `max_width` | `num` | `None` | largura máxima do form | `resolve_max_width` |

#### Slots do form: onde cada campo aparece

Igual à listagem, a posição é pergunta da **página**, não do `Field`: slots em `Page.props.form.positions`, nunca um inteiro mágico no dataclass. São **quatro** slots e uma prop à parte:

| Slot | Afirmação | Default |
|---|---|---|
`bar` | na **barra** do form (ícones/tags, fora do corpo) | — |
`footer` | no **rodapé**, **fora** do `<form id="main-form">` — é o lugar dos toggles, que são POST próprio | — |
`body` | no **corpo** do form | ✅ |
`hidden` | fora da tela — e **não grava** (§ save abaixo) | — |
`visible` | **não é slot**: visibilidade condicional sobre o dado (`NOT_EMPTY`/`EMPTY`/`NOT_NULL`/`NULL`, `{not_empty,empty}`, `{field,op,value}`, `callable`). Um campo na barra ou no corpo pode ter a mesma condição | — |

Precedência quando o mesmo campo é citado em dois slots: **`hidden` > `bar` > `footer` > `body`**. É total, sem arbitragem em runtime.

Os slots aceitam a mesma família de formatos de `columns` (`normalize_fieldspec`/`field_spec_item`): `'Entidade'`, `'campo'`, `'Entidade.campo'`, lista mista, `{'Entidade': [...]}`, `{'Entidade': '*'}`. Props inline são aceitas e **descartadas** — o slot afirma posição, não apresentação. A resolução de nome cru é a da §5.6: **único** na entidade de `fields` → **único** no pool → na ambiguidade a entidade de `fields` desempata; sem entidade, o autor qualifica.

**A chave não aparece sem querer.** Um form não edita a própria chave, então o campo de sistema vai para `hidden` **sem ninguém declarar**: `type` `ID` (a chave) ou `DK` (a chave derivada que o motor gerencia). É por **tipo**, não por nome: numa tabela de ligação (`ProdutoInsumo`), as duas colunas são FKs e o motor tem que mostrá-las. Quem precisa do contrário **cita** o campo em `body` — a declaração existe, e existir é o que ganha da regra.

```python
# pagar — a chave do filho volta à tabela da sessão; o resto do sistema some
'form': {
    'fields': 'Transacao',
    'positions': {'bar': ['status'], 'footer': ['cancelado'],
                  'hidden': ['valor', 'prazo', 'variacao', 'saldo', 'tipo',
                             'compra_id', 'pedido_id']},
    'visible': {'pedido_id': NOT_EMPTY,   # from ajsystem.defs.constants import NOT_EMPTY
                'compra_id': NOT_EMPTY},
    'sessions': {
        # `Previsões` é `table`: as `positions` da sessão valem para as COLUNAS
        # (a `Previsao`). `id` é a chave do filho — citada em `body` para voltar.
        'Previsões': {
            'fields': [...],                       # campos do PAI (Transacao)
            'table': {'columns': ['Previsao'], 'totals': [...]},
            'positions': {'hidden': ['saldo'], 'body': ['id']},
        },
    },
},
```

**Slots de sessão.** Cada sessão tem os **seus** `positions`/`visible`, com uma superfície mais estreita: só `body` e `hidden` (não há barra nem rodapé numa tabela de linhas). O alvo depende do tipo de sessão:

- **`table`/`query`** — as `positions` da sessão posicionam as **colunas** (o filho). Os `fields` da sessão (que vêm do Schema do mestre) são do **pai** e **herdam** a posição do mestre, recortada pelo que a sessão exibe; a sessão não os reposiciona (o recorte da sessão é o filho).
- **`fields` sem `table`/`query`** — a sessão é o pool inteiro: as `positions` valem para ele. Com o primeiro item em snake_case de um campo do pai, a sessão agrupa campos do **pai**; com o primeiro item nomeando uma Entity, são campos do **filho**.

**O slot é o predicado de escrita.** No save, gravam `body` e `footer`; `hidden` e `bar` **não** (o campo não existe na tela, e mandar o que veio do POST gravaria `NULL` onde o campo é derivado). O `readonly` **não** entra nesse predicado: ele renderiza rótulo + hidden que ainda submete o valor, então um campo `readonly` no corpo é reenviado e gravado. Quem barra o save inteiro é o `Form.readonly` (callable sobre a instância), que pula tudo exceto `footer`.

### 5.5.1 `totals` em sessões `table`/`query`

Totalização opcional da tabela da sessão — editável (`table`) ou readonly (`query`). Aceita:

- **lista de nomes** `['qtd', 'valor']` — soma as colunas na linha de totais;
- **lista mista** `['qtd', {'valor': 'total'}]` — o item string soma só a coluna; o item `dict {coluna: campo_master}` soma **e** grava no `<input name="campo_master">` do master (ex.: `total`);
- **string única** `'valor'` — soma a coluna.

A linha de totais é renderizada no `<tfoot>` da tabela desktop. Colunas `calc` (ex.: `valor = qtd * preco`) usam a própria expressão no total. Cada célula do total carrega a formatação da coluna — `data-fmt-mask`/`data-fmt-decimals`/`data-fmt-currency`, por `fm.fmt_attrs` (ver **5.14**) — e o JS as aplica com `itFmtByAttrs`; as casas do total vêm de `Field.num_decimals`, não da escala da coluna no banco.

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

### 5.5.2 `defaults` e `on_new` em sessões `table`

Duas props que deixam **duas sessões de tabela mirarem o mesmo relationship** — o caso da Transferência, em que "Entradas" e "Saídas" são `Movimento` com `tipo` diferente, e por isso não podem ser distinguidas pelo relationship nem pelo `attr` (que o motor resolve pelo mapper: um só, `movtos`).

| Prop | Tipo | Quando age | O quê |
|---|---|---|---|
| `defaults` | `dict` | render + save | campos que a sessão **possui**. Particiona as linhas (só as que batem aparecem e são gravadas), e carimba a linha no save — para campo oculto, que não vem no POST |
| `on_new` | `dict` | client | o que a linha **nova** herda: `{replaces: {alvo: fonte}}`, mesmo formato do `on_set` (5.13) |

```python
# Transferência — as duas sessões dividem `movtos`
NOVO_REGISTRO = {'replaces': {'data': 'data', 'documento': 'documento',
                               'historico': 'historico'}}

'Entradas': {'table': {'columns': ['Movimento']},
             'defaults': {'tipo': ENTRADA},
             'on_new': NOVO_REGISTRO},
'Saídas':   {'table': {'columns': ['Movimento']},
             'defaults': {'tipo': SAIDA},
             'on_new': NOVO_REGISTRO},
```

**As três garantias de `defaults`** (`core/do_form.py`):

- **render** — `_session_rows` filtra `session['_rows']`, e `item_table.html` usa essa lista quando ela existe (o `_rows` só é setado quando há `defaults`, então sessão sem a prop segue lendo `instance|deep_attr(attr)`);
- **save, linha postada** — `_save_table_sessions` pula a linha cujo filho não casa com `defaults`: não é desta sessão, então não salva nem exclui. A linha **nova** é reconhecida pelo que ela posta (`_posted_matches`): o `defaults` que não é célula editável viaja como hidden **dentro de um `<td>`** — solto no `<tr>` é HTML inválido e o parser do navegador pode tirá-lo da tabela, e é ele que leva o `tipo` no POST (sem ele a linha nova seria criada duas vezes, uma em cada sessão);
- **save, exclusão** — a lista de `existing` (linhas do banco ausentes do POST são excluídas) é filtrada pelo mesmo `defaults`, senão "Entradas" apagaria as linhas de "Saídas".

O carimbo é **incondicional**: a sessão é dona do campo, então o que veio no POST não passa por cima.

**`defaults` é identidade, não "campo a zerar".** O mesmo dicionário serve para as três coisas acima, e o filtro compara **todas** as chaves (`_session_matches`): uma chave cujo valor gravado difere do default tira a linha do render e do save. Por isso `'defaults': {'tipo': ENTRADA}` serve e `'defaults': {'conta_id': None}` não — as linhas com `conta_id` gravado deixariam de casar com sessão nenhuma, e o formulário abriria vazio. Para "zerar o que já estava gravado", o caminho é o `post_save` da rota (que roda depois do commit e alcança as linhas por query), não o `defaults`.

**Campo `readonly` na linha nova** — renderiza rótulo + valor e um `<input type="hidden">` que ainda leva o valor no POST (o campo some do POST se for `disabled`, e o `readonly` de linha precisa ser gravado). Na linha **nova** o hidden fica **dentro** de um `<span data-readonly-for="campo" data-readonly-mask="…">`, com o texto em `[data-readonly-text]` — dois motivos:

- o `on_new` escreve o texto (`itReadonlyText`) sem apagar o hidden, que é irmão do texto dentro do mesmo span;
- no mobile o ColumnTemplate é um `<div>` fora de `<table>`, então o parser **descarta** os `<th>`/`<td>` e mantém só o conteúdo — e o `addChildRow` casa os elementos do template com as linhas da tabela mobile **por posição**. Uma célula que renderiza dois elementos (span + hidden soltos) desloca tudo depois dela. Uma célula = um elemento.

**`on_new`** — o mapa vai para `data-new-replaces` no `.child-table-wrap` (mesmo formato `alvo:fonte` do `data-replaces-map`), e o `itOnNewRow` o aplica no `addChildRow`, depois do clone desktop e depois das células mobile. Três regras:

- **origem**: procurada no **mestre** primeiro e só depois na **própria linha nova**. O inverso quebraria todo mapa com nomes iguais — o mais comum (`data:data`): a busca acharia o próprio alvo da linha nova, que está vazio, e nunca chegaria no mestre. A linha fica como segunda opção para "copia de outra coluna da linha", e mestre em branco **não** sobrescreve o que já veio preenchido;
- **escrita**: a mesma do `on_set` — `numToInputFor` (que lê `data-num-decimals`, e é o que funciona em campo `disabled`, onde `fmtFieldInput` é no-op) → `fmtFieldInput` → `input`/`change`, para os `it*` do motor reagirem;
- **todos os alvos**: desktop **e** mobile, porque `itmApplyPage` só pagina — não sincroniza valor nenhum entre as duas cópias. (O `on_set` escreve só no primeiro match; aqui a divergência é deliberada.)

O `on_new` escreve também o **texto** do campo `readonly`: `itReadonlyText` traduz a data que o input `date` entrega em ISO para `dd/mm/aaaa` (o mesmo `fmt_date` do servidor; demais campos saem como vieram, porque o que o `numToInputFor` escreveu no input já é a convenção de exibição). A data é montada em horário local — `new Date('2026-07-13')` é UTC e o `fmtMask` lê os getters locais, o que daria 12/07 num fuso negativo.

`on_new` é client-side: sem JS a linha nova nasce vazia — a mesma classe do `on_set`, que também não roda sem JS.

**`on_new` só alcança a linha nova.** Ele roda no `addChildRow`, ou seja, no instante em que a linha é criada — a linha **já gravada** nunca passa por ele. Se o valor que ela herda puder mudar depois (o mestre é editado, o documento é renumerado, o status avança), a linha velha fica com o valor da época em que foi criada. O caminho para fechar as duas pontas é o **`post_save` da rota**, que roda depois do commit e alcança as linhas por query: ele rebaixa as existentes para o valor novo do mestre. É a divisão: `on_new` cobre a linha que está nascendo, `post_save` cobre as que já estão no banco. Um campo herdado que só o `on_new` escreve é um campo que envelhece.

Os ids dos `<template>` passam a ser por sessão (`data-tpl` no `tbody`), para duas tabelas do mesmo relationship não saírem com `movtosRowTemplate` duplicado no DOM — e a chave da linha nova passou a ser contada **no form inteiro**: com o contador por tabela, as duas sessões geravam a mesma `n-1`.

### 5.5.3 Bloco `MEMORY` — campos que existem só na tela

O `memory` já resolvia "campo editável que não persiste", mas só aparecia citado
campo a campo (`session.fields=['valor','de','para']`) e com `memory: True`
repetido em cada campo. O **bloco** resolve os dois: **chave em MAIÚSCULAS** no
`Schema` cujo valor é um dict de configs é um grupo de memória.

```python
Schema = {
    'Transferencia': {...},
    # chave em MAIÚSCULAS = bloco de memória (não é entidade: não tem model
    # nem coluna). Cada campo do grupo nasce memory=True.
    'MEMORY': {
        'valor': {'type': 'NUM', 'label': 'Valor', 'width': 12, 'mask': MVALOR},
        'de':   {'type': 'FK', 'label': 'De', 'width': 15,
                 'lookup': {'model': 'Recurso', 'display': 'nome'}},
    },
}

Page = {'props': {'form': {
    # lista explícita: é o que traz o bloco para dentro do form
    'fields': {'Transferencia': ['data', 'documento', 'total', 'status', 'historico'],
               'MEMORY': ['valor', 'de']},
}}}
```

- **o que define**: `grupos_memoria` (`defs/data.py`) lê as chaves em MAIÚSCULAS
  do Schema cujo valor é um dict de configs e carimba `memory: True` em cada
  campo. O nome da chave é livre (é namespace); `'Transferencia'`/`'Movimento'`
  são entidades porque não são MAIÚSCULAS.
- **FK sem coluna**: campo de memória não tem coluna no pai, então não há FK para
  o motor inferir — o alvo vem do `lookup.model`, que é o **nome** da entidade
  (`MODEL_MAP`, registrado em `register_model`), não a classe.
- **não persiste**: os dois loops de save pulam `memory` — o das sessões
  (`_save_session_masters`) e o do mestre. Sem o do mestre, um bloco no
  cabeçalho passaria por `setattr` num atributo que o model não tem.
- **visibilidade**: `memory` é pulado na expansão automática; e o **slot** diz o
  que é gravável, mesmo em lista explícita — uma lista explícita assume a
  **ordem**, não o que é campo editável (é por isso que `status`, no slot `bar`,
  não vira NULL vindo de um POST sem input para ele, §5.5).

**`fields` lista/dict no `Form`** — a forma str (`'fields': 'Tarefa'`) é expansão
(aparece todo campo da entidade); lista e dict são autoritativas (só os listados).
O form
passava o schema **plano** para o `normalize_fieldspec`, que o espera indexado por
entidade: a lista e o dict resolviam campo **sem config nenhuma** (a `data` virava
input de texto, o `textarea` perdia o memo). Agora o form indexa a própria fatia
mais os blocos de memória, o que faz as formas documentadas resolverem config de
verdade. Com `'Entidade.campo'` a ordem é a dos prefixados primeiro; com o dict
multi-entidade a ordem é a do spec — use o dict quando a ordem importa.


### 5.6 `List` — `ajsystem/defs/list.py:17` `class List`

#### Slots: onde cada campo aparece

A listagem tem duas etapas, e elas respondem perguntas diferentes:

1. **`columns`** — **quem existe**. Entidade = expansão, lista = autoritativa, query dict = fonte do `qrun`; com `master`, as duas entidades da inversão.
2. **`line` / `card` / `hidden`** — **onde cada um vai**. Slots da **página** (`Page.props.list`), nunca do `Field`: a pergunta "esse campo é coluna aqui?" só tem resposta no lugar onde a lista é montada, e um inteiro mágico espalhado em Entity e Schema obligava a caçar a declaração em três arquivos.

| Slot | Afirmação | Default |
|---|---|---|
`line` | **sempre** na grade, e prioridade máxima quando a tela estreita. **Vence `card`** — é como um campo escapa de um `card: 'Entidade'` | — |
`card` | **sempre** na linha expansória, em qualquer largura | — |
`hidden` | fora da grade, do card **e do painel de filtros** | — |
(não citado) | na grade, prioridade normal — colapsa no overflow se a tela estreitar | ✅ |

Precedência quando o mesmo campo é citado em dois slots: **`hidden` > `line` > `card`**. É total, sem arbitragem em runtime.

Os três aceitam a mesma família de formatos de `columns` (`normalize_fieldspec`/`field_spec_item`): `'Entidade'` (expande), `'campo'`, `'Entidade.campo'`, `['campo', 'Entidade.campo']`, `{'Entidade': [...]}`, `{'Entidade': '*'}`. Props inline (`('campo', {props})`, `{alias: {props}}`) são aceitas e **descartadas** — o slot afirma posição, não apresentação.

**Nome cru resolve; só a ambiguidade obriga a qualificar.** Com `master`, as duas entidades da inversão entram no pool, e algumas dividem nomes (`Transferencia`/`Movimento` têm `id`, `data`, `documento` e `historico`; `Transacao`/`Previsao` têm `id` e `variacao`). A leitura de um nome sem prefixo é, nesta ordem: **único** na entidade de `columns` → **único** no pool (de onde vier) → **ambíguo**, e aí a entidade de `columns` desempata, por ser o assunto da lista. Sem entidade em `columns` (lista de campos ou fonte `query`), ambiguidade é erro e o autor qualifica.

```python
'list': {
    'master': 'Movimento', 'columns': 'Transferencia',
    'line': ['id'],                    # ambíguo → Transferencia.id (abre o pai)
    'hidden': ['documento',            # ambíguo → Transferencia.documento
               'conta_id', 'previsao_id',       # únicos no pool: são do Movimento
               'operacao_id', 'variacao', 'pedido_id', 'compra_id'],
    'card': 'Transferencia',           # o resto do pai
    'order': ['data', 'id'],
}
```

`'Entidade.campo'` é sempre válido e é o desambiguador na mão — que é como se escreve quando a intenção é a entidade que **não** é o assunto: `'hidden': ['Movimento.documento']`.

Toda validação é **fail-fast nomeando**: slot inexistente, campo que não está na listagem, nome ambíguo, `'*'` sem entidade. Não há valor que caia em silêncio (o antigo `pos_list: 3`, documentado e sem consumidor, sumiu junto com a prop).

`hidden` remove o campo da grade, do card **e do painel de filtros**. Para afirmar algo sobre o **painel de filtros** sem mexer nas colunas, a listagem tem a prop `filter` (§5.6.1) — foi para lá que migrou o antigo `Field.pos_filter`.

#### 5.6.1 `filter` — o painel de filtros é da página

O painel nasce do **tipo** de cada campo visível: `infer_filter_type` (não o autor) decide se um campo é eixo de filtro e de que tipo. Regra de motor: a chave derivada (`DK`) e os editores `multi`/`image` **não** filtram; o resto pega o `filter_kind` do input (`boolean`, `date`, `number`, `select`) e o fallback `options`→`select`.

O que a página **ajusta** mora em `Page.props` sob a chave `filter` (irmã de `list`), um dict com cinco chaves independentes:

| Chave | Forma | Efeito |
|---|---|---|
| `hidden` | fieldspec (`'campo'`, `'Ent.campo'`, lista, `{'Ent': [...]}`) | tira do painel — sem UI. Para uma coluna **visível** cujo filtro não faz sentido (ex.: `indice` em `operacoes`); um campo já no slot `hidden` nem chega aqui |
| `fixed` | `{campo: valor}`, lista ou `OR(...)`/`AND(...)` | vira **`WHERE` fixo**, também fora do painel. Dict e lista são **AND**; `OR(...)`/`AND(...)` agrupam (aninháveis). Valor: literal → `=`; sentinelas `NULL`/`NOT_NULL` (↔ `is_null`) e `EMPTY`/`NOT_EMPTY` (↔ `is_empty`); `('op', valor)` com `op` em `=`,`!=`,`>`,`>=`,`<`,`<=`,`like`,`ilike`,`in`,`not in`; lista → `IN`; callable é chamado; `None` **ignora** a folha. Folha que não é field do pool vale como **coluna** do model (ex.: `transferencia_id`, que não é `Field`). Era `pos_filter: 9` + `default` do `Field` — agora o valor mora **na página**, que é quem o usa |
| `default` | `{campo: valor}` ou `OR(...)`/`AND(...)` com valores de filtro | filtro **inicial editável**: nasce aplicado e marcado (**PADRÃO**); o painel deixa editar/remover as linhas em memória e, ao **limpar**, restaura o default **declarado**. `OR(...)`/`AND(...)` viram linhas em DNF (AND distribui sobre OR, limite de 128 linhas) |
| `types` | `{tipo: campo\|lista}` | **override** do tipo do widget, para um campo que a inferência classificaria de outro jeito (ex.: `{'checklist': 'status'}`). `tipo` ∈ `FILTER_TYPES` = `text`, `boolean`, `date`, `number`, `select`, `checklist` |
| `max_width` | `int` ou string CSS | **cap** de largura do painel — `int` vira `ch`, string CSS (ex.: `'72rem'`) passa como está. Sem a chave (ou `None`), usa o default interno **`88ch`** (`DEFAULT_FILTER_MAX_WIDTH`); o valor declarado pelo app vence. O layout é responsivo (quebra linha), sem rolagem horizontal |

`hidden`/`default`/`types` são validados contra o **pool** com o mesmo idioma dos slots (`resolve_filter_spec` reusa `slot_spec_items`/`_slot_match`): campo que não existe ou tipo de filtro desconhecido **quebra nomeando**. `max_width` é validado por `resolve_max_width` (`int` → `ch`; string CSS; qualquer outro tipo **quebra nomeando**); a ausência (ou `None`) usa `DEFAULT_FILTER_MAX_WIDTH` (`88ch`), e o valor declarado vence. Em `fixed`, a folha que casa com um field do pool entra no `hidden` do painel (filtro fixo não é editável); a que não casa é resolvida pelo compilador contra as **colunas do model** (`compile_fixed`) — nome que não é coluna quebra nomeando também.

**Sentinelas e agrupamento (`fixed`).** `EMPTY`/`NOT_EMPTY` espelham `is_empty` (`None`, branco ou coleção vazia): em coluna textual viram `col IS NULL OR trim(col) = ''`; nas demais, só `IS NULL`. `NULL`/`NOT_NULL` espelham `is_null` (só `None`, o NULL do banco) — a distinção é a mesma de `core/utils` (`utils.py:77-98`). O `AND` é o default de dict/lista; o `OR` é explícito por função:

```python
from ajsystem.defs.constants import NULL, NOT_EMPTY, OR, AND

'filter': {
    # AND implícito — o caso comum
    'fixed': {'tipo': 'P', 'transferencia_id': NULL},
}

'filter': {
    # tipo = 'P' AND (pedido_id IS NULL OR compra_id IS NULL)
    'fixed': AND({'tipo': 'P'},
                 OR({'pedido_id': NULL}, {'compra_id': NULL})),
}
```

> `OR(...)`/`AND(...)` recebem dicts de folhas ou outros grupos (aninhamento livre); `OR()` vazio ou item que não é dict/grupo quebra nomeando. Um dict **nunca** mistura folhas com grupo — o grupo é sempre um nó.

**A gramática literal é a mesma no relatório e na query.** `filter.fixed`, `report.body.filter` e `QuerySpec.where` passam pelo mesmo compilador (`core.filters.compile_conditions`): dict/lista = `E`, `OR(...)`/`AND(...)` aninháveis, sentinelas, operadores e `IN`. A diferença é só a origem do spec:

- `fixed` é declarado na página e também fecha o escopo do form;
- `body.filter` é o filtro padrão do relatório; o `filter` recebido por `print_report`/`filter_select` é combinado com ele — dois dicts fazem merge (a chave da request vence) e as demais formas viram `AND`; callable recebe o model e devolve o spec (Query só é aceita na fonte-entity, sem combinação; com `body.source` QuerySpec, devolve spec);
- `QuerySpec.where` e o `extra_where` do `run_query` usam a mesma gramática, com cast pelo tipo do `Field`.

`filter.default`, ao contrário, é um **valor de painel** (`{'preset':...}`, `{'mode':...}`, lista de checklist): ele é convertido para linhas do construtor em DNF, não compilado como literal SQL.

```python
'list': {
    'columns': 'Transacao',
    'master': 'Previsao',
    'hidden': ['cancelado', 'tipo'],
},
'filter': {
    'fixed': {'tipo': 'P'},                 # WHERE tipo = 'P' (era pos_filter: 9)
    'types': {'checklist': 'status'},       # status filtra por checklist (era pos_filter: 3)
},
```

> **Filtro fixo e escopo do form.** Um `fixed` não é só da listagem: `core.do_form` recusa abrir um registro que não casa com ele (`list_fixed_conds` resolve a mesma spec para o modelo do form). É por isso que o `tipo` de `pagar` continua não abrindo um lançamento de `receber` por URL direta — e que um movimento de transferência não abre pelo form de `pagamentos`/`recebimentos`.
>
> **Ponto único.** A prop inteira é lida por `core.filters.resolve_filter` (`spec → ResolvedFilter{hidden, fixed, default, types, panel, initial, default_filters, active, default_on, max_width, filter_cond}`), consumido por `do_list_normal`/`do_list_master` (render + `WHERE`) e por `list_fixed_conds` (guarda do form). Ninguém mais chama `resolve_filter_spec`/`compile_fixed` avulso; o compilador literal compartilhado é `core.filters.compile_conditions` (usado por `fixed`, `body.filter` e `QuerySpec.where`). `initial`/`default_filters` são **linhas** do PADRÃO e `active` são os **blocos** do usuário (ver abaixo); `filter_cond` é o `WHERE` já compilado — quando o default está ligado, o conector do **primeiro bloco efetivo do usuário** liga o PADRÃO ao root: `E` → `and_(default_cond, user_cond)` (o PADRÃO restringe) e `OU` → `or_(default_cond, user_cond)`. O conector não é aplicado duas vezes: `blocks_condition` ignora o primeiro conector do root e `rows_condition` ignora o primeiro de cada bloco.

**Exemplo (Pagar/Receber).** No `master` a linha é a **previsão** e o pai é a transação: `data` é coluna do pai, `vencimento`/`saldo` são da linha. O default combina os três com `OR` e nasce ligado ao filtro do usuário com `AND`; o primeiro E/OU do bloco do usuário pode trocar essa junção para `OR`:

```python
from ajsystem.defs.constants import OR

'filter': {
    'fixed': {'tipo': 'P'},
    'types': {'checklist': 'status'},
    'default': OR(
        {'data': {'preset': 'mes_ano'}},
        {'vencimento': {'preset': 'mes_ano'}},
        {'saldo': {'mode': 'maior_que', 'val1': 0}},
    ),
},
```

`saldo` é uma `@hybrid_property` em `Previsao` (expressão SQL com `coalesce`), então o mesmo nome serve para ordenar e filtrar a linha; a exibição usa o `calc` nulo-seguro com a mesma conta — o default `saldo > 0` usa o saldo **da previsão** (`previsto + variacao - realizado`), não o agregado da transação. O checkbox **PADRÃO** desliga esse bloco (`_d=0`); as três linhas são somente leitura.

**O painel é um construtor de consulta em linhas e blocos.** A **linha seguinte** é o único ponto de adição: ela mostra primeiro só o campo (lista vazia) ou só o select E/OU (já há itens); escolhido o E/OU, a linha completa abre com campo, modo e valor. `E`/`OU` adiciona uma **linha solta**; `E (`/`OU (` abre um **bloco agrupado**. O `)` ao lado do select fecha o bloco aberto ou agrupa a sequência final de linhas soltas. Dentro de um bloco, as linhas escolhem **E**/**OU** com a linha anterior; o **E** tem prioridade (`a E b OU c` = `(a AND b) OR c`). O desenho é de **um nível**: blocos de linhas, sem bloco dentro de bloco.

- **Abertura e fechamento.** O `(` fica no início da **linha de abertura** do bloco agrupado; o `)` fica no fim da **linha divisória inferior**, nunca nas linhas de condição. Linha solta não tem moldura. O botão `)` da linha de adição só aparece quando há bloco aberto ou sequência final de linhas soltas para fechar/agrupar; ao agrupar, ele cria a moldura.
- **Adição e rodapé.** A linha compacta de adição fica **abaixo do bloco**, fora do container do bloco, e mostra `+` no select até a escolha do E/OU; na primeira linha, o select de campo ocupa a coluna `campo` da grade (não a linha inteira). Ao adicionar dentro de bloco agrupado aberto, a grade de edição entra **acima do `)`**, dentro da moldura. Na grade de edição, `[+]` confirma a linha e **rearma o editor no mesmo alvo** (bloco agrupado ou sequência solta); `[)]` confirma e fecha o bloco agrupado, ou agrupa a sequência solta; `[✕]` cancela. Linha solta não tem cabeçalho/rodapé (o `[✕]` da própria linha exclui); bloco agrupado abre com `( ———` e fecha com `——— )`, que **não somem** durante a edição/adição, com o `[🗑]` aparecendo quando não há edição em curso.
- **PADRÃO é somente leitura.** O primeiro bloco é o PADRÃO, com as linhas declaradas e apenas o checkbox de ligar/desligar na linha de abertura. Não tem `[✎]`, `[✕]` nem `[🗑]`; a moldura fecha com `)` sem lixeira. Desligado, as linhas e a moldura somem, mas a linha de abertura com o checkbox continua visível; ligado, o conector do primeiro bloco do usuário (`E`/`OU`) o liga ao root.
- **Um nível cobre os casos comuns.** `(A E B) OU (C E D)` são dois blocos; `A E (B OU C)` também são dois (o primeiro com `A`, o segundo com `B OU C`). Não é possível aninhar `A E (B OU (C E D))` sem blocos dentro de blocos — fica para uma próxima extensão.
- **Vazio não vai para a URL.** Linha solta fica em bloco `g:false` (sem moldura, podendo acumular linhas); bloco agrupado leva `g:true`. Linha/bloco sem valor é descartado no **APLICAR**. O servidor tem limites de 32 blocos e 128 linhas (linhas soltas contam como blocos) e recusa bloco vazio ou estruturalmente inválido.

A URL carrega os blocos no arg reservado **`_f`**:

```json
[
  {"c": "and", "g": false, "rows": [
    {"f": "data", "c": "and", "v": {"preset": "mes_ano"}}
  ]},
  {"c": "or", "g": true, "rows": [
    {"f": "saldo", "c": "and", "v": {"mode": "maior_que", "val1": 0}},
    {"f": "documento", "c": "or", "v": {"mode": "contains", "value": "NF"}}
  ]}
]
```

- No **bloco**, `c` é o elo com o bloco anterior (`and`/`or`); no **primeiro** bloco ele é o elo com o PADRÃO quando ligado (sem PADRÃO, é ignorado). `g` é só visual: `false` é linha solta (um bloco de uma linha), `true` é bloco agrupado; ausente vale `true` para manter o formato antigo. Na **linha**, `c` é o elo com a linha anterior dentro do bloco; na primeira linha ele é ignorado. `v` mantém o shape antigo (texto `{mode,value}`, número `{mode,val1,val2}`, data `{preset,from,to,mes,ano}`, select/boolean escalar, checklist lista).
- Campo fora do painel, conector inválido, `g` não booleano, bloco vazio, mistura de bloco/linha ou JSON malformado **quebra nomeando** (`filter: _f[i].rows[j] campo ...`, `_f[i] bloco vazio`, `_f[i].g esperava booleano`). Nada é descartado em silêncio.
- **Compatibilidade.** O `_f` antigo, uma lista plana de `{f,c,v}`, continua válido: vira **um** bloco com o conector da primeira linha (parênteses em volta de tudo não mudam a expressão). Sem `_f`, os args por campo do painel antigo (`campo`, `campo_value`, `campo_mode`, `campo_val1/2`, `campo_preset`, `campo_from/to/mes/ano`) viram um bloco em **E**.
- **Motor.** `parse_json_blocks`/`parse_blocks` leem os blocos; `rows_condition` compila as linhas de um bloco (primeiro conector ignorado); `blocks_condition` compila o root (primeiro conector ignorado) e `first_block_conn` acha o conector do primeiro bloco efetivo para a junção com o PADRÃO. `resolve_filters` devolve `(initial, edited, active, default_on)` com `active` em **blocos**; `do_list` aplica `filter_cond` uma única vez.

**A seção PADRÃO.** Quando a página declara `default`, o topo do painel ganha o bloco **PADRÃO** com as linhas do default, **somente leitura**: não edita, não remove e não recebe "adicionar" (adições vão para o bloco do usuário). Nasce **ligada**; o checkbox na linha de abertura a desliga. O único estado dele na URL é:

- **`_d`** — `0` desliga o PADRÃO; ausente ou `1` liga. Desligado, `filter_cond` é só o filtro do usuário.
- O antigo `_df` (linhas editadas em memória) **não é mais enviado** pela tela. `_f` continua sendo só o filtro do usuário; o cliente não semeia o default nele.

**LIMPAR** descarta os blocos do usuário, restaura as linhas **declaradas** do PADRÃO e marca o checkbox; só tem efeito ao **APLICAR**. O `canClear` compara o PADRÃO atual com o **declarado** (como ele não é editável, na prática acende com filtro do usuário ou PADRÃO desligado). **APLICAR** confirma a linha seguinte já preenchida, serializa linhas soltas (`g:false`) e blocos (`g:true`), descarta os vazios e remove os args legados. `default` aceita um dict (AND das folhas) ou `OR(...)`/`AND(...)` com valores no shape do painel: o motor converte para **DNF** (`AND` distribui sobre `OR`) e limita a 128 linhas. O valor numérico `0` conta como preenchido (o `hasValue` testa `!== ''`, não truthiness) — é o que faz `saldo > 0` funcionar.

**Catálogo do `date` (14 presets).** `Mês atual`/`Mês anterior` olham **só o mês** (o ano não importa — aniversariantes); `Mês/Ano atual`/`Mês/Ano anterior` olham **mês e ano** (vencimentos) e o widget pré-preenche mês/ano (o "anterior" já vem com o mês anterior). Presets sem parâmetro (`hoje`, `ontem`, `ultimos_7_dias`, `mes_atual`, `mes_anterior`, `mes_ano`, `mes_ano_anterior`, `ano_atual`, `ano_anterior`) não pedem entrada; os demais pedem `mes`, `ano`, `from`/`to` ou ambos:

| Preset | Condição |
|---|---|
| `hoje` / `ontem` | `data = hoje` / `data = hoje - 1` |
| `ultimos_7_dias` | `hoje-6 <= data <= hoje` |
| `mes_atual` / `mes_anterior` | `EXTRACT(month) = mês` (só mês) |
| `mes_ano` / `mes_ano_anterior` | `EXTRACT(month) = mês AND EXTRACT(year) = ano` |
| `mes` | `EXTRACT(month) = mês` informado |
| `ano_atual` / `ano_anterior` | `EXTRACT(year) = ano` |
| `ano` | `EXTRACT(year) = ano` informado |
| `ate_a_data_de` / `a_partir_de` | `data <= to` / `data >= from` |
| `periodo` | `from <= data <= to` (extremidade vazia é aberta) |

Preset com valor vazio devolve `[]` (linha sem condição) — por isso a linha só é confirmável quando tem valor.


#### Props

| Prop | Tipo | Default | Impacto |
|---|---|---|---|
| `fields` | `list[Field]` | — | colunas + card, na ordem `line` + `card`; o motor resolve via `normalize_fieldspec` antes de criar o `List` |
| `fields_master` | `list[int]` | — | **computado** — índices de `fields` que são colunas da linha (as demais vão para o card) |
| `edit_endpoint` | `str` | `None` | endpoint do ícone de editar; `None` esconde a ação |
| `edit_id_field` | `str` | `'id'` | campo usado na URL de edição |
| `detail_data` | `str` | `None` | fonte dos campos de detalhe do card |
| `buttons` | `str\|Button\|list` | `None` | mesmos formatos de `Form.buttons` | `List.resolve_buttons` |
| `template` | `str` | `None` | template alternativo |
| `master` | `str` | `None` | entidade da **linha** na inversão; `columns` passa a ser o pai |
| `line_idx` | `list[int]` | `None` | **computado** — índices em `master_fields` das colunas pinadas por `line`; o `<th>` ganha `data-pinned` |
| `card_idx` | `list[int]` | `None` | **computado** — índices de `fields` que caem no card |

> `fields_master`, `line_idx` e `card_idx` saem do `do_list.py` (`list_obj = List(...)`). **Não** os declare à mão: a engine sobrescreve. `line`/`card`/`hidden` são declarados na **página** (`Page.props.list`), não aqui.

#### `line` e a largura da tela

`line_idx` vira `data-pinned` no `<th>`, e o `fitListColumns` (`pages/list.html`) semeia o `keepIdx` com essas colunas **antes** de preencher o resto por largura — são elas que nunca saem quando a tela estreita. Sem `line` declarado vale a prioridade antiga (a primeira coluna de dados fica sempre). O marcador é um **atributo**, não um nome, porque com `master` a mesma tabela tem dois `data-field="id"`.

Todo campo da grade ganha `<td>` no servidor; quem some é o cliente (classe `col-hide`), e a cópia `of-dyn` na linha expansória garante que a coluna não se perca. Antes havia **dois** mecanismos que podiam discordar: o `<thead>` emitia `<th>` para todas as `cols` enquanto o `<td>` saía só para as de `linha`, desalinhando a tabela.

> `columns` da página (`Page.props.list`) aceita query dict no lugar da entidade (`columns=QPLANO`, ver 5.10.1): os dados vêm do `qrun` e a entrada declara `label`/`width`/`align`/`format`. Com ordem própria, a query entra como item da lista (`columns=[QPLANO, 'id', 'indice', ...]` — no máximo uma query por lista; strings autoritativas, fora do `select` quebra nomeando). Nesse modo `field_id` é exigido para editar (ausente = só-leitura; declarado tem que estar no `select` e ser pk, senão quebra nomeando). Sem query, `edit_id_field` (`'id'`) e o resto seguem como antes. A entrada **não** posiciona campo: quem decide é a página, nos slots.

#### 5.6.2 `report` — a aba Relatórios (PDF por entrada)

A aba `{'Relatórios': {'type': 'Report'}}` existe para **gerar PDFs sem sair da listagem**. Quem a alimenta é `Page.props.report`, irmã de `list`/`filter`, lida por `page_report_cfg` (`defs/data.py`). Só é resolvida quando alguma aba é do tipo `Report`; sem a prop, a aba mostra o vazio (`NO_FILTERS`).

```python
'report': {
    'Saldo de Contas a Receber': {
        'report': SALDO,                  # spec que o print_report já aceita
        'filter': {
            'conta_id': '=',
            'vencimento': '<>',
            'valor': '>=',
        },
    },
},
```

Cada entrada exige a chave `report` (o dict/`Report` impresso, como em 5.7) e aceita `filter` opcional, que declara **quais campos viram inputs** e **com que operador**. O título é o rótulo do accordion e também a origem do **slug** usado na URL (`Previsão de Contas a Receber` → `previsao-de-contas-a-receber`); dois títulos que gerem o mesmo slug quebram nomeando.

**Formas de `filter`.** Como no resto do motor, aceita a família fieldspec (`'campo'`, `'Entidade.campo'`, lista, `{'Entidade': [...]}`), tudo com `=` implícito, **ou** o dict `{campo: operador}`. O nome cru segue a regra da §5.6 (entidade de `columns` → único no pool → ambiguidade decide pela entidade de `columns`), então `'vencimento'` e `'Transacao.vencimento'` convivem. Operador fora do vocabulário, campo que não é eixo de filtro e operador incompatível com o tipo do campo **quebram nomeando** o caminho (`Page.props.report['Título'].filter['campo']`).

| Operador | `text` | `number` | `date` | `select`/`checklist` | `boolean` |
|---|---|---|---|---|---|
| `=` | igual | igual | **na data** (um dia) | igual / contém | igual |
| `!=` | diferente | diferente | diferente | diferente / não contém | diferente |
| `>` | — | maior | **a partir de** (`>=`) | — | — |
| `>=` | — | maior ou igual | **a partir de** (`>=`) | — | — |
| `<` | — | menor | **até** (`<=`) | — | — |
| `<=` | — | menor ou igual | **até** (`<=`) | — | — |
| `like` | contém (`%v%`) | — | — | — | — |
| `<>` | — | **entre** (Valor 1/Valor 2) | **período** (De/Até) | — | — |

Dois detalhes fecham a semântica: em `date`, `>`/`<` são **inclusivos** (compilam como `>=`/`<=`, porque "a partir de"/"até" incluem a data); em `number`, o comparador é literal e `<>` vira duas folhas (`>=`/`<=`) montadas só com as pontas preenchidas. `text` recusa `<>` e comparadores de ordem — texto se filtra por igualdade ou `like`.

**Na tela.** Um accordion por entrada; abrir um cartão mostra os inputs daquele relatório (`Alpine`, sem request). O rótulo do campo vem do `Field`, o complemento vem do catálogo (`FILTER_EQ`, `FILTER_FROM`, `FILTER_PERIOD`…), e o widget segue o tipo: texto, número, data, `select` (options do `Field`/lookup), `checklist` (múltiplo, quando `filter.types` da página o declara) ou `boolean`. `date`/`<>` vira De/Até e `number`/`<>` vira Valor 1/Valor 2. **LIMPAR** zera só o cartão; **GERAR** faz o fetch. Nada disso toca `_f`/`_r`/`auto_report` da listagem: o PDF usa o próprio overlay (`report-content`) e o botão voltar não recarrega a página.

**Endpoint.** `GET /ajsystem/report-action?page=<rota>&rp=<slug>` + os inputs do cartão; devolve JSON `{html}` com o fragmento do overlay, exatamente como `list_action`. O motor relê a página pelo slug (regex `[A-Za-z0-9_]+`, módulo `app.routes.sys.<rota>`), resolve a entrada pelo `rp` e converte os args em **spec literal** da gramática compartilhada (`core.filters.compile_conditions`): `select`/`boolean`/`checklist` viram `in`/`not in`, `like` ganha `%...%`, `date` envia ISO e é convertido para `date` antes de compilar, campo vazio ignora a folha e o resultado é um `AND` (as duas folhas, quando `<>`). Essa spec vai como `filter=` para `print_report(..., _printing=True)` e é **combinada** com o `body.filter` do relatório (`_combine_report_filter`), então o relatório mantém o `WHERE` próprio. Erro de impressão volta como fragmento de erro dentro do `html`; parâmetro inválido ou relatório desconhecido devolve 400/404.

### 5.7 `Report` — `ajsystem/defs/report.py:135` `class Report`

| Prop | Tipo | Default | Valores | Impacto |
|---|---|---|---|---|
| `label` | `str` | — | título | cabeçalho do PDF |
| `page_size` | `str` | `'A4'` | `'A4'`, `'Letter'`… | `fpdf` |
| `orientation` | `str` | `'portrait'` | `'portrait'`, `'landscape'` | `fpdf` |
| `lpi` | `int` | `6` | `6` (4,2333mm/linha) · `8` (3,1750mm) | **grade vertical do documento inteiro** — o corpo da fonte (`60/LPI`) e a altura da linha saem daqui; normalizado e validado na construção do PDF |
| `header` | `dict\|list` | `None` | `{logo, title, fields:[...]}` (legado) ou `[...]` (5.8.1, `LOGO`/`TITLE`/`FIELD`/…) | `do_report.py:_apply_entity` resolve `label` via `Entity`; dict legado sintetiza a lista |
| `body` | `dict\|ReportBody` | `None` | ver 5.8 | fonte dos dados |
| `footer` | `bool\|dict` | `None` | `True` = atalho das 3 flags · `{show_user, show_datetime, show_page_number, show_company, text, separator, cpi, style, align}` | rodapé do PDF, na **última linha** da página — ver 5.8.2 |
| `texts` | `dict\|list` | `None` | `ReportText` — ver 5.8 | blocos de texto avulso |
| (template standalone) | — | `PRINT_TEMPLATE` (`components/print_default.html`) | fixo no motor | página standalone (`print_report_page`); a chave legada `print_template` é ignorada no parse |
| (fragmento) | — | overlay do framework (`print_overlay.html`) | fixo no motor | `print_report` injeta sempre com alternância do container; a chave legada `print_fragment_template` é ignorada no parse |
| (logo) | — | `APP.logo` (relativo a `static/`) com fallback `LOGO_FALLBACK` | `App.logo` / constante | logo do cabeçalho (`do_report._resolve_logo`); a chave legada `logo_path` é ignorada no parse |
| (orientação mutável) | — | — | — | removida; a chave legada `orientation_mutable` é ignorada no parse |
| `margin_top`/`margin_bottom`/`margin_left`/`margin_right` | `num` | `10` / `20` / `10` / `10` | mm | margens do PDF |
| `auto_page_break` | `bool` | `True` | quebra automática de página | `fpdf` |
| `show_table_lines` | `bool` | `False` | grade da tabela | `fpdf` |

Chaves de `body` e `filter` (usadas no exemplo abaixo) resolvem contra o `Entity` do módulo:

| Chave | Tipo | Valores | Impacto |
|---|---|---|---|
| `body.source` | `str\|dict` | `'Tarefa'`, `{'entity':...}` (legado) ou query dict `{select,dist,from,...}` (5.10.1) | `_infer_source` + `_auto_data`; na query, o filtro entra **antes** dos `OVER`s, então a numeração enxerga o recorte |
| `body.order` | `str\|list\|None` | `['vencimento','id']`, `[1,2]` (índices 1-based sobre `body.table.columns`), `'cliente desc'`, `'vencimento'` | sobrescreve `source.order` na hora da impressão, sem mutar o dict original da query. Índices numéricos mapeiam para a posição na lista de colunas do relatório (não do `select`). Strings são nomes explícitos de coluna/campo, com ` desc` opcional. `source.order` continua resolvendo índices sobre o `select` da fonte |
| `body.filter` | `dict\|list\|OR/AND\|callable` | `filter_select('tipo')` | filtro padrão do `source`; mesma gramática literal de `filter.fixed` (cast tipado). Quando declarado, **sobrescreve o `where` da source/query** (o `where` original é descartado); o `filter` recebido por `print_report`/`filter_select` é combinado com ele — dicts fazem merge e as demais formas viram `AND`. Callable recebe o model e devolve o spec; Query é aceita só na fonte-entity, sem combinação (com `body.source` QuerySpec, devolve spec). Aplicado **antes** dos `OVER`s e da ordenação |
| `body.table.columns` | `dict\|list` | `{'titulo':{}}` ou `['indice','nome',{'id':{'width':6}}]` (forma enxuta igual ao `select`) | `_apply_entity` herda `label`/`calc`/**`width`** da `Entity` (Schema vence); coluna computada na query usa o attr direto. **Sem `width`, a coluna mede o field** (mesma conta da listagem, com a máscara como mínimo) e a soma é centralizada na área útil — declarar é exceção, não obrigação |
| `body.table.groups` | `dict\|list` | `{'cliente':{text:'Cliente: {cliente}',on_start:{'lf':-1},on_finish:{'lf':1,'totais':True}}}` | **Modelo único (obrigatório):** `on_start`/`on_finish`. **control-break** por campo (a ordem das quebras deve seguir a ordem em `order` da fonte). Props: **`text`** (título/template do grupo; se ausente, imprime o valor do campo), **`pos`** (`POS_NONE`/`0`/`False` oculta **apenas o rótulo/cabeçalho** impresso em `on_start`; não afeta quebra, acumuladores, propagação ou totais), **`on_start`** (dict ao abrir: `text`, `lf`, `align`, `style`, `cpi`, `pos` — herda do grupo se ausente). **`on_finish`** (dict ao fechar: `text`/`footer_text`, `lf`, `align`, `style`, `cpi`; **`totais`** define a linha de subtotal). **Acumulação hierárquica:** ao abrir, zera o acumulador do nível e de todos os níveis abaixo; acumula em todos os níveis vigentes por linha; ao fechar propaga filho→pai ou filho→total geral da tabela (em modo agrupado o total geral **não** é somado por linha). **Totais:** só são impressos quando o fechamento vem de **`on_finish`** e possui **`totais`**. `totais` = `None` não imprime, `True` imprime totais nas colunas com `agg` com label padrão `'Subtotal'`, `dict` sobrescreve `label/align/span/bline`. `lf` no grupo respira ao redor do título/linha visível (`-n` antes, `n` depois, `[antes,depois]`). Itens de `columns` têm seu próprio `pos` (`POS_ROW` default, `POS_INLINE`, `POS_TITLE`, `POS_TITLE_CENTER`, `POS_NONE`) para onde aparecem. **Formatos legados (`on`/`action`/`pos` numérico/`place`/`total`) não são mais traduzidos e geram erro.** |
| `when` (item) | `str` | `{'TEXT': {'text': '…', 'when': 'evento.tipo'}}` | imprime só se o path (pontilhado ok) for truthy; ausente = sempre |
| templates | — | `'{total:brl}'`, `'{a.b}'`, `'{?c:…}'`, `'{x\|dflt}'` | `:brl` moeda; path pontilhado com navegação segura; `\|dflt` fallback; labels LIST da Entity |
| fluxo | — | `FIELD`/`TEXT` seguem na linha | **cada item ESTACIONA na borda do que desenhou** e o próximo desce sozinho se a linha não tem mais lugar — ver **Estacionar**; `PCOL` avança pela largura; `pcol+largura>ncol` envolve; maior que a linha trunca; quebra por `rows_after/before` ou posicionamento; sem âncora, `FIELD`/`TEXT` com `width` herda o cursor da zona (só volta à 1ª coluna se o cursor está fora da zona), `TEXT` avulso sem `width` é linha própria (avanço de linha automático quando o fluxo terminou antes dela; `align` vale na zona) e bloco (`IMAGE`/`LINE`/…) volta ao início; sub-item de `TEXTS` flui apertado inline. O "início" é o da **zona**, não o da margem — ver **Zona do logo** |
| `body.table.totals` | `dict` | `{'label':'TOTAL GERAL','align':'R','span':3}` | linha de total geral (sempre, com régua antes e depois — internas). `agg` na coluna diz O QUÊ; sem `totals` não totaliza. Legado `footer/footer_label` via shim. Réguas seguidas sem conteúdo entre elas saem uma vez só |
| `body.table.extend` | `list` | `[(col\|[a,b], texto[, props]), 'LINE', 'LF', 'CR']` | linhas **dentro do quadro** depois dos totais (ex.: Acréscimo/Desconto/Total). `when` por linha; placeholder puro `{campo}` herda o `format` da coluna; `font`/`cpi`/`lpi`/`font_size` recusados (a grade da tabela é dela) |
| `body.table.hierarchy` | `list\|dict` | legado (derivado de `groups` quando ausente) | mantido por compat; prefira `groups` |
| `body.filter` | `dict\|list\|OR/AND\|callable` | `filter_select('tipo')` | filtro padrão do `source`; mesma gramática literal de `filter.fixed` (cast tipado). Quando declarado, **sobrescreve o `where` da source/query** (o `where` original é descartado); o `filter` recebido por `print_report`/`filter_select` é combinado com ele — dicts fazem merge e as demais formas viram `AND`. Callable recebe o model e devolve o spec; Query é aceita só na fonte-entity, sem combinação (com `body.source` QuerySpec, devolve spec). Aplicado **antes** dos `OVER`s e da ordenação |

> **Inputs de data na aba Relatórios.** Os inputs `date` da aba Relatórios (renderizados em `list.html` dentro de `.report-card`) são `type="text"` com placeholder `dd/mm/aaaa` para permitir digitação parcial. Enquanto digita, a máscara automática insere barras: `1002` → `10/02`; `10022026` → `10/02/2026`. Ao sair do campo (blur), o preenchimento automático completa com mês/ano corrente quando faltar parte: `10` → `10/10/2026`; `10/02` → `10/02/2026`. O botão de calendário ao lado (`dtOpenPicker`) chama o `showPicker()` nativo do navegador e grava o valor no formato brasileiro. No servidor, `report_filter_from_args` aceita tanto `YYYY-MM-DD` quanto `dd/mm/aaaa`.

### 5.8 `ReportColumn` e amigos — `ajsystem/defs/report.py`

**`ReportColumn`** (`:34`) — 10 props (novas: `pos`, `text`, `suppress`):

| Prop | Tipo | Default | Valores | Impacto |
|---|---|---|---|---|
| `field` | `str` | — | `'qtd'` ou `'produto.nome'` | `data_key` |
| `label` | `str` | `None` | texto; sem ela, `_auto_label`/Entity/entrada do `select` | cabeçalho da coluna |
| `width` | `float` | `None` | `ch` | coluna no PDF. Ausente = a do field (`field.width` / máscara / maior palavra do rótulo, via `field_width_ch`); a soma define a tabela e ela é centralizada. O texto é cortado no que cabe na grade — **nenhuma coluna escreve na vizinha** |
| `align` | `str` | `'left'` | `left,center,right` | herdado do `Field.align` (`NUM`→`right`) |
| `format` | `str` | `None` | formato de data/número | render da célula. `format` do relatório vence; sem ele, a `mask` do Field (Entity/Schema/query/catálogo, ou numérica de `decimals` com milhar) manda; a inferência por type é o último recurso (moeda vem da `mask` via `@M(id)`) |
| `agg` | `str` | `None` | `sum/count/avg/min/max` | O QUÊ somar (só impressão; o ONDE vai em `totals`) |
| `function` | `callable` | `None` | `lambda row:` | usa `Entity.calc` se ausente (coluna computada na query usa o attr) |
| `text` | `str` | `None` | template `'{campo}'`/`{x:02d}`/`{?cond:…}` (6, `core/text.py`) | monta a célula (ex. código) |
| `suppress` | `bool` | `False` | repete valor só na 1ª linha do grupo | `place:0` do `groups` |
| `pos` | `int` | `POS_ROW` (1) | `POS_NONE` (0), `POS_ROW` (1), `POS_INLINE` (2), `POS_TITLE` (3), `POS_TITLE_CENTER` (4). **Em grupos (nível `on_start`):** `POS_NONE` oculta **apenas** o rótulo/cabeçalho ao abrir; agrupamento, quebra, acumulação, subtotal em `on_finish.totals` e propagação filho→pai/total geral **permanecem**. **Em colunas:** controla onde/imprime o valor: `POS_ROW` = coluna da tabela (faz parte do cabeçalho, define largura/fonte — default), `POS_INLINE` = não é coluna, imprime no início da linha sem separação de colunas, `POS_TITLE` = não é coluna, título do grupo alinhado à esquerda antes do corpo da tabela, `POS_TITLE_CENTER` = título do grupo centralizado, `POS_NONE` = campo de controle, não sai no relatório |

**`ReportField`** (`:13`) — 5 props, spec de campo solto (fora de `columns`): `field`, `label`, `align` (`left`), `format`, `function`.

**`ReportGroup`** (`:66`) — 6 props: `field`, `text`, `on_start`, `on_finish`, `pos`, `totais`. **Modelo único e obrigatório** (sem tradução para formato legado).

- **`field`** (`str`) — campo chave do grupo.
- **`text`** (`str\|None`) — título/template do grupo (`'{cliente}'`). Se ausente, imprime o valor do campo.
- **`on_start`** (`dict`) — props ao abrir o grupo: `text`/`lf`/`align`/`style`/`cpi`/`pos`. `pos` é opcional; se ausente usa `pos` do próprio grupo ou `POS_ROW` (1). Se `pos` for `POS_NONE`/`0`/`False`, **apenas o rótulo/cabeçalho fica oculto**; o agrupamento continua totalmente funcional (quebra, acumulação, subtotal em `on_finish.totals`, propagação).
- **`on_finish`** (`dict`) — props ao fechar o grupo: `text`/`footer_text`/`lf`/`align`/`style`/`cpi`/`totais`.
  - **`totais`** (`None|True|dict`) — controla a linha de subtotal ao fechar. `None` não imprime, `True` imprime totais nas colunas com `agg` com label padrão `'Subtotal'`, `dict` sobrescreve `label/align/span/bline`.
- **`pos`** (`int`) — onde o título do grupo é impresso ao abrir (em `on_start`). Valores: `POS_ROW` (1, default), `POS_INLINE` (2), `POS_TITLE` (3), `POS_TITLE_CENTER` (4), `POS_NONE` (0). **Em grupos:** `POS_NONE` oculta **apenas** o rótulo ao abrir, não afeta totais/quebra/propagação. **Em colunas:** controla impressão do valor da coluna como de costume.
- **`totais`** (`None|True|dict`) — só tem efeito quando o nível vem de `on_finish`. `None` não imprime, `True` usa label `'Subtotal'` nas colunas com `agg`, `dict` sobrescreve padrões.

**Não são mais suportados formatos legados** (`on`, `action`, `pos` numérico, `place`, `total`). Estes levantam `ValueError` em `_translate_legacy_group`. Use apenas `on_start`/`on_finish/pos/text/lf/totais`.

**`ReportText`** (`:78`) — 5 props: `text` (obrigatório), `font_size` (`10`), `font_style` (`''`), `align` (`'L'`), `when` (`end_of_report`; também `start_of_report`/similar). Bloco de texto avulso, usado por `Report.texts`.

**`ReportBody`** (`:88`) — 8 props: `source`, `form`, `table`, `before`, `after`, `filter`, `levels`, `items`. `before`/`after` inserem blocos ao redor da tabela; `levels` é numeração hierárquica legada (prefira `select` com `over` + `table.groups`); `items` = lista unificada abaixo.

#### 5.8.1 Items de impressão (`header=[...]`, `body.items`)

String pura ou dict unitário = `FIELD`; MAIÚSCULA = elemento (`None` = nu). Factories puras (`defs/report.py`, tradução 1:1 validada pelo mesmo normalizador):

| factory | equivale a | exemplo |
|---|---|---|
| `'nome'` / `{'total': {...}}` / `FIELD(nome, props?)` | `FIELD` | `'cliente_nome'`, `FIELD('data_pedido', {'tab': 2})` |
| `TITLE(texto?, props?)` | `{'TITLE': {'text': texto, ...}}` | `TITLE()` = nu (texto = `label`, sempre centrado salvo `align`); `width` em cols (sem = até o fim da linha); `style` por título; `options` = catálogo próprio (vence o do field); `mask` = **transform de texto**, e vem `@U` por padrão (título em caixa alta — `mask: ''` devolve como está) |
| `TITLES([...])` | `{'TITLES': [{'TITLE': {...}}, ...]}` | Vários `TITLE` numa tacada: `'texto'`, `('texto', {props})`, callable ou `{'TITLE': {...}}`. Vale em **qualquer prop que seja lista de items** (`header`, `items`, `before`, `after`, `table.after`). A cascata é posicional e o `when` vem **antes** dela |
| `TEXT(texto, props?)` | `{'TEXT': {'text': texto, ...}}` | `TEXT('Obs: …', {'lf': -1})` — a chave é **`lf`**, em **linhas**: negativo é ANTES, positivo é DEPOIS, e `[antes, depois]` cobre os dois. `before`/`after`/`rows_before`/`rows_after` saem — declará-las dá erro |
| `LOGO(ancora, linhas)` | `{'LOGO': {'location': [ancora, linhas]}}` | `LOGO('L', 3)` (âncoras `C/L/R`; ausente não renderiza). `L` encolhe a zona pela borda direita da figura, `R` pela esquerda, `C` não indenta — vale enquanto o cursor estiver na faixa vertical da imagem, e `IND()` cancela ali mesmo |
| `TABS(*args)` | `{'TABS': {...}}` | **Duas coisas, pelo tipo do 1º argumento.** `TABS(5, 35)` (números ou `PCOL`/`NCOL±N`) **define as paradas**, em cols do **início da zona**, crescentes; `TABS()` restaura. `TABS('a', '', 'b')` (texto) **imprime um elemento por parada**, na gramática do `TEXTS`. Ver **Tabulação imprime** |
| `POS(col, lin)` | salto avulso do cursor | `POS(22, 0)` |
| `CPI(base?, flags?)` | diretiva de **grade** na horizontal (`defs/fonts.py`), o contexto decide | `CPI(12)`, `CPI(12, 'EC')`; nu restaura o padrão (10 CPI). `base` é um dos **três modos base** (10 Pica · 12 Elite · 15 Micron) e `flags` o modificador — ver **A matriz**. As props `cpi`/`flags` valem por item. **O eixo vertical não tem diretiva**: o LPI é a prop `lpi` do report (§5.7), porque a linha é uma só para o documento inteiro |
| `PROW(n?)`/`PCOL(n?)` | **função com dois papéis** (`defs/report.py`), o contexto decide | **valor**: `PCOL()`/`PROW()` = posição corrente em grade, em `TABS`/`location`/`pos` (e ainda soma: `PCOL() + 5`). **Diretiva**: `PCOL(n)`/`PROW(n)` solto na lista de items move o cursor — `n` cols do início da **zona**, `n` linhas da margem de topo. `'PCOL+20'` (string) segue válida em `TABS` |
| `LTB`/`RTB`/`NCOL` | constantes (bordas da última tabela; área útil se nenhuma) | `IND([LTB, RTB])`; `NCOL` = cols da área útil |
| `IND([l, r])` / `IND()` | região do fluxo (não-negativos, `l<r`, dentro da área) | sem âncora flui dentro; `IND()` restaura; escopo por render |
| `MEMO(campo, width, props?)` | **um FIELD com medida**: quebra por palavra numa `width` e **centraliza na área livre** | `campo` na gramática de field (`'x'`, `('x', {...})`, `{'x': {...}}`); com `{` vira template. `align` L/C/R/**J (default)**; `options` = override de catálogo; `label` = **prefixo da 1ª linha** (ver abaixo); `recuo` afasta só a 1ª linha |
| `LINE/BOX/CIRCLE(*args)` | grid em números: `LINE(c, r, +cols, +rows[, 'queda'])`; uma lista solta também vale | ver **Régua e formas posicionadas** abaixo |
| `IMAGE(campo, props?)` | `{'IMAGE': {'field': campo, ...}}` | `IMAGE('foto', {'location': [...]})` |
| `FIELDS(*itens)` | expande itens de campo; cada um resolve como `columns`/`fields` (list/form) | `FIELDS('cliente_nome', ('data_pedido', {'tab': 1}))` — item `'campo'` ou `('campo', {props})`; `'Entidade'` expande; `'Entidade.campo'` relacionado |
| `TEXTS(*itens)` / `CR()` / `LF(n?)` / `FF()` | bloco de textos; retorno; avanço; quebra de página (corpo) | `CR` = volta à 1ª coluna; `LF()` = 1 linha; `FF` no header = erro |

**Matriz de props por item.** O que cada kind aceita, o que ele **recusa** e o que **ignora calado** — as três coisas importam, porque prop ignorada é a que dói: o autor acredita que valiu e o documento sai diferente do que ele pediu.

| prop | FIELD | TEXT | TITLE | MEMO | IMAGE | LINE/BOX/CIRCLE | LF | FONT |
|---|---|---|---|---|---|---|---|---|
| `text` | template | obrigatório | sim | ou `field` | — | — | — | — |
| `label` | sim | — | rótulo alternativo | **prefixo da 1ª linha** | — | — | — | — |
| `align` | `L` | `L` | **`C`** | **`J`** | — | — | — | — |
| `width` (cols) | sim | sim | sim | **obrigatório** | — | `LINE(w)` | — | — |
| `wrap` | sim | sim | ignora | ignora | — | — | — | — |
| `when` | sim | sim | sim | sim | sim | sim (posicional final) | sim | — |
| `options` | sim | — | sim | sim | — | — | — | — |
| `function` | sim | — | — | — | — | — | — | — |
| `format` / `mask` | sim | — | `@U` no `TITLE` (só `@U`/`@L`/`@C`/`@T`) | — | — | — | — | — |
| `style` | sim | sim | sim (cascata) | sim | — | — | — | — |
| `cpi` / `flags` | sim | sim | sim | sim | — | — | — | **recusa** |
| `location` / `pos` | sim | sim | sim | — | sim | sim | — | — |
| `tab` | **saiu** | **saiu** | — | — | — | — | — | Escrever à mão é erro: use `TABS('{campo}', …)` |
| `lf` | sim | sim | sim | sim | sim | sim | sim | sim |
| `field` | — | — | — | sim | sim | — | — | — |
| `path` | — | — | — | — | sim | — | — | — |
| `lines` | — | — | — | — | — | — | 1 | — |

`LOGO` e as formas **não têm prop de tamanho**: `LOGO(ancora, linhas)` vira `location: [ancora, linhas]` e `LINE(c, r, cols, rows)` vira `location: [c, r, cols, rows]`, onde o 3º e o 4º são **deltas** (extensão), não posição final. `width` só existe em `LINE(w)` — a forma "sem coordenada", que só o render resolve. `queda` é o único prop nomeado das formas, e `when` é um `str` posicional final.

Regras que a tabela não cabe:

- **`style` é o traço do glifo e `cpi` é a largura da célula — eixos diferentes que combinam livre.** `style` aceita as 8 combinações do fpdf2 (`''|B|I|U|BI|BU|IU|BIU`); `cpi`, a prop de largura, é recusada em `table.extend` porque a grade da tabela é dela. A **fonte** é prop do `Report`, não de item: uma por documento.
- **`tab` não vale no corpo do `TITLE`**: as paradas são do header, e ancorar no lugar errado calado é pior que recusar.
- **`location` e `pos` são a mesma prop** (apelido); `tab` não combina com nenhuma das duas.
- **`lf` conta LINHAS da grade** (6 LPI → 4,2333mm), enquanto `width` conta **COLUNAS**. Um número só, com sinal: **`lf: 2` são 2 linhas depois, `lf: -2` são 2 antes**, e **`lf: [1, 2]`** cobre os dois de uma vez — que é o que a chave do `table` precisa, já que uma tabela pode respirar antes e depois e isso não cabe num número com sinal. Vale para **todo item** — `FIELD`, `TEXT`, `MEMO`, `TITLE`, `LINE` — e também para `table: {'lf': …}` e, nos reports agrupados, para o grupo (`groups[campo].lf`, ao redor do título/linha visível).

  **No item, `0` (ou ausente) é ausência. Na tabela, ausente é `[1, 1]`.** São duas regras porque a pergunta é outra: o `lf` de um item é um enfeite escolhido por quem escreve, e o da tabela é o **respiro do bloco** — a grade é densa, colada no texto que vem antes e no que vem depois, e é o `lf` que abre e fecha esse respiro. Sem ele a tabela nasce colada. Por isso o padrão interno da tabela é `[1, 1]` (uma linha antes, uma depois), e o item continua ausente por padrão.

  **O `lf` da tabela é DA TABELA — uma vez antes, uma depois, e só isso.** O grupo faz parte dela: um report agrupado não é "várias tabelas", é uma tabela com faixas de cabeçalho repetidas. Por isso o `lf` do `table` **não** é aplicado por grupo nem multiplicado pelo número de tipos: `lf: [0, 1]` numa tabela com 3 grupos deixa 0 antes e 1 depois, não 1 antes e 4 depois. E ele é aplicado **uma vez só**, esteja ou não `body.items` acima — antes, o "antes" vivia pendurado no `items` e o "depois" caía no meio dos grupos, de modo que a mesma declaração produzia três distâncias diferentes conforme a forma do report. O `lf` **do grupo** é independente: ele respira ao redor do título/linha do próprio grupo.

  Por dentro o par vira dois campos, `lf_before_table` e `lf_after_table` (`_ReportTable`), resolvidos uma vez em `_build_table`: `n` → `(0, n)`, `-n` → `(n, 0)`, `[a, b]` → `(a, b)`, ausente → `(1, 1)`. Os dois lados usam o mesmo `_space_before`/`_space_after` que o `lf` de item usa, então o incremento vertical tem um só dono.

  O **sinal também é o que faz o `lf` valer**. O lado "depois" mexe **só no Y**, preservando o estacionamento do `.0022`: um `ln` devolveria o X à margem, apagaria o estacionamento, e a descida automática do próximo item cairia na mesma linha do `lf: 0`. O lado "antes" é o primeiro a ver a linha, então consome a descida pendente **antes** de aplicar o `N` e volta o X para a 1ª coluna — sem isso o `MEMO(..., {'lf': -1})` perderia a linha automática e o `-1` viraria o total.

  `LF(n)` continua sendo o **item** de avanço, e `lf` a **prop**: `LF(1, {'when': …})` ocupa um lugar da lista e precisa do `when` repetido, enquanto `MEMO(..., {'lf': -1, 'when': …})` respira junto com o bloco e some com ele.
- **`wrap` é binária** por escolha: `rows` responderia "quantas linhas" e arrastaria altura mínima junto. `MEMO` quebra por `width` sempre, então `wrap` não diz nada lá.
- **`options` só troca o catálogo**, nunca o valor.

**Rótulo do `MEMO` é prefixo da 1ª linha.** `MEMO('observacao', 84, {'label': 'Obs.:'})` imprime `Obs.: produto esgotado` na mesma linha — o rótulo ocupa o começo da 1ª linha e o texto vem depois dele, quebrando na medida que sobra; as linhas seguintes voltam para a borda do bloco. Era uma linha própria acima do parágrafo, e o `MEMO` era o único item que empurrava o texto para baixo (`FIELD` já era inline). Três decisões:

- **O rótulo é verbatim**: o motor escreve o que o autor declarar, com ou sem dois-pontos. Ele é medido **na fonte dele** (negrito), que é a que sai.
- **O respiro depois do rótulo é `GAP_LABEL`, em cols** (1 col = `25,4/CPI` = 2,54mm no base padrão) — e não um `2` fixo em mm, porque assim ele acompanha o pitch como `width` e `recuo`.
- **Com `recuo`, o rótulo nasce dentro dele** (`x + recuo`), porque `recuo` significa "afasta a primeira linha" e o rótulo é parte dela. Se `recuo + rótulo` não deixar medida para a 1ª linha, o render **levanta** nomeando as duas em vez de degenerar em uma palavra por linha.

Com `align: 'J'` a 1ª linha justifica no que sobra **depois** do rótulo, então a borda direita continua em `x + w` e o rótulo não é esticado; `C`/`R` alinham o conjunto rótulo+texto. Sem texto, o rótulo fica sozinho na linha própria.

**Título e subtítulo (`TITLES`).** `options` no `TITLE` troca o catálogo que resolve o `{campo}` do `text` — é o que permite imprimir o **nome** de um documento ("Cancelamento de Pedido") onde o field traria o **rótulo** do estado ("Cancelado"), sem callable. `TITLE` já era o 1º item de uma lista de
títulos: o 1º desenhado sai com `title_font_size`/`title_font_style` do header e
os demais com `subtitle_font_size` — a cascata é **posicional**, e o `when` é
avaliado **antes** dela, então um subtítulo pulado não vira título grande nem
come o respiro de subtítulo. `TITLES([...])` é o plural, na forma do `TEXTS`:
`'texto'`, `('texto', {props})`, callable ou `{'TITLE': {...}}`, e vale em
**qualquer prop que seja lista de items** (`header`, `body.items`, `before`,
`after`, `table.after`) — é o mesmo helper de desenho nos dois caminhos, com os
defaults vindos do header lá e das constantes no corpo. `font_size`/`font_style`
declarados mudam a **fonte** sem mudar a **posição**, e são validados no render
(`> 0`, `''|B|I|BI`). O `text` de template sai pelo mesmo avaliador do `TEXT` —
`'Status: {status}'` vira `Status: Cancelado`, com o catálogo do field — mas
só resolve quando o nome do campo é **único** no Entity merged; como `status`
existe em Compra, Orçamento, Pedido e Transação, é a entidade **principal** do
report que desempata (`_fmt_opts_for(prefer=...)`). No corpo `tab` é **recusado**
nomeando a prop: as paradas são do header, e ancorar no lugar errado calado é
pior que não aceitar.

**Moeda no rótulo, não na célula.** Coluna de dinheiro que repete `R$ ` em cada
célula polui a leitura — e com a grade CPI dói mais ainda, porque 3 caracteres a
mais numerejam meia coluna. O caminho é tirar o símbolo da **máscara** e pô-lo no
**rótulo**: `'label': 'Valor (R$)'` com a máscara numérica pura. O placeholder do
`table.extend` e a linha de total **herdam o `format` da coluna**, então ficam
limpos de graça (medido: `Acréscimo 100,00`, `Total 1.398,56`). O que a máscara
deixa de carregar não volta sozinho em outro lugar: `Field.currency` vem de
`@M(id)`, e sem ele a coluna de **lista** perde o símbolo também — a mesma
leitura, mas é escolha do app, não do motor.

**Régua e formas posicionadas — a grade CPI × LPI.** Colunas no horizontal,
linhas no vertical, e **as duas em polegada**:

**A matriz: três números e duas letras.** O `CPI` só aceita os **modos base** —
o trio da impressora de linha — e o resto é modificador, resolvido no motor:

| base | | `''`/`'N'` | `'E'` expandido | `'C'` condensado | `'EC'` |
|---|---|---|---|---|---|
| **10** Pica | | 10 → 2,5400mm | 5 → 5,0800 | 17,1 → 1,4854 | 8,55 → 2,9708 |
| **12** Elite | | 12 → 2,1167mm | 6 → 4,2333 | 20 → 1,2700 | 10 → 2,5400 |
| **15** Micron | | 15 → 1,6933mm | 7,5 → 3,3867 | **fica 15** | **fica 15** |

Três regras, e a matriz inteira sai delas: `expanded = base / 2` (exato nos
três), `condensado = CPI_CONDENSED[base]` (só 10 e 12 têm), e
`condensado+expandido = condensado / 2`. **Onde a matriz recusa, o motor fica no
base** — é o caso do Micron condensado, e é pedido, não esquecimento. O `N` é o
"sem modificador" explícito e por isso **não** combina com `E`/`C`: `'NE'` seria
pedir normal e expandido ao mesmo tempo. A ordem não importa (`'EC'` ≡ `'CE'`).

Nem todo valor derivado é alcançável por letra: `CPI(13)` só diz que nenhum dos
três modos serve. Já os que a matriz produzem são todos — e o erro diz com o que
escrever: `CPI(5)` → *"use CPI(10, 'E')"*.

| | fórmula | |
|---|---|---|
| coluna | `25,4 / CPI` | o CPI **final**, depois das flags |
| linha | `25,4 / LPI` | `6` **4,2333mm** · `8` **3,1750** — o LPI é a prop `lpi` do report |
| corpo | `60 / LPI` | 10pt a 6 LPI, 7,5pt a 8 LPI — **derivado**, não declarado |
| alongamento | `7200 / (avanço × corpo × CPI)` % | 100 (CPI 12, o pitch natural) a 240 (CPI 5) a 6 LPI |

**O glifo é esticado para preencher a célula** (`Tz` no PDF), então o CPI é a largura *de verdade* do caractere e **trocar a fonte não move nada** — muda só a letra desenhada. Por isso o corpo não é prop: `font_size` saiu, e declará-lo quebraria a relação com o LPI (o limite é a tinta ≤ 1,2em, e é o que reprova fonte que não cabe).

**O `TITLE` grita por padrão.** A máscara do título é `@U`, aplicada **depois**
do template e das substituições — o `@U` tem de valer sobre o texto já
resolvido, e não sobre o `{campo}` que virou rótulo. A prop `mask` vence:
`mask: ''` devolve o texto como está, `'@L'` vai para minúscula, `'@C'` para
capitalizado. Só os **comandos de texto** contam, nunca a parte numérica:
`format('Orçamento nº 7', '999,999.99')` devolve `'7'` — a máscara numérica
consome os dígitos do título e deixa só o resto. Aqui a parte numérica é
ignorada de propósito, então `@U 999,999.99` ainda só grita. Substituir o `@U`
não é novidade: com o corpo derivado do LPI o título deixou de ser maior, e a
caixa alta é o que ainda o separa do corpo sem pedir corpo maior.

### Estacionar — a linha é o que o cursor ocupa

Nenhum item decide sozinho se avança uma linha. Todo item **estaciona na borda
do que desenhou**, e o item seguinte **desce porque não cabe mais nada**. A
pergunta é uma só — *"a linha ainda tem lugar?"* — e a resposta sai do próprio X,
sem contador e sem estado:

| item | estaciona em | o que vem depois |
|---|---|---|
| `TITLE` `align:'C'` (padrão) | fim da **LINHA** — a caixa é a zona toda | desce |
| `TITLE` `align:'L'/'R'` | fim do **TEXTO** | continua na mesma linha, se couber |
| `LINE()` | fim da régua = fim da linha da página/zona/tabela | desce |
| `LINE(30)` | fim da régua, 30 cols adiante | continua à direita, se couber |
| `FIELD`/`TEXT` inline | fim do próprio texto | continua na mesma linha |
| `MEMO`, `BOX`, `CIRCLE` | já descem sozinhos (ou são ancorados) | — |

O `TITLE` centralizado é o caso que mudou: ele ocupava **duas** linhas (a
célula + o `rows_after: 1` de então), então a cascata do `TITLES` punha uma
linha em branco entre cada par. Medido antes → depois, a 6 LPI: COMPRA com 1 título 3 → **2**
linhas de header, com 2 títulos 5 → **3**.

Duas coisas fazem o `align` deixar de ser cosmético no `TITLE`: `align:'L'` com
`width` declarada deixa o próximo item **na mesma linha**, e é o `width` que
diz "isto é um pedaço da linha", não o alinhamento.

**`set_y` não desce linha.** O fpdf2 devolve o X para a margem tanto no `set_y`
quanto no `ln` — o `set_y` parece só mexer na ordenada, mas apaga o
estacionamento. O lado "depois" do `lf` por isso é `set_xy` com o X que já
estava: se fosse `ln`, `lf: 1` e `lf: 0` dariam a mesma linha.

### Tabulação imprime

`TABS` faz **dois** trabalhos, distinguidos pelo tipo do primeiro argumento:

```python
TABS(1, 30),                                   # NÚMEROS → define as paradas
TABS(),                                        #           restaura
TABS(1, 30),
TABS('Orçamento'),                             # TEXTO  → imprime
TABS('{cliente_nome}', '{data_pedido}'),
TABS('{cliente_telefone}', '{validade_data}'),  # desce sozinho
```

**A string nua é a forma normal** — a tupla só aparece quando o elemento leva
props: `('{data}', {'lf': 1})`, `('{x}', {'style': 'B'})`, `('{x}', 'quando')`.

Misturar número com texto é erro — são dois comandos com o mesmo nome e a mesma
aridade, e decidir pelo primeiro seria adivinhação.

| elemento | vira | rota |
|---|---|---|
| `'texto'` | texto | TEXT |
| `'texto', {props}` | texto + props | TEXT |
| `'{campo}'` — **token puro** (`^\{\s*[\w.]+\s*\}$`) | campo | **FIELD**: rótulo em negrito, máscara, catálogo `options`, `label` da Entity |
| `'Cliente: {campo}'` | texto | TEXT — o rótulo sai **no mesmo peso** do valor |
| `''` | a parada **não existe nesta linha** | não imprime, e o elemento anterior **não é cortado** |
| `(str, {props})` / `(texto, 'quando')` | str + props / + `when` | a gramática do `TEXTS` |

O token puro é o que preserva o rótulo em negrito: por dentro é o caminho FIELD
de sempre (`_expande_tabs` emite um `FIELDS` de uma entrada, para o caminho
pontilhado `'{Conta.telefone}'` resolver pelo mesmo ramo de sempre).

**Uma linha nova de `TABS` desce sozinha.** A pergunta é *"o cursor já passou
da 1ª parada?"* — se passou, a linha nova começaria em cima do que a anterior
escreveu, e desce. Se não passou, fica onde está: a **1ª linha do header** não
desce, e a 2ª desce sozinha. É o `lf: -1` automático, e é por isso que um grid
não declara `lf` para separar as fileiras:

```python
TABS(1, 30),
TABS('{cliente_nome}', '{data_pedido}'),   # 1ª parada: fica na linha atual
TABS('{cliente_telefone}', '{validade_data}'),   # 1ª parada já passou: desce
```

O `lf` continua valendo por cima: `lf: -1` **é** a descida (e a automática não
soma outra — ela só age quando não há descida nenhuma), e `lf: 2` deixa duas
linhas em branco depois.

### O teto é em COLUNAS, não em milímetros

O elemento `i` leva no máximo `paradas[i+1] - paradas[i] - 1` colunas. Sem
elemento seguinte, ou com `''` no lugar, não há teto — e o texto vai até a
**margem** da zona, que sempre limita.

```python
TABS(1, 30),
TABS('{cliente_nome}', '{data_pedido}'),   # 28 colunas entre as duas paradas
```

**Por que colunas e não milímetros:** a grade conta células e a célula **é** o
caractere — o glifo é esticado para preencher a coluna. Medido com
`TABS(1, 30)`: **28 caracteres nos três CPIs** (10, 12 e 15). O corte em mm
(`_cut_to_fit`, que desconta o `c_margin` de 2mm) tirava um caractere no
CPI 15 — os 2mm fixos sendo fração maior de uma célula de 1,69mm. Contando
células não há fração: ou cabe, ou não cabe.

Antes disso não havia teto nenhum: o corte recebia `right - _x0`, a **largura
da zona inteira**, e isso só parecia certo porque item sem âncora sempre quebra
de volta para `x0` antes de medir. Medido, `TABS(1, 30)` deixava o texto da 1ª
parada chegar a **168,48mm** com a tab 2 em 86,20mm, e o da última a
**242,14mm**, 42mm **além da margem**.

**`{campo}` agora leva a máscara.** A máscara do campo entra no template pelo
mesmo caminho do FIELD — `resolve_field_mask`, com a precedência que já existia
(`explícita > catálogo do input > decimals`) — e vale quando o template não dá
spec próprio. Antes `{data_pedido}` saía com o `repr` cru do Python
(`2026-10-09 14:37:52`); agora sai `09/10/2026 14:37`, em todo template —
`TITLES`, `MEMO`, `TEXT`, coluna e `table.after`.

**Condensed e expanded são as duas pontas do mesmo eixo** (5 e 20), não dois estilos: pedir os dois dá 0,5× × 2× = 1×, que é o normal. O que combina com tudo é o outro eixo, `style`, que muda o **traço**.

As factories de grade (`LINE`/`BOX`/`CIRCLE`, como `TABS`/`IND`/`POS`) são **variádicas**: declare os números, a lista interna é do motor.

```python
CPI()            # volta ao padrão (10 CPI)
CPI(15)          # Micron: 1,6933mm por caractere
CPI(12, 'EC')    # Elite condensado+expandido = 10 CPI

{'TEXT': {'text': 'x', 'flags': 'E'}}   # prop: expandido do base vigente
```

O `TITLE` recusa `cpi` nomeado — a cascata escolhe a largura dele por `flags`
(1º expandido, 2º e 3º+ normal), e é por isso que ele acompanha o base vigente
em vez de ser um número cravado.

```python
LINE()                      # largura da zona: a indentação vigente (IND) ou,
                            #   sem ela, a última tabela
LINE(True)                  # largura da página inteira (ignora IND)
LINE(w)                     # w colunas a partir do cursor  == LINE(PCOL, PROW, w)
LINE(c, r)                  # PONTO em (c, r)      -- extensão (0,0)
LINE(c, r, cols)            # horizontal: de (c,r) até (c+cols, r)
LINE(c, r, 0, rows)         # vertical:   de (c,r) até (c, r+rows)
LINE(c, r, cols, rows)      # inclinada:  de (c,r) até (c+cols, r+rows)
LINE(..., 'queda')          # só quando `queda` é verdadeira (when)
BOX(c, r, cols[, rows])     # altura omitida = quadrado de verdade
CIRCLE(c, r, raio[, achata])
```

O 3º e 4º são **deltas** (extensão a partir da origem), não posição final; omissão vale 0 no `LINE` (de onde vem o ponto). `LINE` desenha e avança uma linha — o cursor desce e volta ao início da zona, para o próximo item não colidir com a régua; espaço extra é `LF(n)`. `when` vale para `FIELD`, `TEXT`, `LINE`, `BOX` e `CIRCLE`. As formas de largura (`()`, `(True)`, `(w)`) são de régua e só existem no `LINE`.

**Zona do logo.** A **zona** é a faixa em que o fluxo sem âncora vive: `[margem esquerda | recuo do `IND` | recuo do `LOGO` | margem direita]`. Tudo que se posiciona pela zona — `TABS`, `location`, `pos`, `PCOL(n)`, a `width` implícita do `TITLE` e a centralização dele — mede a partir da borda **esquerda** da zona e para na **direita**, então um logo à esquerda empurra o texto e um à direita o puxa:

```python
LOGO('L', 3),      # zona vira [fim da imagem | margem direita]
PROW(0),           # diretiva: volta para a linha 0 (o topo da margem)
CPI(12),           # a zona NÃO se move: ela é a borda da IMAGEM, em mm
TABS(5, 35),       # paradas em cols a partir do início da zona
TITLES([
    'Orçamento #{id}',
    ('Status: {status}', {'when': 'status > 0'}),
]),
```

**A borda do logo é medida em MILÍMETROS, e `CPI` depois do `LOGO` não a move.**
A imagem já foi desenhada em mm e não se move quando a grade muda; a zona é o
espaço vago ao lado dela, então é a mesma medida. A conversão de mm para cols
acontece na hora de usar, com o CPI vigente — foi justamente por guardar a
borda em cols que a zona **encolhia para dentro da figura** quando o `CPI`
mudava depois do `LOGO`: medido, com a imagem terminando em 52,33mm, `CPI(12)`
punha o `FIELD` de tab 1 em x=45,28mm e `CPI(15)` em x=38,22mm.

`LOGO('C')` não indenta (a sobra é igual dos dois lados, e ela some depois). A zona do logo vale **enquanto o cursor estiver na faixa vertical da imagem** — passar da faixa devolve a zona, e é por isso que a 2ª linha de `FIELDS` de um report com logo sai já na margem. `IND()` cancela o recuo do logo ali mesmo, dentro da faixa, que é o jeito de voltar ao que era. `PCOL(n)` fora da zona levanta nomeando as cols disponíveis, e `_tab_x` faz o mesmo com a parada — antes era a largura da página inteira que validava, e a parada "certa" era a que o papel rejeitava.

**`wrap` e a frase que nascia cortada.** `cell` do fpdf2 **não quebra linha**: o texto passa reto e a ponta sai da folha. A frase de cancelamento do COMPRA media 206mm contra 190mm úteis — os últimos "itens:" iam para fora da página, sem aviso. `wrap: True` troca `cell` por `multi_cell` na largura da zona (ou da prop `width`), e vale nos três renderizadores: linha de texto, item `TEXT` e item `FIELD`/`FIELDS` (onde o rótulo fica na 1ª linha e o valor quebra no resto da zona). **Ausente é `cell`**, ou seja, o comportamento de sempre — a correção só acontece onde alguém declara. Para "altura em linhas" continua valendo `rows_before`/`rows_after` (espaço); `rows` é outra coisa, do formulário (`<textarea rows>`), que o report ainda não lê.

**Linha de texto fala a língua do `TEXT`.** `body.before`/`body.after` passam pelo mesmo avaliador (`{campo}`, `{campo:brl}`, `{campo|fallback}`, `{?campo:...}`) que os items, com o catálogo do campo vindo da Entity. **Para um texto que precisa de OUTRO catálogo — uma frase de documento — o item certo é `MEMO('campo', width, {'options': ...})`**, que é um field com medida: o catálogo é o override normal e não uma prop nova na linha de texto.

```python
FRASE = {0: 'Solicitamos o orçamento referente aos seguintes itens:',
         6: 'Conforme conversado anteriormente, por motivo de {observacao|(não informado)}, '
            'solicitamos o cancelamento do pedido com os seguintes itens:'}

'before': lambda c: [{'text': ''},
                     {'text': '{fornecedor.nome|-}', 'font_size': 12, 'font_style': 'B', 'align': 'C'},
                     {'text': ''},
                     {'text': '{status}', 'wrap': True}]   # catálogo do campo, da Entity
```

O rótulo de catálogo pode ter `{campo}` dentro dele, e aí o avaliador faz uma segunda passada (`core.text.LABEL_DEPTH`, com guarda de recursão para catálogo que se referencia). Seguro no app: **0 dos 57 rótulos** dos catálogos têm `{`.

**`MEMO(campo, width)` — um FIELD com medida.** `campo` é o **field** (mesma gramática de `FIELD`/`FIELDS`/`list.columns`), então o catálogo é o override normal dele — `options` — e label, `calc` e máscara vêm da Entity. Não há `labels` nem catálogo colado no texto. Com `{` no `campo`, vira template (`MEMO('Prezado {fornecedor.nome}, ...')`) e aí não tem label nem override de catálogo, que é a mesma distinção que separa `FIELD` de `TEXT`. Quebra por palavra numa medida, **centraliza o bloco na área livre** da zona, e **`align` é `'J'` por default** — parágrafo se justifica, e `L` é a exceção declarada. (A última linha nunca é justificada, como em tipografia.) É o que o `IND` não resolvia: `IND` abre uma zona que **vaza** para os itens seguintes e depende de ordem (`LTB`/`RTB` só valem depois que a tabela desenhou), enquanto `MEMO` tem a largura no próprio item. Dois blocos com o mesmo `width` ficam com o mesmo recuo das margens por construção. `recuo` (cols, padrão 0) afasta **só a primeira linha** — equivale a `spaces(recuo) + texto`, e `recuo >= width` é recusado — é assim que o preâmbulo e o bloco de observações do COMPRA se alinham sem número mágico.

```python
LARGURA = 80                      # cols da grade

'before': [MEMO('status', LARGURA, {'options': FRASE, 'label': '',
                                     'when': {'status': FRASE}})],
'after':  [LF(2, {'when': 'observacao'}),
           MEMO('observacao', LARGURA, {'label': 'Obs.:', 'when': 'observacao'})]
```

Justificar é um **pedido com sanidade**, não uma garantia: o espaço só estica até `JUSTIFY_MAX` (o espaço pode no máximo dobrar) e, acima disso, a linha cai em `L`. Passando disso o olho lê "palavra␣␣␣␣␣palavra" e não texto justificado — medido a 60 cols a sobra é 213% do espaço, e bloco serrilhado fica melhor que buraco. O `multi_cell` do fpdf2 **documenta** `J: justify` mas não implementa (escreve cada linha no x dela: 102.5mm e 99.2mm numa coluna de 105.9mm), então a justificação é nossa, palavra a palavra.

**`when` aceita path, expressão (com comparação) e `{campo: valores}`.** Path (`'observacao'`), expressão booleana (`'acrescimo or desconto'`, `'not x'`, com parênteses) e o mesmo formato que o Schema já usava: `{'ativo': True, 'tipo': [1, 2]}` — e com o dicionário como alvo, `{'status': FRASE}` quer dizer "só nos status que estão neste catálogo". Foi o que deixou o catálogo ser a única fonte de verdade do COMPRA: o `FRASE` diz o texto *e* quais status têm frase, sem um `if status not in (...)` em Python para divergir. `LF` ganhou props pelo mesmo motivo (o respiro de um bloco condicional precisa sumir com ele).

**Um avaliador só: `ajsystem/core/expr.py`.** `avaliar(expr, obj=None, get=None, funcoes=None, rotulo=...)` devolve o **valor**; `condicao(...)` devolve a verdade. Uma gramática para tudo o que é expressão no framework:

| | |
|---|---|
| paths | `valor`, `a.b.c` (de `obj`, ou do getter em `get`) |
| literais | número, string entre aspas, `True`/`False`/`None` |
| aritmética | `+ - * / // %`, unário `+`/`-`, parêntese |
| comparação | `>`, `>=`, `<`, `<=`, `==`, `!=`, `=`, `<>` |
| booleano | `and`/`or`/`not`, e as grafias `&`, `|`, `||`, `!` |
| função | só da allowlist do caller (`funcoes=`) |

Precedência do Python, do mais fraco ao mais forte: `or` < `and` < `not` < comparação < `+ -` < `* / // %` < unário < primário. **O `calc` da Entity, o `when`, o ternário do template e o `calc_value` da list usam todos esta função** — usar direto no app também: `from ajsystem.core.expr import avaliar, condicao`. Não é Python: parser próprio, sem `exec`/`eval`, porque o módulo é genérico e `eval` aqui abriria execução de código sem motivo. O que ele não sabe, ele diz: função fora da allowlist, operador desconhecido e tipo incompatível levantam nomeando a expressão.

**Ternário no template: `{cond ? a : b}`.** Escolhe `a` ou `b` pela **mesma** gramática do `when` — paths, comparação, `and`/`or`/`not`, parênteses. Não é um segundo condicional: é a decisão dentro do texto, para quando a escolha muda **uma palavra** e não a linha inteira (o título do COMPRA: `'{status == 1 ? Pedido : COMPRA} #{id}'`, com o `when: 'status != 0'` fazendo o guard que o ramo 'COMPRA' não pode fazer sozinho). Se a escolha muda a **linha** inteira, use `when` por item — aí o que se quer é a linha sumir, não o texto trocar dentro dela. Os ramos aceitam `{campo}` (então `{c ? {nome} : X}` sai com o valor resolvido e o catálogo do LIST), e aninhar é **entre chaves**: `{c ? x : {c2 ? y : z}}`. O espaço em volta de `?` e `:` é separador. Um `?`/`:` de nível 0 dentro de um ramo levanta, porque é ambíguo — melhor do que trocar a palavra errada em silêncio. Scanner, não regex: o ramo pode ter `{qtd:02d}`, e o `:` do format-spec não pode ser confundido com o separador.

**Comparação: `>`, `>=`, `<`, `<=`, `==`, `!=`, `=` e `<>`** — `'status > 0'`, `'valor >= 100'`, `'status == 6'`, `'nome != "X"'`. Liga mais forte que `not` (igual ao Python: `not status > 0` é `not (status > 0)`), e mais fraca que `and`/`or`. O lado direito é literal (número, `True`/`False`/`None` ou string **entre aspas**) ou **outro path** (`'valor > minimo'`), que resolve pelo mesmo `dotted_get`. Campo **ausente** não ordena (devolve `false`) nem estoura: `None > 0` em Python é `TypeError`, e aqui a linha inteira sumiria com um erro que ninguém vê; em `==`/`!=` ausente segue a identidade, que é o que `x == None` quer dizer. Operador que não vira comparação (`'status >> 0'`, `'a >'`) **levanta** em vez de cair em `dotted_get` e virar `false` calado.

**Expressão: `or`/`and`/`not` (e `|`/`&`/`!`), sempre inclusivos.** `or` e `|` são **sinônimos exatos** — mesmo regex, mesmo `any()`, resultado idêntico:

| expressão | nenhum | só A | só B | A e B |
|---|---|---|---|---|
| `'A or B'` = `'A \| B'` | não | **sim** | **sim** | **sim** |

XOR não existe, e é por isso que `|` é a grafia perigosa: em C, shell, SQL, R e no bitwise de Python ele é bitwise, e em booleanos bitwise **é** o XOR (`True | True` → `False`) — o oposto do que o `when` faz. Quem não conhece essa convenção da casa lê `|` como "exatamente um" e erra. Use `or`; `|` continua aceito, mas é sinônimo e não faz nada a mais.

Na forma **dict** o alvo é **comparação**, não truthiness: `{'ativo': True}` casa com campo booleano, mas `{'acrescimo': True}` procuraria o valor `True` no campo e não encontraria. Para "algum destes" a expressão é o caminho.

**Onde cada prop aceita o quê.** `header` (lista), `body.items`, `body.before`, `body.after` e `body.table.after` passam pelo **mesmo** renderizador de items — e as duas últimas também aceitam **linha de texto** (`{text, font_*, align, width, wrap}`), que é o que dá o espaçador e o texto avulso. Um item vindo de *callable* é recusado nomeando a prop: a função roda depois do `_apply_entity`, então o item não tem como ser resolvido contra a Entity (um LIST sairia com o código em vez do rótulo). E `FIELD` solto agora resolve em todas elas — antes saía o rótulo no header e o **código** em `items`/`after`, e o `calc` da Entity nem chegava. Em `table.extend`, a régua é `LINE()` e ela **não avança linha** (é divisor: a linha seguinte se apoia nela, em vez de pagar uma faixa em branco) — é a régua da própria tabela, sujeita ao latch que impede duas réguas seguidas sem conteúdo entre elas (a antiga string `'LINE'` saiu por ser o mesmo desenho com dois nomes).

> **Todo field mostra o valor de exibição, em qualquer prop que o imprima.** `LIST` sai pelo rótulo do catálogo (`options`/`list` da Entity) e `BOOL` por Sim/Não — em coluna (`table.columns`, `header.fields`) e em item de layout (`items`, `after`, `table.after`, header) alike, porque os dois caminhos usam o mesmo passo (`core/resolve.field_display_fn`). Código fora do catálogo cai no valor cru, como na listagem. Antes de `1.26.10.08.0005` só as colunas traduziam, e o mesmo field saía `1` num lugar e `Fornecidas pelo Cliente` no outro.

#### 5.8.2 O rodapé — `'footer'`

O rodapé é a **última linha da página**, e a página tem um número finito de linhas: o motor conta quantas cabem entre as margens superior e inferior, na altura de linha do `lpi`, e reserva a última para o rodapé. O conteúdo é medido até a anterior e **nunca a toca**.

**`True` é o atalho das três flags:**

```python
'footer': True,          # == show_user + show_datetime + show_page_number
```

Sem rodapé declarado (`None`, `False`, `{}`) a área útil é a de sempre — um report que não pede rodapé não paga a linha.

| chave | default | valores | efeito |
|---|---|---|---|
| `show_user` / `show_datetime` / `show_page_number` | `False` | `bool` | os três segmentos do rodapé, unidos por `separator` |
| `show_company` | `False` | `bool` | reservado; hoje não escreve nada |
| `text` | `None` | `str` \| `callable` | texto livre, com `{user}` `{datetime}` `{company}` `{page}` `{total}` |
| `separator` | `' \| '` | `str` | junta os segmentos |
| `cpi` | `12` + `'C'` = **20** | base `10`, `12`, `15` | largura do caractete do rodapé. O **default é a letra mais fina da grade** (`CPI(12,'C')`, Elite condensado, 1,2700mm) — o menor CPI que a matriz alcança, porque o Micron recusa condensar. O que o dev declara é um **base**, então declarar sempre *abre* a letra |
| `style` | `'I'` | `''`, `B`, `I`, `BI` | a face; itálico é o padrão do framework |
| `align` | `'R'` | `L`, `C`, `R`, `J` | alinhamento na página |

**O que o rodapé NÃO tem prop:** família e corpo. Vêm do report (`font` e `lpi`) — o rodapé é parte do mesmo documento, e é o **estilo** que o distingue, não a letra.

`cpi`, `style` e `align` são os overrides: `'footer': {'show_page_number': True, 'align': 'C'}` desenha só o número, ao centro. Com `lpi: 8` a altura cai para 7,5pt e o rodapé fecha a menor letra que a grade permite. Valor fora do catálogo levanta `ValueError` no build (`cpi: 13` → *"não é um base; use um de [10, 12, 15]"*), e `footer` que não for `True` nem dict levanta `TypeError` — no build, não no meio da renderização.

**A contagem é por página, não fixa.** Ela sai de `pdf.h` menos as margens, dividida por `25,4/lpi`: no A4 retrato a 6 LPI são 63 linhas (o rodapé na 63, o conteúdo usa 62); a 8 LPI, 84 linhas. O gatilho de quebra passa a ser essa linha — `b_margin` e `page_break_trigger` escrevem o mesmo número, porque `_check_page_break` (motor) lê um e o `multi_cell` (fpdf2) lê o outro, e se divergissem o texto quebraria num ponto e a tabela noutro.

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
| `position` | `str` | `'top_right'` | `POSITION_CONTEXT` — `before`, `after`, `before_up`, `after_down`, `top_left`, `top_right`, `bottom_left`, `bottom_right` | ver abaixo |

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

**`position`** — são 8 nomes, e cada um diz ONDE o botão cai em relação aos **fields** (inline ou faixa) ou à **tabela** (título/ação). `_check_position` valida contra a tabela do contexto e **levanta erro** em valor fora dela (nada de sumir em silêncio). `before`/`after`/`before_up`/`after_down` são **sempre relativos aos fields** — por isso não valem em sessão só de `table`/`query` (não há bloco para encostar). `top_*`/`bottom_*` são relativos à **tabela**, com fallback para os fields quando a sessão não tem tabela. Na **sessão mista** (`fields` + `table`/`query`, ex.: `Financeiro` em pedidos/compras) os dois convivem: `before*`/`after*` nos fields, `top_*`/`bottom_*` na tabela.

| `position` | form | sessão só de `fields` | sessão só de `table`/`query` | sessão mista (`fields` + `table`/`query`) |
|---|---|---|---|---|
| `before` | inline, antes do 1º field | inline, antes do 1º field | **erro** (sem fields) | inline, antes do 1º field |
| `after` | inline, depois do último field | inline, depois do último field | **erro** (sem fields) | inline, depois do último field |
| `before_up` | faixa acima dos fields | faixa acima dos fields | **erro** (sem fields) | faixa acima dos fields |
| `after_down` | faixa abaixo dos fields | faixa abaixo dos fields | **erro** (sem fields) | faixa abaixo dos fields |
| `top_left` | barra de cima, à esquerda | faixa acima dos fields, à esquerda | faixa acima da tabela (título), à esquerda | faixa acima da tabela, à esquerda |
| `top_right` | barra de cima, à direita | faixa acima dos fields, à direita | faixa acima da tabela, à direita | faixa acima da tabela, à direita |
| `bottom_left` | rodapé do form, à esquerda | faixa abaixo dos fields, à esquerda | **faixa de ação: `+ Adicionar` primeiro, depois o botão** | faixa de ação, à esquerda |
| `bottom_right` | rodapé do form, à direita | faixa abaixo dos fields, à direita | faixa de ação, encostado à direita | faixa de ação, encostado à direita |

`before`/`after` são **inline** (mesma linha dos fields, antes do 1º / depois do último) e `before_up`/`after_down` são faixas em linha própria acima/abaixo dos fields; os quatro são **relativos aos fields** em qualquer lugar — form e sessão. `top_*`/`bottom_*` são relativos à **tabela** (faixa-título acima / faixa de ação abaixo) e caem nos fields quando não há tabela. **No form**, porém, `top_left`/`top_right`/`bottom_left`/`bottom_right` são as **BARRAS** (fora do `<form>`), logo **não** são aliases de `before_up`/`after_down` ali. Na **sessão mista** (`fields` + `table`/`query`, ex.: `Financeiro` em pedidos/compras) vale a mesma separação: `before*`/`after*` ficam nos **fields** e os `top_*`/`bottom_*` na **tabela**. A **faixa de ação** fica dentro do `.child-table-wrap` e **fora** do `<tfoot>` (a tabela pode ter linha de totais, e a largura de colunas do Adicionar não é a delas) e **fora** de `.it-desktop`/`.it-mobile` — por isso o `Adicionar` é renderizado uma vez só e `btn.closest('.child-table-wrap')` funciona nos dois tamanhos de tela. Listagem não usa `position`.

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
| `slot` | `str` | `'body'` | `body` no corpo do form, `bar` na barra — o campo tem que estar no slot `bar` (§5.5) |
| `boolean` | `bool` | `False` | valor é booleano; ausência no POST = `False` |
| `number` | `bool` | `False` | input numérico: entra por `fmt_num`, exibe por `render_value` (ver **5.14**) |
| `multi` | `bool` | `False` | lista de opções marcadas |
| `masked` | `bool` | `False` | o texto passa por `mask`/`mask_cmd` |
| `textual` | `bool` | `True` | texto livre — só isso aceita transform `@U/@L/@C/@T` |
| `filter_kind` | `str` | `'text'` | editor de filtro da listagem: `text/boolean/date/number/select` |
| `upload` | `bool` | `False` | o valor é o nome de um arquivo enviado |
| `mask` | `str` | `''` | máscara default; o `Field` vence |
| `validate` | `str\|list` | `None` | validador default; o `Field` vence |
| `mask_group` | `str` | `'text'` | comandos `@X` liberados: `text` (`ULCTR`), `number` (`BXM`), `*` |
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
- **As três entradas de data/hora têm máscara default, e nenhuma mostra segundos.** `date` é `dd/mm/yyyy`, `time` é `hh:ii` e `datetime-local` é `dd/mm/yyyy hh:ii`. Os tokens de tempo são `hh` (hora), `ii` (minuto) e `ss` (segundo) — **`mm` é o MÊS**. `ss` existe na gramática mas não entra em nenhum default: em data de negócio ele só polui a coluna. E o `datetime-local` sem máscara não caía num default elegante, caía no **`repr` cru do Python**: um `DATA_HORA` sem `mask` explícita saía como `2026-10-09 14:37:52`.
- **`Inputs`** (mesmo arquivo) é a camada do **motor**: só o `toggle`. A entrada diverge de `checkbox` declarando `type: 'checkbox'`, e acrescenta `slot: 'bar'`, `route: 'toggle'`, `method: 'POST'`, `label_on`/`label_off` e `badge_off`. `INPUTS` é a soma das duas, já com o `type` resolvido.
- **`type`** é metadado de qual base usar e sai do merge. Base inexistente **levanta erro dizendo o nome**; entrada sem `type` e com nome novo **também**, porque todo tipo do app diverge de um genérico.
- **`App.inputs`** (`app/config.py` → `build_app(inputs=…)`) é a camada do app, lida por `core/adapter.py` e fixada como default de processo por `definir_camadas_padrao` no `init.py` — antes de `registrar_modulos`, porque o `Entity` já é expandido no import do model. É onde `cpf`/`cnpj` e a máscara do telefone BR ganham forma: `app/extends/inputs.py`, gêmeo de `app/extends/buttons.py`.
- **`Inputs` da rota** é a variável de módulo lida por `module_inputs`, no mesmo papel que `Schema` e `Buttons` têm na sua rota. A listagem resolve as mesmas camadas por `_camadas_inputs`.
- **`input_props`** é a última camada e vale só para aquele campo: `{'type': 'BOOL', 'input_props': {'cls': 'meu-toggle'}}`. Chave que não existe em `Input` **levanta erro** com a lista das válidas.

**Resolução** — `Field.input` continua sendo `str` (o *nome* do tipo, porque é isso que o `Schema` e o spec referenciam); o objeto resolvido é `Field.inp`. A resolução é **eager**, no `Field.__post_init__`, e não preguiçosa: `mask`, `validate`, `width` e `align` são computados ali, e um input resolvido depois deixaria a máscara de fora. O `Field` ainda valida dois pares que não podem divergir: comando de máscara não liberado pelo `mask_group`, e `@U/@L/@C/@T` combináveis entre si (são exclusivos). O par "input de barra ⇒ campo no slot `bar`" saiu do `Field`: posição é da página, então quem valida é `apply_positions` (superfície `form`, §5.5).

**Toggle** — `{'type': 'BOOL', 'input': 'toggle'}` no model, com o campo no slot `bar` da página. Renderiza no rodapé do form (`form_macros.html:render_toggle_field`), **fora** do `<form id="main-form">`, porque cada um é um POST próprio. O endpoint é genérico — um por módulo, em `POST /<rota>/<id>/toggle/<campo>` — e valida o `<campo>` da URL contra `Form.toggle_fields` (os campos cujo input declara `route`), então um POST não escolhe coluna arbitrária do model para inverter. É POST e não GET porque muda dados: GET mutante quebra o cache do navegador, o prefetch de link e o back/forward. Respondendo a HTMX, devolve `204` + `HX-Refresh`; fora dela, `302` para o form.

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

### 5.9.3 Funções do framework para o app

O que o host (`app/`) pode importar e chamar. Não é a lista do que existe: é a do que é **contrato**. `do_page`/`do_list`/`do_form`/`do_report`, `core/resolve`, `core/list`, `core/qrun` e os internos de `pdf`/`list`/`filters` existem e funcionam, mas são **motor** — mudam com o assunto, e ancorar neles cria dívida. Se faltar algo daqui, o caminho é **adicionar à API**, não importar o interno.

**Expressão — `ajsystem/core/expr.py`.** O avaliador único do framework (ver **when** em 5.8.1): uma gramática para path, literal, aritmética, comparação, booleano e função da allowlist, na precedência do Python. Sem `eval`.

```python
from ajsystem.core.expr import avaliar, condicao

avaliar('valor + acrescimo - desconto', obj, funcoes={'divide': divide})  # 108.0
condicao('status > 0 and nome != "X"', obj)                              # True
condicao('{...}', get=lambda k: ...)   # com getter, sem objeto (é o template)
```

**Opções e valores — `ajsystem/core/utils.py`.**

```python
from ajsystem.core.utils import as_options, add_dias, divide, is_zero_or_empty

UND_INSUMO = as_options('Kg', 'G', 'L', 'Ml', 'Un')   # chave pelo slug do rótulo
TIPO_EVENTO = as_options(('chave_fixa', 'Rótulo'))     # par (chave, rótulo)
add_dias(q.data_renovacao or q.data_pedido, q.validade or 3)   # dia somado, None→None
divide(valor, qtd)   # divisão segura: 0 quando o divisor é nulo/zero
```

`as_options(*itens, slug=True)` monta `{valor: rótulo}` para field `LIST`; a chave deriva do rótulo via `normalizar_slug` (`'Chá de Bebê'` → `cha_de_bebe`), e `slug=False` usa o próprio rótulo. Predicados: `is_null`, `is_empty`, `is_zero_or_empty`, `as_num`, `deep_attr(obj, path)`, `field_value(field, item)`.

**Máscaras e formatação — `ajsystem/core/formats.py` e `defs/masks.py`.**

**`fmt_mask` NÃO é formatador numérico** — é posicionamento de dígitos: tira os não-dígitos do valor e preenche os `9` da máscara (`fmt_mask('1234567', '999.999')` → `'123.456'`). Por isso `fmt_mask(1234.56, MVALOR)` não dá dinheiro: para isso use `fmt_money`, ou a `mask` de um field, que passa pela camada do host (ver **5.14**). `parse_brl` e `fmt_money` falam o formato **canônico** (`'1234.56'`, `'$ 1,234.56'`); a forma brasileira (`'1.234,56'`) é a de exibição, e quem decide é `DECIMAL`/`THOUSAND`/`MONEY` do host. `MVALOR` e afins são escritas no padrão canônico justamente por isso — o motor troca os separadores.

```python
from ajsystem.core.formats import parse_brl, fmt_money, fmt_mask
from ajsystem.defs.masks import MVALOR, merge_masks, definir_masks

parse_brl('1234.56')            # 1234.56  (float)
fmt_money(1234.56, True)        # '$ 1,234.56' (canônico; o host troca DECIMAL/THOUSAND/MONEY)
fmt_mask('1234567', '999.999')  # '123.456'
definir_masks(overrides)        # monta a camada do host (no boot do app)
```

**Carry entre requests — `ajsystem/core/memory.py`.** Guarda o `request.form` numa página e devolve na outra, com TTL.

```python
from ajsystem.core.memory import store_carry, carry_get, carry_take, carry_renames

carry_token = store_carry(request.form)          # -> str; devolve na URL
carry = carry_take(request.args.get('carry')) or {}   # pega e CONSOME
form_preenchido = carry_get(request.args.get('carry'))  # pega sem consumir
renomes = carry_renames(token)                   # {destino: origem} de __carry_map
```

**Ordenação e agregação em memória — `ajsystem/core/query.py`.** As mesmas semânticas da `QuerySpec`, para quando os dados já vêm em Python.

```python
from ajsystem.core.query import order_items, aggregate_rows, group_items

order_items(itens, 'data_pedido desc', fields)     # estável; spec por lista também vale
aggregate_rows(itens, {'total': {'sum': 'valor'}}, fields)
group_items(itens, 'tipo', {'titulo': 'titulo', 'subtotal': True}, fields)
```

**Menu e rota corrente — `ajsystem/core/menu.py`.**

Exigem **contexto de app/request** (`current_app`/`request`) — são para montar o contexto de template, não para script avulso:

```python
from ajsystem.core.menu import modulo_atual, menus_para_json, url_do_item, item_ativo

contexto = {'modulo': modulo_atual(),
            'modulo_menus_json': json.dumps(menus_para_json())}
```

**Segredo — `ajsystem/core/crypto.py`.** `encrypt(plaintext)` / `decrypt(ciphertext)`, para campo de configuração que não vai em claro no banco.

```python
from ajsystem.core.crypto import encrypt, decrypt
self.encrypted_value = encrypt(raw) if raw else ''
```

**Markdown e notificação — `ajsystem/core/content.py` e `core/ntfy.py`.**

```python
from ajsystem.core.content import render_pagina
html = render_pagina('termos')    # .md -> HTML sanitizado; None se ausente; recusa '..'

from ajsystem.core.ntfy import notificar
notificar('alerta', 'Backup', 'Concluído', tags=['white_check_mark'])   # falha calada
```

**Geometria — `ajsystem/core/geom.py`.** É o que compõe `location`/`LINE()` quando a coordenada é calculada em vez de declarada.

```python
from ajsystem.core.geom import normalize, to_mm, resolve_anchor

norm = normalize('LINE', [2, 3, 4, 0])        # ('LINE', 2, 3, 4, 0)
to_mm(norm, 6.0, 2.54)
# {'x1': 5.08, 'y1': 18.0, 'x2': 15.24, 'y2': 18.0, 'ponto': False}
```

`to_mm` recebe a altura de linha e a coluna da fonte, e devolve mm mais os pontos de cada extremidade (`x1`/`y1`/`x2`/`y2`) e `ponto` (extensão nula). `resolve_anchor` é o passo que traduz `[âncora, linhas]` na caixa real da imagem.

**Filtros, máscara do host e fontes — `core/filters.py`, `core/adapter.py`, `defs/fonts.py`.**

```python
from ajsystem.core.filters import resolve_filters, apply_filters
from ajsystem.core.adapter import masks_override, TEMAS
from ajsystem.defs.fonts import col_mm, line_mm, body_pt, stretch_pct, FONTS
```

`masks_override()` é o dicionário de máscaras do host, consumido por `merge_masks`/`definir_masks` no boot. `FONTS` é a lista **fixa** de famílias aceitas (os arquivos acompanham o framework, com a licença de cada uma ao lado); `font()` mede o avanço e a tinta **do próprio arquivo** e recusa o que não for monoespaçada. `col_mm`/`line_mm`/`body_pt`/`stretch_pct` são as quatro fórmulas da grade.

**Registro de model — `ajsystem/defs/data.py`.** `register_model(Model)` liga um model SQLAlchemy ao nome de entidade que o report/list usa.

```python
from ajsystem.defs.data import register_model, entity_fields
register_model('compra', Compra)     # nome da ENTIDADE + a classe; liga o model ao report/list
campos = entity_fields(Compra)         # dicionário campo -> cfg, do próprio model
```

### 5.10 `Query`, `Table` e `Session` — `ajsystem/defs/data.py`

**`Query`** (`:95`) — 6 props, fonte de dados **readonly** de sessão ou relatório: `columns`, `join`, `when`, `groups`, `order`, `totals`.

**`Table`** (`:106`) — 3 props, variante **editável**: `columns`, `order`, `totals`.

**`Session`** (`:136`) — 4 props: `template`, `fields`, `query`, `table`. É a spec da sessão dentro de `Form.sessions`; `fields` é a relação 1:1 child↔pai e `query`/`table` o corpo.

### 5.10.1 QSpec — query declarativa SQL-like (`ajsystem/defs/qspec.py`, `core/qrun.py`, `core/text.py`)

`QuerySpec` com as props na ordem do SQL — `select, dist, from, join, where, groups, order, limit` — executada por `qrun.run_query`: WHERE/ORDER/LIMIT/GROUP BY no banco, `OVER` em passo único (1 query, sem N+1), `calc` depois, ordenação final incluindo computados, com cast tipado e nulo-primeiro no asc. `where` (e o `extra_where` do executor) usa a **gramática literal dos filtros** — dict/lista = `E`, `OR(...)`/`AND(...)`, sentinelas, operadores e `IN`; nome fora do model quebra nomeando. `extra_conditions` recebe condições SQLAlchemy já compiladas (ex.: `fixed`/`filter_cond` da listagem) e as aplica antes dos `OVER`s. Entrada do `select` espelha o `Field` (`field/agg/func/over/calc/pos_list/label/width/align/format`, sem sub-dict); `over` exige `func` explícito do catálogo (`rownumber/rank/denserank/…`) e `order` aceita expressão do registro `EXPR_FUNCS` (só `coalesce` liberado). Templates (`calc`, coluna `text`, `group text`) falam a mesma língua (`core/text.py`): `'{campo}'` label, `'{x:02d}'` cru, `'{?campo:literal}'` ternário sem `else`. `PivotSpec` (`src/lines/columns/aggs/filters`) declara a estrutura do pivot; o executor em `core/pivot.py` agrega em memória, produzindo linhas por combinação de `lines` e colunas por valor do eixo `columns` × medida. Nomes gerados: `` `<agg>__<slug(valor)>` `` (ex.: `total__jan/2026`). `count` conta valores não-nulos; `sum/avg/min/max` ignoram `None`. Valor `None` no eixo de coluna vira coluna própria, rotulada `'(vazio)'`, ordenada por último. Colunas geradas herdam a cfg do campo medido (tipo/máscara/decimais) via `pivot_layer`. Restrições: somente leitura (sem `field_id`, sem `master/detail/edit`), coluna única no v1 (multi-nível é fase 2).

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

| Formato | Exemplo | Comportamento |
|---|---|---|
| **Entidade única** | `'Orcamento'` | Expande todos os campos da entidade |
| **Lista explícita** | `['data', 'total', 'cliente_id']` | Inclui exatamente os campos listados |
| **Lista com prefixo** | `['Orcamento.data', 'Cliente.nome']` | Campos de entidades diferentes via prefixo `Entidade.campo` |
| **Multi-entidade** | `{'Orcamento': ['data', 'total'], 'Cliente': ['nome', 'telefone']}` | Agrupa por entidade; resolve cada grupo contra seu Schema merged |

#### Regras

1. **Entity/Schema são a base de overrides** — Entity (model) + Schema (rota) = merged config; a entrada do `select` (query) é uma camada de props por cima. Inline dicts em lista são ignorados (warning).
2. **`fields`/`columns` respondem "quem existe e em que ordem"** — não "onde aparece". A posição é dos slots da **página**: listagem `line`/`card`/`hidden` (§5.6), form `bar`/`footer`/`body`/`hidden` (§5.5); vale igual nos dois formatos (expansão ou lista explícita).
3. **Multi-entidade** — cada entidade resolve contra seu próprio `full_schema[entidade]`. Requer que o Schema da página tenha as entidades declaradas.

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

### 5.14 Máscaras e formatação numérica — `defs/masks.py` + `app/extends/masks.py`

Catálogo do motor (default **en-US**) com override do host (mesmo merge de `buttons`/`inputs`/`fonts`): `MASKS < Masks(app)`. `init.py` aplica via `defs.masks.definir_masks` **antes** de registrar módulos e publica `AJ_MASKS` no Jinja (→ `window.AJ_MASK` no `sys.html`).

| Chave | Default (framework) | Papel |
|---|---|---|
| `DECIMAL` / `THOUSAND` | `'.'` / `','` | separadores de saída (`pt-BR`: `','`/`'.'`) |
| `MONEY` | `{'USD': '$'}` | catálogo por id ISO (`{'BRL':'R$',…}`) |
| `DEFAULT_MONEY` | `'USD'` | moeda-base (legados `1`/`True`/`'brl'` e `@M` sem id) |
| `MVALOR`, `MCPF`, `MCNPJ`, `MCEP`, `MPLACA`, `MTEL`… | — | máscaras nomeadas (o host define as de domínio). Nas Entities/Schemas importe **o nome**: `from app.extends.masks import MVALOR` e `'mask': MVALOR` |

**Comandos `@X`** (`core/formats.py:parse_mask`): `U/L/C/T` (texto), `R` (remove separadores no save), `B` (branco se zero), `X` (sufixo C/D), `M(id)` (moeda: `@M(BRL) 999,999.99`).

**Máscara numérica canônica** (escrita em inglês; o motor troca pelos `DECIMAL`/`THOUSAND`): `0` = dígito com zero-pad, `9` = dígito opcional, `,` = milhar (agrupa se presente), `.` = decimal (casas após o último `.`). Ex.: `'999,999.99'` → `1.234,50` em pt-BR. Máscaras de texto/data usam literais (o `9` de CPF casa `0` e preserva zeros à esquerda).

**Exemplo de troca de moeda** — só `app/extends/masks.py` (mudar `DEFAULT_MONEY`/`MONEY`/`MVALOR`):
```python
DECIMAL, THOUSAND = '.', ','
MONEY = {'BRL': 'R$', 'USD': '$', 'EUR': '€'}
DEFAULT_MONEY = 'USD'
MVALOR = '@M(USD) 999,999,999.99'
# ...
Masks = {'DECIMAL': DECIMAL, 'THOUSAND': THOUSAND, 'MONEY': MONEY,
         'DEFAULT_MONEY': DEFAULT_MONEY, 'MVALOR': MVALOR, ...}
```
→ list/form/report/totais passam a `$ 1,234.56`, sem tocar Entity/Route/template.

**Leitura/escrita do valor de um input numérico.** O input guarda o valor na convenção do **campo**, nem sempre igual à do texto exibido, e cálculo (`data-calc`), totais, `enabled`/`on_set` leem esse valor — então a leitura tem de ser a mesma que o servidor fará no POST:

| Onde | Função | Regra |
|---|---|---|
| Python | `parse_brl` (`core/formats.py`), `as_num` (`core/utils.py`), `_coerce` (`core/form.py`) | vírgula presente → decimal do app, ponto é milhar (`'1.234,56'`); **sem vírgula o ponto é decimal** (`'6.00'`, `'6.5'`) |
| JS | `parseNumText(v)` / `parseNumField(el)` (`static/js/formats.js`) | idem — é o espelho de `_coerce`/`as_num` |
| JS | `parseNum(v)` | só para **texto exibido** (ordenar coluna, comparar célula): ponto é sempre milhar |
| JS | `numToInput(v, dec)` / `numToInputFor(el, v)` | escreve na convenção do campo alvo (`dec` = `data-num-decimals`), espelhando `fmt_num` |

Sem `decimals`, `fmt_num` **não agrupa** (`'1000'`, `'1234,5'`) justamente para a leitura de volta ser inequívoca. `'1.000'` continua ambíguo por construção: sem vírgula é lido como `1.0`, nos dois lados — quem quiser `1000` escreve `'1000'` ou `'1.000,0'`. Num campo com `decimals`, use `numToInputFor`/`fmtNumBR` para escrever, nunca `String(valor)`: um `Decimal` cru (`'6.00'`) entra no input e sai multiplicado por 100 no `calc`.

**Espaço de input ≠ espaço de exibição — a linha que separa os dois formatadores.** `fmt_num`/`numToInputFor` escrevem **`inp.value`**, na convenção do campo (`dec` = `data-num-decimals`); `render_value`/`itFmtByAttrs` escrevem **`textContent`**, na convenção da máscara (`data-fmt-mask`). Trocar um pelo outro não é detalhe de estilo: `itFmtByAttrs` num campo `percent` colocaria `'12,5%'` dentro do input, duplicando o `%` do span ao lado.

E **`data-num-decimals` tem que existir em todo input numérico, inclusive desabilitado** — é ele que dá a `dec` para o escritor documentado. `calc` (`total`), `readonly` e `_ro_msg` renderizam `disabled`, e todo destino de `data-total-target` é um deles: com o atributo ausente não havia o que ler e a escrita caía em `String(num)`, que perdia a formatação que o servidor tinha acabado de renderizar. As guardas de `disabled`/`readOnly` em `numDecimals` (`static/js/formats.js`) e `calcIsCalc` (`pages/sys.html`) já eram código morto esperando isso.

**Exibição do valor — um passo só.** `fmt_num` é o que entra no `<input>`; o que sai na tela é `components/form_macros.html:render_value(val, f)`, o mesmo passo para o form (campo `readonly`/`calc`), a `item_table` e a listagem/`query` (`pages/list.html:_value_cell` chama e só resolve `calc`/`lookup`/`options`/imagem/booleano). `f` pode ser um `Field` ou a coluna da listagem (`core/list.py:field_to_column`) — os dois expõem `input`/`mask`/`num_decimals`/`currency`/`percent`.

| Ordem | Condição | Filtro | Exemplo |
|---|---|---|---|
| 1 | `none` ou string vazia | — | `—`, `''` |
| 2 | `percent` | `percent` | `12,5%` |
| 3 | valor tem `strftime` | `mask` se a máscara tem tokens, senão `fmtdate` | `07/03/2026` |
| 4 | `input == 'number'` | `mask_cmd` (com `num_decimals`) | `1.234,50` · `R$ 1.234,50` · `''` no `@B` zero · `-5,00 D` no `@X` · `1.234` no `ID` |
| 5 | tem `mask` | `format` | `123.456.789-09` (`@R` de CPF), `João Silva` (`@T`) |
| 6 | sem máscara | o valor cru | — |

`Field.num_decimals` (`defs/data.py`) é a prop de **exibição** das casas: o `decimals` declarado, ou **0** para input numérico sem casas — o caso de `ID`/`DK`, que `FIELD_TYPES` define como `input: 'number'` sem `decimals` e sem máscara, e portanto não recebem `num_mask`. Sem essa regra o `mask_cmd` recebia `None` e caía no default de 2 casas, e o `#` da listagem virava `6,00`.

Número **não** passa por `fmt_id`: aquele alinha em 7 colunas com NBSP (é layout de id, não de coluna, e numa coluna alinhada à direita pelo CSS o padding vira espaço à esquerda), e agrupando a string inteira punha o separador dentro das casas decimais (`'1.234..50'`) e dentro do texto (`'J.oão'`). `format` só trata número como número quando a máscara tem corpo numérico **ou** não tem transform de texto — `@T` com `1234.50` devolve `'1234.50'`, não `'1.234,50'`.

**O cliente é o segundo renderizador, e ele recebe a máscara.** `calc`, coluna calculada e total são redesenhados no navegador (`itCalcRefresh`/`formCalcRefresh`/`itSessionTotals`), e antes disso só viajavam `data-calc-currency` — emitido **quando a máscara tem `@M`**. Como `MVALOR` é `'999,999.99'` (sem `@M`, de propósito: a moeda vai no rótulo da coluna do relatório), esses pontos caíam em `String(v)` e devolviam o que o servidor tinha acabado de formatar. Por isso o contrato é a **máscara**, não a moeda: `components/form_macros.html:fmt_attrs(f)` emite `data-fmt-mask`/`data-fmt-decimals`/`data-fmt-currency`/`data-fmt-percent` do `Field`, e `pages/sys.html:itFmtByAttrs(el, v, dec)` decide no cliente na **mesma ordem** da tabela acima. Quem declara a máscara manda; um campo numérico sem máscara declarada ainda sai pelas casas, e um `ID` sai inteiro agrupado. As casas saem por `_fmtDec` e não por `fmtNumBR`, porque `fmtNumBR` escreve o input (que sem casas não agrupa de propósito — ver a tabela de leitura/escrita acima) e aqui é `textContent`.

Os dois lados são verificados como par, e nos **dois espaços**: o mesmo `Field` e o mesmo
valor têm que dar a mesma string de `render_value` (Python) e de `itFmtByAttrs` (JS,
`textContent`); e o mesmo valor nas mesmas casas, a mesma de `fmt_num` e de
`numToInputFor` (`inp.value`). A única divergência conhecida é o arredondamento de meio exato (`0.125` em 2 casas, `12.5` em 0): o `%.Nf` do Python arredonda para par e o `toFixed(n)` do JS para cima. Ela é **pré-existente** — o par `fmt_num`/`fmtNumBR` já discordava assim — e só aparece quando o float é exatamente um meio na casa mostrada.

Um agregado de `totals` (`query`/`table`) recebe o `Field` e sai por `render_value` também (`item_table.html:render_agg_total(total, f)`), e as casas do total vêm de `num_decimals`, não da escala da coluna no banco — `compra_itens.qtd` é `NUMERIC(12,3)` com `type: 'NUM'` (2 casas na linha), então o total saía com 3. A grade do modal de busca (`core/search.py:_fmt_cell`) tem o mesmo despacho e usa `format` no ramo numérico.

### 5.14.1 Constantes `ajsystem/defs/constants.py`

| Constante | Valor | Impacto |
|---|---|---|
| `POS_0_NOT_EMPTY` | `{'pos':0,'when':{'not_empty':True}}` | `pos:0` explícito só quando valor≠vazio (só `form`, `ajsystem/defs/data.py` `is_visible_by_pos`) |
| `TODAY` | `date.today` (callable) | default de `Field.data` em forms novos |
| `CONNECTORS` | `frozenset` de ~40 preposições PT | normalização de busca textual |

> **Legado:** `CURRENCY`/`DEFAULT_CURRENCY` seguem em `constants.py` só como compatibilidade — a formatação passou a ler `MONEY`/`DEFAULT_MONEY` (masks) e o dataclass `Field` **não tem mais `currency`** (a moeda vem da `mask`, via `@M(id)`; `Field.currency` é derivada pelo motor). `normalize_currency` aceita ids ISO (`'BRL'`), legados `1`/`True`/`'brl'` e (`2`/`3`→`'USD'`/`'EUR'` se existirem); `0`/`None` = desligado.

> **Versionamento:** bump em `ajsystem/version` a cada assunto que muda **código de `ajsystem/`** — `core/`, `defs/`, `templates/`, `static/js/`, `init.py`, o que for. Não se limita aos dataclasses citados acima (`Field`/`Form`/`Report` são os exemplos mais visíveis, não a condição); um ajuste em `formats.js` ou num template é bump do mesmo jeito. **Alterações só em `app/` não bumparam a versão do framework.** A versão é `ciclo.ano.mes.dia.seq` (`1.26.10.08.0001`): o dia vem do calendário e o `seq` reinicia em `0001` a cada dia novo — dentro do mesmo dia é o `seq` que sobe (`.0002`, `.0003`…), nunca o dia. Ajustar só esta README é `docs` e não bumpa. A versão do **app hospedeiro** é separada e **não é bumpada pelo motor**: mora em `APP['version']` (`app/config.py`, `{cycle, year, month, number}`) sem arquivo próprio, e quem bumpa é o dev, na mão, com o comando `versao` do shell — roda na raiz do projeto, preserva `cycle`, toma `year`/`month` da data de hoje, incrementa `number` e o zera em ano/mês novo, grava em `app/config.py` e imprime o resultado como `1.aa.mm-nnn`. É função do host (`~/.bash_aliases`), não do repo. Como mexe só em `app/config.py`, não afeta a versão do framework. `FIELD_TYPES`/`_FIELD_KEYS` (`data.py:413`) valida chaves (`FieldConfigError`).

