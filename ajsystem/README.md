# AJSYSTEM 1.26.10.22.0004 — Manual do Framework

> Vinculado a `ajsystem/version` (`1.26.10.22.0004`) — formato `ciclo.ano.mes.dia.seq`: ciclo `1`, ano `aa`, mês `mm`, dia `dd` e **seq no dia** `bbbb` (4 dígitos). O bump vem de cada assunto que muda código de `ajsystem/` (não só os dataclasses desta referência; `app/` não entra) — ver **Versionamento** em 5.14.1. O dia vem do calendário e o `seq` reinicia em `0001` a cada dia novo; no mesmo dia, só o `seq` sobe. Histórico na seção 6. A versão do **app hospedeiro** é outra, em `APP['version']` (`app/config.py`), e é o dev que bumpa na mão com o comando `versao` (ver 5.14.1).

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

O que a página **ajusta** mora em `Page.props.list` sob a chave `filter`, um dict com cinco chaves independentes:

| Chave | Forma | Efeito |
|---|---|---|
| `hidden` | fieldspec (`'campo'`, `'Ent.campo'`, lista, `{'Ent': [...]}`) | tira do painel — sem UI. Para uma coluna **visível** cujo filtro não faz sentido (ex.: `indice` em `operacoes`); um campo já no slot `hidden` nem chega aqui |
| `fixed` | `{campo: valor}`, lista ou `OR(...)`/`AND(...)` | vira **`WHERE` fixo**, também fora do painel. Dict e lista são **AND**; `OR(...)`/`AND(...)` agrupam (aninháveis). Valor: literal → `=`; sentinelas `NULL`/`NOT_NULL` (↔ `is_null`) e `EMPTY`/`NOT_EMPTY` (↔ `is_empty`); `('op', valor)` com `op` em `=`,`!=`,`>`,`>=`,`<`,`<=`,`like`,`ilike`,`in`,`not in`; lista → `IN`; callable é chamado; `None` **ignora** a folha. Folha que não é field do pool vale como **coluna** do model (ex.: `transferencia_id`, que não é `Field`). Era `pos_filter: 9` + `default` do `Field` — agora o valor mora **na listagem**, que é quem o usa |
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
    'filter': {
        'fixed': {'tipo': 'P'},                 # WHERE tipo = 'P' (era pos_filter: 9)
        'types': {'checklist': 'status'},       # status filtra por checklist (era pos_filter: 3)
    },
    'hidden': ['cancelado', 'tipo'],
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
- Campo fora do painel, conector inválido, `g` não booleano, bloco vazio, mistura de bloco/linha ou JSON malformado **quebra nomeando** (`list.filter: _f[i].rows[j] campo ...`, `_f[i] bloco vazio`, `_f[i].g esperava booleano`). Nada é descartado em silêncio.
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
| `body.table.columns` | `dict\|list` | `{'titulo':{}}` ou `['indice','nome',{'id':{'width':6}}]` (forma enxuta igual ao `select`) | `_apply_entity` herda `label`/`calc`/**`width`** da `Entity` (Schema vence); coluna computada na query usa o attr direto. **Sem `width`, a coluna mede o field** (mesma conta da listagem, com a máscara como mínimo) e a soma é centralizada na área útil — declarar é exceção, não obrigação |
| `body.table.groups` | `dict\|list` | `{'tipo':{action:1,print:3,text:'{tipo:d}. {tipo}'}}` | control-break: `action` (quando: 1 abre, 2 fecha, ausente = toda linha) × `print` (onde: 0 nunca, 1 coluna, 2 linha, 3 fora da tabela). Legado `{print,place}` traduzido via shim. `order` da fonte tem que abrir com as quebras (senão quebra nomeando). `totals` no grupo = subtotal (`{'label','align','span','bline'}`; ausente = não totaliza; `bline` = régua antes); fechamento do grupo usa `gline` (legado `line` traduzido); `lf` no grupo respira **ao redor do título/linha visível** (`-n` antes, `n` depois, `[antes, depois]`) |
| `when` (item) | `str` | `{'TEXT': {'text': '…', 'when': 'evento.tipo'}}` | imprime só se o path (pontilhado ok) for truthy; ausente = sempre |
| templates | — | `'{total:brl}'`, `'{a.b}'`, `'{?c:…}'`, `'{x\|dflt}'` | `:brl` moeda; path pontilhado com navegação segura; `\|dflt` fallback; labels LIST da Entity |
| fluxo | — | `FIELD`/`TEXT` seguem na linha | **cada item ESTACIONA na borda do que desenhou** e o próximo desce sozinho se a linha não tem mais lugar — ver **Estacionar**; `PCOL` avança pela largura; `pcol+largura>ncol` envolve; maior que a linha trunca; quebra por `rows_after/before` ou posicionamento; sem âncora, `FIELD`/`TEXT` com `width` herda o cursor da zona (só volta à 1ª coluna se o cursor está fora da zona), `TEXT` avulso sem `width` é linha própria (avanço de linha automático quando o fluxo terminou antes dela; `align` vale na zona) e bloco (`IMAGE`/`LINE`/…) volta ao início; sub-item de `TEXTS` flui apertado inline. O "início" é o da **zona**, não o da margem — ver **Zona do logo** |
| `body.table.totals` | `dict` | `{'label':'TOTAL GERAL','align':'R','span':3}` | linha de total geral (sempre, com régua antes e depois — internas). `agg` na coluna diz O QUÊ; sem `totals` não totaliza. Legado `footer/footer_label` via shim. Réguas seguidas sem conteúdo entre elas saem uma vez só |
| `body.table.extend` | `list` | `[(col\|[a,b], texto[, props]), 'LINE', 'LF', 'CR']` | linhas **dentro do quadro** depois dos totais (ex.: Acréscimo/Desconto/Total). `when` por linha; placeholder puro `{campo}` herda o `format` da coluna; `font`/`cpi`/`lpi`/`font_size` recusados (a grade da tabela é dela) |
| `body.table.hierarchy` | `list\|dict` | legado (derivado de `groups` quando ausente) | mantido por compat; prefira `groups` |
| `body.filter` | `dict\|list\|OR/AND\|callable` | `filter_select('tipo')` | filtro padrão do `source`; mesma gramática literal de `filter.fixed` (cast tipado). O `filter` recebido por `print_report`/`filter_select` é combinado: dicts fazem merge e as demais formas viram `AND`. Callable recebe o model e devolve o spec; Query é aceita só na fonte-entity, sem combinação (com `body.source` QuerySpec, devolve spec). Aplicado **antes** dos `OVER`s e da ordenação |

### 5.8 `ReportColumn` e amigos — `ajsystem/defs/report.py`

**`ReportColumn`** (`:34`) — 9 props (novas: `text`, `suppress`):

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

**`ReportField`** (`:13`) — 5 props, spec de campo solto (fora de `columns`): `field`, `label`, `align` (`left`), `format`, `function`.

**`ReportGroup`** (`:66`) — 7 props: `field`, `label`, `position` (`titulo`), `subtotal` (`True`), `total` (`True`), `fecha_tabela` (`False`), `nova_pagina` (`False`). Agrupa linhas por campo; `position` decide se o rótulo entra como título de página (`titulo`) ou como linha da tabela.

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

`QuerySpec` com as props na ordem do SQL — `select, dist, from, join, where, groups, order, limit` — executada por `qrun.run_query`: WHERE/ORDER/LIMIT/GROUP BY no banco, `OVER` em passo único (1 query, sem N+1), `calc` depois, ordenação final incluindo computados, com cast tipado e nulo-primeiro no asc. `where` (e o `extra_where` do executor) usa a **gramática literal dos filtros** — dict/lista = `E`, `OR(...)`/`AND(...)`, sentinelas, operadores e `IN`; nome fora do model quebra nomeando. `extra_conditions` recebe condições SQLAlchemy já compiladas (ex.: `fixed`/`filter_cond` da listagem) e as aplica antes dos `OVER`s. Entrada do `select` espelha o `Field` (`field/agg/func/over/calc/pos_list/label/width/align/format`, sem sub-dict); `over` exige `func` explícito do catálogo (`rownumber/rank/denserank/…`) e `order` aceita expressão do registro `EXPR_FUNCS` (só `coalesce` liberado). Templates (`calc`, coluna `text`, `group text`) falam a mesma língua (`core/text.py`): `'{campo}'` label, `'{x:02d}'` cru, `'{?campo:literal}'` ternário sem `else`. `PivotSpec` (`src/lines/columns/aggs/filters`) declarado, executor pendente.

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

> **Versionamento:** bump em `ajsystem/version` (e entrada na seção 6) a cada assunto que muda **código de `ajsystem/`** — `core/`, `defs/`, `templates/`, `static/js/`, `init.py`, o que for. Não se limita aos dataclasses citados acima (`Field`/`Form`/`Report` são os exemplos mais visíveis, não a condição); um ajuste em `formats.js` ou num template é bump do mesmo jeito. **Alterações só em `app/` não bumparam a versão do framework.** A versão é `ciclo.ano.mes.dia.seq` (`1.26.10.08.0001`): o dia vem do calendário e o `seq` reinicia em `0001` a cada dia novo — dentro do mesmo dia é o `seq` que sobe (`.0002`, `.0003`…), nunca o dia. Ajustar só esta README é `docs` e não bumpa. A versão do **app hospedeiro** é separada e **não é bumpada pelo motor**: mora em `APP['version']` (`app/config.py`, `{cycle, year, month, number}`) sem arquivo próprio, e quem bumpa é o dev, na mão, com o comando `versao` do shell — roda na raiz do projeto, preserva `cycle`, toma `year`/`month` da data de hoje, incrementa `number` e o zera em ano/mês novo, grava em `app/config.py` e imprime o resultado como `1.aa.mm-nnn`. É função do host (`~/.bash_aliases`), não do repo. Como mexe só em `app/config.py`, não afeta a versão do framework. `FIELD_TYPES`/`_FIELD_KEYS` (`data.py:413`) valida chaves (`FieldConfigError`).

---

## 6. Histórico de versões

### 1.26.10.22.0004
- **`lf` no grupo.** `body.table.groups[campo].lf` passou a ser preservado na síntese de `levels` e aplicado ao redor do título/linha visível do grupo (`-n` antes, `n` depois, `[antes, depois]`), sem alterar o `table.lf` (que continua único para a tabela). No grupo `print:2`, o respiro entra **depois do cabeçalho de colunas repetido e antes do título**; no `PLANO`, `'lf': -1` abre a linha antes do título, inclusive no primeiro grupo.
- **Verificado.** Posições Y do PDF com e sem `lf` no grupo, `test_group_lf.py` e harness HTTP/`PLANO` com filtros.

### 1.26.10.22.0003
- **A gramática literal dos filtros virou uma só.** `core.filters.compile_conditions` passou a ser o ponto único de `list.filter.fixed`, `report.body.filter` e `QuerySpec.where`/`extra_where`: dict/lista em `E`, `OR(...)`/`AND(...)` aninháveis, sentinelas, operadores e `IN`, com cast opcional pelo tipo do field. `compile_fixed` continua como wrapper compatível.
- **`body.filter` respeita o filtro da request.** O argumento de `_auto_data` deixou de ser sobrescrito pelo `body.filter` (o bug anulava `filter_select`): agora `body.filter` é o padrão e o filtro explícito é combinado — dois dicts fazem merge (a request vence) e as demais formas viram `AND`. Callable recebe o model e devolve spec; na fonte-entity, uma Query devolvida continua aceita quando não há combinação. Com isso o `PLANO` volta a filtrar por `tipo` no tempo de execução, antes dos `OVER`s.
- **`run_query` aceita condições já compiladas.** `extra_conditions` aplica `fixed`/`filter_cond` antes dos `OVER`s e do `calc`; o caminho `columns=QuerySpec` da listagem passou a usá-las (antes o `_base_query` era ignorado nesse caminho).
- **Verificado.** Harness com `compile_conditions` (dict/lista/`OR`/`AND`/sentinelas/`IN`/`LIKE` sem cast/campo inválido), `apply_where` com cast, `PLANO` com e sem `body.filter`, merge de dicts e `AND` com `OR`, listagem `QuerySpec` filtrando `6/13` (`/operacoes/?tipo=1`), PDF do `PLANO` recebendo `tipo=1` e HTTP 200 em `/operacoes/`, `/operacoes/?tipo=1`, `/operacoes/?_d=0`, `/pagar/` e `/receber/`.

### 1.26.10.22.0002
- **Campo inicial na largura da coluna.** No filtro em branco, o select de campo da linha compacta deixou de ocupar toda a linha: ele reusa a grade do construtor, fica na coluna `campo` e reserva a coluna de ações, mantendo a mesma posição e largura da linha de edição; no mobile acompanha a coluna de `1fr`.
- **Verificado.** Jinja parse e `/pagar/`, `/receber/`, `/insumos/` em 200 (inclusive `_d=0`), com `filter-next-first`/`filter-first-field` no HTML.

### 1.26.10.22.0001
- **Construtor de filtros com a linha seguinte como ponto de adição.** A linha seguinte virou o único ponto de adição, agora **abaixo do bloco** e com `+` no select em vez de "Adicionar": select E/OU (ou só o campo na primeira linha) e, após a escolha, a grade completa. `E`/`OU` cria linha solta; `E (`/`OU (` abre bloco agrupado; `)` separado fecha o bloco aberto ou agrupa a sequência final de linhas soltas. Os parênteses agora emolduram o bloco: `(` no início da linha de abertura e `)` no fim da divisória inferior. Linha solta não tem cabeçalho/rodapé; bloco agrupado do usuário tem só `[🗑]` no rodapé; o PADRÃO ficou somente leitura, com o checkbox na abertura e `)` sem lixeira.
- **`g` no `_f`.** `parse_json_blocks` passou a preservar e validar `g` por bloco (`false` = linha solta, `true` = agrupado; ausente = `true`), e o cliente serializa `g` junto de `c`/`rows`. `_df` deixou de ser enviado; o PADRÃO não é mais editável em memória.
- **`[+]`/`[)]` na linha de edição.** O `OK` único da linha seguinte virou dois botões: `[+]` confirma a row e rearma o editor no mesmo bloco/sequência, sem voltar ao select compacto; `[)]` confirma e fecha o bloco agrupado (ou agrupa a sequência solta). O alvo é preservado em `next.openBlock`/`next.blockId`, então o bloco agrupado aceita várias linhas seguidas.
- **Verificado.** Jinja parse, `ast.parse`, `node --check` e harness do `listPage()` (linha solta sem moldura, grupo com moldura, edição dentro do bloco, `[+]` rearmando o mesmo alvo, `[)]` fechando/agrupando, `closeRun`, commit no APLICAR, PADRÃO, `g` na serialização); `/pagar/`, `/receber/` e `/insumos/` em 200, inclusive `_f` com `g:false`, `g:true` e formato legado.

### 1.26.10.21.0012
- **PADRÃO ativo por padrão, com toggle.** O estado inicial do checkbox agora nasce direto de `default_on` (`defaultOn: true/false` no `x-data`), sem depender do `init()`, e o input recebe `checked` no HTML quando o servidor resolve o PADRÃO ligado — assim aparece marcado desde o primeiro render. Sem `_d` (ou `_d=1`) o PADRÃO continua ativo; `_d=0` o desliga, e o checkbox na linha de abertura do bloco permite religar/desligar a qualquer momento.
- **Verificado.** `/pagar/` sem args e com `_d=1` → `defaultOn: true` e `checked`; `?_d=0` → `defaultOn: false` sem `checked`; Jinja parse ok.

### 1.26.10.21.0011
- **Checkbox do PADRÃO no início do bloco.** O checkbox que liga/desliga o filtro padrão saiu do rodapé (ao lado de **APLICAR**) e foi para o fim da linha de abertura do bloco **Filtro Padrão**, depois da divisória. Sem texto visível, usa `FILTER_DEFAULT` como `title`/`aria-label` para não repetir o título da seção. A linha de abertura saiu do bloco e fica visível sempre que há PADRÃO, mesmo com ele desligado, para o checkbox continuar alcançável (antes ele sumia junto com as linhas).
- **Verificado.** Jinja parse ok e `git diff --check` limpo.

### 1.26.10.21.0010
- **Coluna dos presets mais larga.** A coluna `opção` da `.filter-grid` (select de preset do `date`) passou de `minmax(7ch, 1fr)` para `minmax(16ch, 1.2fr)`, cabendo rótulos como `Mês/Ano Anterior` sem corte; as colunas de valor foram para `minmax(12ch, 1fr)` para os inputs de `mes`/`ano`/`from`/`to` não ficarem espremidos.
- **Largura padrão do painel de 88ch.** `DEFAULT_FILTER_MAX_WIDTH` subiu de `70ch` para `88ch` para a linha da grade respirar; o app continua vencendo ao declarar `filter.max_width`.
- **Verificado.** Jinja parse ok e `git diff --check` limpo.

### 1.26.10.21.0009
- **Blocos de filtro com parênteses.** O root de `_f` agora é uma lista de blocos `{c, rows}`; cada bloco é um operando entre parênteses, com linhas em E/OU (E prioritário) e blocos ligados por E/OU (E prioritário). O `(` abre na primeira linha, o `)` fecha na última, e a primeira linha não tem conector; o elo do bloco com o anterior fica no rodapé do anterior. O PADRÃO é o primeiro bloco.
- **Rodapé e ações.** Cada bloco termina em linha + seletor E/OU + `[+]`; o seletor edita o próximo bloco, o `[+]` (só no último visível) cria um bloco irmão e o `X` remove o bloco do usuário. O rótulo **"Fim do bloco"** foi removido.
- **Servidor.** `parse_json_blocks` aceita o formato novo e o `_f` plano legado (um bloco); `blocks_condition` compila o root e `first_block_conn` acha o elo com o PADRÃO; limites de 32 blocos/128 linhas; bloco vazio, mistura, conector inválido ou JSON malformado quebra nomeando. `active` agora são **blocos**; `_df` continua em **linhas**.
- **Verificado.** Parser (legado/novo, erros nomeados e limites); 10 casos HTTP de junção e precedência em `/pagar/`; 15 listagens e 2 forms em 200; harness do `listPage()` com 38 asserções (blocos, rodapé, `[+]`, exclusão, serialização, `_df` e no-default) e `git diff --check` limpo.

### 1.26.10.21.0008
- **Sem spinner nos valores do filtro.** Os `input[type=number]` do painel (valor 1/2 e mês/ano dos presets) perderam as setas nativas: `::-webkit-inner/outer-spin-button` desligados e `-moz-appearance:textfield`/`appearance:textfield` no escopo `.list-filter-wrap`, sem mexer nos numbers de outras telas.
- **Verificado.** CSS renderizado em `/pagar/` e `/insumos/`; 15 listagens em 200 e `git diff --check` limpo.

### 1.26.10.21.0007
- **Placeholder do campo: `Campo:` / `Field:`.** `FILTER_SELECT_FIELD` deixou de ser `Selecione Campo`/`Select field`; o option vazio do select de campo agora mostra **`Campo:`** em pt e **`Field:`** em en.
- **Verificado.** Render de `/pagar/` e `/insumos/` em 200 com o novo texto; `node --check` do script.

### 1.26.10.21.0006
- **Ícone de remover/cancelar visível.** As ações chamavam `heroicon('x-mark')`, que gera `<use href="#i-x-mark">`; o sprite só tem **`i-xmark`**, então o `<use>` ficava vazio e o botão parecia invisível. Trocado para `heroicon('xmark')` nas duas ações: remover a linha confirmada e cancelar/limpar a linha em edição.
- **Verificado.** HTML de `/pagar/`: 7 usos de `#i-xmark`, 0 de `#i-x-mark`, símbolo presente no sprite; 15 listagens em 200 e `git diff --check` limpo.

### 1.26.10.21.0005
- **Linha nova recolhida com `[+]`.** O rascunho do bloco do usuário nasce só com o botão **`+`** na coluna E/OU (`FILTER_ADD`). Ao clicar, o `+` some e aparecem o conector (quando aplicável) e o select de campo; o `[X]` limpa e recolhe a linha nova. Linhas confirmadas continuam abrindo com o lápis, e o `[X]` restaura o snapshot anterior.
- **Conector depois do PADRÃO.** `hasActiveDefault`/`showsConnector` decidem quando a coluna aparece: segunda linha em diante, ou primeira linha do usuário quando há PADRÃO ativo com valor. Sem PADRÃO, a primeira linha do usuário não mostra conector (não há com o que ligar).
- **O primeiro conector do usuário liga os blocos.** `resolve_filter` usa o `c` da primeira linha **efetiva** de `_f` para combinar `default_cond` e `user_cond`: `and` mantém o PADRÃO restringindo; `or` produz `or_(default_cond, user_cond)`. `rows_condition` continua ignorando o primeiro conector dentro do bloco, então não há dupla aplicação. O PADRÃO nasce em `and`; a mudança de contrato está documentada na §5.6.
- **Verificado.** Harness do `listPage()`: rascunho recolhido, `arm()` revelando campo/conector, `[X]` recolhendo, conector na primeira linha do usuário só com PADRÃO ativo, segunda linha sempre com conector. No servidor, `/pagar/?_f=[id=79,c=and]` retorna 1 linha e `c=or` retorna 4 (PADRÃO OR id), provando a junção; 15 listagens em 200 e `node --check`.

### 1.26.10.21.0004
- **Divisórias visíveis.** O cabeçalho **`Filtro Padrão`** / `Default filter` e a linha que fecha o bloco padrão passaram a usar `height:1px;background:currentColor;opacity:.4` (em vez de depender só de `border-base-300`), garantindo as três linhas do desenho mesmo em temas claros.
- **Select de campo com `Selecione Campo` / `Select field`.** O option vazio usa a nova chave `FILTER_SELECT_FIELD`; `FILTER_FIELD` continua como `aria-label` e catálogo.
- **`[X]` de cancelar/limpar na linha em edição.** Aparece assim que há campo escolhido ou a linha ficou *dirty*. Em linha já confirmada (inclusive PADRÃO), restaura o snapshot anterior (`prev`) e volta ao texto; em linha nova ainda não confirmada, limpa campo/conector/valor. O `[ok]` continua condicionado a `hasValue(row)`. Snapshots são feitos no load, em `edit()` e em `ok()`; `cancelRow()` não remove a linha.
- **`mes_ano` do PADRÃO pré-preenchido.** `fromRow` chama `_fillMesAno`, que completa mês/ano atuais (ou do mês anterior) quando o default/URL traz só `{preset:'mes_ano'}`. Sem isso o default ficava com `hasValue=false` e era descartado no `_df` ao APLICAR; agora aparece como `10/2026` e serializa os três defaults.
- **LIMPAR não acende sozinho.** `_initialDefaults` guarda o snapshot já normalizado dos defaults, e `_rowValue` clona `v` (antes devolvia a mesma referência, então editar o default mutava o snapshot e o `canClear` invertia). Agora fica apagado no load, acende ao editar e apaga ao cancelar/limpar.
- **Verificado.** Harness do `listPage()`: defaults com `hasValue=true`, `cancelRow` restaurando alteração do PADRÃO, X aparecendo ao selecionar campo e limpando a linha nova, `submitFilters()` gerando `_df` com 3 linhas, `canClear` correto no load/edição/cancelamento/limpeza; 15 listagens em 200 e `node --check`.

### 1.26.10.21.0003
- **Seção PADRÃO com divisória.** Quando há default e ele está ligado, o painel abre com o cabeçalho **`Filtro Padrão`** / `Default filter` entre duas linhas; o fim do bloco padrão ganhou uma divisória de largura total antes do primeiro filtro do usuário. A chave i18n nova é `FILTER_DEFAULT_SECTION` (o checkbox do rodapé continua usando `FILTER_DEFAULT`).
- **Verificado.** `/pagar/` (com default) e `/insumos/` (sem default) em 200; `FILTER_DEFAULT_SECTION` presente em `pt`/`en`.

### 1.26.10.21.0002
- **Painel de filtros em grade sem cabeçalho.** A linha do construtor virou uma grade alinhada (`e/ou | campo | opção | valor 1 | valor 2 | ações`) via `.filter-grid`, sem a linha de títulos. O select de campo vazio mostra **`Campo`** / `Field` (`FILTER_FIELD`) no lugar de `—`. `[x]`/`[ok]` só aparecem quando `hasValue(row)` — inclusive datas que exigem parâmetro (`mes`, `ano`, `mes_ano`, `periodo`, `a_partir_de`, `ate_a_data_de`). Ao confirmar, os inputs da linha são trocados pelo **texto** alinhado na mesma grade (campo, operador/preset e valor), com editar/remover nos confirmados. Em telas < 768px a grade empilha sem rolagem horizontal.
- **Verificado.** Jinja/`node --check`; render das 15 listagens em 200; `hasValue`/`spansTwo`/resumos conferidos via harness do script; `/insumos/`, `/pagar/`, `/receber/`, `/categorias/`, `/orcamentos/` e `/transferencias/` em 200.

### 1.26.10.21.0001
- **Painel de filtros com largura padrão de 70ch.** `filter.max_width` passou a ter default interno: quando a chave não existe (ou é `None`), `core.filters.resolve_filter` aplica `DEFAULT_FILTER_MAX_WIDTH` (`70ch`). O app continua vencendo ao declarar `filter.max_width` (`int` → `ch`; string CSS), para mais ou para menos. `max_width` inválido segue quebrando nomeando.
- **A listagem abre espaço para o painel sem alargar a tabela.** `do_list_normal`/`do_list_master` usam `max_width = max(largura da lista, filter.max_width)` no container da página e prendem a aba **Dados** à largura da lista (`tab.max_width`, antes sem consumidor). Assim `/insumos/` (lista 67ch) mostra o painel em 70ch mantendo a tabela em 67ch; `/pagar/` (144ch) mantém a tabela e limita o painel a 70ch. Em telas pequenas o `mw-bound` continua sem cap.
- **Verificado.** `resolve_filter` para spec ausente/`int`/string/inválido; HTML de `/insumos/`, `/categorias/` e `/pagar/` com `--mw-cap` e estilos das abas conferidos; 15 listagens em 200.

### 1.26.10.19.0002
- **O `default` agora é uma seção PADRÃO de verdade.** As linhas declaradas aparecem no topo do painel, **editáveis/removíveis em memória**, e nascem ligadas; o checkbox ao lado de **APLICAR** desliga. O estado ganhou dois args reservados: **`_d`** (`0` desliga; ausente/`1` liga) e **`_df`** (JSON das linhas do PADRÃO **editadas em memória**). `_f` continua sendo **só** o bloco do usuário — o cliente não semeia mais o default nele. **LIMPAR** descarta as edições do PADRÃO e restaura as linhas declaradas; **APLICAR** serializa também a linha em edição (não perde o digitado).
- **O default restringe o filtro do usuário.** `filter_cond = and_(default_cond, user_cond)` quando o PADRÃO está ligado (antes o cliente misturava as linhas). `default` aceita um dict (AND das folhas) ou `OR(...)`/`AND(...)` com valores no shape do painel; o motor converte para **DNF** (`AND` distribui sobre `OR`) com limite de 128 linhas — `default_expression_rows`/`parse_json_rows` são a porta única, e o default declarado continua validado contra o painel.
- **Layout do painel sem rolagem horizontal.** `.list-filter-wrap` passou a `width: 100%`, o grupo de filtros quebra linha (`flex-wrap`) com `min-w-0`, e o label **`Campo:`** precede o select (a opção vazia é `—`). Nova chave **`filter.max_width`** (`int` → `ch`, ou string CSS) limita a largura do painel; sem ela, 100%.
- **Número `0` conta como valor.** `hasValue`/resumo do `listPage()` deixaram de usar truthiness: `0` agora é um valor preenchido (essencial para `saldo > 0`). Novo i18n `FILTER_FIELD`/`FILTER_DEFAULT` em `pt`/`en`.
- **Pagar/Receber ganharam default OR.** `(data mês/ano) OR (vencimento mês/ano) OR (saldo > 0)`, com `data` no pai e `vencimento`/`saldo` na linha. Para o `saldo` valer nos dois lados, `Previsao.saldo` virou **`@hybrid_property`** com expressão SQL (`coalesce(previsto)+coalesce(variacao)-coalesce(realizado)`); sem isso `_inversion_order_attr` devolvia a `property` Python e `?saldo_val1=1` dava 500 (`'>' not supported between property and float`). O mesmo caminho passou a devolver **só atributo usável em SQL** (hybrid/coluna), caindo para a coluna do pai quando o filho é `property` simples — é o que conserta também `status` no `master`. De passagem, o `calc` de exibição do `saldo` da previsão ficou nulo-seguro (`previsto - (realizado or 0) + (variacao or 0)`), que mostrava `—` quando `realizado` era `NULL`.
- **Verificado.** `ast.parse`/Jinja e `node --check` do script renderizado; smoke do default (DNF, `_d=0`, `_df` editado, `_d` ignorando `_df`, PADRÃO `AND` usuário, `max_width` int/CSS/inválido) e contagem de linhas de Pagar conferida contra SQL independente; `/pagar/` e `/receber/` em 200, inclusive `?saldo_val1=1` e `?status=1`.

### 1.26.10.19.0001
- **O painel de filtros virou um construtor de consulta.** Cada condição é uma **linha** (campo → operador/valor → **OK**) e a linha seguinte escolhe o conector **E**/**OU** com a anterior; `E` tem prioridade (`a E b OU c` = `(a AND b) OR c`). Os campos, os widgets por tipo e a aba **Filtros** continuam os mesmos — o que muda é que o valor deixou de ser um só por campo e a ordem/ligação passou a ser explícita.
- **A URL ganhou o arg reservado `_f`.** É um JSON **ordenado** de `{f, c, v}` (`v` no mesmo shape do painel antigo). `parse_rows` valida contra o painel e **quebra nomeando** (`list.filter: _f[i] campo ...` / conector inválido / JSON malformado) — nada some em silêncio. Sem `_f`, os args por campo do painel antigo (`campo`, `campo_value`, `campo_mode`, `campo_val1/2`, `campo_preset`, `campo_from/to/mes/ano`) continuam valendo em **E**, e o `default` segue para os campos que a URL não citou; com `_f` as linhas são a verdade inteira.
- **Motor.** `core.filters` ganhou `_row`/`parse_rows`/`default_rows`/`rows_condition` (agrupa ANDs consecutivos e abre grupo a cada `or`) e `resolve_filters` devolve `(initial, active)`; `ResolvedFilter` expõe `initial`/`active` (linhas) e `filter_cond` (WHERE compilado). `do_list_normal`/`do_list_master` aplicam `filter_cond` uma vez e **não** percorrem mais campo a campo; `apply_filters` deixou de ser chamado.
- **Catálogo do `date` corrigido e completado (14 presets).** `Mês atual`/`Mês anterior` passam a olhar **só o mês** (aniversariantes), separados de `Mês/Ano atual`/`Mês/Ano anterior` (mês **e** ano, para vencimentos) — o novo `mes_ano_anterior` fecha a simetria e o widget pré-preenche mês/ano (o anterior com o mês anterior). Os presets que eram no-op (`ultimos_7_dias`, `mes`, `ano`, `ate_a_data_de`, `a_partir_de`, `periodo`) passam a filtrar de verdade, e `mes`/`ano` pedem o valor no widget. Corrigido de passagem o `do_list` que passava o `from` da linha como `hoje` em `filtrar_vencimento_query`; hoje `_date_conds(col, cfg, hoje=None)` recebe o dict inteiro.
- **UI (`templates/pages/list.html`).** A aba `Filter` foi reescrita com `x-for` de linhas, seletor de campo, resumo por linha (editar/remover), botão OK, conector E/OU e um rascunho sempre no fim; `listPage()` serializa `_f` e remove os args legados dos campos conhecidos ao aplicar. Novo `i18n.FILTER_AND`/`FILTER_OR` e `FILTER_MONTH_YEAR`/`FILTER_MONTH_YEAR_LAST` em `pt`/`en`.
- **Verificado.** `ast.parse` limpo e Jinja parse ok; 19 listagens e 15 forms em 200; painel não expõe `tipo` (fixo) nem `conta_id`/`indice` (hidden); `_f` fim-a-fim em `/recebimentos/` (`mes_ano`, `mes_atual`, `ano_atual`, `mes OR valor`), fallback legado, `_date_conds` dos 14 presets, `parse_rows` e agrupamento `AND>OR`.

