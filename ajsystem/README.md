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

Declara um campo na `Entity`/`Schema`. Cada prop abaixo pode ser declarada isoladamente ou combinada com outras.

#### `type` — tipo do campo (obrigatório)

Define o input do catálogo e a máscara padrão. Valores:

| Valor | Input padrão | Máscara padrão | Uso |
|-------|-------------|----------------|-----|
| `TEXT` | `text` | — | texto livre |
| `MEMO` | `textarea` | — | texto multilinha (`rows`) |
| `INT` | `number` | numérico inteiro | inteiro sem casas |
| `NUM` | `number` | numérico com `decimals` | número decimal |
| `PERCENT` | `number` | sufixo `%` | percentual |
| `PK`/`ID` | oculto | — | chave primária (não exibe) |
| `DK` | oculto | — | chave derivada (não exibe) |
| `FK` | `select` ou modal | — | chave estrangeira (`lookup` obrigatório) |
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

#### `label` — rótulo do campo

Texto exibido no cabeçalho da coluna/lista e do form. Se ausente, usa `_auto_label(name)` (converte `snake_case` em Título).

```python
{'label': 'Valor (R$)'}
{'label': 'Data de Vencimento'}
```

#### `width` — largura em colunas `ch`

Define a largura do campo na tela. Valores típicos: `6` (ID), `12` (NUM/DATA), `20` (TEXT), `30` (nome).

```python
{'width': 12}
{'width': 20}
```

#### `align` — alinhamento

| Valor | Efeito |
|-------|--------|
| `left` | alinha à esquerda (default) |
| `center` | centraliza |
| `right` | alinha à direita (automático para `NUM`) |

```python
{'align': 'right'}
```

#### `input` — tipo de input do catálogo

Sobrescreve o input padrão do `type`. Valores: `text`, `number`, `date`, `select`, `textarea`, `email`, `tel`, `password`, `checkbox`, `toggle`, `multi`, `image`.

```python
{'type': 'BOOL', 'input': 'toggle'}
{'type': 'TEXT', 'input': 'email'}
```

#### `input_props` — override parcial do input

Merge raso sobre as props do `Input` resolvido para este campo apenas. Última camada do merge (vence app e rota).

```python
{'input_props': {'cls': 'meu-campo', 'size': 9}}
```

#### `options` — catálogo de `LIST`/`MULT10`

Dicionário `{valor: rótulo}`.

```python
{'type': 'LIST', 'options': {0: 'Pagar', 1: 'Receber', 2: 'Cancelado'}}
{'type': 'MULT10', 'options': {'A': 'Item A', 'B': 'Item B'}}
```

#### `mask` — máscara de exibição

**Não existe prop `currency`.** A moeda sai da `mask` via comando `@M(id)`. A máscara é uma string que pode combinar:

- **Comandos de texto:** `@U` (maiúsculo), `@L` (minúsculo), `@C` (capitalizado), `@T` (título case), `@R` (apenas dígitos).
- **Comando de moeda:** `@M(id)` onde `id` é o identificador da máscara de moeda (ex: `@M(BRL)`).
- **Padrão numérico:** `0` = dígito obrigatório, `9` = dígito opcional, `,` = milhar, `.` = decimal.

**Declarações possíveis de `mask`:**

| Máscara | Significado | Pode combinar com |
|---------|-------------|-------------------|
| `@M(BRL) 999,999.99` | moeda BRL com milhar e 2 decimais | `@U`, `@L`, `@C` (texto antes/ depois) |
| `@M(BRL) 9,99` | moeda BRL simplificada | `@U`, `@L` |
| `@M(USD) 999,999.99` | moeda USD | `@U`, `@L` |
| `dd/mm/aaaa` | data brasileira | — (não combina com `@M`) |
| `dd/mm/aaaa HH:MM` | data e hora | — (não combina com `@M`) |
| `HH:MM` | hora | — (não combina com `@M`) |
| `@R 999.999.999-99` | CPF/CNPJ apenas dígitos | `@U`, `@L` (não tem efeito prático) |
| `@T` | título case | — (comando de texto isolado) |
| `999,99` | numérico com 2 decimais, sem símbolo | `@U`, `@L`, `@C` |
| `@U 999,99` | maiúsculo + numérico | — |
| `@L nome` | minúsculo | — |

