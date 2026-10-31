# AJSYSTEM — Manual do Framework

> Vinculado a `ajsystem/version` (`1.26.10.24.0001`) — formato `ciclo.ano.mes.dia.seq`. O bump vem de cada assunto que muda código de `ajsystem/` (não só os dataclasses desta referência; `app/` não entra). A versão do **app hospedeiro** mora em `APP['version']` (`app/config.py`) e quem bumpa é o dev, na mão, com o comando `versao`.

---

## 1. Ordem de leitura do motor

O framework lê o app nesta ordem:

1. **`app/config.py`** — configuração geral, tema e menus (`SYS`, `SITE`, `ADMIN`).
2. **`app/models/*.py`** — model SQLAlchemy + `Entity` (declara campos).
3. **`app/routes/sys/*.py`** — `Schema` (overrides por página) + `Page` (tipo e props: `list`, `form`, `filter`, `report`, `sessions`).
4. **Relatórios** — `Report`, `ReportBody`, `ReportColumn` (PDF).
5. **Auxiliares** — `Tag`, `Lookup`, `Button`, `Input`, constantes.

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

## 3. Configuração geral — `app/config.py`

Lido primeiro pelo motor. Declara tema, módulos e menus.

### `APP` — dicionário raiz

| Chave | Tipo | Exemplo |
|-------|------|---------|
| `name` | `str` | `'AlgoDoce'` |
| `title` | `str` | `'Sistema Gerenciador de Doceria'` |
| `logo` | `str` | `'icons/Logo.png'` |
| `tema` | `str` | `'algodoce'` |
| `version` | `dict` | `{'cycle': 1, 'year': 26, 'month': 10, 'number': 15}` |
| `modules` | `list` | `[SITE, SYS, ADMIN]` |

### `Temas` — paleta de cores

Declara cores para tema DaisyUI compilado pelo motor (`do_themes.py`).

| Grupo | Chaves | Exemplo |
|-------|--------|---------|
| `marca` | `primary`, `secondary` | `primary: '#26A69A'`, `secondary: '#E91E63'` |
| `neutras` | `base-100`, `base-content` | fundo e texto principal |
| `feedback` | `success`, `warning`, `error`, `info` | estados semânticos fixos |
| `apoio` | `accent` | destaque complementar |
| `barras` | `menu`, `submenu`, `form`, `lista`, `rodape` | chrome do app (runtime, sem rebuild) |
| `modal` | `tons`, `tipos` | cores de modal por tipo |

### `SYS` — módulo do sistema

| Chave | Tipo | Exemplo |
|-------|------|---------|
| `type` | `str` | `'system'` |
| `default_path` | `str` | `'cadastro/categorias'` |
| `layout.header.logo` | `dict` | `{'rows': 4, 'align': 'center'}` |
| `layout.header.title` | `dict` | `{'text': 'app_title', 'align': 'center'}` |
| `layout.footer` | `dict` | `{'user': True}` |
| `menus` | `dict` | grupos com submenus e ícones |

Exemplo de menu:

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

---

## 4. Model + Entity — `app/models/*.py`

Lido depois do config. Declara o model SQLAlchemy e o dicionário `Entity` (única fonte de campos).

### `Entity`

Dicionário `{nome_campo: {config}}`. Cada chave é um campo do model; o valor são as props do `Field`.

