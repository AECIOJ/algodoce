# AJSYSTEM — Manual do Framework

> Vinculado a `ajsystem/version` (`1.26.10.24.0001`) — formato `ciclo.ano.mes.dia.seq`. O bump vem de cada assunto que muda código de `ajsystem/` (não só os dataclasses desta referência; `app/` não entra). A versão do **app hospedeiro** mora em `APP['version']` (`app/config.py`) e quem bumpa é o dev, na mão, com o comando `versao`.

---

## 1. Conceitos

O framework monta rotas, telas e menu a partir de três dicts declarados no app:

| Item | Onde | O que é |
|------|------|---------|
| `Entity` | `app/models/*.py` | Declara os campos do model (única fonte de campos). |
| `Schema` | `app/routes/sys/*.py` | Overrides de `Entity` por página (Schema vence sobre Entity). |
| `Page` | `app/routes/sys/*.py` | Tipo da página (`crud`, `redirect`, `cart`, `showcase`, `contacts`, `custom`) e seus props (`list`, `form`, `filter`, `report`, `sessions`). |

Fluxo: `config.py:menus → auto.py:registrar_modulos → Page/Schema → resolve_entity_fields → Field → form/list/report`.

Merge de props (cada camada sobrescreve a anterior):
`tipo → Entity → Schema → Query/report → Field`.

> Posição/visibilidade são props da **página** (`Page.props`), nunca do `Field` nem do `Schema`. Slots do form: `bar`, `footer`, `body`, `hidden`. Slots da lista: `line`, `card`, `hidden`.

---

## 2. Instalação e primeiro CRUD

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
npm install && npm run build:css
flask run  # http://localhost:5000/categorias
```

Exemplo mínimo (tarefa):

```python
# app/models/tarefa.py
class Tarefa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    feito = db.Column(db.Boolean, default=False)

Entity = {
    'id':    {'type': 'ID'},
    'titulo': {'type': 'TEXT', 'required': True, 'width': 20},
    'feito': {'type': 'BOOL', 'input': 'toggle'},
}

# app/routes/sys/tarefas.py
Page = {
    'type': 'crud',
    'props': {
        'list': {'columns': 'Tarefa', 'order': ['titulo']},
        'form': {'fields': 'Tarefa'},
    },
}