### 1.26.10.08.0044
- **As transferências saíram de `pagamentos`/`recebimentos`.** Um movimento de transferência (`transferencia_id` preenchido) aparecia nas duas pontas — era uma saída e uma entrada como qualquer outra. A resposta não é um `if` na rota nem um `join` solto: é o `WHERE` fixo da listagem (`'fixed': {'tipo': SAIDA, 'transferencia_id': NULL}`). O problema do `fixed`, porém, era o formato: `{campo: valor}` só sabia de folha **igual** e de colunas que fossem `Field` — e `transferencia_id` não é `Field` (é FK crua do `Entity`). Isso abriu o resto desta versão.
- **Sentinelas de valor em `defs.constants`.** `NULL`/`NOT_NULL` (↔ `is_null`) e `EMPTY`/`NOT_EMPTY` (↔ `is_empty`), singletons com `__repr__`, no mesmo espírito dos atalhos já existentes (`TODAY`). `NULL` é só o NULL do banco; `EMPTY` é `None`, branco ou coleção vazia — a distinção já existia em `core/utils` (`is_null`/`is_empty`) e agora tem forma declarativa. `EMPTY`/`NOT_EMPTY` compilam para `col IS NULL` e, em coluna textual, `OR trim(col) = ''` (espelha o `.strip()` de `is_empty`); em int/FK, só `IS NULL`. `NULL`/`NOT_NULL` são também aceitos em `visible` (idem `_eval_pos_when`).
- **`fixed` ganhou vocabulário de folha e agrupamento.** Folha: valor literal → `=`, sentinela `NULL`/`NOT_NULL`/`EMPTY`/`NOT_EMPTY`, tupla `('op', valor)` (`=`,`!=`,`>`,`>=`,`<`,`<=`,`like`,`ilike`,`in`,`not in`), lista → `IN`, `callable` chamado no compile, `None` **ignora** a folha. E `OR(*itens)`/`AND(*itens)` (fábricas de `_Grupo`, aninháveis) resolvem o que o dict não resolvia: `{'a': 1}` E `{'tipo': 'S' OU 'E'}`. Um dict é AND implícito; grupo é nó à parte (não se mistura folha com grupo no mesmo dict — erro de sintaxe). `OR()` vazio ou item que não é dict/grupo **quebra nomeando** (`ValueError`/`TypeError`).
- **`fixed` aceita coluna crua do model, não só `Field`.** O `resolve_filter_spec` continua validando `hidden`/`default`/`types` contra o **pool** (idioma dos slots) e só esconde as folhas de `fixed` que casam com um field; as demais (ex.: `transferencia_id`) são resolvidas por `compile_fixed` contra as **colunas do model**, que dá `ValueError` nomeando o que não existe. É o que permite filtrar por coluna que o form nunca edita.
- **A prop `filter` passou a ter um ponto único de leitura.** `core.filters.resolve_filter(spec, *, pool, fields=...)` faz spec → `ResolvedFilter{hidden, fixed, default, types, panel, initial, active}` (spec resolvida + `WHERE` compilado + painel + estado do request). `do_list_normal`/`do_list_master` consomem esse objeto (render, `WHERE`) e `core.do_list.list_fixed_conds` é o mesmo caminho sem `fields`, para a guarda do form. Antes a spec era resolvida em `do_list` e recompilada na guarda; agora os dois leem o mesmo `resolve_filter`.
- **A guarda de escopo do form virou membership por SQL.** `core.do_form` não reconstrói mais o `WHERE` nem reusa `_build_nav` como oráculo: checa `id ∈ SELECT id ... WHERE <conds>` (`db.session.query(model.id).filter(*conds)`) e, se não casa, 302. `_build_nav(model, current_id, conds=None)` passou a navegar a mesma lista de condições (`db.session.query`), então a navegação anterior/próxima respeita o escopo (não pula para um registro agora invisível).
- **`list_fixed_filters` → `list_fixed_conds`.** O nome acompanha o que devolve: condições SQLAlchemy compiladas (não mais a spec/filtros). `do_form`/`auto._form` passam a usar `fixed_conds`.
- **Migração no app.** `pagamentos`/`recebimentos` ganharam `'transferencia_id': NULL` no `filter.fixed`; os cinco `visible` que usavam `{'not_empty': True}` (`pedidos`, `compras`, `pagar`, `receber`, `orcamentos`) passaram à sentinela `NOT_EMPTY`.
- **Verificado.** `compile_fixed` (dict+`NULL`, `NOT_NULL`, `EMPTY`/`NOT_EMPTY` textual com `trim`, `OR`, `AND`+`OR`, tupla de op, `IN`, `None` ignora, nome inválido/`OR()` vazio/item inválido quebrando nomeando) e `_eval_pos_when` com as quatro sentinelas; as 19 listagens e os 15 forms do AlgoDoce em HTTP 200; e o comportamento fim-a-fim: movimentos `#4`/`#5` (transferência) fora de `pagamentos`/`recebimentos` **e** barrados por URL (`/pagamentos/4/editar`, `/recebimentos/5/editar` → 302), `#3` legítimo permanece.

### 1.26.10.08.0043
- **O painel de filtros virou prop da PÁGINA: `Page.props.list.filter`.** `Field.pos_filter` (`0` sem filtro, `1` texto, `2` select, `3` checklist, `9` fixo com `WHERE` do `default`) era o último inteiro mágico de posicionamento no `Field`, declarado no Entity/Schema e respondendo "por que esse campo não filtra agora?" longe da listagem. A pergunta é da lista, então a resposta mora nela, no mesmo desenho da §5.6 (§5.6.1). Quatro chaves independentes: `hidden` (fieldspec, tira do painel), `fixed` (`{campo: valor}`, vira `WHERE` e some do painel), `default` (**novo** — filtro inicial editável que volta ao limpar) e `types` (`{tipo: campo|lista}`, override do widget).
- **O tipo do filtro passa a ser inferido, não declarado.** `infer_filter_type` (por tipo de campo: `DK` e os editores `multi`/`image` não filtram; o resto lê o `filter_kind` do input, com fallback `options`→`select`) substitui o par `pos_filter: 1/2/3` + `FIELD_TYPES` — que agora só declara o `input`. `FILTER_TYPES` (`text/boolean/date/number/select/checklist`) é o vocabulário próprio da prop: `checklist` (multi-escolha) não existe como `filter_kind` de input.
- **`fixed` carrega o valor consigo.** Antes o `WHERE` saía do `field.default` via `fixed_filters(fields, model)`; agora sai do `{campo: valor}` da listagem — o valor e o filtro ficam no mesmo lugar e o `Field` não precisa mais ter `pos_filter` só para ser lido por outra tela. `resolve_filter_spec` valida a spec contra o **pool** (idioma dos slots, `slot_spec_items`/`_slot_match`): nome errado ou tipo desconhecido **quebra nomeando**.
- **O form mantém a guarda de escopo.** `core.do_form` recusava abrir (302) um registro fora do `pos_filter: 9` lendo o `default` do próprio `Field`; agora lê `list.filter.fixed` pela spec resolvida (`list_fixed_filters`) contra o modelo do form — abrir um `tipo` errado em `pagar`/`receber` continua sendo 302.
- **Migração no app (12 usos, 8 rotas).** `pos_filter: 3` → `filter.types.checklist` (`status` em `compras`/`pedidos`/`pagar`/`receber`/`transferencias`/`orcamentos`); `pos_filter: 0` → `filter.hidden` (`indice` em `operacoes`, `conta_id` em `transferencias`); `pos_filter: 9` → `filter.fixed` (`tipo` em `pagamentos`/`recebimentos`/`pagar`/`receber`). `pagamentos`/`recebimentos` ganharam `form.positions.hidden: ['tipo']`, que o `pos_filter: 9` escondia sozinho pela regra de campo de sistema — que deixou de citá-lo.
- **Mortos com a prop:** `Field.pos_filter`, a coerção em `Field.__post_init__`, as entradas `pos_filter` de `FIELD_TYPES` (`DK`/`MULT10`/`IMAGE`) e o ramo `pos_filter == 9` de "campo de sistema" em `core/resolve.apply_positions`. `core/old`-style ramos de `pos_filter == 0` em `field_to_column` foram junto.
- **Verificado no ambiente de dev.** `ast.parse` limpo; 19 listagens + 15 forms do AlgoDoce em HTTP 200 (test client); o painel não expõe mais `tipo` (fixo), `conta_id`/`indice` (hidden) e mantém o `status` como checklist; o `WHERE` fixo confere com o banco (`pagar` = 1 linha tipo `P`, `receber` = 6 tipo `R`); a guarda de escopo do form responde 302 no `tipo` errado e 200 no certo.