| Prop | Tipo | Declarações possíveis | Exemplo |
|------|------|----------------------|---------|
| `type` | `str` | `TEXT`, `MEMO`, `INT`, `NUM`, `PERCENT`, `PK`, `ID`, `DK`, `FK`, `DATA`, `DATA_HORA`, `HORA`, `BOOL`, `FONE`, `CPF`, `CNPJ`, `LIST`, `MULT10`, `IMAGE` | `{'type': 'NUM', 'mask': MVALOR}` |
| `label` | `str` | texto ou `None` (usa `_auto_label(name)`) | `{'label': 'Valor (R$)'}` |
| `width` | `int` | colunas `ch` (ex: `6` ID, `12` NUM, `20` TEXT) | `{'width': 12}` |
| `align` | `str` | `left`, `center`, `right` (`NUM` → `right` automático) | `{'align': 'right'}` |
| `input` | `str` | nome do `Input` do catálogo (`text`, `number`, `date`, `select`, `textarea`, `email`, `tel`, `password`, `checkbox`, `toggle`, `multi`, `image`) | `{'input': 'toggle'}` |
| `input_props` | `dict` | override parcial do input neste campo | `{'input_props': {'cls': 'x'}}` |
| `options` | `dict` | `{valor: rótulo}` para `LIST`/`MULT10` | `{'options': {0: 'Pagar', 1: 'Receber'}}` |
| `mask` | `str` | máscara de exibição (ver abaixo) | `{'mask': MVALOR}` |
| `placeholder` | `str` | texto de ajuda | `{'placeholder': 'Digite aqui'}` |
| `decimals` | `int` | `0` int, `2` moeda | `{'decimals': 2}` |
| `min`/`max`/`step` | `num` | limites numéricos | `{'min': 0, 'step': 1}` |
| `percent` | `bool` | `True` → sufixo `%` | `{'percent': True}` |
| `required` | `bool` | `True` → `*` no label e `required` no input | `{'required': True}` |
| `disabled` | `bool\|callable` | `True` ou `callable(row)->bool` | `{'disabled': True}` |
| `readonly` | `bool` | rótulo + hidden; valor ainda vai no POST | `{'readonly': True}` |
| `hidden` | `bool` | `<input type=hidden>`, enviado mas não exibido | `{'hidden': True}` |
| `default` | `any\|callable` | `TODAY`, `lambda: 1` | `{'default': TODAY}` |
| `rows` | `int` | altura textarea (`MEMO`) | `{'rows': 4}` |
| `lookup` | `bool\|dict\|Lookup` | `True` ou `{display, fields, value, when, query}` | `{'lookup': {'model': 'Conta', 'display': 'nome'}}` |
| `validate` | `str` | `cpf`, `cnpj`, `placa` | `{'validate': 'cpf'}` |
| `help` | `str\|list` | texto de ajuda | `{'help': 'Informe o CPF'}` |
| `on_set` | `dict` | `{replaces: {campo: fonte}, disables: [...]}` | `{'on_set': {'disables': ['cnpj']}}` |
| `calc` | `str\|callable\|dict` | `'qtd*preco'`, `lambda row:`, `{'type':'agg',...}`, `{'type':'call',...}` | `{'calc': 'previsto - (realizado or 0)'}` |
| `carry` | `str` | campo origem no map do botão | `{'carry': 'conta_id'}` |
| `memory` | `bool` | `True` → só de tela, não persiste | `{'memory': True}` |
| `tag` | `dict\|Tag` | `{colors, color, link, size, preset, text_field, outline, cls}` | `{'tag': {'link': 'pedidos.form', 'color': 'info'}}` |

#### `type` — tipo do campo (obrigatório)

| Valor | Input padrão | Máscara padrão | Uso |
|-------|-------------|----------------|-----|
| `TEXT` | `text` | — | texto livre |
| `MEMO` | `textarea` | — | texto multilinha |
| `INT` | `number` | inteiro | inteiro sem casas |
| `NUM` | `number` | decimal com `decimals` | número decimal |
| `PERCENT` | `number` | sufixo `%` | percentual |
| `PK`/`ID` | oculto | — | chave primária |
| `DK` | oculto | — | chave derivada |
| `FK` | `select`/modal | — | chave estrangeira (`lookup` obrigatório) |
| `DATA` | `date` | `dd/mm/aaaa` | data |
| `DATA_HORA` | `datetime` | `dd/mm/aaaa HH:MM` | data e hora |
| `HORA` | `time` | `HH:MM` | hora |
| `BOOL` | `checkbox`/`toggle` | — | booleano |
| `FONE` | `tel` | `@R 999.999.999-99` | telefone |
| `CPF` | `text` | `@R 999.999.999-99` | CPF |
| `CNPJ` | `text` | `@R 99.999.999/0001-99` | CNPJ |
| `LIST` | `select` | — | lista de `options` |
| `MULT10` | `multi` | — | múltipla seleção |
| `IMAGE` | `image` | — | upload de imagem |