**Exemplos de declaração completa:**
```python
{'type': 'NUM', 'mask': MVALOR, 'decimals': 2}          # MVALOR = '@M(BRL) 999,999.99'
{'type': 'DATA', 'mask': 'dd/mm/aaaa'}
{'type': 'CPF', 'mask': '@R 999.999.999-99'}
{'type': 'TEXT', 'mask': '@U'}
{'type': 'NUM', 'mask': '999,99', 'decimals': 2}
{'type': 'NUM', 'mask': '@M(BRL) 999,999.99', 'decimals': 2}
```

> A máscara vence a inferência por `type`. Precedência: `explícita (mask) > catálogo do input > numérico de decimals`. `@M(id)` e comandos de texto (`@U`, `@L`, `@C`, `@T`, `@R`) podem ser combinados na mesma string; `@M` e padrão numérico (ex: `999,99`) não se misturam na mesma máscara.

#### `placeholder` — texto de ajuda no input

```python
{'placeholder': 'Digite o CPF'}
{'placeholder': '00/00/0000'}
```

#### `decimals` — casas decimais

| Valor | Efeito |
|-------|--------|
| `0` | número inteiro |
| `2` | moeda/decimal com 2 casas (default para `NUM`) |

```python
{'decimals': 2}
{'decimals': 0}
```

#### `min` / `max` / `step` — limites numéricos

Valores numéricos. Aplicados ao input `number`.

```python
{'min': 0, 'max': 100, 'step': 1}
{'min': 0.01, 'step': 0.01}
```

#### `percent` — sufixo `%`

| Valor | Efeito |
|-------|--------|
| `True` | exibe sufixo `%` |

```python
{'percent': True}
```

#### `required` — campo obrigatório

| Valor | Efeito |
|-------|--------|
| `True` | exibe `*` no label, atributo `required` no input, bloqueia `POST` vazio |

```python
{'required': True}
```

#### `disabled` — desabilita input

Aceita `True` ou `callable(row) -> bool`.

```python
{'disabled': True}
{'disabled': lambda row: row.status == 8}
```

#### `readonly` — somente leitura

Renderiza rótulo + `<input type=hidden>`. O valor **ainda vai no POST** e é gravado.

```python
{'readonly': True}
```

#### `hidden` — campo oculto

Renderiza `<input type=hidden>`. Enviado no POST, não exibido na tela. Não entra na expansão automática de listagem/filtro.

```python
{'hidden': True}
```

#### `default` — valor inicial

Aceita literal ou callable. Aplicado quando o valor é `None` no `POST`.

```python
{'default': TODAY}          # date.today()
{'default': lambda: 1}
{'default': 'R'}
```

#### `rows` — altura do textarea (`MEMO`)

```python
{'rows': 4}
{'rows': 6}
```

#### `lookup` — configuração de FK

Para campos `FK`. Define o model alvo, campo de exibição e filtro. **Não existe `Lookup.model`** — o model alvo é inferido do FK.

| Sub-prop | Tipo | Exemplo |
|----------|------|---------|
| `display` | `str` | campo exibido (`'nome'`) |
| `fields` | `str\|list` | campos retornados (`['nome']`) |
| `value` | `str` | campo gravado (`'id'`) |
| `when` | `str\|dict\|callable` | filtro das opções (`{'ativo': True}`) |
| `query` | `str` | nome de busca declarada na rota (`'PREVISOES'`) |

```python
{'lookup': {'model': 'Conta', 'display': 'nome', 'fields': ['nome']}}
{'lookup': {'display': 'nome', 'when': {'ativo': True}}}
{'lookup': True}  # defaults, alvo inferido do FK
{'lookup': {'query': 'PREVISOES'}}
```

#### `validate` — validação client/servidor

| Valor | Efeito |
|-------|--------|
| `cpf` | valida CPF |
| `cnpj` | valida CNPJ |
| `placa` | valida placa de veículo |

```python
{'validate': 'cpf'}
{'validate': 'cnpj'}
```

#### `help` — texto de ajuda

Exibe botão `?` com o texto.

```python
{'help': 'Informe o CPF do cliente'}
{'help': ['Linha 1', 'Linha 2']}
```

#### `on_set` — reações em runtime

Executa quando o campo muda no cliente.

| Sub-prop | Tipo | Exemplo |
|----------|------|---------|
| `replaces` | `{campo: fonte}` | copia valor de outro campo |
| `disables` | `list` | desabilita campos (`['cnpj', 'cnpj']`) |

```python
{'on_set': {'disables': ['cnpj', 'insc_estadual']}}
{'on_set': {'replaces': {'documento': 'numero'}}}
```

#### `calc` — campo calculado