### 1.26.10.08.0042
- **`Button.position` vira um vocabulário definitivo de 8 nomes**, com o sentido atrelado ao alvo e não ao "contexto": `before`/`after` são **inline** (mesma linha dos fields, antes do 1º / depois do último), `before_up`/`after_down` são faixas em **linha própria** acima/abaixo dos fields, e `top_left`/`top_right`/`bottom_left`/`bottom_right` são o **título** (faixa acima) e a **ação** (faixa abaixo) da **tabela**. Renomeia o vocabulário antigo: `left`→`before`, `right`→`after`, `before`→`before_up`, `after`→`after_down` (§5.9).
- **`before*`/`after*` são SEMPRE relativos aos fields.** Por isso só valem onde há `fields`: em sessão só de `table`/`query` (e no item de tabela) são **erro** — não há bloco para encostar. `top_*`/`bottom_*` são relativos à **tabela**, com fallback para os fields quando a sessão não tem tabela. Na **sessão mista** (`fields` + `table`/`query`, ex.: `Financeiro`) os dois convivem: `before*`/`after*` nos fields, `top_*`/`bottom_*` na tabela. `POSITION_CONTEXT` passa a ser: `form` = 8, `fields` = 8, `table` = só `top_*`/`bottom_*`.
- **O form ganha os 8 nomes.** As faixas internas em volta do bloco de fields viram `before_up`/`after_down`, e o form passa a aceitar o inline `before`/`after` (renderizado no `head`/`tail` do `render_fields`, via `render_session_button` — sem `<form>` aninhado). `top_left`/`top_right`/`bottom_left`/`bottom_right` continuam sendo as **BARRAS** do form (fora do `<form>`), logo **não** são aliases das faixas.
- **Listagem ignora `position`** (como antes): o botão de listagem é só de cabeçalho.
- **Migração no app:** `right`→`after` em `pedidos` (gerar financeiro), `compras` (gerar financeiro) e `orcamentos` (aprovar); `after`→`after_down` em `transferencias` (lançar transferência, era a faixa abaixo dos fields). Os `top_*`/`bottom_*` existentes não mudam de nome. O harness e os 45 endpoints só diferem em linhas em branco no HTML.

### 1.26.10.08.0041
- **A posição de um campo no form saiu do `Field` e virou prop da PÁGINA: `bar`/`footer`/`body`/`hidden`, mais `visible`.** `Field.pos_form` (`0` oculto · `1` visível · `2` readonly sempre · `3` barra/tag · `5` rodapé, com a forma `dict{pos,when}`) era o mesmo inteiro mágico que o `pos_list` era na listagem — declarado em Entity e Schema ao mesmo tempo, e respondendo "por que esse campo não aparece?" só num arquivo 50 linhas acima do form. A pergunta é do form, então a resposta mora nele (`Page.props.form`, §5.5), no **mesmo desenho** da §5.6: `positions` posiciona, `normalize_fieldspec`/`field_spec_item` são os mesmos formatos, nome cru resolve e só a ambiguidade obriga a qualificar, e as props inline num slot são descartadas. Precedência total `hidden` > `bar` > `footer` > `body`; quem não é citado vai para o corpo.
- **A chave some por TIPO, não por nome — e o autor pode trazê-la de volta.** O form não edita a própria chave, então o campo de sistema vai para `hidden` **sem ninguém declarar**: `type` `ID` (a chave) ou `DK` (a chave derivada que o motor gerencia), e qualquer `pos_filter: 9` (filtro fixo). É a tradução fiel do que o catálogo `FIELD_TYPES` declarava como `pos_form: 0`. Ser por **tipo** é o que preserva a tabela de ligação: em `ProdutoInsumo` as duas colunas são FKs e o motor tem que mostrá-las — uma regra "é a pk?" comeria as colunas dela (a chave lá é composta por FKs). Quem precisa do contrário **cita** o campo em `body` (`'Previsões': {'positions': {'body': ['id']}}`): existir vence a regra, e é exatamente o que a `Previsao.id` fazia com `pos_form: 1`.
- **`visible` é prop separada, não slot.** A condição (`not_empty`, `empty`, `{field,op,value}`, `callable`) é uma resposta sobre o **dado**, não sobre a posição: o mesmo `not_empty` que a `pos_form` `dict` carregava agora vive em `positions['visible']`/`Page.props.form.visible`, e um campo na barra ou no corpo pode tê-la. `POS_0_NOT_EMPTY` (o atalho `{'pos':0,'when':{'not_empty':True}}`) deixou de ter uso e foi removido — a leitura virou `'hidden': ['x'], 'visible': {'x': {'not_empty': True}}`.
- **Sessões têm os seus slots, numa superfície mais estreita.** Cada sessão aceita `positions`/`visible` próprios, com só `body` e `hidden` (não há barra nem rodapé numa tabela de linhas). O alvo depende do tipo: em `table`/`query` as `positions` posicionam as **colunas** (o filho) e os `fields` da sessão — que vêm do Schema do mestre — **herdam** a posição do mestre, recortada pelo que a sessão exibe (o `hidden` do mestre cita campos fora do recorte, e citá-los ali seria erro); em `fields` sem `table`/`query` a sessão é o pool inteiro (campos do pai, se o primeiro item for um campo dele; do filho, se nomear uma Entity).
- **O slot é o predicado de escrita; `_pos_managed` saiu.** No save gravam `body` e `footer`; `hidden` e `bar` não — mandar o que veio do POST gravaria `NULL` onde o campo é derivado (um toggle carimba pela rota própria, um campo oculto é do motor). O guard antigo (`if f._pos_managed and f.pos_form not in (1,5)`) consultava `_pos_managed`, que só existia porque uma lista explícita de `fields` desligava o filtro de `pos_form`; com o slot como predicado o guard deixou de consultá-la; a flag segue existindo só na **resolução** de `fields` — `memory` fora da expansão e a lista explícita como autoritativa. **Efeito visível e aceito:** um campo do pai que uma sessão `query`/`table` carregava como *explicitamente não-gerido* (`saved: True`) deixa de ser regravado a partir do hidden — é o mesmo dado da instância, então não muda tela nem valor. O `readonly` **não** entra nesse predicado: renderiza rótulo + `<input type=hidden>` que ainda submete, então um campo `readonly` no corpo é reenviado e gravado; quem barra o save inteiro é o `Form.readonly` (callable sobre a instância), que pula tudo exceto o `footer`.
- **Um ajuste de comportamento, declarado.** `pos_form: 2` ("readonly que não salvava") foi removido: tinha **um** uso, em `orcamentos`/`Orcamento.validade_data`, e era redundante com `readonly: True` (que é o que a tela quer — o valor é reenviado igual). A troca está no harness como a única divergência de forma esperada.
- **Mortos com a prop:** `Field.pos_form`, `POS_0_NOT_EMPTY` (`defs/constants.py`), o par "input de barra ⇒ `pos_form: 3`" que o `Field.__post_init__` validava (virou a checagem de slot em `apply_positions`), e a prop interna `_pos_form_when` (substituída por `_visible_when`, posta por `resolve_visible`).
- **Equivalência provada por harness.** Snapshot semântico (slot + saved + bar + readonly + memory + visible) dos **309** campos dos 15 forms do AlgoDoce contra o `HEAD` (`pos_form` normalizado para o vocabulário novo): **0 divergências reais** (as de `transferencias` são drift alheio — o modelo lá ainda era pré-migração). Os 45 endpoints (15 listagens + 30 forms) respondem 200, `ast.parse`/`jinja.parse`/`node --check` limpos, e a regra de tipo foi confirmada preservando a tabela de ligação `ProdutoInsumo`.

### 1.26.10.08.0040
- **A posição de um campo na listagem saiu do `Field` e virou prop da PÁGINA: `line`/`card`/`hidden`.** `Field.pos_list` (`0` oculto · `1` coluna · `2` card) era um inteiro mágico declarado em três lugares ao mesmo tempo — Entity, Schema e rota — e responder "por que essa coluna não aparece?" significaba caçar o `pos_list` num Schema que estava 50 linhas acima da lista. A pergunta é da listagem, então a resposta mora nela (`Page.props.list`, §5.6). **Nome cru resolve**: único na entidade de `columns` → único no pool (de onde vier) → na ambiguidade quem desempata é `columns`, por ser o assunto da lista; sem entidade em `columns`, ambiguidade é erro e o autor qualifica. Só `Entidade.campo` é ambíguo de propósito. Precedência total `hidden` > `line` > `card`; o que não é citado vai para a linha.
- **O que estava quebrado e saiu junto.** (1) `pos_list: 3` era **documentado** (README e `defs/tags.py`) e **sem consumidor nenhum** — o campo passava o filtro `!= 0`, não era `1` nem `2`, e sumia em silêncio; pior, `Field.pos_list` não validava valor nenhum (`validate_field_config` só checa chave), então `'2'` ou `7` caíam no mesmo buraco. Hoje a validação é **fail-fast nomeando** (slot, campo inexistente, nome ambíguo sem desempate). (2) O filtro de `pos_list` só valia com `columns` como nome de entidade, por um gate `any(f._pos_managed)` — **um** campo expandido no meio desligava o filtro dos outros, em silêncio. `_pos_managed` saiu do caminho da listagem. (3) A lógica estava em **4 cópias** (`do_list.py:65/329/572`, uma delas sem o split de card, então `list_max_width` podia divergir da grade real); virou `core/resolve.resolve_slots`, uma fonte só. (4) A precedência na camada `query` era assimétrica — a entrada do `select` forçava `pos_list: 0` mas era **ignorada** em `1`/`2` se o campo já existisse — e a entrada deixou de posicionar: quem posiciona é a página.
- **`line` é prop nova de verdade, com metade no cliente.** O `linha` antigo era um split de **servidor** entre `<td>` e o overflow, e o ajuste por largura (`fitListColumns`, que já existia e já media) ficava atrás de `not has_card`. Agora o servidor renderiza **todas** as colunas da grade, e quem some é o cliente (`col-hide`), com a cópia `of-dyn` na linha expansória garantindo que nada se perca. Isso mata um bug latente: com `linha` declarado, o `<thead>` emitia `<th>` para todas as `cols` e o `<td>` só para as pinadas — a tabela desalinhava. `line` vira `data-pinned` no `<th>` e semeia o `keepIdx` antes do preenchimento por largura; é **atributo** e não nome porque com `master` a mesma tabela tem dois `data-field="id"` (a `Transferencia.id` e a `Movimento.id` — o marcador por nome pinava as duas).
- **`pos_filter: 9` parou de esconder coluna sozinho** (mantém o `pos_form: 0`, que é dele). O efeito colateral existia porque a posição era do `Field`; agora quem tira um campo da grade é `hidden`, e as 4 rotas com filtro fixo (`pagar`/`receber`/`pagamentos`/`recebimentos`, o `tipo`) ganharam a linha explícita. **Esta é a única linha que, esquecida, muda a tela** — o `tipo` viraria coluna.
- **`_list_pool` passou a ser o construtor único do pool**, incluindo a inversão `master` — antes `list_max_width` (que o `do_form` chama para a largura do container) montava só o pool do pai e quebrava com qualquer `hidden` que citasse a entidade do filho. `do_list_normal` e `do_list_master` passaram a reusá-lo, e as 4 cópias de merge cairam para uma. O truque do `fields_all` pré-filtro (que existia só porque `pos_filter: 9` jogava o campo fora do pool) foi junto: os filtros fixos leem o `pool`.
- **Mortos com a prop:** `SelectEntry.pos_list` (`defs/qspec.py`), os 2 hints de listagem dentro da fonte `QPLANO` compartilhada com o report (que nunca os leu), a prop `card` da `List` (virou slot), a prop `linha` e `List.card_fields` (canal morto no template), `_card_layer` (reimplementação restrita de 3 dos formatos que os slots agora aceitam), e 4 `pos_list` que já eram **no-op** (`Previsao.id`, `Movimento.historico`, `Operacao.indice`, `Transferencia.historico` — redundantes com o default ou com a camada `card`).
- **Equivalência provada por harness.** Snapshot da **resolução** (colunas com label/width/align/input/stored, ordem do `fields_all`, card-only, detalhe, filtros, `max_width`, endpoint de edição) das 15 listagens do AlgoDoce contra o `HEAD`: **0 divergências** — as 3 invertidas (`pagar`/`receber`/`transferencias`) saem id a id. Snapshot do **HTML** renderizado: 12 das 15 saem **byte a byte** idênticas; as 3 com `line` diferem só pelo `data-pinned` (1 coluna) e pela cópia `of-dyn` da coluna pinada a menos. Mais 12 forms e 15 listagens pelo test client (HTTP 200, `<thead>` conferido). O único desvio real que apareceu no caminho foi o `pos_filter: 9` acima, pego justamente porque a verificação foi feita.

### 1.26.10.08.0039
- **Bloco `MEMORY` no Schema: chave em MAIÚSCULAS = campos que existem só na
  tela.** O `memory` (renderiza/editável, não persiste) só aparecia citado campo a
  campo, com `memory: True` repetido. `grupos_memoria` (`defs/data.py`) lê a chave
  em MAIÚSCULAS cujo valor é dict de configs e carimba `memory: True` em cada
  campo do grupo — o nome da chave é livre, é só namespace. Ver 5.5.3.
- **`fields` lista/dict no `Form` voltou a resolver a config dos campos.** O form
  entregava o schema plano ao `normalize_fieldspec`, que o espera indexado por
  entidade: a lista e o dict (formas documentadas) resolviam campo sem config —
  a `data` virava input de texto e o histórico perdia o textarea. Nenhuma rota do
  AlgoDoce usava a forma lista/dict, então o conserto não muda nada existente.
- **`pos_form` passou a mandar no save mesmo em lista explícita.** O guard do
  loop do mestre era `if f._pos_managed and f.pos_form != 1 and f.pos_form != 5`:
  com lista explícita (`_pos_managed=False`) ele não segurava, e um campo
  derivado com `pos_form: 3` (que o form desenha como tag, sem input) virava
  NULL no banco. Lista explícita assume a ordem, não a regra de gravável.
- **O save do mestre pula campo `memory`.** O das sessões já pulava
  (`_save_session_masters`); sem o do mestre, um bloco no cabeçalho passaria por
  `setattr` num atributo inexistente no model.
- **`_entidade_principal` ignora chave em MAIÚSCULAS.** A entidade principal do
  módulo era `next(iter(Schema))`, que num bloco de memória devolveria um nome
  sem model e quebraria o `_get_model` da rota inteira.
- **`addChildRow` devolve a chave da linha nova** (`n-N`): o app precisa dela para
  escrever nos inputs daquela linha pelo nome, sem raspar o DOM.

### 1.26.10.08.0038
- **Campo `readonly` na linha de sessão agora tem texto, e o `on_new` o escreve.**
  A célula readonly na linha nova é `<span data-readonly-for data-readonly-mask>`
  com `[data-readonly-text]` + o `<input type="hidden">` **dentro** do span (antes
  o hidden era irmão do texto, e a célula renderizava dois elementos). O `on_new`
  escreve o texto pelo `itReadonlyText`: data ISO vira `dd/mm/aaaa` — montada em
  **horário local**, porque `new Date('2026-07-13')` é UTC e o `fmtMask` lê os
  getters locais (daria 12/07 num fuso negativo) — e os demais campos saem como
  vieram, já que o que o `numToInputFor` escreveu no input é a convenção de exibição.
- **`addChildRow` não descarta mais o que sobra do template mobile.** No mobile o
  ColumnTemplate é um `<div>` fora de `<table>`: o parser descarta os `<th>`/`<td>` e
  o `addChildRow` casa os elementos do template com as linhas da tabela **por
  posição** — uma célula com dois elementos (readonly) deslocava todas as
  seguintes, e os hidden que não têm linha correspondente (o `tipo` da sessão, e
  qualquer campo `pos_form: 0`) sumiam junto com o `box` removido, sem ir no POST
  (e no celular a cópia desktop está `disabled`, ou seja, também não vai).
- **`defaults` é identidade de sessão, não "campo a zerar"** — o filtro de
  `_session_matches` compara todas as chaves, então uma chave cujo valor gravado
  difere do default esconde a linha do render e do save. Documentado em 5.5.2.

### 1.26.10.08.0037
- **Duas sessões `table` agora podem mirar o mesmo relationship.** A Transferência
  do AlgoDoce tem "Entradas" e "Saídas" que são as duas `Movimento` com `tipo`
  diferente — e o relationship é um só: `_resolve_parent_link` acha o
  pai→filho pelo mapper, então as duas sessões caíam no mesmo `attr` (`movtos`),
  no mesmo prefixo de POST (`child_movtos_`) e nas **mesmas linhas**. Pior, a
  exclusão é "linha do banco ausente no POST": cada sessão apagaria a da outra.
  As duas props novas resolvem sem HTML nem JS:
  - **`defaults`** (`dict`) — os campos que a sessão **possui**. O render mostra
    só as linhas que batem (`_session_rows` preenche `session['_rows']`, e
    `item_table.html` usa essa lista quando existe). No save, a linha postada
    cujo filho não casa é de outra sessão e é ignorada — nem salva, nem exclui —
    e a lista de `existing` da exclusão é filtrada pelo mesmo `defaults`.
    O valor também é **carimbado** na linha nova antes do check de `required`,
    que é o que faltava: campo oculto não vem no POST, então a linha nascia com
    `tipo` nulo e batia no `NOT NULL`.
  - **`on_new`** (`{replaces: {alvo: fonte}}`) — o que a linha **nova** herda,
    no mesmo formato do `on_set`. O mapa vira `data-new-replaces` no wrap da
    tabela e o `itOnNewRow` o aplica no `addChildRow` — a origem é procurada no
    **mestre** primeiro (o inverso quebraria todo `alvo:fonte` de nomes iguais,
    como `data:data`) e depois na **própria linha nova**; escreve com a disciplina
    do `on_set` (`numToInputFor` → `fmtFieldInput` → `input`/`change`) em
    **todos** os alvos, desktop e mobile, porque o `itmApplyPage` só pagina e não
    sincroniza valor entre as duas cópias. Client-side, como o `on_set`: sem JS a
    linha nasce vazia. Ver 5.5.2.
  - **O hidden do `defaults` saiu de dentro do `<tr>`.** Ele é o que leva o
    `tipo` da linha no POST, e `<input>` solto entre `<td>` é HTML inválido — o
    parser do navegador pode tirá-lo da tabela (e sem ele a linha nova seria
    criada duas vezes, uma em cada sessão). Agora vai dentro de um `<td>`; no
    mobile, direto do `<div>` do `ColumnTemplate`, que já aceita flow content.
- **Os `<template>` da linha nova passaram a ser por sessão** (`data-tpl` no
  `tbody`, lido pelo `addChildRow`): duas tabelas do mesmo relationship saíam
  com `movtosRowTemplate` duplicado no DOM. O prefixo do POST continua sendo o
  `attr` — é ele que amarra o input ao filho.
- **O card do `master` calcula com o PAI, e não com a linha.** `_value_cell`
  (`list.html`) resolvia o valor por `card_path` (`trf.total`) em todos os ramos
  — exceto o do `calc`, que recebia a linha (o filho): um `calc` de property no
  pai estourava com `AttributeError` e o de agregação voltava vazio, sem erro
  nenhum. Agora o `calc` é avaliado no dono do campo. Foi o que apareceu ao
  colocar a `Diferença` (soma dos lançamentos) no card da Transferência.
- **O `defaults` viaja em TODA linha, não só na nova.** Com o hidden só no
  template `__IDX__`, o POST não trazia o `tipo` das linhas já gravadas: um
  `pre_save` do app não conseguia somar com sinal e nenhum cliente sabia o sinal
  da linha salva. Agora sai também no loop das linhas (com o valor do item), o
  carimbo do save ficou **incondicional** — a sessão é dona do campo, então o que
  veio no POST não passa por cima — e a renderização do hidden é a mesma nos dois
  lugares (`_postados`, calculado uma vez no macro).