**Declarações possíveis:**
```python
{'type': 'TEXT', 'required': True, 'width': 20}
{'type': 'NUM', 'mask': MVALOR, 'decimals': 2}
{'type': 'FK', 'lookup': {'model': 'Conta', 'display': 'nome'}}
{'type': 'DATA', 'default': TODAY}
{'type': 'BOOL', 'input': 'toggle'}
```

#### `mask` — máscara de exibição

**Não existe prop `currency`.** A moeda sai da `mask` via comando `@M(id)`.

Comandos de texto: `@U` (maiúsculo), `@L` (minúsculo), `@C` (capitalizado), `@T` (título case), `@R` (apenas dígitos).
Comando de moeda: `@M(id)` onde `id` é o identificador (ex: `@M(BRL)`).
Padrão numérico: `0` = dígito obrigatório, `9` = dígito opcional, `,` = milhar, `.` = decimal.

| Máscara | Significado |
|---------|-------------|
| `@M(BRL) 999,999.99` | moeda BRL com milhar e 2 decimais |
| `@M(BRL) 9,99` | moeda BRL simplificada |
| `@M(USD) 999,999.99` | moeda USD |
| `dd/mm/aaaa` | data brasileira |
| `dd/mm/aaaa HH:MM` | data e hora |
| `HH:MM` | hora |
| `@R 999.999.999-99` | CPF/CNPJ apenas dígitos |
| `@T` | título case |
| `999,99` | numérico com 2 decimais, sem símbolo |
| `@U 999,99` | maiúsculo + numérico |

> `@M(id)` e comandos de texto (`@U`, `@L`, `@C`, `@T`, `@R`) podem ser combinados. `@M` e padrão numérico (`999,99`) não se misturam na mesma máscara.

**Exemplos:**
```python
{'type': 'NUM', 'mask': MVALOR, 'decimals': 2}          # MVALOR = '@M(BRL) 999,999.99'
{'type': 'DATA', 'mask': 'dd/mm/aaaa'}
{'type': 'CPF', 'mask': '@R 999.999.999-99'}
{'type': 'TEXT', 'mask': '@U'}
{'type': 'NUM', 'mask': '999,99', 'decimals': 2}
```

#### `lookup` — configuração de FK

Para campos `FK`. O model alvo é inferido do FK automaticamente (**não existe `Lookup.model`**).

| Sub-prop | Tipo | Exemplo |
|----------|------|---------|
| `display` | `str` | campo exibido (`'nome'`) |
| `fields` | `str\|list` | campos retornados (`['nome']`) |
| `value` | `str` | campo gravado (`'id'`) |
| `when` | `str\|dict\|callable` | filtro das opções (`{'ativo': True}`) |
| `query` | `str` | busca declarada na rota (`'PREVISOES'`) |

```python
{'lookup': {'model': 'Conta', 'display': 'nome', 'fields': ['nome']}}
{'lookup': {'display': 'nome', 'when': {'ativo': True}}}
{'lookup': True}  # defaults, alvo inferido do FK
{'lookup': {'query': 'PREVISOES'}}
```

#### `calc` — campo calculado

| Forma | Exemplo | Efeito |
|-------|---------|--------|
| `str` | `'qtd * preco'` | expressão avaliada no cliente |
| `callable` | `lambda row: row.valor * 2` | função Python (virtual, não persiste) |
| `dict` | `{'type': 'agg', 'source': 'sum(Item.valor)'}` | agregado SQL (coluna real) |
| `dict` | `{'type': 'call', 'source': 'calc_status'}` | callable do model |

```python
{'calc': 'previsto - (realizado or 0)'}
{'calc': lambda row: row.qtd * row.preco}
{'calc': {'type': 'agg', 'source': 'sum(Previsao.previsto)'}}
{'calc': {'type': 'call', 'source': 'calc_status'}}
```

> Um `calc` de tipo `property` do model **não pode ser persistido**. Use `calc` virtual (`str` ou `callable`) ou `memory: True`.

#### `tag` — etiqueta visual (usa dataclass `Tag`, seção 5)

| Sub-prop | Tipo | Exemplo |
|----------|------|---------|
| `colors` | `{valor: cor}` | `{True: 'success', False: 'warning'}` |
| `color` | `str` | `'info'` |
| `link` | `str\|callable` | `'pedidos.form'` |
| `size` | `str` | `'sm'` |
| `outline` | `bool` | `True` |
| `preset` | `str` | `'boolean'`, `'ativo'`, `'status'` |
| `text_field` | `str` | `'status_label'` |
| `cls` | `str` | `'badge-pill'` |