Aceita três formas:

| Forma | Exemplo | Efeito |
|-------|---------|--------|
| `str` | `'qtd * preco'` | expressão avaliada no cliente |
| `callable` | `lambda row: row.valor * 2` | função Python (virtual, não persiste) |
| `dict` | `{'type': 'agg', 'source': 'sum(Item.valor)'}` | agregado SQL (persiste como coluna real) |
| `dict` | `{'type': 'call', 'source': 'calc_status'}` | callable do model |

```python
{'calc': 'previsto - (realizado or 0)'}
{'calc': lambda row: row.qtd * row.preco}
{'calc': {'type': 'agg', 'source': 'sum(Previsao.previsto)'}}
{'calc': {'type': 'call', 'source': 'calc_status'}}
```

> Um `calc` de tipo `property` do model **não pode ser persistido**. Use `calc` virtual (`str` ou `callable`) ou `memory: True`.

#### `carry` — origem do valor no botão

Nome do campo de origem no map do botão.

```python
{'carry': 'conta_id'}
{'carry': 'valor'}
```

#### `memory` — campo só de tela

| Valor | Efeito |
|-------|--------|
| `True` | renderiza/editável, não persiste, não entra na expansão automática |

```python
{'memory': True}
```

> O campo `memory` só aparece onde citado explicitamente — `session.fields` ou bloco `MEMORY` do Schema.

#### `tag` — etiqueta visual

Usa a dataclass `Tag` (seção 3.2).

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

---

### 3.2 `Tag` — `ajsystem/defs/tags.py` `class Tag`

Usado na prop `tag` de `Field`. Renderiza um badge/pill ao lado do valor.

| Sub-prop | Tipo | Valores possíveis | Exemplo |
|----------|------|-------------------|---------|
| `colors` | `dict` | `{valor: cor}` onde cor ∈ `ghost`, `primary`, `success`, `warning`, `error`, `info` ou `0-9` | `{'colors': {True: 'success', False: 'warning'}}` |
| `color` | `str` | cor fixa | `{'color': 'info'}` |
| `link` | `str\|callable` | `'pedidos.form'` ou `lambda row: 'pagar.form'` | `{'link': 'receber.form'}` |
| `size` | `str` | `sm` (default) | `{'size': 'sm'}` |
| `outline` | `bool` | `True` → estilo outline | `{'outline': True}` |
| `preset` | `str` | `boolean`, `ativo`, `status` | `{'preset': 'ativo'}` |
| `text_field` | `str` | campo de onde vem o rótulo exibido | `{'text_field': 'status_label'}` |
| `cls` | `str` | classe CSS extra concatenada | `{'cls': 'badge-pill'}` |

**Declarações possíveis:**
```python
{'tag': {'colors': {True: 'success', False: 'warning'}, 'link': 'receber.form'}}
{'tag': {'preset': 'ativo', 'color': 'primary'}}
{'tag': {'size': 'sm', 'outline': True, 'cls': 'badge-pill'}}
```

---

### 3.3 `Lookup` — `ajsystem/defs/data.py` `class Lookup`

Usado na prop `lookup` de `Field` (FK). **Não existe `Lookup.model`** — o model alvo é inferido do FK automaticamente.

| Sub-prop | Tipo | Default | Declarações possíveis | Exemplo |
|----------|------|---------|----------------------|---------|
| `display` | `str` | 1º campo após `id` do alvo | nome do campo exibido | `{'display': 'nome'}` |
| `fields` | `str\|list` | `[display]` | `'nome'` ou `['nome', 'documento']` | `{'fields': ['nome']}` |
| `value` | `str` | `'id'` | campo gravado no banco | `{'value': 'id'}` |
| `when` | `str\|dict\|callable` | `None` | filtro das opções | `{'when': {'ativo': True}}` |
| `query` | `str` | `None` | nome de busca declarada na rota | `{'query': 'PREVISOES'}` |

**Declarações possíveis:**
```python
{'lookup': {'model': 'Conta', 'display': 'nome', 'fields': ['nome']}}
{'lookup': {'display': 'nome', 'when': {'ativo': True}}}
{'lookup': True}  # defaults, alvo inferido do FK
{'lookup': {'query': 'PREVISOES'}}
```

---

### 3.4 `Page` — `ajsystem/defs/pages.py` `class Page`

Declara a página na rota.