- **Não-regressão:** sessão sem `defaults` não ganha `_rows` (segue lendo
  `instance|deep_attr(attr)`) e o `data-tpl` só muda o id, não o `data-rel` que
  monta o prefixo.

### 1.26.10.08.0036
- **O rodapé é a ÚLTIMA LINHA da página, e o motor conta as linhas em vez de
  adivinhar.** O rodapé vivia em `FOOTER_Y = -15`, que no fpdf2 2.8.7 é
  `h - 15` — **dentro da margem inferior**, fora da grade, 15mm do papel, onde
  a maioria das impressoras não garante nada. Agora o motor conta
  `int((h - t_margin - b_margin) // (25,4/lpi))` e reserva a última dessas
  linhas: no A4 retrato a 6 LPI são 63 linhas, o rodapé entra na 63 e o
  conteúdo usa 62. O gatilho de quebra **passa a ser essa linha** — e os dois
  atributos que o fpdf2 e o motor leem (`page_break_trigger` e `b_margin`)
  recebem o mesmo número, porque `_check_page_break` lê um e `multi_cell` lê o
  outro: divergindo, o texto quebraria de página num ponto e a tabela noutro.
  Medido em report de 4 páginas cheias: y máximo do corpo **267,176mm** contra a
  linha do rodapé em **272,467mm**, ou seja, nenhum texto do corpo na linha nem
  abaixo. Report **sem** rodapé não paga a linha — `_recalc_break_trigger`
  sai antes de tocar em qualquer atributo.
- **`'footer': True` é o atalho das três flags** (`show_user`, `show_datetime`,
  `show_page_number`; `show_company` fica fora, e hoje ele não escreve nada).
  `True`, `False`, ausente e `{}` são os quatro jeitos de perguntar "o rodapé
  existe?" — `{}` continua sendo declaração vazia. Valor fora de `bool`/`dict`
  levanta `TypeError` **no build**, e não um `AttributeError: 'bool' object has
  no attribute 'get'` no meio da renderização.