```python
{'tag': {'colors': {True: 'success'}, 'link': 'receber.form'}}
{'tag': {'preset': 'ativo', 'color': 'primary'}}
```

**Exemplo completo de Entity:**
```python
Entity = {
    'id':           {'type': 'ID', 'width': 6},
    'nome':         {'type': 'TEXT', 'required': True, 'width': 20, 'mask': '@T'},
    'valor':        {'type': 'NUM', 'label': 'Valor', 'required': True, 'mask': MVALOR},
    'preco':        {'type': 'NUM', 'label': 'Preço', 'mask': MVALOR, 'calc': 'divide(valor, qtd_minima)'},
    'categoria_id': {'type': 'FK', 'label': 'Categoria', 'width': 12},
    'ativo':        {'type': 'BOOL', 'input': 'toggle'},
    'imagem':       {'type': 'IMAGE'},
    'descricao':    {'type': 'MEMO', 'label': 'Descrição', 'rows': 4},
}
```

---

## 5. Rota + Schema + Page — `app/routes/sys/*.py`

Lido depois do model. Declara `Schema` (overrides de Entity por página) e `Page` (tipo e props).

### `Schema`

Dicionário `{NomeEntidade: {campo: {overrides}}}`. Schema vence sobre Entity.

```python
Schema = {
    'Produto': {
        'valor': {'readonly': True},
        'ativo': {'input': 'toggle'},
    },
}
```

### `Page`

Declara o tipo da página e seus props.

| Prop | Tipo | Default | Declarações possíveis | Exemplo |
|------|------|---------|----------------------|---------|
| `label` | `str` | `None` | título da página | `{'label': 'Produto'}` |
| `type` | `str` | `'crud'` | `crud`, `redirect`, `cart`, `showcase`, `contacts`, `custom` | `{'type': 'crud'}` |
| `props` | `dict` | `{}` | `{list, form, filter, report, sessions, scripts}` | `{'props': {...}}` |
| `on_show` | `callable` | `None` | hook ao renderizar | `{'on_show': fn}` |
| `upload` | `dict` | `None` | política de upload | `{'upload': {'max_size': 5}}` |

#### `props.form` — Formulário

| Sub-prop | Tipo | Declarações possíveis | Exemplo |
|----------|------|----------------------|---------|
| `fields` | `str\|list\|dict` | `'Ent'`, `['c1','c2']`, `{'Ent': ['c1']}` | `'Transacao'`, `['valor','prazo']` |
| `positions` | `dict` | `{bar, footer, body, hidden}` | `{'bar': ['status'], 'hidden': ['tipo']}` |
| `visible` | `dict` | `{campo: cond}` | `{'pedido_id': NOT_EMPTY}` |
| `sessions` | `dict` | `{Nome:{fields,table,...}}` | `{'Previsões': {'fields': [...]}}` |
| `template` | `str` | `None` | caminho alternativo | `{'template': 'custom.html'}` |
| `flash_ok`/`flash_update` | `str` | mensagem de sucesso | `{'flash_ok': 'Salvo!'}` |
| `readonly` | `bool\|callable` | `False` ou callable | `{'readonly': lambda q: q.pedido_id}` |
| `delete` | `bool\|dict\|callable` | `False`, `{'when': [...]}` | `{'delete': {'when': [PedidoItem]}}` |
| `pre_save`/`post_save` | `callable` | `None` | `{'pre_save': fn}` | |
| `buttons` | `str\|Button\|list` | tipos ou instâncias | `{'buttons': [BTN_SAVE]}` |
| `spacing` | `num` | gap entre campos | `{'spacing': 2}` |
| `max_width` | `num` | largura máxima | `{'max_width': 110}` |

**Slots do form** (onde cada campo aparece): `bar` (ícones/tags fora do corpo), `footer` (fora do `<form>`, toggles), `body` (corpo, default), `hidden` (não exibe, não grava). Precedência: `hidden > bar > footer > body`.

#### `props.list` — Listagem