| Prop | Tipo | Default | Declarações possíveis | Exemplo |
|------|------|---------|----------------------|---------|
| `label` | `str` | `None` | título da página | `{'label': 'Contas a Receber'}` |
| `type` | `str` | `'crud'` | `crud`, `redirect`, `cart`, `showcase`, `contacts`, `custom` | `{'type': 'crud'}` |
| `props` | `dict` | `{}` | `{list, form, filter, report, sessions, scripts}` | `{'props': {'list': {...}}}` |
| `on_show` | `callable` | `None` | hook executado ao renderizar | `{'on_show': minha_funcao}` |
| `upload` | `dict` | `None` | política de upload | `{'upload': {'max_size': 5}}` |

#### `props.form` — Formulário

| Sub-prop | Tipo | Declarações possíveis | Exemplo |
|----------|------|----------------------|---------|
| `fields` | `str\|list\|dict` | `'Entidade'`, `['c1','c2']`, `{'Ent': ['c1']}` | `'Transacao'`, `['valor','prazo']` |
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

---

### 3.5 `Report` — `ajsystem/defs/report.py` `class Report`

Declara um relatório PDF.

| Prop | Tipo | Default | Declarações possíveis | Exemplo |
|------|------|---------|----------------------|---------|
| `label` | `str` | — | título | `{'label': 'Contas a Receber'}` |
| `page_size` | `str` | `'A4'` | `'A4'`, `'Letter'` | `{'page_size': 'A4'}` |
| `orientation` | `str` | `'portrait'` | `'portrait'`, `'landscape'` | `{'orientation': 'portrait'}` |
| `lpi` | `int` | `6` | `6` (4,23mm/linha) ou `8` (3,17mm) | `{'lpi': 6}` |
| `header` | `dict\|list` | `None` | `[LOGO(), TITLE()]` | `{'header': [...]}` |
| `body` | `dict\|ReportBody` | `None` | ver 3.6 | `{'body': {...}}` |
| `footer` | `bool\|dict` | `None` | `True` ou `{show_user, ...}` | `{'footer': True}` |
| `texts` | `dict\|list` | `None` | blocos de texto | `{'texts': {...}}` |
| `margin_top/bottom/left/right` | `num` | `10`/`20`/`10`/`10` | mm | `{'margin_top': 10}` |
| `auto_page_break` | `bool` | `True` | quebra automática | `{'auto_page_break': True}` |
| `show_table_lines` | `bool` | `False` | grade da tabela | `{'show_table_lines': True}` |

---

### 3.6 `ReportBody` — `ajsystem/defs/report.py` `class ReportBody`

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

---

### 3.7 `ReportColumn` — `ajsystem/defs/report.py` `class ReportColumn`

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

### 3.8 `ReportGroup` — `ajsystem/defs/report.py` `class ReportGroup`

Configuração de agrupamento (control-break) — usada dentro de `table.columns` via `group: '*'` + `on_start`/`on_finish`.

| Prop | Tipo | Declarações possíveis | Exemplo |
|------|------|----------------------|---------|
| `field` | `str` | campo chave do grupo | `'cliente'` |
| `text` | `str\|None` | título/template `'{cliente}'` | `'{conta}. {cliente}'` |
| `on_start` | `dict` | `{text, lf, align, style, cpi, pos}` | `{'text': ..., 'lf': -1, 'pos': POS_TITLE}` |
| `on_finish` | `dict` | `{text, footer_text, lf, align, style, cpi, totals}` | `{'text': ..., 'totals': True}` |
| `pos` | `int` | onde o título é impresso ao abrir | `POS_TITLE`, `POS_TITLE_CENTER` |
| `totais` | `None\|True\|dict` | controle de subtotal ao fechar | `True`, `{'label': 'Subtotal'}` |

> Formatos legados (`on`, `action`, `pos` numérico, `place`, `total`) não são suportados. Use apenas `on_start`/`on_finish/pos/text/lf/totais`.

---

### 3.9 `Button` — `ajsystem/defs/buttons.py` `class Button`

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

---

### 3.10 `Input` — `ajsystem/defs/inputs.py` `class Input`

Declara um tipo de input do catálogo. Usado indiretamente via `Field.input`.

| Prop | Tipo | Declarações possíveis | Exemplo |
|------|------|----------------------|---------|
| `name` | `str` | `'text'`, `'number'`, `'date'`, `'select'`, `'toggle'` | `'text'` |
| `input_type` | `str` | `'text'`, `'email'`, `'tel'`, `'password'` | `'email'` |
| `cls` | `str` | classe CSS | `'meu-input'` |
| `size` | `int` | tamanho do input | `9` |

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