- **O rodapé é `CPI(12,'C')`, itálico, à direita** — e `cpi`/`style`/`align`
  são overrides do dev. Antes era CPI 10 (o do fluxo), itálico fixo e centro,
  sem como mudar nada disso; o header, no mesmo arquivo, já tinha `style`
  configurável. O default é a **menor letra que a grade permite**: Elite
  condensado, CPI efetivo **20** (1,2700mm por caractere), o menor que a
  matriz alcança — o Micron (15) recusa condensar e volta ao base. Com
  `lpi: 8` a altura cai para 7,5pt e fecha o par mais fechado do motor. A
  prop `cpi` do dev é um **base**, então declarar sempre *abre* a letra.
  `cpi` fora de base levanta o erro do próprio normalizador (`13` → *"não é um
  base; use um de [10, 12, 15]"*). **Família e corpo não são props**: vêm de
  `Report.font` e `Report.lpi`, porque o rodapé é parte do mesmo documento — é
  o estilo que o distingue, não a letra.
- **`LPI()` saiu como comando; `Report.lpi` entrou como prop.** A grade vertical
  é uma só para o documento, igual à orientação, e por isso parou de ser
  diretiva de fluxo — que podia mudar no meio da renderização e fazia a linha
  do rodapé (que conta linhas) sair do lugar. `lpi` é normalizado e validado na
  **construção** do PDF, então `lpi: 7` morre antes de qualquer página sair.
  `_reset_fluxo` deixou de mexer no campo (ele continuava restaurando 6 a cada
  seção, o que anulava o `LPI(8)` do body na hora do rodapé). `CPI()` continua
  diretiva: o eixo horizontal é por item mesmo.
- **`FONT` saiu do código morto.** O caso que apontava o substituto (`use
  CPI()/LPI()`) estava **depois** do gate `if k not in ITEM_KINDS`, então nunca
  disparava — quem declarava `FONT` recebia *"elemento 'FONT' desconhecido"*.
  Removidos (`FONT` e `LPI`) agora são checados **antes** do gate, numa tabela
  `_REMOVED_ITEMS`, e o erro diz para onde foi.
- **Não-regressão:** report sem rodapé sai **byte a byte igual** ao de antes da
  mudança (`f98f4e8acc0be343c98a`), e `footer: True` produz content stream
  idêntico ao do dict completo. 155 arquivos, 141 imports, 74 respostas de rota
  (GET e POST) iguais ao HEAD e a matriz do `lf` 4/4 em 1,00.

### 1.26.10.08.0035
- **O `lf` do `table` passou a ser da TABELA, uma vez antes e uma depois.**
  A leitura da prop estava certa (`_lf_de` já separava `n`, `-n` e `[a, b]`); o
  que estava errado era **onde ela era aplicada**. O "antes" vivia pendurado no
  `if body.items:` — sem `items` a tabela não respirava em cima — e o "depois"
  caía **entre os grupos**, com o `_walk_field_groups` aplicando um `lf` por
  tipo. Uma tabela agrupada com 2 tipos e `lf: [0, 1]` rendia 0 antes e **3**
  depois (2 grupos + 1), e a simples rendia 0 antes, 1 depois e 1 antes se
  tivesse `items`. Mesma declaração, três distâncias. Agora `_build_table`
  resolve o par uma vez em `lf_before_table`/`lf_after_table` e o
  `gerar_pdf_relatorio` aplica `_space_before`/`_space_after` em volta de
  `_render_table` — os dois lados passam pelo mesmo `_space_*` que o `lf` de
  item usa, então o incremento vertical tem um só dono. Medido com 13 operações
  reais, as quatro combinações (simples/agrupada × com/sem `items`) devolvem
  1,00 linha antes e 1,00 depois.
- **Ausente na tabela é `[1, 1]`; ausente no item continua ausência.** O
  padrão do `table` é o **respiro do bloco**: a grade é densa e nasce colada no
  texto que a precede e no que a segue, e é o `lf` que abre e fecha esse espaço.
  No item o `lf` é enfeite de quem escreve, e o padrão segue sendo nada. Por
  isso ausente numa tabela rende +2 linhas frente a `[0, 0]`, e o `PLANO` do
  app — que declara `lf: [0, 1]` — fica com 0 antes e 1 depois.
- **Identificadores com nome em português foram para inglês.** Só o código:
  funções (`render_pagina`→`render_page`, `montar_blueprint`→`build_blueprint`,
  `_linha_cheia`→`_line_is_full`, `_desce_se_cheia`→`_descend_if_full`,
  `_lf_de`→`_lf_one_side`, `fecha_tabela`→`close_table`, `nova_pagina`→
  `new_page`, …) e variáveis/locais (`_titulos`, `n_linhas`, `colunas`,
  `valores`, `grupo`, …). **Não** são identificador: chave de `jsonify`/
  `render_template` (`pagina=`, `titulo=`, `tem_usuario=` — contrato com o
  template e o JS), coluna de ORM (`cliente_nome`, `valor`), chave de i18n e
  chave de dicionário de dados — esses ficaram. A renomeação foi feita por AST,
  não por replace de texto, justamente para não tocar string: `valor` é nome de
  coluna em `produtos`, e um replace cego quebraria o SQL. Os 4 reports do app
  saem com o **conteúdo desenhado idêntico** (hash do content stream
  descomprimido, com o timestamp de minuto do rodapé normalizado).

### 1.26.10.08.0034
- **`total` e `valor` desformatavam no navegador — o `.0033` trocou a linha.**
  O servidor renderizava `value="1.365,00"` e o JS sobrescrevia com `'1365'`: em
  `itSessionTotals`, o destino de `data-total-target` era escrito com
  `numDecimals(el)`, um **leitor** que recusa elemento `disabled` (`formats.js:384`),
  e todo destino é um campo `readonly`/`calc`, que o `render_field` sempre
  renderiza `disabled`. Sobrava o `String(num)`, e o `fmtFieldInput` logo abaixo
  não reparava pelo mesmo motivo. `formCalcRefresh` tinha o erro irmão, pelo
  outro lado: escrevia `inp.value` com `itFmtByAttrs`, que é o formatador de
  **exibição** — num campo `percent` isso meteria `'12,5%'` dentro do input,
  duplicando o `%` do span ao lado. Os dois foram para `numToInputFor`, que é o
  que o §5.14 manda para `inp.value` (`dec` = `data-num-decimals`).
- **A peça que faltava: input numérico `disabled` não declarava sua convenção.**
  `numToInputFor` lê `dec` de `data-num-decimals`, e `render_field` só emitia o
  atributo no ramo **editável** — nunca em `calc` (`total`), `readonly`
  (`total` do orçamento) nem `_ro_msg`, e nem no da barra
  (`render_footer_field`). Sem ele não havia o que ler, então nem a chamada
  correta resolvia. Os quatro ramos agora emitem
  `data-num-decimals="{{ field.num_decimals }}"`, e o editável trocou
  `decimals` por `num_decimals` para o atributo significar a mesma coisa em todo
  lugar. As guardas de `disabled`/`readOnly` em `numDecimals` e `calcIsCalc`
  (`pages/sys.html`) já existiam esperando isso — eram código morto. A
  calculadora não se prende ao campo desabilitado porque `calcIsCalc` já o
  recusava; `focusout` não dispara em input desabilitado; `itZeroOrEmpty`/
  `itEnabledEval` leem `el.value` e não olham o atributo.
- **`numToInput` passou a espelhar `fmt_num`** (`static/js/formats.js`), que o
  §5.14 já afirmava ser verdade e não era: com `dec = 0` ele agrupava
  (`numToInput(1000, 0)` → `'1.000'`, contra `'1000'` do `fmt_num`) **e**
  arredondava (`numToInput(1234.5, 0)` → `'1235'`, contra `'1234,5'`).
  `'1.000'` volta como `1` — pelo `parseNumText` e pelo `_coerce` no POST, ou
  seja, `1000` gravava `1`. Sem casas agora não agrupa nem arredonda, como o
  `fmt_num`, e o round-trip fecha nos dois lados.
- **Um terceiro ponto de escrita tinha o mesmo defeito:** `searchApplyReplaces`
  (`pages/sys.html`) escrevia `String(Math.round(v * 100) / 100)` — `'1234.5'`
  cru — e contava com o `fmtFieldInput` seguinte para normalizar, que não
  repara em alvo desabilitado. Agora usa `numToInputFor`, mas **só quando o
  alvo declara `data-num-decimals`**: texto e código (`tel`, `cpf`, `cep`) ficam
  em `String(v)`, porque passar por `Number` comeria o zero à esquerda de
  `'01310100'`.
- **Verificado como par nos dois espaços:** 80 casos de `render_value` ↔
  `itFmtByAttrs` (`textContent`, 0 divergências reais) e 32 de `fmt_num` ↔
  `numToInputFor` (`inp.value`, 0 divergências, com round-trip contra o valor
  nas casas declaradas). E uma simulação do cliente sobre o **HTML real** dos
  forms de COMPRA/PEDIDO/ORÇAMENTO, rodando o `formCalcRefresh` e o
  `itSessionTotals` extraídos do `sys.html` contra os inputs que o servidor
  emitiu: `total` fica `29,00`/`480,00`/`1.365,00`, `valor` fica `29,70`/`480,00`,
  e o `<tfoot>` sai `3,00`·`29,70`, `133`·`480,00`, `300`·`1.365,00` — o `INT`
  sem agrupar, como manda a regra. Não há DOM headless aqui: o harness monta um
  stub mínimo (`getAttribute`/`querySelector*`/`closest`/`value`/`textContent`)
  a partir das tags do HTML.

### 1.26.10.08.0033
- **O cliente é o segundo renderizador, e ele não recebia a máscara.** O `.0032`
  arrumou o servidor (`render_value`), mas `calc`, coluna calculada e total são
  redesenhados no navegador — e antes disso só viajavam `data-calc-currency`,
  emitido **quando a máscara tem `@M`**. Como `MVALOR` é `'999,999.99'` (sem
  `@M`, de propósito: `653a166` pôs a moeda no rótulo da coluna do relatório),
  `f.currency` era `None` e os quatro pontos caíam em `String(v)`: o input de
  `total` abria `29` e perdia os centavos (`29.70 - 0.70` → `'29'`), a coluna
  `valor` dos itens saía `12.5`, e o total do `<tfoot>` saía por
  `Number(result).toFixed(dec)` — **`1234.50`, com ponto**. Era o `653a166` que
  tinha deixado os quatro sem fallback.
- **O contrato com o cliente passou a ser a máscara, não a moeda.**
  `components/form_macros.html:fmt_attrs(f)` emite `data-fmt-mask` /
  `data-fmt-decimals` / `data-fmt-currency` / `data-fmt-percent` do `Field`, e
  entra no input `calc` do form, nas 4 células `it-calc` (item_table) e no
  `<td class="it-calc-total">`. `pages/sys.html:itFmtByAttrs(el, v, dec)` decide
  no cliente na **mesma ordem** de `render_value`. `data-calc-currency` e
  `data-total-currency`/`data-total-decimals` saíram: dois atributos dizendo a
  mesma coisa é como a divergência entrou. As casas do cliente saem por
  `_fmtDec` e não por `fmtNumBR`, que escreve o input e sem casas não agrupa de
  propósito. Passar pela máscara também mata o artefato de float, porque
  `_renderNumMask`/`_fmtDec` usam `toFixed`.
- **`Field.num_decimals`** (`defs/data.py`) — a prop de exibição das casas: o
  `decimals` declarado, ou **0** para input numérico sem casas. É o caso de
  `ID`/`DK`, que `FIELD_TYPES` define como `input: 'number'` sem `decimals` e sem
  máscara, então não recebem `num_mask`. Sem a regra, `mask_cmd` recebia `None`
  e caía no default de 2 casas — foi o que fez a coluna `#` virar `6,00` quando
  o `.0032` roteou número por `mask_cmd`. `render_value` perdeu o desvio do
  `fmtid` (que alinhava em 7 colunas com NBSP: numa coluna já alinhada à direita
  pelo CSS o padding vira espaço à esquerda, e era ele que punha o separador
  dentro das casas — `'1.234..50'`). `core/list.py:field_to_column` passou a
  emitir `num_decimals` no lugar de `decimals`.
- **`_total_decimals` saiu** (`defs/form.py`): preferia a **escala da coluna no
  banco** quando a Entity não declarava `decimals`, o que discordava da própria
  linha — `compra_itens.qtd` é `NUMERIC(12,3)` com `type: 'NUM'` (2 casas na
  linha) e o total saía com 3, por cima do `toFixed` com ponto. O total usa
  agora `num_decimals`, que é o mesmo número que a linha exibe. E
  `'currency': bool(getattr(f, 'currency', None))` virou o id, como o ramo
  vizinho já fazia: com `@M(USD)` num total de entrada em string, emitia
  `data-total-currency="True"` e o JS resolvia para `BRL`.
- **`itTotalsRefresh` perdeu o `|| 'brl'`** (`pages/sys.html`): um motor genérico
  não pode inventar moeda num campo que não pediu nenhuma. O caminho é código
  morto — `_session_totals` é sempre `{}` (`do_form.py:608`), então
  `data-total-expr` nunca sai — e foi deixado no lugar por decisão, mas agora
  degrada para o número cru em vez de `R$`.
- **Verificado como par, que é o que faltava:** 80 casos do mesmo `Field` com o
  mesmo valor por `render_value` (Python) e `itFmtByAttrs` (JS, com stub de
  `getAttribute` — a função só lê atributo, então não precisa de DOM) — 0
  divergências reais. As 4 do arredondamento de meio exato (`12.5` em 0 casas:
  `%.0f` do Python arredonda para par, `toFixed(0)` do JS para cima) são
  **pré-existentes** — o par `fmt_num`/`fmtNumBR` já discordava — e o harness as
  classifica à parte em vez de escondê-las. Além disso: diff dos `data-*` no
  form real de COMPRA/PEDIDO/ORÇAMENTO (todo `calc`/coluna/total com
  `data-fmt-mask`), diff das 6 cadeias de exibição do `.0032` (0 mudança), diff
  das listagens contra o Postgres (só a coluna `#` perdendo o padding), `env.parse`
  nos 24 templates, `ast.parse` nos 155 `.py`, import dos 50 módulos e
  `node --check` nos 8 blocos de `sys.html`.

### 1.26.10.08.0032
- **O valor gravado não era formatado em três superfícies ao mesmo tempo — a
  cadeia de exibição nunca roteava o número pela máscara dele.** `NUM` com
  `mask: MVALOR` saía `1.234..50` no campo `readonly`/`calc` do form e em toda
  célula do `item_table`, e `1234.50` cru na listagem e na `query`. Duas causas:
  `render_label` mandava todo campo de `input: 'number'` para `fmt_id`, que
  agrupava a **string** inteira e punha o separador dentro das casas decimais
  (`'1.234..50'`) e dentro do texto (`'João da Silva'` → `'J.oão.\xa0da.\xa0Si.lva'`,
  `True` → `'T.rue'`); e o ramo do valor gravado da listagem — as cinco cópias
  do encadeamento em `pages/list.html` — só testava `datemask`/`strftime`/`@R` e
  caía em `{{ _raw }}`. O `.0005` havia ligado `|format` só no ramo `calc`.
- **`render_value(val, f)` é agora o passo único de exibição** (em
  `components/form_macros.html`), para `Field` e para a coluna da listagem:
  `none`/vazio → `percent` → data → `input == 'number'` (`mask_cmd`, que
  resolve a canônica, o `@M`, o `@B` e o `@X`) → `mask` (`format`) → cru.
  `render_label` virou uma chamada; `pages/list.html` colapsou as cinco cópias
  em `_value_cell(item, col, img_h, img_js)`, e `_det_cell` (que
  `item_table_display` invoca com 3 args) virou um wrapper. O `col.tag` ficou
  no `<td>` de propósito: ele desenha uma pílula com a largura da coluna, o que
  não faz sentido no card. Divergências que a unificação resolveu: `_det_cell`
  não tinha os ramos `currency`/`percent`/`boolean` que os outros quatro tinham.
- **`fmt_id` parou de agrupar a string inteira** (`core/formats.py`): inteiro
  como antes (`'  1.234'`, NBSP), fração em 2 casas no `DECIMAL` do app e sem o
  alinhamento do id, não numérico como `str`. O filtro `fmtid` continua
  registrado e é o `converter.html` que o usa — id inteiro, inalterado.
- **`format` só trata número como número quando a máscara manda.** Corpo vazio
  com transform de texto (`@U`/`@L`/`@C`/`@T`) é instrução de texto: `@T` com
  `1234.50` devolve `'1234.50'`, não `'1.234,50'`. Espelhado em
  `static/js/formats.js` — os 15 casos de paridade Python↔JS conferem.
- **`core/search.py:_fmt_cell`** usa `format` no ramo numérico com máscara
  (ganha `@M`, `@B`, `@X`) e **não** no de texto/data, cujo caminho é
  posicionamento de dígitos e devolveria vazio ou lixo. `render_agg_total`
  (`item_table.html`) recebe o `Field` do agregado e sai por `render_value` —
  soma/média sem `currency` paravam em `1234.50` cru.
- **Precedência deliberada:** `percent` e `strftime` vêm antes de `currency` e
  de `@B`/`@X`. Uma data num campo com `@M` saía `R$ 2026-03-07` e sai
  `07/03/2026`; `@T`/`@U` passaram a valer na exibição (o valor já vem
  gravado transformado por `apply_field_transforms`, e os três são idempotentes).
  Equivalência: 1129 linhas de harness nas 6 cadeias (`render_label`,
  `_det_cell`/`_value_cell`, `render_agg_total`, `_fmt_cell`, `fmt_id`) × 21
  campos × 22 valores, com `git archive HEAD` numa árvore paralela como
  baseline; `env.parse` nos 5 templates tocados, `ast.parse` e import nos .py.

### 1.26.10.08.0031
- **A `width` do field ficou só na COLUNA.** O `.0029` anexou a `width` ao
  `_resolve_map`, que é a rotina **partilhada** entre `body.table.columns` e os
  itens de layout (`header.fields`, `items`, `before`, `after`, `table.after`).
  Na tabela é a medida certa; no fluxo, `width` é prop do **item** — a medida do
  bloco no `MEMO`, a largura fixa no `FIELD`/`TEXT` — e só o autor a declara. O
  `MEMO` do preâmbulo do COMPRA saiu com **12** em vez de **84** (12 colunas =
  30,5mm) e a frase saiu palavra a palavra. Agora `_resolve_map` recebe
  `colunas=True`, e só `table.columns` o passa. O `MEMO` ainda era o pior caso
  porque `_resolve_fields` tira a `width` **antes** de chamar o `_resolve_map`
  ("`width` fica de fora porque é do bloco, não do campo") e funde o resultado
  de volta com `update` — a do field voltava por baixo. **O mesmo vazamento
  atingia todo `FIELD`/`FIELDS`** do fluxo, que passava a medir-se pela largura
  do field em vez de encher a zona.
- **No app, `LARGURA` do COMPRA foi de 84 para 70.** Com o body no CPI 10, 84
  colunas são 213,4mm numa página de 190mm úteis (o máximo é 74). Os quatro
  préâmbulos saem inteiros, em 1 a 3 linhas, sem escrever fora do bloco — e o
  `J` do `MEMO` estica 0,09mm porque as linhas preenchem o bloco quase exacto
  (sobra de 0,5mm por linha).
- **Os cabeçalhos dos três relatórios passaram a declarar a densidade depois do
  título** (`LF(1)` e daí `CPI`/`TABS`), em vez de a declarar antes: com o reset
  de secção a HEADER continua a ter a sua, e escrevê-la uma vez, logo depois do
  `TITLES`, deixa claro que o corpo é que volta ao CPI 10. O `COMPRA` e o
  `PEDIDO` passaram a usar `CPI(10,'C')` — a grade continua a ser a do base
  (25,4/10 = 2,5400mm) e é o **glifo** que condensa; `TABS(1, 25)` mede-se
  nessa grade, não na do condensado.
- **Uma coluna FK com `width` declarado** (`'insumo_id': {'width': 35}` no
  COMPRA) exercita a precedência nova pela parte difícil: a coluna resolve a FK
  pelo lookup para `insumo.nome`, e o **`width` declarado vence** o do field
  (que seria 19, o preset `TEXT`). Sem declarado sairia 19 — que é o certo para
  o `list`, e curto demais para um nome de insumo numa compra impressa.

### 1.26.10.08.0030
- **Header, body e footer entram com o fluxo limpo.** As três secções já
  limpavam o estado em pontos diferentes, e nenhum deles era o de entrada: o
  header só limpava quando desenhava (o `header()` volta cedo quando não há
  `on_each_page`, e a 2ª página nascia com as paradas da 1ª), o footer nunca, e
  o `body.before` entra por `_render_table_lines`, que preserva o estado entre
  itens da **própria** secção — de propósito, para vários itens seguirem em
  linha. O resultado era o `IND` do header empurrar o `body.before`: medido,
  `IND([20,70])` no header botava um `TEXT` do body em x=61,80mm em vez de
  11,00mm.
- **`_reset_fluxo` reune o que header e `_render_items` já faziam** e passa a
  ser chamado na entrada das três secções: `TABS`, `IND`, a **zona do logo** e
  a grade, esta ao **CPI 10**. Um helper só, para header, body e footer não
  divergirem no que esquecem de limpar. A zona do logo entra porque um `IND` do
  body que intersectasse com a faixa do `LOGO` do header sairia mais estreito
  do que pediu; a grade volta ao default porque quem quiser outra densidade no
  body a declara nele, e a conta passa a ser do body em vez de uma herança
  implícita do cabeçalho.
- **O app não se moveu:** nenhum dos três headers declara `IND`, e `TABS` só
  ancora itens `TABS` (não a zona), então os três relatórios saíram com a
  geometria idêntica antes e depois — conferido texto a texto no PDF.
- **Uma afirmação minha que este número corrige:** eu escrevi que o reset não
  mudava o app. Isso sevia para a geometria dos *textos*, e continuava a
  valer; mas o `MEMO` do `before` herdava o `CPI(12)` do header e passou a
  desenhar a CPI 10. Para este relatório o texto sai igual (medido: `x=27,26`
  nos dois), mas um `MEMO` com texto mais justo sentiria a diferença.

### 1.26.10.08.0029
- **A coluna da tabela segue o field, e a soma é centralizada.** Era o
  contrário: `_resolve_map` montava `label`/`format`/`function` e **nunca a
  `width`**, então a coluna chegava sem ela ao `_calc_col_widths` e recebia o
  `leftover` da página — a tabela se espalhava de margem a margem. Agora a
  largura sai do field pela **mesma conta da listagem**
  (`core.list.field_width_ch`, extraída de `field_to_column` para as duas
  usarem uma só), com a **máscara como mínimo**: o PDF escreve a célula numa
  linha só, então uma coluna mais estreita que `999.999.999,99` veria o valor
  derrubar na coluna vizinha em vez de quebrar. Precedência:
  `width` do report > field > rótulo. Chave pontada (`insumo.nome`) mede o
  campo exibido; coluna sem field mede o rótulo (ou o template, com 8 chars por
  `{campo}`). O **fluxo não se move**: `width` em cols e `recuo` seguem na
  grade do report.
- **O CPI da escada passou a valer para o glifo, não só para a régua.** A
  escada escolhe um CPI e media as células nele, mas `_render_table` jogava o
  valor fora (`_cpi`) e só guardava em `pdf._table_cpi`, que ninguém lia: a
  fonte continuava no CPI do report, mais larga que a célula, e **uma coluna
  escrevia por cima da vizinha**. Agora a tabela estica a fonte para o CPI
  escolhido enquanto desenha (`_face_tabela`) e restaura ao final, porque o
  `Tz` do fpdf2 é pegajoso. Numa tabela larga a escada escolhe 17,1 e o PDF
  passa a gravar `Tz 70,18%`.
- **A escada media um valor que ela própria recusava.** `TABLE_LADDER` é
  `(10, 12, 15, 17,1, 20)` e os dois últimos são **derivados** (`{10: 17,1,
  12: 20}`), mas `col_mm` era `cpi()` por dentro, que só aceita base: na 4ª
  etapa da escada o `_fit_table` estourava `ValueError` no lugar do recado de
  "não cabe no papel". `cpi_geom` separa as duas contas — **declarar** segue
  fechado para derivados (`CPI(20)` recusa e sugere `CPI(12,'C')`), **medir**
  aceita.
- **Nenhuma coluna escreve sobre a outra.** Rede final no `_render_data_row` e
  no cabeçalho: o texto é cortado na grade (`_pad_cols`) pelo que cabe na
  célula. A largura vem do field, mas o dado é do app — e dado maior que a
  coluna não passa reto.
- **No app, os três relatórios pararam de declarar `width`.** As somas caíram
  de 112/106 ch para **52/68/52 ch**, o que cabe no **CPI 10** do report: a
  escada deixa de ser acionada e a tabela sai centralizada no meio da página
  (132,1 / 172,7 / 119,4mm de 190mm úteis) em vez de esticar para a folha
  inteira. A coluna de dinheiro que estava com `width: 26` passa a ter as 11 ch
  que a máscara `999,999.99` pede. *(Cifras medidas quando esta versão foi
  escrita; o `PEDIDO` foi a 68 ch/172,7mm depois, com um `width: 40` declarado
  na primeira coluna.)*

### 1.26.10.08.0028
- **Uma linha nova de `TABS` desce sozinha.** A pergunta é *"o cursor já
  passou da 1ª parada?"* — se passou, a linha nova começaria em cima do que a
  anterior escreveu, e desce; se não passou, fica. A **1ª linha do header** não
  desce, a **2ª** desce sozinha. É o `lf: -1` automático, e é o `lf` que o
  `.0026` trouxe deixa de ser necessário para separar as fileiras de um grid.
- **O `TABS` não é mais dono da descida de linha, e sim da COLUNA.** Antes
  `.0027` dizia que ele "nunca desce sozinho" e jogava a responsabilidade no
  autor; a posição na grade já sabe a resposta, e perguntar era mais honesto do
  que exigir declaração.
- **Os demais elementos da MESMA linha não descem** — eles andam pela largura,
  e descer é decisão da LINHA, não do item. Só o primeiro elemento (`_tab == 1`)
  decide, e os outros mantêm a descida DON'T-LOSE do `.0022`.
- **A string nua é a forma normal, e sempre foi.** `TABS('{cliente_nome}',
  '{data_pedido}')` produz byte a byte o mesmo que `TABS(('{cliente_nome}', {}),
  ('{data_pedido}', {}))` — a tupla vazia nunca teve função, e escrevê-la só
  confundia. A tupla aparece quando há **props**: `('{d}', {'lf': 1})`.
- **`lf: -1` não soma com a automática**, e é o certo: ele *é* a descida, então
  a automática age só quando não houve nenhuma.
- Migração dos 3 reports: as 10 entradas `('{campo}', {})` viraram
  `'{campo}'` e os `lf: 1` do grid 2×2 saíram (a automática cobre). Geometria
  dos headers conferida coordenada a coordenada — **inalterada**.
- 12 verificações: a 1ª linha não desce e a 2ª/3ª descem, `lf: 2` somando com a
  automática, `lf: -1` não somando, o grid de string nua com rótulo e máscara
  nas duas fileiras, e os 6 cenários dos 3 reports.

### 1.26.10.08.0027
- **`TABS` passou a fazer dois trabalhos, distinguidos pelo tipo do 1º
  argumento.** `TABS(1, 30)` (números ou cursor±N) **define as paradas**, como
  antes; `TABS('a', '', 'b')` (texto) **imprime um elemento por parada**, na
  gramática do `TEXTS`. Misturar os dois é erro — dois comandos com o mesmo nome
  e a mesma aridade, e decidir pelo primeiro seria adivinhação.
- **A prop `tab` saiu.** Escrever à mão dá erro nomeando a prop e apontando
  `TABS`. Por baixo continua existindo, como a chave interna `_tab`, que o
  motor injeta: ancorar o X na parada não cambió.
- **`'{campo}'` como token puro é rota FIELD**, e isso é o que preserva o rótulo
  em **negrito**, a máscara e o catálogo `options`. `'Cliente: {campo}'` **não**
  é token puro e sai como texto, com o rótulo no mesmo peso do valor — a
  escolha fica com quem escreve. Não existe mais `{'field': …}` nem
  `{'text': …}` como elemento de tabulação: o campo é `{campo}` dentro da
  string, como em todo template.
- **`''` é a parada que não existe nesta linha**: não imprime, e o elemento
  anterior **não é cortado**. Um `''` no FIM é redundante (elemento sem
  sucessor já significa "sem corte"), então ninguém escreve.
- **`TABS` nunca desce de linha sozinho** — imprime na linha corrente. Quem
  desce é o `lf` ou o `LF(n)`, e o grid 2×2 dos reports põe o `lf` no primeiro
  elemento da primeira linha.
- **O teto passou a ser contado em COLUNAS, não em milímetros.** O elemento `i`
  leva no máximo `paradas[i+1] - paradas[i] - 1`. Medido com `TABS(1, 30)`:
  **28 caracteres nos três CPIs** — 10, 12 e 15. O corte em mm desconta o
  `c_margin` de 2mm, e 2mm é fração maior de uma célula de 1,69mm, o que tirava
  um caractere no CPI 15. Contando células não há fração: ou cabe, ou não cabe.
  `GAP_TAB` e o `_limite_x` foram embora — a folga não é mais uma constante
  somada no motor, é a contagem das paradas.
- **`{campo}` passou a levar a máscara do campo**, pelo caminho do FIELD e pela
  precedência que já existia (`explícita > catálogo do input > decimals`).
  Antes `{data_pedido}` imprimia o `repr` cru do Python (`2026-10-09
  14:37:52`); agora `09/10/2026 14:37` — em todo template, não só no TABS.
  O `render` ganhou um `masks` e o `spec` do template continua vencendo.
- **O `FIELD` de token puro sai como `FIELDS` de uma entrada**, não como
  `{'field': …}` cru: o caminho pontilhado (`'{Conta.telefone}'`) é resolvido no
  ramo de `FIELDS` de `_expand_fields_list`, pelo mesmo caminho que o
  `FIELDS(...)` de sempre usa. E a expansão do `TABS` roda **antes** dessa e da
  resolução — depois, o campo chegaria sem rótulo e sem máscara.
- Bug de escopo: `_val` recebia `spec=''` (o `_sub` passa `m.group(2) or ''`) e
  o teste de "não há spec" era `is None`. A máscara nunca entrava.
- Migração dos 3 reports: 10 usos de `tab` viraram `TABS('{campo}', …)`, e o
  `rows_after` do grid 2×2 (já `lf: 1`) virou um `TABS` por fileira. A
  geometria dos headers não mudou — conferido coordenada a coordenada.
- 28 verificações: as duas formas do `TABS`, os quatro tipos de elemento, o teto
  em colunas nos três CPIs, o `lf` separando fileiras, as 4 recusas (mistura,
  `tab` à mão, mais elementos que paradas, paradas coladas), a precedência da
  máscara, o `lf` do `.0026`, a cascata do `.0022`, a matriz do `.0020`, as
  datas do `.0024` e os 6 cenários dos 3 reports.

### 1.26.10.08.0026
- **`rows_before`/`rows_after` viraram `lf`, um número só com sinal.**
  `'lf': 2` são 2 linhas **depois**, `'lf': -2` são 2 **antes**. Um par de props
  virou uma, e o nome deixou de sugerir contagem de "linhas de formulário" —
  que o `rows` do `<textarea>` fazia e que o README já precisei avisar que era
  outra coisa. `0` (ou ausente) é ausência, como `rows_after: 0` era.
- **`'lf': [antes, depois]` cobre os dois de uma vez.** Existe porque
  `table: {'rows_before': 1, 'rows_after': 2}` é uma declaração legítima — uma
  tabela pode respirar antes e depois — e isso não cabe num número com sinal.
  Vale para a chave do `table` e para a do `body.table` dos reports agrupados
  (o OPERACOES usa a segunda).
- **O sinal é o que faz a prop valer.** O lado "depois" mexe **só no Y**,
  preservando o estacionamento do `.0022`: um `ln` devolveria o X à margem e a
  descida automática do próximo item cairia na mesma linha do `lf: 0`. O lado
  "antes" consome a descida pendente **antes** de aplicar o `N` e volta o X
  para a 1ª coluna — sem isso o `MEMO(..., {'lf': -1})` perderia a linha
  automática e o `-1` viraria o total.
- **`_respiro` e `_respiro_depois` viraram uma função só**, com o lado pedido em
  vez de dois nomes, e `LF(n)` continua sendo o **item** de avanço: `LF(1,
  {'when': …})` ocupa um lugar da lista e precisa do `when` repetido, enquanto
  `MEMO(..., {'lf': -1, 'when': …})` respira junto com o bloco e some com ele.
- **Bug de escopo, e era um erro de leitura de sinal.** `_lf_de` devolvia o
  número com o sinal em vez do módulo, e o `lf: -1` **subia** uma linha em vez
  de descer — `pdf.ln(-1 * linha)`. E a forma `[antes, depois]` caía no mesmo
  teste de sinal, que é do escalar: `[3, 0]` não respirava nada. Os dois agora
  saem de uma leitura só, com o sinal decidindo o lado.
- **Shadowing:** a variável local que recebia o `rows_before` da tabela se
  chamava `_lf_antes`, exatamente o nome da função nova — uma mina no meio de
  `gerar_pdf_relatorio`, que tem quase 200 linhas.
- `_ReportTable` deixou de carregar `rows_before`/`rows_after` e carrega `lf`.
  O leitor `_lf_de` aceita dict (item, `table`) ou o dataclass, para não haver
  duas regras para o mesmo eixo.
- Migração: 3 `rows_*` viraram `lf` no app (o `rows_after` do grid 2×2 do
  PEDIDO e do ORCAMENTO, o `rows_before` do `MEMO` da COMPRA e o
  `rows_after` da tabela do OPERACOES). 16 verificações: as 8 combinações de
  `lf` como prop, as 5 como chave de `table`, as 2 recusas e os 6 cenários dos
  3 reports.

### 1.26.10.08.0025
- **A tabulação passou a ter TETO: o texto de um item não entra na próxima
  parada.** Com `TABS(1, 30)` e um item em `tab:1`, o corte é 1 col antes da tab
  2 (`GAP_TAB = 1`, ao lado do `GAP_LABEL`). Sem tabulação seguinte — a última
  parada, ou um `TABS(5)` sozinho — o teto é a margem direita da zona, e essa
  parte vale para qualquer app, **mesmo sem `TABS`**.
- **O corte recebia `right - _x0`, a largura da ZONA INTEIRA**, e só parecia
  certo porque item sem âncora sempre quebra de volta para `x0` antes de medir.
  Com `tab` o X já está no meio da linha e a conta ignorava: medido, `TABS(1,
  30)` deixava o texto da tab 1 chegar a **168,48mm** com a tab 2 em 86,20mm, e
  o da **última** tab a **242,14mm** — 42mm **além da margem**. Agora o teto é
  `_limite_x(...)`, medido a partir de onde o item começa.
- **O respiro é 1 coluna inteira mais os 1mm de célula.** Os 1mm são o
  `c_margin` do fpdf2, os mesmos que a célula da tabela deixa, e `_cut_to_fit`
  já os desconta — o `+2` dele são as duas margens. Medido: tab 2 em 86,20mm,
  teto em 83,66mm, texto parando em 82,66mm.
- **`width` declara o ancho, o teto é o teto.** `{'tab': 1, 'width': 40}`
  media 101,6mm de caixa e atravessava a tab 2 mesmo assim.
- **Só o valor do `FIELD` é cortado**, nunca o `Nome: ` — é a chave que o leitor
  procura, e cortar o rótulo deixaria a linha sem identificação. Se o rótulo
  sozinho cruzar o teto, o valor sai vazio.
- **`wrap: True` não muda** (quebra em `width` ou na margem), e `location`/`pos`
  ganham o teto da margem — hoje um item ancorado que sai da zona estoura a
  folha.
- **`TITLE` passou a IGNORAR `tab`, em silêncio, no header e no corpo.** Nem
  título nem `MEMO` são blocos ancorados. Ancorar a caixa do título na parada
  não o levava para a parada: só encurtava a caixa para `right - tab_x` e
  deslocava o centro — medido, **91,03mm com `tab:1` contra 89,76mm sem**, e
  ainda cruzando a próxima parada. O `MEMO` já ignorava (80,60mm com e sem),
  por recentralizar na zona. A recusa que o corpo fazia ("TITLE no corpo não
  aceita 'tab'") saiu junto: header que ignora calado e corpo que explode é
  incoerente.
- 16 verificações: o teto em 6 arranjos de `TABS`/`tab` (última parada, tab no
  meio de três, `TABS` sozinho, `width`+`tab`), o FIELD com rótulo intacto,
  o `TITLE` com e sem `tab` dando o mesmo x, nada passando da margem, e as
  regressões de `.0022` (estacionar), `.0023` (zona do logo), `.0020` (matriz)
  e `.0024` (datas).

### 1.26.10.08.0024
- **O `DATA_HORA` saiu sem máscara default, e caía no `repr` cru do Python.**
  `date` tinha `dd/mm/yyyy` e `time` tinha máscara, mas `datetime-local` ficou de
  fora do catálogo — e um campo sem `mask` não tem para onde cair: um
  `DATA_HORA` sem `mask` explícita saía **`2026-10-09 14:37:52`**, `repr` do
  `datetime`, com os segundos e o separador ISO. Passa a ser
  **`09/10/2026 14:37`**.
- **Nenhum dos três defaults mostra segundos.** `date` → `dd/mm/yyyy`, `time` →
  `hh:ii`, `datetime-local` → `dd/mm/yyyy hh:ii`. O token `ss` continua
  existindo na gramática — quem quiser o segundo declara a `mask` do campo — mas
  não entra em nenhum default, porque em data de negócio ele só polui a coluna.
- **Bug de token: o default do `time` era `hh:mm`, e `mm` é o MÊS.** Um horário
  de outubro às 14:37 saía **`14:10`** — a hora certa com o mês no lugar do
  minuto. Agora é `hh:ii`. Afeta `evento.hora` e o `hora` do form de orçamento.
- No form nada muda: o coercion de data/hora é **fallback** — tenta
  `datetime.fromisoformat` primeiro e só usa a máscara quando o ISO não bate
  (`core/form.py:158`), então a máscara nova só acrescenta um caminho de parse
  em vez de tirar um.

### 1.26.10.08.0023
- **Bug: a zona do logo encolhia para dentro da imagem quando o `CPI` mudava
  depois do `LOGO`.** A borda da figura era guardada em **colunas**, calculadas
  com o CPI do momento em que a imagem foi desenhada, e a zona — que é em cols
  — a remultiplicava pelo CPI **vigente**. Com CPI menor a conta dava menos
  milímetros, e a zona passava a começar *dentro* do logo: medido com a imagem
  terminando em 52,33mm, `CPI(12)` punha o `FIELD` de tab 1 em **45,28mm** e
  `CPI(15)` em **38,22mm**. Com logo à direita era pior (−24,61mm e −49,22mm),
  porque a zona é a borda **esquerda** e encolher a levava para dentro da
  figura por dentro.
- **A borda do logo passou a ser guardada em mm**, que é a medida em que a
  imagem foi desenhada, e a conversão para cols acontece em `_zone_cols`, na
  hora de usar, com o CPI vigente. Medido depois: desvio **0,00mm** para
  `LOGO('L')` e `LOGO('R')` com CPI 10, 12 e 15. É o que o `CPI(12)` logo
  abaixo de `LOGO('L', 4)` do ORCAMENTO sempre esteve pedindo.
- Vale notar o que **não** mudou: `TABS` continua em cols (é declarado em
  cols, e é o autor que conta), e a caixa da imagem continua sendo resolvida no
  momento do desenho. O que estava em cols por acidente era a borda dela.

### 1.26.10.08.0022
- **Nenhum item decide sozinho se avança linha. Todo item ESTACIONA na borda do
  que desenhou, e o próximo desce porque não cabe mais nada.** A pergunta ficou
  sendo uma — *"a linha ainda tem lugar?"* — e a resposta sai do próprio X, sem
  contador e sem estado. O `TITLE` centralizado vai no fim da **linha** (a
  caixa é a zona toda), o alinhado à esquerda vai no fim do **texto**, e o
  `LINE` vai no fim da **régua**: `LINE()` tem a largura da zona e fecha a
  linha; `LINE(30)` deixa 30 cols à direita e o próximo continua nelas.
- **O `TITLE` deixou de ocupar duas linhas.** Ele somava a própria célula com
  `rows_after: 1` no padrão, e a cascata do `TITLES` punha uma linha em branco
  entre cada par de títulos. Medido antes → depois, a 6 LPI: COMPRA com 1
  título vai de 3 para **2** linhas de header, com 2 títulos de 5 para **3**.
- **O padrão de `rows_after` foi de 1 para 0**, e a prop virou o que o nome
  sempre disse: **linhas em branco depois**. A linha seguinte já vem de graça,
  porque o item estacionou; `rows_after: N` são N a mais. `rows_before: N`
  continua sendo N antes, e as duas são a única forma de pedir respiro.
- **`align` deixou de ser cosmético no `TITLE`.** `align:'L'` deixa o próximo
  item **na mesma linha** — é o `width` declarado que diz "isto é um pedaço da
  linha", não o alinhamento.
- **Bug de escopo: `set_y` do fpdf2 devolve o X para a margem, igual ao `ln`.**
  O `set_y` parece só mexer na ordenada, e foi a escolha óbvia para "descer sem
  tocar no estacionamento" — mas ele apaga o estacionamento, e `rows_after: 1`
  e `rows_after: 0` davam a mesma linha. Agora é `set_xy` com o X que já
  estava (`_y_desce`).
- **A descida mora dentro do `TITLE`, não só em `_place_item`.** No header o
  `TITLE` é chamado direto — a cascata do `TITLES` não passa pelo renderizador
  de itens —, então sem a descida no próprio `_draw_titulo` o 2º título saía na
  linha do 1º. E ela tem que vir **antes** de posicionar e antes de medir: o
  `set_x` logo abaixo devolve o cursor ao início da zona, e a largura do título
  é `right - get_x()` — com a linha cheia ela daria 0, e `cell(0, …)` no fpdf2
  é "até a margem", que centralizaria o título no espaço inteiro e o faria
  atravessar o logo.
- **`tab` ficou de fora do estacionamento, e o grid 2×2 do ORCAMENTO/PEDIDO
  continua igual.** `tab` é posição absoluta: o autor já manage a linha. O item
  `tab` ainda **descobre** a linha cheia e desce (senão os fields caem na linha
  do título), mas não estaciona. `pos`/`location` não descem: o `set_xy` joga
  fora, e perto do rodapé ainda quebraria a página à toa.
- **`MEMO` com `rows_before: 1` continua com 1 linha** — o `_respiro` consome a
  descida pendente antes de aplicar o `N`, senão o `set_x` dele apagava o
  "estacionado" do item anterior e o `N` virava o total.
- **O fechamento no fim de cada lista de itens.** O corpo nasce no Y que o
  header deixou (`add_page` não restaura o Y), então um título estacionado
  como último item fazia a tabela nascer em cima dele.
- O header em dict legado saiu junto: tinha o mesmo avanço duplo cravado
  (`self.ln(_row_unit(self))  # título sempre deixa a PRÓXIMA linha`) e o
  `GAP_TITLE_SIDE` virou um deslocamento só de Y.
- Verificação: 22 medições de linha (cascata de 1/2/3 títulos, os três `align`,
  `rows_after` 0/1/2, `when` falso no meio, `LINE()` × `LINE(30)`, título
  estacionado seguido de item, `CR`, `LF`, título + `LF`), a matriz de CPI
  intacta e os 3 reports do app comparados coordenada a coordenada antes e
  depois — a única diferença é uma linha a menos por título.

### 1.26.10.08.0021
- **O `TITLE` passou a gritar: `mask='@U'` por padrão.** A caixa alta é o que
  separa o cabeçalho do corpo agora que o **corpo** deixou de fazer esse
  trabalho: no `.0020` o `TITLE` ficou com o mesmo corpo do texto e só se
  distinguia pelo CPI expandido, e "Orçamento nº 7" e "STATUS: DEVOLVIDO" saíam
  do mesmo jeito que uma linha de texto.
- **A prop `mask` do `TITLE` vence o padrão.** `mask: ''` devolve o texto como
  está, `'@L'` vai para minúscula, `'@C'` para capitalizado — sem precisar
  desligar a máscara inteira, que é o que `mask: ''` faz.
- **A máscara entra DEPOIS do template e das substituições.** Aplicar antes
  faria o `@U` agir sobre o `{campo}` cru em vez do rótulo que ele virou, e o
  título sairia gritando o nome do campo em vez do valor (medido: `'Documento
  nº {id}'` → `'DOCUMENTO Nº 7'`, e não `'DOCUMENTO Nº {ID}'`).
- **Só os comandos de texto contam, nunca a parte numérica da máscara.** A
  alternativa era passar o texto por `format()`, e `format('Orçamento nº 7',
  '999,999.99')` devolve `'7'` — a máscara numérica consome os dígitos do
  título e deixa só o que sobrou. Aplicando só `@U`/`@L`/`@C`/`@T`, a parte
  numérica é ignorada de propósito: `@U 999,999.99` ainda só grita, e
  `@M(BRL) 999,999.99` num título não o destrói.
- Os três reports do app passaram a sair com o título em caixa alta sem
  tocar em uma linha: `ORÇAMENTO #7`, `PEDIDO Nº 7`, `COMPRA #7`,
  `STATUS: DEVOLVIDO`.

### 1.26.10.08.0020
- **A matriz de impressora virou a grade: três números e duas letras.** O `CPI` passou a aceitar **só os modos base** — 10 Pica, 12 Elite, 15 Micron — e o resto virou modificador na prop `flags` (`'E'` expandido, `'C'` condensado), escrito `CPI(12, 'EC')`. Antes eram oito valores com nome próprio, e cinco deles (5 · 6 · 7,5 · 17,1 · 20) eram consequência, não escolha: o autor decorria cinco números para ter três densidades.
- **A matriz inteira sai de três regras, não de uma tabela de oito.** `expanded = base/2` (exato nos três: 5 · 6 · 7,5), `condensado = CPI_CONDENSED[base]` (só 10 e 12 têm), `condensado+expandido = condensado/2`. O que sobrou de tabela foi uma linha.
- **Onde a impressora recusa, o motor fica no base.** `CPI(15, 'C')` devolve 15: é a célula que a matriz marca "Não aceita". Comportamento pedido, e **não** é o mesmo que calar um caso que a matriz aceita — `CPI(15, 'E')` continua dando 7,5.
- **`'N'` é o "sem modificador" explícito e por isso não combina com `E`/`C`.** `'NE'` seria pedir normal e expandido ao mesmo tempo; deixar passar seria uma letra ignorada em silêncio. A ordem também não importa: `'EC'` e `'CE'` são o mesmo pedido e normalizam para a mesma string.
- **O erro de base virou instrutivo, porque todo valor derivado continua alcançável.** `CPI(5)` → *"5 não é um base; use um de [10, 12, 15] (use CPI(10, 'E'))"*. Um número que a matriz produz tem sempre um caminho; `CPI(13)` — que a matriz não produz — é o único que não recebe sugestão.
- **O `TITLE` deixou de ter número de CPI.** A cascata é `flags: 'E'` no 1º, e ela acompanha o base vigente: medido 2,00× o corpo em 10→5, 12→6 e 15→7,5. Antes era `5 if first else 10`, com o 5 cravado — trocar o padrão do report deixaria o título mais estreito que o corpo sem ninguém ver.
- **A escada de auto-fit da tabela ficou completa** (`10, 12, 15, 17,1, 20`), e é motor-interna: a densidade da tabela já era escolha do motor, então nenhum número novo aparece para o autor. **O efeito no app é visível**: as tabelas passam a escolher 15 em vez de 17 — COMPRA e PEDIDO de 167,3mm para **189,7mm** e ORÇAMENTO de 158,4mm para **179,5mm**, com a coluna de dinheiro abrindo de 38,8mm para 44mm. O **fluxo não se move**: o padrão é 10, que é a mesma coluna de 2,5400mm em produção, então `TABS`, `width` em cols e `recuo` ficam idênticos.
- **`flags` entrou como prop, e `cpi` saiu do `TITLE`.** A cascata escolhe a largura do título por `flags`, então declarar `cpi` lá é recusado nomeando a prop — as duasfalariam pelo mesmo eixo e a última a ser lida venceria sem aviso.
- **Bug de escopo:** `stretch_pct` normalizava o CPI com `cpi()`, que passou a esperar um **base** — mas o que chega ali já é o **final**. Reprovar os valores derivados (5 · 7,5 · 20) era justamente o que a matriz existe para alcançar, e o sintoma era `CPI: 5 não é um base` no primeiro render. A assinatura ficou `(advance, body, valor_final)` e a docstring avisa.
- Verificação: as 12 combinações de base×flags com o `Tz` medido no PDF (e o caso de 100% sem `Tz`, que é o default do PDF e não um buraco), o título em 2,00× o corpo nos três bases, a matriz (inclusive `12+'EC' == 10`, dois caminhos e um destino), 7 recusas e as 5 fontes com geometria idêntica (título expandido em x=79,60 nas cinco).

### 1.26.10.08.0019
- **A grade virou CPI × LPI, em polegada, e o glifo passa a PREENCHER a coluna.** `col = 25,4/CPI`, `linha = 25,4/LPI`, `corpo = 60/LPI` e `alongamento = 7200/(avanço × corpo × CPI)` — quatro fórmulas, uma conta. O `CPI` deixa de ser a largura *nominal* da coluna e vira a largura **de verdade** do caractere, porque o fpdf2 tem `set_stretching` (o operador `Tz`) e o `get_string_width` já conta o alongamento. Consequência que vale mais que a conta: **trocar a fonte não move nada** — as cinco renderizam o mesmo report com o mesmo `x` no mesmo lugar, e só muda a letra (medido: título expandido centrado em x=79,60 nas cinco).
- **O CPI e o LPI são o valor real, não um índice, e `cpp` virou `cpi`.** `CPI(5)` é cinco caracteres por polegada e não "o quinto degrau"; a indireção do índice só servia para mapear `0→10, 1→12, 2→17, 3→20` e podia divergir da conta. A escada ficou `{5, 10, 17, 20}` = expanded/normal/semi-condensed/condensed, com letra (`E`/`N`/`S`/`C`) **e** número aceitos, padrão 10. O `S` é *semi-condensed* porque é o termo real de tipografia — `I` seria *italic*, que é do outro eixo.
- **A coluna de fluxo tinha duas contas, e a que valia dependia de haver diretiva.** Sem `FONT`, era `get_string_width('0')` = 1,7653mm; com, `25,4/cpp` = 2,54mm. Agora é `25,4/CPI` nos dois casos, e o `get_string_width` some do cálculo da grade — ele media o glifo cru, que é justamente o que a grade corrige.
- **`font_size` saiu, e com ele os corpos `FONT_*`.** O corpo é derivado do LPI: 6 LPI → 10pt, 8 LPI → 7,5pt. Declarar um corpo solto quebraria a relação, porque o limite é a **tinta ≤ 1,2em** — que decorre de `60/LPI` contra `25,4/LPI`, e é o que garante que qualquer fonte escolhida caiba na linha mais apertada. O `TITLE` deixou de ocupar `size * 0.6` (quase duas linhas) e passou a ocupar **1 linha** como todo mundo; o que o separa do resto não é mais o corpo, é o **CPI expandido**.
- **`font_style` virou `style`, e ganhou o `U`.** São as 8 combinações que o fpdf2 sabe desenhar. O `U` estava **prometido na docstring e recusado no código** desde sempre — e a validação vivia em três lugares: `TITLE` e a tabela validavam, `FIELD`/`TEXT` não, então um estilo inválido escapava e explodia dentro do fpdf2 com mensagem de outra biblioteca. Agora é uma função só, `_validate_style`.
- **A fonte virou lista fixa no motor, com os arquivos dentro do framework** (`defs/fonts/`, com a licença de cada uma ao lado, como a OFL exige). Cinco: `courier` (núcleo do PDF, sem arquivo, padrão), `jetbrains`, `hack`, `plex` e `space`. Só entra fonte **monoespaçada** — é o que garante "1 coluna = 1 caractere"; proporcional passaria a exigir a largura do glifo mais largo no lugar do avanço, que é outra conta. `FONT(nome)` e as camadas `app.extends.fonts` saíram: sem família trocável no meio do fluxo, o catálogo não tem o que layerar.
- **A tinta é medida do DESENHO dos glifos, não do `OS/2` — e isso mudou um veredito.** O `OS/2` da JetBrains Mono diz 1,32em, acima do limite de 1,2, e teria reprovado a fonte; o desenho de verdade para em 0,957em e cabe com folga. `OS/2` é métrica tipográfica, folgada para caber acento e outra escrita. A pior parte é que o erro seria silencioso e plausível: a fonte simplesmente não entraria no catálogo.
- **O `Tz` é pegadioso, e o reset de página não segura.** O fpdf2 só emite `Tz` na **mudança** e o repete no primeiro texto de cada página; `_beginpage` escreve 100 num estado que é substituído em seguida. Medido: um desenho que não reestica herda o do desenho anterior **e o erro atravessa a quebra de página**. Por isso `_apply_face` é o ponto único — família, estilo, corpo e alongamento juntos, e **antes de medir**, porque `get_string_width` conta o alongamento e medir antes de esticar daria a largura do glifo cru. Verificado página a página: a 2ª reemite `240` e `120` corretamente.
- **Bugs achados no caminho, todos de escopo:** `_row_unit(pdf)` entrou em seis linhas de métodos onde o objeto é `self` (o header e o rodapé quebravam com `NameError`); `_font_info` validava a fonte **default** em vez da do report, então `'font': 'arial'` passava sem reclamar; `parse_report_item` mandava `None` para o normalizador e `CPI()`/`LPI()` nu — o "restaura" — levantava; e o check de idempotência do `add_font` usava tupla onde o fpdf2 indexa por `nome + style`, disparando `UserWarning` a cada desenho.
- **O aviso `TTFA NOT subset` do fontTools sumiu.** Ele descarta uma tabela de metadado do FontLab que o Hack traz e gritava 4 linhas por PDF sobre algo que o autor do report não pediu. Os arquivos ficaram intactos — mexer em fonte versionada é problema de manutenção e de nome reservado — e quem cala é o `output()` do `DocPDFReport`, só naquele logger e só durante a geração. Detalhe do mute: o logger nasce em `NOTSET` e herda do pai, então o guarda `if level > WARNING` era falso justamente no caso comum.

### 1.26.10.08.0018
- **O `LOGO` passou a ENCOLHER A ZONA, e a zona deixou de ser um detalhe do `IND`.** Antes o logo era só uma figura: o texto ao lado era posicionado na mão, `TABS(PCOL+5, PCOL+40)` mais `POS(PCOL, 0)`, e um número de coluna que só funcionava porque ninguém media a distância entre a margem e a imagem. `LOGO('L')` agora recua a borda esquerda da zona para a borda **direita** da figura (e `R` a direita para a esquerda; `C` não recua), e tudo que se posiciona pela zona mede dentro dela: `TABS`, `location`, `pos`, `LINE`/`BOX`/`IMAGE`, a `width` implícita do `TITLE` e a centralização dele. A zona vale enquanto o cursor estiver na faixa vertical do logo, e `IND()` cancela ali mesmo. Consequência medida: com `LOGO('L', 3)` o título sai em x=70 (era x=10, dentro da imagem) e a 2ª linha de `FIELDS` volta para x=18,83 — a margem, porque a faixa acabou.
- **A zona valia no papel errado: o logo encolhia a largura, mas o texto ainda era medido pela página.** Duas contas divergiam. `_anchor` validava a coluna contra a área útil inteira, então `location` aceitando `PCOL(120)` e o motor desenhando fora da folha; e `_tab_x`-mediava as paradas a partir da margem esquerda mesmo com o `IND` vigente, que é o que fazia o bloco `after` alinhado por `IND(LTB, RTB)` sair torto. As duas passam a usar `_zone_ncols`, e o erro passa a dizer quantas cols a zona **tem** em vez de reclamar de uma largura que ninguém pediu.
- **`PCOL`/`PROW` viraram função com dois papéis, e o contexto decide qual é.** Antes eram constantes — `PCOL+5` era concatenação de string que o motor reconhecia de longe. Agora `PCOL()`/`PROW()` são o **valor** da posição corrente (usável em `TABS`/`location`/`pos`, e ainda somando: `PCOL() + 5`), e `PCOL(n)`/`PROW(n)` solto na lista de items é a **diretiva** que move o cursor: `n` cols do início da zona, `n` linhas da margem de topo. Um nome só porque a conta é a mesma — o que muda é de onde ela conta. A string `'PCOL+20'` continua válida em `TABS`, e argumento que não é número levanta nomeando a função.
- **O título parou de espaçar em milímetros.** `GAP_TITLE`/`GAP_SUBTITLE` (4mm no 1º, 3mm nos demais) eram a única coisa no framework que espaçava em mm enquanto `rows_before`/`rows_after` já contavam linhas — duas unidades para a mesma ideia, e `GAP_SUBTITLE` sem par no arquivo era o tipo de coisa que some do autocomplete e volta como typo. Agora o avanço é `rows_after` como em qualquer item, com o padrão **1 linha** no `TITLE`/`TITLES` (que é o que a documentação sempre disse que ele fazia) e validação de número >= 0 no render. O header em dict legado, que ainda usava as constantes, também passou a avançar uma linha.
- **Bug de `.0017` publicado e corrigido aqui: o `rows_before` era aplicado duas vezes.** Ao generalizar o respiro para todo item, o bloco antigo dentro de `_um_item` continuou lá, e `rows_before: 2` virava 4 linhas em `TEXT`, `FIELD` e `MEMO` (medido: y=34 em vez de y=22). Só apareceu porque a zona mudou a geometria do cabeçalho e o canto ficou visível; a verificação de uma linha por item é a que pega isso.

### 1.26.10.08.0017
- **O `label` do `MEMO` virou prefixo da 1ª linha.** `MEMO('observacao', 84, {'label': 'Obs.:'})` sai como `Obs.: produto esgotado` na mesma linha, com as seguintes voltando para a borda do bloco. Era uma linha própria acima do parágrafo — e o `MEMO` era o único item que empurrava o texto para baixo, já que o `FIELD` sempre foi inline. É **mudança de comportamento** de prop documentada. O rótulo é verbatim (com ou sem dois-pontos), medido na fonte que sai, e o `J` justifica no que sobra depois dele: a borda direita da 1ª linha continua em `x + w` e o rótulo não estica. Com `recuo` ele nasce dentro do recuo, porque `recuo` é "afasta a primeira linha" e o rótulo faz parte dela; e `recuo + rótulo` sem medida levanta nomeando as duas, em vez de virar uma palavra por linha.
- **`rows_before`/`rows_after` valem para todo item.** O bloco do respiro ficava no FIM do laço de `_render_items`, e todo item que dava `continue` nunca chegava nele — então `MEMO(..., {'rows_before': 2})` era lido e **ignorado calado** (medido: y=10, enquanto o mesmo `rows_before` num `TEXT` ia a y=22). A regra agora é uma só, num `_respiro` só, chamado dos dois lados do item. O COMPRA usava um `LF(1, {'when': 'observacao'})` na mão para contornar isso, com o mesmo `when` repetido; agora é `MEMO(..., {'rows_before': 1, 'when': 'observacao'})` — geometria idêntica, um item a menos.
- **`GAP_LABEL` entra como respiro rótulo→valor, em cols** (1 col = 1,7653mm na fonte de referência, que é `get_string_width('0')`, não `25.4/cpp`). Só o `MEMO` usa, porque só lá o gap é **desenhado**: no `FIELD` o `+ 2` é largura de CAIXA, e o fpdf posiciona a próxima célula em `new_x="END"`, que é a borda do **texto** — o respiro real ali é o `c_margin` da biblioteca. Converter aquele `+ 2` para cols não mudaria nada no papel, só a conta de estouro, e seria afirmar uma coisa falsa.

### 1.26.10.08.0016
- **Um avaliador para o framework inteiro: `ajsystem/core/expr.py`.** `avaliar()` devolve o valor, `condicao()` a verdade, e os dois servem `when`, ternário, `calc` da Entity e `calc_value` da list — inclusive no app. Uma gramática só: paths, literais, aritmética, comparação, booleano e função da allowlist, com a precedência do Python. Os dois `eval` do Python (`do_report._calc_fn` e `utils.calc_value`) saíram: o mesmo conceito estava em duas linguagens dentro do motor, e um `eval` a menos num módulo que roda em request. Antes de trocar, o inventário do `calc` do app (`valor + acrescimo - desconto`, `qtd * preco`, `previsto - realizado + variacao`, `divide(valor, qtd_minima)`) foi medido no avaliador novo.
- **O avaliador quase mentiu duas vezes, e as duas são a mesma classe de erro: resultado plausível e errado.** `and` estava com a semântica de `or` — `a and b` devolvia `a` quando `a` era verdade — e `x > 0 and y > 5` dava `True` com `y` falso; uma condição que mente calada é o pior bug que existe. E `not` estava no primário, o que fazia `not status > 0` virar `(not status) > 0`, sempre falso e nunca reclamando. A tabela-verdade de `and`/`or` nos quatro estados de entrada é o teste que pega a primeira, e é o que roda na verificação.

### 1.26.10.08.0015
- **Um avaliador só: `ajsystem/core/expr.py`.** `avaliar(expr, obj=None, get=None, funcoes=None, rotulo=...)` devolve o **valor**; `condicao(...)` devolve a verdade. Uma gramática para tudo o que é expressão no framework:

| | |
|---|---|
| paths | `valor`, `a.b.c` (de `obj`, ou do getter em `get`) |
| literais | número, string entre aspas, `True`/`False`/`None` |
| aritmética | `+ - * / // %`, unário `+`/`-`, parêntese |
| comparação | `>`, `>=`, `<`, `<=`, `==`, `!=`, `=`, `<>` |
| booleano | `and`/`or`/`not`, e as grafias `&`, `|`, `||`, `!` |
| função | só da allowlist do caller (`funcoes=`) |

Precedência do Python, do mais fraco ao mais forte: `or` < `and` < `not` < comparação < `+ -` < `* / // %` < unário < primário. **O `calc` da Entity, o `when`, o ternário do template e o `calc_value` da list usam todos esta função** — usar direto no app também: `from ajsystem.core.expr import avaliar, condicao`. Não é Python: parser próprio, sem `exec`/`eval`, porque o módulo é genérico e `eval` aqui abriria execução de código sem motivo. O que ele não sabe, ele diz: função fora da allowlist, operador desconhecido e tipo incompatível levantam nomeando a expressão.

**Ternário no template: `{cond ? a : b}`.** A condição é a **mesma** gramática do `when` — path, comparação, `and`/`or`/`not`, parênteses — e não um segundo condicional: é a decisão **dentro** do texto, para quando muda uma palavra em vez de a linha inteira. No COMPRA o título virou `'{status == 1 ? Pedido : COMPRA} #{id}'` com `when: 'status != 0'` fazendo o guard, porque o ramo 'COMPRA' cobre tudo que não é 1 e status 0 incluído. Para escolha que **some a linha**, `when` por item continua sendo o caminho certo: o que se quer ali é a linha sumir, não o texto trocar dentro dela. Ramos aceitam `{campo}` (e saem com o catálogo do LIST) e aninham entre chaves.
- **O ternário quase virou bug duas vezes, e agrammar de `when` foi o que segurou.** `_truth` ganhou um getter opcional (`get`) porque `render` não tem objeto — e a folha passou a ler por ele, mas o ramo de comparação continuou em `dotted_get(obj, ...)`: com `obj=None` todo operando esquerdo dava `None` e **toda comparação virava `false` calado**. Depois o espaço em volta de `?` e `:` sobrou no ramo, e o título saiu `' Pedido '`. Os dois são a mesma classe de erro — resultado plausível e errado — então o scanner é por profundidade (`_pos_topo`), não regex: o ramo pode conter `{qtd:02d}`, e o `:` do format-spec confundido com o separador troca a palavra sem reclamar. `?`/`:` de nível 0 dentro de ramo levanta, com a regra de aninhar entre chaves na mensagem.

### 1.26.10.08.0014
- **`TITLE` (e `TEXTS`) aceitam `options`: o catálogo do item vence o do field.** Um template resolve `{campo}` pelo catálogo que a Entity traz, e às vezes esse não é o catálogo que o documento quer: o nome impresso de um documento ("Cancelamento de Pedido") e o rótulo do estado do mesmo campo ("Cancelado") são vocabulários distintos. Trocar um pelo outro era um callable em Python — que escondia a troca dentro dele — e agora é `('{status} #{id}', {'options': CATALOGO})`, o mesmo caminho que o `MEMO` já usava com `options`. Bônus: a declaração passa a **mostrar** qual vocabulário cada título usa. `options` que não seja dict é recusado nomeando a prop, no apply e no render. O `TEXT` passa a aceitar o mesmo override, e o `callable` continua valendo.

### 1.26.10.08.0013
- **`TITLES([...])`: vários `TITLE` numa tacada, com fonte por título.** Como `TEXTS`/`FIELDS`: `'texto'`, `('texto', {props})`, callable ou `{'TITLE': {...}}`, e vale em **qualquer prop que seja lista de items** (`header`, `items`, `before`, `after`, `table.after`) — a lógica do título saiu do header para um helper só, com os defaults chegando por argumento (header: `h.title_font_size`/`h.title_font_style`; corpo: as constantes), porque os dois caminhos têm a mesma cascata e a mesma conta de altura. `font_size`/`font_style` mudam a **fonte** sem mudar a **posição** — quem escreve `'A', ('B', {...})` continua vendo B como subtítulo, com respiro de subtítulo — e são validados no render (`> 0`, `''|B|I|BI`). COMPRA, Orçamento e Pedido ganharam o subtítulo `'Status: {status}'` condicional.
- **O `text` do `TITLE` virou template de verdade, e o catálogo do field desambigua.** `'Status: {status}'` saía literalmente: o ramo do título só trocava `{id}`. Agora passa pelo mesmo avaliador do `TEXT`, e o rótulo do LIST vem do field — mas `_fmt_opts_for` exigia nome **único** no Entity merged, e `status` existe em Compra, Orçamento, Pedido e Transação: o `Status:` saía com o código. A entidade **principal** do report passou a ser o desempate (`prefer`), em vez de estreitar o Entity — que resolveria o título e quebraria `{Conta.telefone}`, que é de outra entidade.
- **`when` com comparação:** `'status > 0'`, `>=`, `<`, `<=`, `==`, `!=`, `=`, `<>`, com o lado direito literal ou outro path. Liga mais forte que `not` e mais fraca que `and`/`or`. Campo ausente não ordena (devolve `false`) nem estoura, porque `None > 0` em Python é `TypeError` e aqui a linha inteira sumiria sem erro visível; em `==`/`!=` ausente segue a identidade. Operador malformado **levanta** em vez de virar `false` calado.
- **Bug antigo: o parêntese do `when` não fazia nada.** O split de `or`/`and` ignorava profundidade, então `(a or b) and c` cortava no `or` do meio e tratava `(a` como um path — que nunca existe, então a expressão dava `false` sem reclamar, com o parêntese documentado como sintaxe desde sempre. `_split_topo` só divide no nível 0. Este bug apareceu porque a comparação **transformava** o silêncio em `ValueError`, o que seria pior.

### 1.26.10.08.0012
- **`MEMO` tem `recuo`: afasta só a primeira linha, em cols.** `MEMO(campo, width, {'recuo': n})` é literalmente `spaces(n) + texto`: a 1ª linha quebra na medida `w - recuo` e as seguintes ficam como estavam, então um parágrafo recuado não é um bloco novo nem muda a centralização — `width` continua medindo o bloco inteiro e o `label` continua na borda dele. O recuo entra como **posição**, e não como espaços no texto, de propósito: se entrasse como texto o `J` esticaria os espaços do recuo junto e ele cresceria só na 1ª linha (medido: 10.6mm em vez de 7.06mm). Por isso o invariante testado não é "a 1ª linha acaba onde acabava" — o recuo muda o **conteúdo** dela e a justificação pode entrar ou não — e sim que a 1ª linha nunca sai do bloco: `(x + recuo) + (w - recuo) = x + w` (medido: a 1ª linha recuada termina em 163.02mm num bloco que vai até 175.61mm). `recuo >= width` é recusado na factory **e** no parse (mesma regra, `_memo_check`), e `recuo` não vira prop do field.
- **`LINE()` no `table.extend` não avança linha: a régua é divisor, não linha.** Ela nascia no topo da faixa e empurrava tudo 6mm abaixo, então um separador custava uma **faixa em branco** — o autor bancava uma linha vazia para pagar a régua. Agora a linha seguinte se apoia na régua, e ela ocupa o lugar da faixa. Corrige de passagem a régua que vinha **por cima** do texto de uma linha que ficou pela esquerda (span que não fecha a linha): ela agora fecha a linha antes de desenhar. `LINE` **fora** do `extend` continua ocupando uma linha — lá a régua é intenção do autor, desenhada na zona, e quem quer espaço extra pede `LF(n)`. Equivalência: 18 cenários do COMPRA, 41 casos, 4 reports, forms/listas/RQ/moeda/parse/calc byte a byte — a única diferença de definição é a do próprio COMPRA, que passou a declarar `recuo` e a régua.

### 1.26.10.08.0011
- **`when` aceita expressão booleana sobre paths.** `or`/`and`/`not` e `|`/`&`/`!`, com parênteses e precedência NOT > AND > OR: `when: 'acrescimo or desconto'` (ou `'acrescimo | desconto'`). O COMPRA precisava disso para o Total aparecer quando houver acréscimo **ou** desconto, e até agora o `when` só avaliava um path — então a expressão dava `False` e a linha do Total **sumia do documento**, sem erro. Parser próprio (`core/text._truth`) em vez de `eval`: o avaliador de `calc` (`do_report._calc_fn`) usa `eval` porque é aritmética com namespace montada, e trazer isso para o `text.py` — que list/select também usam — abriria execução de código num módulo genérico. Na forma **dict** o alvo continua sendo comparação (`{'ativo': True}` casa com campo booleano), não truthiness: para "algum destes" a expressão é o caminho.

### 1.26.10.08.0010
- **`MEMO` virou um FIELD com medida: o catálogo é o override do field, e `labels` saiu.** O primeiro argumento passa pela mesma gramática de `field_spec_item` (`'x'`, `('x', {...})`, `{'x': {...}}`) e as props do `MEMO` são as props do campo — `options` (catálogo), `label`, `when`, máscara. Inventar `labels` para carregar catálogo era o que obrigava a repetir o mapeamento que a Entity e o override do field já sabem fazer. `campo` com `{` continua template, sem label nem override, que é a mesma distinção que separa `FIELD` de `TEXT`. Provado que o catálogo do report vence o da Entity fim a fim (sai `SEIS`, não `Cancelado`) e que o documento do COMPRA ficou **byte-idêntico** (18 cenários).
- **Um `LIST` com `calc` dict imprimia o CÓDIGO em vez do rótulo.** O Schema da Compra declara `status: {'calc': {'type': 'call', 'source': 'calc_status'}}` — um `calc` **dict**, do formulário, que recalcula no save. No `_resolve_map` o ramo do `calc` engolia o campo: como dict não é `str` nem callable, nenhum `function` era gerado **e não caía no display de LIST/BOOL**. Agora o `calc` que o report não consegue usar deixa o campo passar para o passo genérico de exibição, e o `options` do report entra nele (`{**raw_cfg, **extra}`) em vez de o catálogo da Entity vencer. Sem isso o `MEMO('status')` do COMPRA simplesmente não imprimia nada. Isso é a mesma família do `LIST/BOOL` de 052ec2b, agora pelo lado do `calc`.
- **`_locate` preferia `None` a escolher, em campo que existe em vários models.** `status` existe em Compra, Orcamento, Pedido, Transacao e Transferencia: com a Entity mesclada, `len(hits) > 1` devolvia `None` e o item perdia label, catálogo e `calc` de uma vez — silencioso, porque `_resolve_map` só levanta quando não acha `label`/`function` no report. Agora, havendo ambiguidade, vence a entidade **principal** do report (comparada pelo nome da classe, que `_pmodel` é).

### 1.26.10.08.0009
- **`align` do `MEMO` passou a ser `'J'` por default.** `MEMO` é parágrafo, e parágrafo se justifica — `L` é a exceção declarada, não o padrão. Como `J` aqui já era um pedido com sanidade (`JUSTIFY_MAX`), o default não produz buraco onde ninguém pediu: no máximo deixa a linha como `L`, que é o mesmo que pedir `L`. Virou constante nomeada (`MEMO_ALIGN`) para o default ter um lugar de verdade, e o COMPRA pode finalmente **omitir** o `'align': 'J'` que repetia nas duas chamadas. Medido: as duas chamadas do COMPRA já passavam `'J'`, então o documento saiu **byte-idêntico** (18 cenários) — o ganho é só de declaração. E o default não fica no ar: o harness compara `MEMO(t)` com `MEMO(t, align='J')` e conta as chamadas de desenho (10 palavra-a-palavra contra 2 da linha inteira), que é a única medida que distingue os dois depois de agrupar por `y`.

### 1.26.10.08.0008
- **`MEMO(texto, width)`: o documento tem parágrafo com medida.** Um item de texto que quebra por palavra numa largura e **centraliza o bloco na área livre**, com `align: 'J'` justificando. É a resposta ao que o `IND` não resolvia — `IND` abre uma zona que **vaza** para os itens seguintes e depende de ordem, e `LTB`/`RTB` só valem depois que a tabela desenhou (medido: na 1ª instância dão a área útil inteira, na 2ª dão a tabela). Com a largura no item, dois blocos com o mesmo `width` ficam com o mesmo recuo das margens por construção. A casa não tinha quebra por palavra — só `_cut_to_fit`, que corta — então `_wrap_linhas` entrou junto. E a justificação é nossa: `multi_cell` do fpdf2 **documenta** `J: justify` mas não implementa (medido: 102.5mm e 99.2mm numa coluna de 105.9mm), e `align: 'J'` é um **pedido** — o espaço só estica até o dobro do natural (`JUSTIFY_MAX`), acima disso a linha cai em `L`, porque a 60 cols a sobra é 213% e buraco Justificado se lê pior que serrilhado.
- **`before`/`after` aceitam item, e `FIELD` solto resolve em todo lugar.** As cinco props de items passam pelo mesmo `_render_items`; `before`/`after` continuam aceitando linha de texto (é o que dá o espaçador). Um item vindo de callable é **recusado** nomeando a prop: a função roda depois do `_apply_entity`, então não tem como resolver contra a Entity. E o `FIELD` solto passou a resolver pela mesma rotina do header — antes o mesmo campo imprimia rótulo no header e **código** em `items`/`after`, e o `calc` da Entity nem chegava: `FIELD('valor')` agora traz `function` (`qtd * preco`) em vez de célula vazia. Procurei fazer isso por `_field_item` e foi **regressão**: ele não resolve caminho pontilhado de relação, e `items.qtd` voltava cru em vez de `OrcamentoItem.qtd`, sem o `align` do type. A rotina certa é a do header, agora compartilhada.
- **`when` de item aceita `{campo: valores}`** — mesmo formato que o Schema já usava no app (`{'ativo': True, 'tipo': [1, 2]}`), e com dicionário como alvo: `{'status': FRASE}` quer dizer "só nos status deste catálogo".Foi o que deixou o catálogo do COMPRA ser a única fonte de verdade (o texto *e* quais status têm frase), sem um `if status not in (...)` em Python para divergir. `LF` ganhou props pelo mesmo motivo: o respiro de um bloco condicional precisa sumir junto com ele.

### 1.26.10.08.0007
- **`wrap`: a frase de documento não nasce mais cortada.** `cell` do fpdf2 não quebra linha — o texto passa reto e a ponta sai da folha. Medido no COMPRA: a frase de cancelamento dava 206mm contra 190mm úteis, e a de devolução estourava com motivo longo (255mm). `wrap: True` troca `cell` por `multi_cell` na largura da zona e vale nos três renderizadores (linha de texto, item `TEXT`, item `FIELD`/`FIELDS`); **ausente é `cell`**, ou seja, o comportamento de sempre. A prop não precisou de dataclass: `wrap` já sobrevive ao `_apply_entity` por `item.update(cfg)`. Junto veio a **linguagem de template nas linhas de texto** de `before`/`after` (`{campo}`, `{campo:brl}`, `{campo|fallback}` e o catálogo `labels`), e um rótulo de catálogo agora aceita `{campo}` dentro dele (segunda passada, com guarda de recursão em `core.text.LABEL_DEPTH`). Isso permitiu declarar a frase do COMPRA como catálogo de `status` em vez de um dict montado em Python — e o texto passou a ser do report, ao lado do layout que o imprime. Efeito colateral bom: o `(não informado)` que era `obs = ... or '(não informado)'` virou `{observacao|(não informado)}`, a mesma sintaxe do resto do framework. Prova: 18 cenários de COMPRA (6 status × motivo vazio/curto/longo), **14 byte-idênticos** e 4 mudados — exatamente as 4 frases que estouravam, agora em 2 linhas com a ponta no lugar; mais `wrap` nos três renderizadores e a guarda de `wrap` não-booleano. Este report era o de menos cobertura do projeto: o snapshot gravava `"before": "<fn _report_before>"`, o nome da função, nunca o conteúdo.

### 1.26.10.08.0006
- **`LINE`/`BOX`/`CIRCLE` declarados em números, e a régua deixou de exigir número mágico.** As factories de grade viraram variádicas como `TABS`/`IND`/`POS` (a lista solta continua valendo): `LINE(c, r, +cols, +rows)` — o 3º e 4º são **deltas** a partir da origem, e omissão vale 0, o que torna `LINE(10, 5)` um **ponto** (antes era `ValueError: linha nula`; agora sai um disco de raio `col_w/8`, que acompanha o pitch da fonte — um `line` degenerado emitiria um subcaminho de comprimento zero e não pintaria nada). `LINE()` pega a largura da zona (a indentação vigente ou, sem ela, a última tabela), `LINE(True)` a da página inteira, e `LINE(w)` equivale a `LINE(PCOL, PROW, w)` — essas três referências só divergem onde a tabela é mais estreita que a página ou o `IND` recua, e é por isso que o harness monta esse cenário. `LINE` desenha e avança uma linha; espaço extra é `LF(n)`, que compõe exatamente o que `rows_before`/`rows_after` faziam (medido). `when` passou a valer também para `LINE`/`BOX`/`CIRCLE` — era aceito e ignorado. `body.before`/`body.after` **recusam** item nomeando a prop (são linhas de texto) em vez de virarem linha em branco, e `table.extend` passa a usar `LINE()` no lugar da string `'LINE'`, que eram dois nomes para a mesma régua. Equivalência: 4 reports + 41 casos, 20 forms, 15 listas, RQ, moeda, parse e calc byte a byte, mais 40+ medições de coordenada das formas.

### 1.26.10.08.0005
- **`LIST`/`BOOL` imprimem rótulo em toda prop que mostra field, não só nas colunas.** O report resolve campo por dois caminhos: `_resolve_map` (colunas e `header.fields`) e `_field_item` (`FIELDS` em `items`/`after`/`table.after`/header). Só o primeiro consultava o catálogo, então um `FIELDS('forminhas')` em `body.after` imprimia `1` onde a coluna imprimia `Fornecidas pelo Cliente` — o mesmo campo, o mesmo catálogo, resultado diferente só pela prop. O passo virou genérico: `core/resolve.field_options` (o catálogo, aceitando `list` e `options` com a precedência de `build_field_config` — seis pontos do report liam isso à mão, um deles com a ordem das chaves invertida) e `core/resolve.field_display_fn` (a tradução, `LIST`→rótulo e `BOOL`→Sim/Não), consumidos pelos dois caminhos. Código fora do catálogo cai no valor cru, como na listagem. A **listagem não muda**: ela traduz no template e renderizava certo. Provado no PDF renderizado, não só no dict: `forminhas=0/1` saem `Simples (Inclusa)`/`Fornecidas pelo Cliente` e `7` (fora do catálogo) sai `7`. Equivalência do resto: o diff inteiro são linhas de `"function"` a mais, zero remoções.

### 1.26.10.08.0004
- **Uma função decide o que é um item que enumera field (`core/resolve.field_spec_item`),** e as três gramáticas que existiam passam a usá-la: `do_report._resolve_map` (lista solta), `do_report._expand_fields_list` (itens de layout) e o factory `FIELDS`. As formas são as de `list.columns` — `'campo'`, `('campo', {props})`, `{alias: {props}}`, `{'field': 'campo', **props}` — e quem chama decide a **política**: `FIELDS` mantém ser estrito (só as duas formas curtas, com os mesmos erros), os itens de layout descartam o que não nomeia field, e `_resolve_map` preserva a forma legada em que um dict de props sem nome vira `_0`, `_1`…. `parse_select` ficou de fora de propósito: o tipo canônico dele é `SelectEntry` e o contrato de erro é outro. Equivalência por harness: os 4 reports, os 12 casos sintéticos e 16 novos de gramática (as 4 formas em `columns`/`header.fields`/`FIELDS`, entidade expandida, forma legada) com os 7 caminhos de erro travados — tudo byte a byte igual.

### 1.26.10.08.0003
- **Três passos de resolução de field deixaram de ter cópia própria.** `core/list.py` tinha um `_build_fields_from_merged` idêntico ao `defs/data._build_fields_from_names` (mesmo `merged.get`, mesmo skip de `memory`, mesmo `_pos_managed`) — o de `list.py` saiu e passou a importar o de `data.py`. A decisão de apresentação (máscara → moeda via `@M(id)`; `NUM`→`brl`; `DATA`/`date`→data; `INT`→centro) estava escrita duas vezes com o mesmo encadeamento, em `do_report._infer_presentation` e `search._fmt_cell`; virou `core/resolve.field_presentation`, chamada pelos dois. E `defs/data.resolve_field_mask` responde "qual a máscara deste field" sem materializar o `Field` — o `do_report._field_mask` montava um field inteiro só para ler `.mask`. Equivalência por harness: 4 reports + 12 casos sintéticos, 20 forms, 15 listas, camada RQ e 352 combinações de célula da busca (`search._fmt_cell`) saem idênticos.

### 1.26.10.08.0002
- **O report passou a ler a fonte `select` pela máquina (`core/resolve.py`).** O que era `_disp_map`/`_computed` reimplementados à mão em `do_report._apply_entity` virou as primitivas `select_entry_props`/`select_entry_computed`, as mesmas que `query_select_layer` usa — o report continua passando `format` na lista de chaves porque a prop é dele, não da listagem. O merge do report segue *overlay* (Entity/Schema < select < inline), então ele **não** foi para `apply_field_layers`, que é fill-gap; a docstring do módulo registra a distinção. Equivalência provada por harness: os 4 reports do app e 10 casos sintéticos (props inline, `format` explícito vs máscara, coluna nova do select, `levels`/`hierarchy`, chave pontuada, header dict/lista, `text`) resolvem byte a byte igual, e as 20 forms + 15 listas do app (outros consumidores da máquina) também.
### 1.26.10.08.0001
- **Cálculo de `calc` lê o valor *desformatado* do input (`parseNumText`/`parseNumField` em `static/js/formats.js`).** O `on_set` de `produto_id` (itens do orçamento) copia `data-preco` do `<option>` — `str(Decimal)`, `'6.00'` — direto pro input, e `parseNum` lia o ponto como milhar pt-BR: `100 × 600 = 60.000,00` em vez de `600,00`. A leitura do input numérico passou a ser a regra de `_coerce` (`core/form.py`) e de `as_num` (`core/utils.py`): vírgula presente = decimal do app (ponto é milhar); sem vírgula, ponto é decimal. No lado da escrita, `numToInput`/`numToInputFor` põem no input o valor na convenção do campo alvo (`numToInputFor(target, val)` em `itOnSetBind` e `itUpdateZerados`), espelhando `fmt_num`. `parseNum` ficou como era (ler exibição/ordenar coluna), e `parse_brl` passou a fazer o que o docstring já prometia. `'1.000'` segue ambíguo por construção: sem vírgula é lido como `1.0`, igual o servidor.


### 1.26.10.07.0004
- **Células `calc` da lista passam a renderizar pela máscara.** O ramo `col.calc` de `list.html` só formatava `B/X/R` e data — um `@M` (ex. `MVALOR` no `total` de orçamentos) caía no valor cru. O fallback dos 5 ramos de calc (linha, detail, card, cardonly) virou `_cv|format(col.mask) if col.mask … else _cv`, e o filtro Jinja `format` (= `core.formats.format`) foi registrado no `init`. Resultado: `total` (agg) sai `R$ 1.234,50`, e qualquer coluna calc com máscara numérica `0/9` passa a agrupar milhar. Sem regressão em calc sem máscara (reproduz `{{ _cv }}`).
- **`Masks`/`MASKS` deixaram de ser repetidos à mão** — derivados no próprio import por `collect_mask_catalog` (nomes maiúsculos, valores `str`/`dict`, na ordem declarada) em `ajsystem/defs/masks.py` e `app/extends/masks.py`. Adicionar um `M*` novo no arquivo não exige mais atualizar o dict.
- **Máquina genérica de camadas de fields (`core/resolve.py`: `RL`/`RQ`/`RS`/`RE`).** `apply_field_layers` aplica props por camada em *fill-gap* (quem declara primeiro vence) com a validação de sempre, e `query_select_layer` extrai a camada de uma fonte `query` (destila `calc` herdado quando a query computa, sobrescreve `label/width/align`, `pos_list: 0` salvo override do Schema). `resolve_entity_fields` passou a delegar a ele (ordem `[Schema, layer, Entity]` = mesmo vencedor por chave do `{**Entity, **layer, **Schema}` anterior) e `do_list` orquestra `RS/RE → RQ → build`. Equivalência provada por harness: os 26 merges (22 entidades + card em `pagar`/`receber`) e a listagem com query (`operacoes`/`QPLANO`) são idênticos ao fluxo antigo, byte a byte.
- **`Form._resolve_fields` migrou para a RL da listagem (`resolve_column_configs`).** O ramo `is_multi_entity` morto (o merge de `resolve_entity_fields` é sempre single-entity) caiu, e a expansão de `fields` como nome de entidade passou a reusar `resolve_column_configs(…, pos_managed=True)` no lugar do `_build_fields_from_merged` inline — o form e a listagem agora montam campos pelo mesmo código. Equivalência provada por harness: os 21 forms resolvidos (fields, sessões query/table, colunas, botões, label/redirect/flash) são byte a byte iguais aos anteriores.

### 1.26.10.07.0003
- **`currency` deixou de ser prop de `Field` (vira motor, derivada da `mask`).** O dataclass não tem mais `currency` — Entity/Schema que declarar levanta `FieldConfigError` (nova chave desconhecida em `_FIELD_KEYS`), e `Field(**{...,'currency':...})` falha no construtor. `Field.currency` é agora **property derivada** de `mask_money_id(self.mask)` (`@M(id)` validado em `MONEY`; `@M` sem id → `DEFAULT_MONEY`; sem `@M` → `None`), lida pelos mesmos consumidores de sempre: lista (`field_to_column`), formulário (totais), templates (`field.currency`/`col.currency`) e report. `search._fmt_cell` e `_infer_presentation` passaram a derivar a moeda de `cfg['mask']`; a guarda obsoleta de `_field_mask` (number+currency sem mask) caiu. Migrados todos os campos de dinheiro do app para `mask: MVALOR` (que já carrega o `@M(BRL)`): `previsao` (previsto/realizado/variacao/saldo), `recurso` (saldo), `transacao` (valor/variacao/saldo), rotas `pagar`/`receber` (previsto/realizado/ratear), `site/orcamento` (preco) e o `total` do Schema de `sys/orcamentos` (era `999,999.99`). `decimals` segue declarativo (entrada `data-num-decimals`, arredondamento no POST, totais).
- **`formats.format`/`fmt_mask_cmd` roteiam número × máscara de texto corretamente.** Máscara de documento tem literal fora de `09,.` (CPF `-`, tel `(`/`)`, placa letras) → cai no caminho de texto (`fmt_mask`), não mais no numérico (que calculava casas a partir do `.` e saía `12345678901,00000000`). Mesmo guard (`_isNumMask`) espelhado no JS.

### 1.26.10.07.0002
- **Máscaras e formatação numérica dirigidas pelo app (`defs/masks.py` + `app/extends/masks.py`).** Separadores (`DECIMAL`/`THOUSAND`), catálogo de moedas por id ISO (`MONEY`/`DEFAULT_MONEY`) e máscaras nomeadas (`MVALOR`, `MCPF`, `MCNPJ`, `MCEP`, `MPLACA`, `MTEL`) num arquivo só, com override do host (merge de `buttons`/`inputs`/`fonts`) aplicado no `init` e publicado em `window.AJ_MASK`. `core/formats.py` passa a ler as constantes; JS (`static/js/formats.js`) espelha. Comando `@M(id)` (moeda, ex. `@M(BRL) 999,999.99`) e `@R` (remoção de separadores no save, agora em CPF/CNPJ/tel). Máscara numérica canônica (`0`=pad, `9`=opcional, `,`=milhar, `.`=decimal) escrita em inglês e renderizada nos separadores do app; `num_mask`/`_mask_decimals`/`parse_brl`/`fmt_num`/`fmt_money`/`fmt_percent`/`fmt_id` alinhados. Moeda **não é prop declarativa**: o dataclass `Field` não tem `currency` (Entity/Schema que declarar levanta `FieldConfigError`) — `Field.currency` é derivada da `mask` (`@M(id)`) pelo motor (`mask_money_id`). Trocar de moeda = editar `app/extends/masks.py`. Trocar os separadores do report (`_format_cell_value`/`_format_field`) e da list idem.

### 1.26.10.07.0001
- **Resolução de props do field unificada: `tipo (FIELD_TYPES+INPUT_TYPES) → Entity → Schema → Query → report`.** Cada camada sobrescreve a anterior (declaração, não motor). `list`/`form` consomem o `Field` resolvido sem override; o `report` mantém override de props de display (`format`/`mask`), e a entrada do `select` da query sobrescreve as props que já declara (`label/width/align/format/pos_list`). A `mask` é prop de **exibição**: explícita (Entity/Schema/query/report) vence; senão o default do input (cpf/cnpj/telefone/data/hora — `time` ganhou `hh:mm`); senão o default numérico de `decimals`, renderizado **com separador de milhar sempre**. `decimals` controla a **entrada** (`data-num-decimals`), o arredondamento no POST e compõe o default numérico; a moeda **não** é prop declarativa — `Field.currency` é derivada da `mask` (`@M(id)`) pelo motor (lista/form/report/totais leem `f.currency`). `_field_mask` resolve pelo `Field` (não re-deriva do catálogo) e `_format_cell_value` usa `formats.format` (número agrupa no report).
- **`FIELDS` v2 e resolução de field do report unificada.** `FIELDS(*itens)`, item `'campo'` ou `('campo', {props})`; `'Entidade'` expande, `'Entidade.campo'` é campo relacionado. Cada item resolve **como `columns`/`fields`** (list/form): `build_field` sobre Entity+Schema, com label da Entity (não mais auto-label) e `lookup` de FK; sem lookup, o caminho é `<relação>.nome`. Props de `Field` no dict são override; `tab/when/rows_*/font*/function` são overlay de report. O resolvedor próprio (`_expand_fields_list`/`_resolve_map`/`_attach_field_mask` na parte de field) foi substituído por um caminho único; `table.columns` também aceita `('campo', {props})`. Relatórios do app migraram: pedido/compra referenciam o **FK declarado** (`conta_id`/`fornecedor_id` + `Conta.telefone`), eliminando os virtuais `_cliente_nome`/`_cliente_telefone`/`_fornecedor_nome`; orçamento usa `Evento.<campo>`.

### 1.26.10.06.0002
- **Bloco `table.after` passou a fluir: o cursor é herdado entre itens (fix do "imprime tudo no mesmo ponto").** `_place_item` separou as semânticas de posicionamento: âncora (`tab`/`location`/`pos`) absoluta, inalterada; sem âncora, `FIELD` e `TEXT` com `width` **herdam o X do item anterior** (só entram na 1ª coluna da zona se o cursor está fora dela — início de bloco pós-tabela ou zona nova do `IND`); `TEXT` avulso sem `width` é **linha própria** (começa na 1ª coluna da zona e avança a linha automaticamente quando o fluxo terminou antes dela — é o "avanço ao final" dos `rows_after`/`CR`); bloco (`IMAGE`/`LINE`/`BOX`/`CIRCLE`/`CALL`) volta ao início como antes. O bug: todo item sem âncora recebia `set_x(zone0)` individual, então os campos de `FIELDS` e os `TEXT` do `after` de pedido/orçamento/compra **imprimiam todos sobre o mesmo ponto** (o wrap nunca disparava porque `x == x0` zera a condição) — e `TEXTS` sofria do mesmo mal. Verificado por dump de coordenadas em PDF: campos do evento lado a lado com wrap na zona `IND`, `Data`/`Forminhas` em linhas distintas, zero pares `(x,y)` duplicados em pedido (com e sem `obs`), compra e orçamento.
- **`TEXT` avulso ocupa o resto da zona, e o bloco `after` em lista ganha o respiro de 4 mm.** O preenchimento (`fill`) é só do `TEXT` standalone — é o que faz `align: 'R'/'C'` valer na zona (Acréscimo/Desconto/Total da compra saem colados na direita e a régua `____` centrada); sub-item de `TEXTS` continua apertado inline (`fill=False`) e `FIELD` nunca preenche. `pdf.ln(GAP_AFTER_TABLE)` passou a rodar antes de `_render_items` na lista de `table.after` — a constante existia, mas só era usada no ramo de string.

### 1.26.10.06.0001
- **Diretivas de fluxo novas: `FONT`, `IND`, `TEXTS`/`CR`/`LF`/`FF` e as âncoras `LTB`/`RTB`/`NCOL`.** `FONT(nome, cpp?)` troca família/pitch no meio do fluxo (`cpp` 0..3 = 10/12/17/20; col nominal `25.4/cpp`; `FONT()` nu restaura o default) sobre o catálogo `defs/fonts.py` + camada `app.extends.fonts` (mesmo merge de `buttons`/`inputs`). `IND([l, r])` delimita a região em que o fluxo flui sem âncora (`IND()` restaura; validação em cols da fonte corrente) e `LTB`/`RTB`/`NCOL` são as bordas da última tabela (área útil se nenhuma) — `IND(LTB, RTB)` alinha o bloco `after` às colunas da tabela. `TEXTS(*itens)` monta blocos de texto (`str` = sempre, `(texto, when)` = condicional, dict = props), `CR()` volta à 1ª coluna, `LF(n)` avança linhas e `FF()` quebra página no corpo. `TABS()`/`IND()` sem parada = restaura (`TABS` sem argumento deixou de ser erro).
- **`table.extend`: linhas dentro do quadro, depois dos totais.** Tuplas `(col|[a,b], texto[, props])` + `LINE()` (divisor, **não** avança linha)/`'LF'`/`'CR'`; `when` por linha, placeholder puro `{campo}` herda o `format` da coluna, span `[a,b]` centraliza. `font`/`cpi`/`lpi`/`font_size` são recusados na tabela e `style` aceita só `''|B|I|U|BI|BU|IU|BIU`. No `_apply_entity` o `format`/`mask` do campo vira `_fmt_opts` da linha. Pedido/compra passaram a imprimir Acréscimo/Desconto/Total por `extend`, sem helper Python.
- **`FIELDS` aceita kwargs e dict de cfg.** `FIELDS(a={'tab': 1}, …)` (kwargs, sem chaves; exige modelo `str` ou ausente), `FIELDS({'a': {...}})` ou a forma interna `{'model': …, 'fields': …}`; cfg por campo aceita `label`/`when`/`function` (com `_auto_label` quando não há rótulo) e o `when` posicional vale para todos. Relatórios do app migraram para `from ajsystem.defs.report import *` (`__all__` novo entrega **só** as factories de declaração; `Report*`/`parse_*` seguem import explícito) — `_brl`/`_report_after`/`_event_after`/`_forminhas_carteira` saíram de `pedidos`/`compras` e o bloco do evento virou `IND(LTB, RTB)` + `FIELDS('Evento', tipo={…, 'when': 'evento.tipo'}, …)`.
- **Controles de régua: `totals.bline` e `groups.gline`.** `bline` = régua antes da linha de subtotal/total; fechamento de grupo usa `gline` (legado `line` traduzido no parse e nas sínteses de `levels`). Réguas seguidas sem conteúdo entre elas saem uma vez só; o total geral ganhou régua antes e depois internas.
- **Logo e página standalone saíram da declaração do `Report`.** `do_report._resolve_logo` lê `APP.logo` (relativo a `static/`) com fallback `LOGO_FALLBACK` (`static/icons/Logo.png`), e `print_report_page` usa a constante `PRINT_TEMPLATE`. As chaves legadas `print_template`, `logo_path` e `orientation_mutable` são ignoradas no parse (shim) — a última não tinha consumidor e a feature saiu.
- **Correções de impressão e de form.** `_render_table` guarda as bordas da última tabela em **mm** e converte na resolução (`_table_edges`): gravar já em cols do pitch da tabela brigava com o `ncol` da validação do `IND` depois que `FONT` mudou a unidade. `data-enabled` no botão escapava para `&#34;` (Markup do `title` escapava a string do `~`) e o `itEnabledEval` morria com seletor inválido **antes** de amarrar os listeners do form — o `total` nunca recalculava; fix é `|safe` + espaço inicial em `_attrs` (`form_macros`). `item_table` fechava o `</div>` de `.itm-scroll` só dentro de `{% if _can_edit %}`: sessão readonly (pedido com evento) deixava o HTML desbalanceado, `#report-content` nascia dentro de `#page-content` e o overlay escondia os dois — página em branco ao imprimir; agora o fechamento é incondicional e o `{% if _can_edit %}` do ColumnTemplate é separado. `transformers` lê o atributo com `getattr` tolerante (property que levanta não derruba o form), input `date` ganhou máscara `dd/mm/yyyy`, `'LINE'` (string) no relatório de pedido parou de quebrar o boot e `app/extends/utils.py` ganhou `num0` (Decimal tolerante a None/str/float).

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