| Sub-prop | Tipo | Declarações possíveis | Exemplo |
|----------|------|----------------------|---------|
| `columns` | `str\|list\|dict` | `'Ent'`, `['c1','c2']`, `{'Ent': ['*']}` | `'Transacao'`, `['id','nome']` |
| `line`/`card`/`hidden` | `list` | campos por slot | `line: ['id']`, `card: 'Transacao'` |
| `order` | `list` | ordem de classificação | `order: ['vencimento', 'id']` |
| `master` | `str` | entidade pai (inversão) | `master: 'Previsao'` |

**Slots da lista**: `line` (sempre na grade, vence `card`), `card` (linha expansória), `hidden` (fora da grade e card). Precedência: `hidden > line > card`.

#### `props.filter` — Painel de filtros

| Sub-prop | Tipo | Declarações possíveis | Exemplo |
|----------|------|----------------------|---------|
| `hidden` | fieldspec | campos ocultos do painel | `{'hidden': ['tipo']}` |
| `fixed` | `{campo: op}` ou `OR`/`AND` | `WHERE` fixo | `{'fixed': {'tipo': 'R'}}` |
| `default` | `{campo: val}` ou `OR`/`AND` | filtro inicial editável | `{'default': {'vencimento': {'preset': 'mes_ano'}}}` |
| `types` | `{tipo: campo\|lista}` | override do tipo de widget | `{'types': {'checklist': 'status'}}` |
| `max_width` | `int\|string CSS` | cap de largura | `{'max_width': 88}` |

Operadores: `=`, `!=`, `>`, `>=`, `<`, `<=`, `like`, `<>`. Em `date`, `>`/`<` compilam inclusivos (`>=`/`<=`); `<>` abre De/Até.

#### `props.report` — ABA Relatórios (PDF por entrada)

| Sub-prop | Tipo | Declarações possíveis | Exemplo |
|----------|------|----------------------|---------|
| `report` | dict | spec do relatório | `{'report': RECEBER}` |
| `filter` | `{campo: operador}` | campos/operadores do formulário | `{'filter': {'conta_id': '=', 'vencimento': '<'}}` |

#### `props.scripts` — Scripts JS da página

Lista de nomes de arquivos JS estáticos.

```python
'scripts': ['previsoes', 'rel/gerar']
```

---

## 6. Relatório — `app/reports/*.py`

Lido quando a página tem aba `Report`. Declara `Report`, `ReportBody`, `ReportColumn` (PDF).

### `Report` — `ajsystem/defs/report.py` `class Report`

| Prop | Tipo | Default | Declarações possíveis | Exemplo |
|------|------|---------|----------------------|---------|
| `label` | `str` | — | título | `{'label': 'Contas a Receber'}` |
| `page_size` | `str` | `'A4'` | `'A4'`, `'Letter'` | `{'page_size': 'A4'}` |
| `orientation` | `str` | `'portrait'` | `'portrait'`, `'landscape'` | `{'orientation': 'portrait'}` |
| `lpi` | `int` | `6` | `6` (4,23mm/linha) ou `8` (3,17mm) | `{'lpi': 6}` |
| `header` | `dict\|list` | `None` | `[LOGO(), TITLE()]` | `{'header': [...]}` |
| `body` | `dict\|ReportBody` | `None` | ver `ReportBody` | `{'body': {...}}` |
| `footer` | `bool\|dict` | `None` | `True` ou `{show_user, ...}` | `{'footer': True}` |
| `texts` | `dict\|list` | `None` | blocos de texto | `{'texts': {...}}` |
| `margin_top/bottom/left/right` | `num` | `10`/`20`/`10`/`10` | mm | `{'margin_top': 10}` |
| `auto_page_break` | `bool` | `True` | quebra automática | `{'auto_page_break': True}` |
| `show_table_lines` | `bool` | `False` | grade da tabela | `{'show_table_lines': True}` |

### `ReportBody` — `ajsystem/defs/report.py` `class ReportBody`

Declara o corpo do relatório (`Report.body`).