# app/config.py — dentro de SYS.menus.Cadastro.submenus
'Tarefas': {'icon': 'bi-check'},
```

---

## 3. Dataclasses declaráveis no app (ordem de utilização)

Cada dataclass abaixo é o que o desenvolvedor declara no app. Props do motor (com prefixo `_` ou resolvidas internamente) são omitidas.

### 3.1 `Field` — `ajsystem/defs/data.py` `class Field`

Declara um campo na `Entity`/`Schema`.

| Prop | Tipo | Valores possíveis | Exemplo |
|------|------|-------------------|---------|
| `type` | `str` | `TEXT`, `MEMO`, `INT`, `NUM`, `PERCENT`, `PK`, `ID`, `DK`, `FK`, `DATA`, `DATA_HORA`, `HORA`, `BOOL`, `FONE`, `CPF`, `CNPJ`, `LIST`, `MULT10`, `IMAGE` | `{'type': 'NUM', 'mask': MVALOR}` |
| `label` | `str` | texto ou `None` (usa `_auto_label(name)`) | `{'label': 'Valor (R$)'}` |
| `width` | `int` | colunas `ch` (ex: `6` ID, `12` NUM) | `{'width': 12}` |
| `align` | `str` | `left`, `center`, `right` (`NUM` → `right` automático) | `{'align': 'right'}` |
| `input` | `str` | nome de um `Input` do catálogo (`text`, `number`, `date`, `select`, `textarea`, `email`, `tel`, `checkbox`, `toggle`, `multi`, `image`) | `{'input': 'toggle'}` |
| `input_props` | `dict` | override parcial do input neste campo | `{'input_props': {'cls': 'x'}}` |
| `options` | `dict` | `{k: label}` para `LIST`/`MULT10` | `{'options': {0: 'Pagar', 1: 'Receber'}}` |
| `mask` | `str` | `@R 999.999.999-99`, `dd/mm/aaaa`, `@M(BRL) 999,999.99`, `@T` | `{'mask': MVALOR}` |
| `placeholder` | `str` | texto | `{'placeholder': 'Digite aqui'}` |
| `decimals` | `int` | `0` int, `2` moeda | `{'decimals': 2}` |
| `min`/`max`/`step` | `num` | limites numéricos | `{'min': 0, 'step': 1}` |
| `percent` | `bool` | `True` → sufixo `%` | `{'percent': True}` |
| `required` | `bool` | `True` → `*` no label e `required` no input | `{'required': True}` |
| `disabled` | `bool\|callable` | `True` ou `callable(row)->bool` | `{'disabled': True}` |
| `readonly` | `bool` | renderiza rótulo + hidden; valor ainda vai no POST | `{'readonly': True}` |
| `hidden` | `bool` | `<input type=hidden>`, enviado mas não exibido | `{'hidden': True}` |
| `default` | `any\|callable` | `TODAY` (`date.today`), `lambda: 1` | `{'default': TODAY}` |
| `rows` | `int` | altura textarea | `{'rows': 4}` |
| `lookup` | `bool\|dict\|Lookup` | `True` (defaults) ou `{display, fields, value, when, query}` | `{'lookup': {'model': 'Conta', 'display': 'nome'}}` |
| `validate` | `str` | `cpf`, `cnpj`, `placa` | `{'validate': 'cpf'}` |
| `help` | `str\|list` | texto de ajuda (botão `?`) | `{'help': 'Informe o CPF'}` |
| `on_set` | `dict` | `{replaces: {campo: fonte}, disables: [...]}` | `{'on_set': {'disables': ['cnpj']}}` |
| `calc` | `str\|callable\|dict` | `'qtd*preco'`, `lambda row:`, `{'type':'agg','source':'sum(...)'}`, `{'type':'call','source':'calc_status'}` | `{'calc': 'previsto - (realizado or 0)'}` |
| `carry` | `str` | nome do campo origem no map do botão | `{'carry': 'conta_id'}` |
| `memory` | `bool` | `True` → só de tela, não persiste | `{'memory': True}` |
| `tag` | `dict\|Tag` | `{colors, color, link, size, preset, text_field, outline, cls}` | `{'tag': {'link': 'pedidos.form', 'color': 'info'}}` |

> **Moeda não é prop de `Field`.** Não existe `currency`. A moeda sai da `mask` — comando `@M(id)` (ex: `@M(BRL)`).

---

### 3.2 `Tag` — `ajsystem/defs/tags.py` `class Tag`

Usado na prop `tag` de `Field`.

| Prop | Tipo | Valores | Exemplo |
|------|------|---------|---------|
| `colors` | `dict` | `{valor: cor}` cor `ghost/primary/success/warning/error/info` ou `0-9` | `{'colors': {True: 'success'}}` |
| `color` | `str` | cor fixa | `{'color': 'info'}` |
| `link` | `str\|callable` | `'pedidos.form'` ou `lambda row: 'pagar.form'` | `{'link': 'receber.form'}` |
| `size` | `str` | `sm` (default) | `{'size': 'sm'}` |
| `outline` | `bool` | `True` → outline | `{'outline': True}` |
| `preset` | `str` | `boolean`, `ativo`, `status` | `{'preset': 'ativo'}` |
| `text_field` | `str` | campo de onde vem o rótulo | `{'text_field': 'status_label'}` |
| `cls` | `str` | classe CSS extra | `{'cls': 'badge-pill'}` |

---

### 3.3 `Lookup` — `ajsystem/defs/data.py` `class Lookup`

Usado na prop `lookup` de `Field` (FK). **Não existe `Lookup.model`** — o model alvo é inferido do FK.

| Prop | Tipo | Default | Exemplo |
|------|------|---------|---------|
| `fields` | `str\|list` | `[display]` | `{'fields': ['nome']}` |
| `display` | `str` | 1º campo após `id` do alvo | `{'display': 'nome'}` |
| `value` | `str` | `'id'` | `{'value': 'id'}` |
| `when` | `str\|dict\|callable` | `None` | `{'when': {'ativo': True}}` |
| `query` | `str` | `None` | `{'query': 'PREVISOES'}` |

---

### 3.4 `Page` — `ajsystem/defs/pages.py` `class Page`

Declara a página na rota.

| Prop | Tipo | Default | Exemplo |
|------|------|---------|---------|
| `label` | `str` | `None` | `{'label': 'Contas a Receber'}` |
| `type` | `str` | `'crud'` | `{'type': 'crud'}` |
| `props` | `dict` | `{}` | `{'props': {'list': {...}, 'form': {...}}}` |
| `on_show` | `callable` | `None` | `{'on_show': minha_funcao}` |
| `upload` | `dict` | `None` | `{'upload': {'max_size': 5}}` |

#### `props.form` — Formulário

| Prop | Tipo | Exemplo |
|------|------|---------|
| `fields` | `str\|list\|dict` | `'Transacao'`, `['valor','prazo']`, `{'Transacao': ['valor']}` |
| `positions` | `dict` | `{'bar': ['status'], 'footer': ['cancelado'], 'hidden': ['tipo']}` |
| `visible` | `dict` | `{'pedido_id': NOT_EMPTY}` |
| `sessions` | `dict` | `{'Previsões': {'fields': [...], 'table': {...}}}` |
| `template` | `str` | `None` |
| `flash_ok`/`flash_update` | `str` | `{'flash_ok': 'Salvo!'}` |
| `readonly` | `bool\|callable` | `{'readonly': lambda q: q.pedido_id is not None}` |
| `delete` | `bool\|dict\|callable` | `{'delete': {'when': [PedidoItem]}}` |
| `pre_save`/`post_save` | `callable` | `{'pre_save': minha_funcao}` |
| `buttons` | `str\|Button\|list` | `{'buttons': [BTN_SAVE]}` |
| `spacing` | `num` | `{'spacing': 2}` |
| `max_width` | `num` | `{'max_width': 110}` |

**Slots do form** (onde cada campo aparece): `bar` (ícones/tags fora do corpo), `footer` (fora do `<form>`, toggles), `body` (corpo, default), `hidden` (não exibe, não grava). Precedência: `hidden > bar > footer > body`.

#### `props.list` — Listagem

| Prop | Tipo | Exemplo |
|------|------|---------|
| `columns` | `str\|list\|dict` | `'Transacao'`, `['id','nome']`, `{'Transacao': ['*']}` |
| `line`/`card`/`hidden` | `list` | `line: ['id']`, `card: 'Transacao'`, `hidden: ['cancelado']` |
| `order` | `list` | `order: ['vencimento', 'id']` |
| `master` | `str` | `master: 'Previsao'` (inversão pai/linha) |

**Slots da lista**: `line` (sempre na grade, vence `card`), `card` (linha expansória), `hidden` (fora da grade e card). Precedência: `hidden > line > card`.

#### `props.filter` — Painel de filtros

| Prop | Tipo | Exemplo |
|------|------|---------|
| `hidden` | fieldspec | `{'hidden': ['tipo']}` |
| `fixed` | `{campo: operador}` ou `OR`/`AND` | `{'fixed': {'tipo': 'R'}}` |
| `default` | `{campo: valor}` ou `OR`/`AND` | `{'default': {'vencimento': {'preset': 'mes_ano'}}}` |
| `types` | `{tipo: campo\|lista}` | `{'types': {'checklist': 'status'}}` |
| `max_width` | `int`\|string CSS | `{'max_width': 88}` |

Operadores: `=`, `!=`, `>`, `>=`, `<`, `<=`, `like`, `<>`. Em `date`, `>`/`<` compilam inclusivos (`>=`/`<=`); `<>` abre De/Até.

#### `props.report` — ABA Relatórios (PDF por entrada)

| Prop | Tipo | Exemplo |
|------|------|---------|
| `report` | dict | `'Saldo de Contas a Receber': {'report': RECEBER}` |
| `filter` | `{campo: operador}` | `{'filter': {'conta_id': '=', 'vencimento': '<'}}` |

---

### 3.5 `Report` — `ajsystem/defs/report.py` `class Report`

Declara um relatório PDF.

| Prop | Tipo | Default | Exemplo |
|------|------|---------|---------|
| `label` | `str` | — | `{'label': 'Contas a Receber'}` |
| `page_size` | `str` | `'A4'` | `{'page_size': 'A4'}` |
| `orientation` | `str` | `'portrait'` | `{'orientation': 'portrait'}` |
| `lpi` | `int` | `6` | `{'lpi': 6}` |
| `header` | `dict\|list` | `None` | `{'header': [LOGO(), TITLE()]}` |
| `body` | `dict\|ReportBody` | `None` | ver 3.6 |
| `footer` | `bool\|dict` | `None` | `{'footer': True}` |
| `texts` | `dict\|list` | `None` | `{'texts': {...}}` |
| `margin_*` | `num` | `10`/`20`/`10`/`10` | `{'margin_top': 10}` |
| `auto_page_break` | `bool` | `True` | `{'auto_page_break': True}` |
| `show_table_lines` | `bool` | `False` | `{'show_table_lines': True}` |

---

### 3.6 `ReportBody` — `ajsystem/defs/report.py` `class ReportBody`

Declara o corpo do relatório (`Report.body`).

| Prop | Tipo | Exemplo |
|------|------|---------|
| `source` | `str\|dict` | `'Tarefa'` ou `{'select': [...], 'from': 'Tarefa'}` |
| `form`\|`table` | `dict` | `{'table': {...}}` (mutuamente exclusivos) |
| `before`\|`after` | `object` | `{'before': [...]}` |
| `filter` | `dict\|list\|OR\|AND\|callable` | `{'filter': {'tipo': 'R'}}` |
| `order` | `str\|list\|None` | `['vencimento','id']` ou `[1, 3]` (índices 1-based sobre `table.columns`) |
| `levels` | `dict` | `{'pk': 'id', 'parent': 'pai_id'}` |
| `items` | `list` | `['titulo', ('data', {'lf': 1})]` |

---

### 3.7 `ReportColumn` — `ajsystem/defs/report.py` `class ReportColumn`

Declara uma coluna de `body.table.columns`.

| Prop | Tipo | Default | Valores possíveis | Exemplo |
|------|------|---------|-------------------|---------|
| `field` | `str` | — | nome da coluna | `{'field': 'valor'}` |
| `label` | `str` | `None` | texto | `{'label': 'Valor'}` |
| `width` | `float` | `None` | colunas `ch` | `{'width': 12}` |
| `align` | `str` | `'left'` | `left`, `center`, `right` | `{'align': 'right'}` |
| `format` | `str` | `None` | formato data/número | `{'format': 'dd/mm/aaaa'}` |
| `agg` | `str` | `None` | `sum`, `count`, `avg`, `min`, `max` | `{'agg': 'sum'}` |
| `function` | `callable` | `None` | `lambda row:` | `{'function': lambda r: r.valor}` |
| `text` | `str` | `None` | template `'{campo}'`/`{x:02d}` | `{'text': '{tipo:d}. {tipo}'}` |
| `suppress` | `bool` | `False` | `True` | `{'suppress': True}` |
| `pos` | `int` | `POS_ROW` (1) | `POS_NONE` (0), `POS_ROW` (1), `POS_INLINE` (2), `POS_TITLE` (3), `POS_TITLE_CENTER` (4) | `{'pos': POS_INLINE}` |
| `group` | `str` | `None` | `'*'` (grupo/break) ou `'<nome>'` | `{'group': '*'}` |
| `on_start` | `dict` | `None` | `{text, lf, align, style, cpi, pos}` | `{'on_start': {'lf': -1}}` |
| `on_finish` | `dict` | `None` | `{text, footer_text, lf, align, style, cpi, totals}` | `{'on_finish': {'totals': True}}` |
| `totals` | `object` | `None` | `None`, `True`, `dict` | `{'totals': {'align': 'R', 'span': 4}}` |

**`pos` classifica onde o campo aparece no relatório:**
- `POS_ROW` (1, default): coluna da tabela — entra no cabeçalho, define largura/fonte.
- `POS_INLINE` (2): não-coluna, imprime no início da linha sem separação de colunas.
- `POS_TITLE` (3): não-coluna, título do grupo alinhado à esquerda antes do corpo.
- `POS_TITLE_CENTER` (4): não-coluna, título do grupo centralizado.
- `POS_NONE` (0): campo de controle, não sai no relatório.

Exemplo de report agrupado por cliente:

```python
RECEBER = {
    'label': 'Contas a Receber',
    'body': {
        'source': QRECEBER,
        'order': [1, 3],
        'table': {
            'columns': {
                'cliente': {'group': '*', 'pos': POS_INLINE, 'text': '{conta}. {cliente}',
                            'on_start': {'lf': -1}, 'on_finish': {'lf': 1},
                            'totals': {'align': 'R', 'span': 4}},
                'previsto': {'agg': 'sum'},
                'realizado': {'agg': 'sum'},
            },
        },
    },
}
```

---

### 3.8 `ReportGroup` — `ajsystem/defs/report.py` `class ReportGroup`

Configuração de agrupamento (control-break) — usada dentro de `table.columns` via `group: '*'` + `on_start`/`on_finish`.

| Prop | Tipo | Exemplo |
|------|------|---------|
| `field` | `str` | campo chave do grupo |
| `text` | `str\|None` | título/template `'{cliente}'` |
| `on_start` | `dict` | `{'text': ..., 'lf': -1, 'pos': POS_TITLE}` |
| `on_finish` | `dict` | `{'text': ..., 'totals': True}` |
| `pos` | `int` | onde o título é impresso ao abrir |
| `totais` | `None\|True\|dict` | controle de subtotal ao fechar |

> Formatos legados (`on`, `action`, `pos` numérico, `place`, `total`) não são suportados. Use apenas `on_start`/`on_finish/pos/text/lf/totais`.

---

### 3.9 `Button` — `ajsystem/defs/buttons.py` `class Button`

Declara um botão no form.

| Prop | Tipo | Exemplo |
|------|------|---------|
| `type` | `str` | `'save'`, `'delete'`, `'print'`, `'send'` |
| `report` | dict | `{'type': 'print', 'report': REL}` |
| `filter_field` | `str` | `{'type': 'print', 'report': PLANO, 'filter_field': 'tipo'}` |
| `label` | `str` | `{'label': 'Imprimir'}` |
| `icon` | `str` | `{'icon': 'printer'}` |
| `color` | `str` | `{'color': 'info'}` |
| `action` | `str\|callable` | `{'action': 'gerarPrevisoes'}` |
| `enabled` | `dict\|list` | `{'enabled': {'fields': ['valor'], 'mode': 'all_zero'}}` |
| `position` | `str` | `{'position': 'top_left'}` |

Factories comuns: `BTN_SAVE`, `BTN_PRINT`, `BTN_SEND`, `BTN_DELETE`, `BTN_ON_OFF`.

---

### 3.10 `Input` — `ajsystem/defs/inputs.py` `class Input`

Declara um tipo de input do catálogo. Usado indiretamente via `Field.input`.

| Prop | Tipo | Exemplo |
|------|------|---------|
| `name` | `str` | `'text'`, `'number'`, `'date'`, `'select'`, `'toggle'` |
| `input_type` | `str` | `'text'`, `'email'`, `'tel'`, `'password'` |
| `cls` | `str` | classe CSS |
| `size` | `int` | tamanho do input |

---

### 3.11 Constantes úteis — `ajsystem/defs/constants.py`

| Constante | Uso |
|-----------|-----|
| `TODAY()` | data de hoje (default de campos `DATA`) |
| `NOT_EMPTY`, `EMPTY`, `NULL`, `NOT_NULL` | sentinelas de `visible` e `filter` |
| `OR(...)`, `AND(...)` | agrupamento de filtros |
| `POS_NONE`, `POS_ROW`, `POS_INLINE`, `POS_TITLE`, `POS_TITLE_CENTER` | posição de coluna de relatório |
| `MONEY`, `DEFAULT_MONEY` | máscaras de moeda |

---

### 3.12 `Menu` — `app/config.py`

Declara os menus do módulo `SYS` (sistema) e `SITE` (público).

```python
SYS = {
    'type': 'system',
    'default_path': 'cadastro/categorias',
    'menus': {
        'Cadastro': {
            'icon': 'bi-journal',
            'submenus': {
                'Categorias': {'icon': 'bi-journal'},
                'Insumos': {'icon': 'bi-box-seam'},
                'Produtos': {'icon': 'bi-gift'},
                'Contas': {'icon': 'bi-people'},
                'Operações': {'icon': 'bi-tags'},
                'Carteiras': {'icon': 'bi-wallet2'},
            },
        },
        'Comercial': {
            'icon': 'bi-cart',
            'submenus': {
                'Orçamentos': {'icon': 'bi-file-text'},
                'Pedidos': {'icon': 'bi-cart'},
                'Compras': {'icon': 'bi-bag'},
            },
        },
        'Financeiro': {
            'icon': 'bi-cash-stack',
            'submenus': {
                'Recursos': {'icon': 'bi-piggy-bank'},
                'Contas a Receber': {'icon': 'bi-arrow-down-circle', 'page': 'receber'},
                'Contas a Pagar': {'icon': 'bi-arrow-up-circle', 'page': 'pagar'},
                'Recebimentos': {'icon': 'bi-cash'},
                'Pagamentos': {'icon': 'bi-credit-card'},
                'Transferências': {'icon': 'bi-arrow-left-right'},
            },
        },
    },
}
```

Cada submenu com `'page'` aponta para uma rota existente; sem `page`, o nome vira o slug da rota (ex: `'Categorias'` → `/categorias/`).