| Prop | Tipo | Declarações possíveis | Exemplo |
|------|------|----------------------|---------|
| `source` | `str\|dict` | `'Ent'` ou `{'select': [...], 'from': 'Ent'}` | `'Tarefa'`, `{'select': [...], 'from': 'Tarefa'}` |
| `form`\|`table` | `dict` | um só dos dois | `{'table': {...}}` (mutuamente exclusivos) |
| `before`\|`after` | `object` | blocos antes/depois | `{'before': [...]}` |
| `filter` | `dict\|list\|OR\|AND\|callable` | filtro padrão | `{'filter': {'tipo': 'R'}}` |
| `order` | `str\|list\|None` | nomes ou índices 1-based | `['vencimento','id']` ou `[1, 3]` |
| `levels` | `dict` | numeração hierárquica | `{'pk': 'id', 'parent': 'pai_id'}` |
| `items` | `list` | itens inline antes da tabela | `['titulo', ('data', {'lf': 1})]` |

### `ReportColumn` — `ajsystem/defs/report.py` `class ReportColumn`

Declara uma coluna de `body.table.columns`.

| Prop | Tipo | Default | Declarações possíveis | Exemplo |
|------|------|---------|----------------------|---------|
| `field` | `str` | — | nome da coluna | `{'field': 'valor'}` |
| `label` | `str` | `None` | texto do cabeçalho | `{'label': 'Valor'}` |
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

- `POS_ROW` (1, default): **coluna da tabela** — entra no cabeçalho, define largura/fonte. É o único que consome coluna da grade.
- `POS_INLINE` (2): **não-coluna**, imprime no início da linha da tabela sem separação de colunas.
- `POS_TITLE` (3): **não-coluna**, título do grupo alinhado à esquerda, antes do corpo da tabela.
- `POS_TITLE_CENTER` (4): **não-coluna**, título do grupo centralizado, antes do corpo da tabela.
- `POS_NONE` (0): **campo de controle**, não sai no relatório (não entra na grade, não imprime).

O motor classifica as colunas antes de imprimir: apenas `POS_ROW` entra na grade da tabela. `POS_INLINE`/`POS_TITLE*` são impressos fora da grade (linha/título do grupo). `POS_NONE` não imprime.

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

## 7. Componentes auxiliares

### `Tag` — `ajsystem/defs/tags.py` `class Tag`

Usado na prop `tag` de `Field`. Renderiza um badge/pill ao lado do valor.

| Sub-prop | Tipo | Valores possíveis | Exemplo |
|----------|------|-------------------|---------|
| `colors` | `dict` | `{valor: cor}` (cor ∈ `ghost`, `primary`, `success`, `warning`, `error`, `info`, `0-9`) | `{'colors': {True: 'success', False: 'warning'}}` |
| `color` | `str` | cor fixa | `{'color': 'info'}` |
| `link` | `str\|callable` | `'pedidos.form'` ou `lambda row: 'pagar.form'` | `{'link': 'receber.form'}` |
| `size` | `str` | `sm` (default) | `{'size': 'sm'}` |
| `outline` | `bool` | `True` → estilo outline | `{'outline': True}` |
| `preset` | `str` | `boolean`, `ativo`, `status` | `{'preset': 'ativo'}` |
| `text_field` | `str` | campo de onde vem o rótulo exibido | `{'text_field': 'status_label'}` |
| `cls` | `str` | classe CSS extra concatenada | `{'cls': 'badge-pill'}` |

```python
{'tag': {'colors': {True: 'success', False: 'warning'}, 'link': 'receber.form'}}
{'tag': {'preset': 'ativo', 'color': 'primary'}}
{'tag': {'size': 'sm', 'outline': True, 'cls': 'badge-pill'}}
```

### `Lookup` — `ajsystem/defs/data.py` `class Lookup`

Usado na prop `lookup` de `Field` (FK). **Não existe `Lookup.model`** — o model alvo é inferido do FK automaticamente.

| Sub-prop | Tipo | Default | Declarações possíveis | Exemplo |
|----------|------|---------|----------------------|---------|
| `display` | `str` | 1º campo após `id` do alvo | nome do campo exibido | `{'display': 'nome'}` |
| `fields` | `str\|list` | `[display]` | `'nome'` ou `['nome', 'documento']` | `{'fields': ['nome']}` |
| `value` | `str` | `'id'` | campo gravado no banco | `{'value': 'id'}` |
| `when` | `str\|dict\|callable` | `None` | filtro das opções | `{'when': {'ativo': True}}` |
| `query` | `str` | `None` | busca declarada na rota | `{'query': 'PREVISOES'}` |

```python
{'lookup': {'model': 'Conta', 'display': 'nome', 'fields': ['nome']}}
{'lookup': {'display': 'nome', 'when': {'ativo': True}}}
{'lookup': True}  # defaults, alvo inferido do FK
{'lookup': {'query': 'PREVISOES'}}
```

### `Button` — `ajsystem/defs/buttons.py` `class Button`

Declara um botão no form.

| Prop | Tipo | Declarações possíveis | Exemplo |
|------|------|----------------------|---------|
| `type` | `str` | `'save'`, `'delete'`, `'print'`, `'send'` | `{'type': 'print'}` |
| `report` | dict | spec do relatório | `{'report': REL}` |
| `filter_field` | `str` | campo de filtro | `{'filter_field': 'tipo'}` |
| `label` | `str` | texto do botão | `{'label': 'Imprimir'}` |
| `icon` | `str` | ícone Bootstrap | `{'icon': 'printer'}` |
| `color` | `str` | cor do botão | `{'color': 'info'}` |
| `action` | `str\|callable` | ação JS ou Python | `{'action': 'gerarPrevisoes'}` |
| `enabled` | `dict\|list` | condição de ativação | `{'enabled': {'fields': ['valor'], 'mode': 'all_zero'}}` |
| `position` | `str` | posição no form | `{'position': 'top_left'}` |

Factories comuns: `BTN_SAVE`, `BTN_PRINT`, `BTN_SEND`, `BTN_DELETE`, `BTN_ON_OFF`.

### `Input` — `ajsystem/defs/inputs.py` `class Input`

Declara um tipo de input do catálogo. Usado indiretamente via `Field.input`.

| Prop | Tipo | Declarações possíveis | Exemplo |
|------|------|----------------------|---------|
| `name` | `str` | `'text'`, `'number'`, `'date'`, `'select'`, `'toggle'` | `'text'` |
| `input_type` | `str` | `'text'`, `'email'`, `'tel'`, `'password'` | `'email'` |
| `cls` | `str` | classe CSS | `'meu-input'` |
| `size` | `int` | tamanho do input | `9` |

### Constantes úteis — `ajsystem/defs/constants.py`

| Constante | Uso |
|-----------|-----|
| `TODAY()` | data de hoje (default de campos `DATA`) |
| `NOT_EMPTY`, `EMPTY`, `NULL`, `NOT_NULL` | sentinelas de `visible` e `filter` |
| `OR(...)`, `AND(...)` | agrupamento de filtros |
| `POS_NONE`, `POS_ROW`, `POS_INLINE`, `POS_TITLE`, `POS_TITLE_CENTER` | posição de coluna de relatório |
| `MONEY`, `DEFAULT_MONEY` | máscaras de moeda |


```python
Page = {
    'label': 'Conta a Receber',
    'type': 'crud',
    'props': {
        'list': {
            'columns': 'Transacao',
            'master': 'Previsao',
            'line': ['pedido_id'],
            'hidden': ['cancelado', 'tipo'],
            'card': 'Transacao',
            'order': ['vencimento', 'id'],
        },
        'filter': {
            'fixed': {'tipo': 'R'},
            'types': {'checklist': 'status'},
            'default': OR(
                {'data': {'preset': 'mes_ano'}},
                {'vencimento': {'preset': 'mes_ano'}},
                {'saldo': {'mode': 'maior_que', 'val1': 0}},
            ),
        },
        'report': {
            'Saldo de Contas a Receber': {
                'filter': {'conta_id': '=', 'vencimento': ('<', TODAY())},
                'report': RECEBER,
            },
        },
        'form': {
            'max_width': 110,
            'fields': 'Transacao',
            'positions': {
                'bar': ['status'],
                'footer': ['cancelado'],
                'hidden': ['valor', 'prazo', 'variacao', 'saldo', 'tipo', 'compra_id', 'pedido_id'],
            },
        },
    },
}
```



### `SITE` — módulo público

Mesma estrutura de `SYS`, com `type: 'public'` e `default_path` para a loja virtual.

### `ADMIN` — módulo administrativo

`type: 'admin'`, `default_path: 'seguranca.painel'`, menus vazios (painel gerado pelo motor).

