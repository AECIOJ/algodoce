# AJSYSTEM — Manual de Configuração

> Versão do motor em `ajsystem/version` (`ciclo.ano.mes.dia.seq`). A versão do app hospedeiro fica em `APP['version']` (`app/config.py`).

---

## 1. Ordem de leitura do motor

O framework lê o app nesta ordem:

1. **`app/config.py`** — configuração geral, tema e menus (`SYS`, `SITE`, `ADMIN`).
2. **`app/models/*.py`** — model SQLAlchemy + `Entity` (declara campos).
3. **`app/routes/sys/*.py`** — `Schema` (overrides por página) + `Page` (tipo e props: `list`, `form`, `filter`, `report`, `sessions`).
4. **Relatórios** — `Report`, `ReportBody` (`table`/`chart`), `ReportColumn` (PDF).
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
'Tarefas': {'icon': 'check'},
```

---

## 3. Configuração geral — `app/config.py`

Lido primeiro pelo motor. Declara tema, módulos e menus.

### `APP` — dicionário raiz

| Chave | Tipo | Exemplo |
|-------|------|---------|
| `name` | `str` | `'MeuApp'` |
| `title` | `str` | `'Sistema de Gestão'` |
| `logo` | `str` | `'icons/logo.png'` |
| `tema` | `str` | `'meutema'` |
| `version` | `dict` | `{'cycle': 1, 'year': 26, 'month': 10, 'number': 15}` |
| `modules` | `list` | `[SITE, SYS, ADMIN]` |

### `Temas` — paleta de cores

Declara cores para tema DaisyUI compilado pelo motor (`do_themes.py`).

| Grupo | Chaves | Exemplo |
|-------|--------|---------|
| `marca` | `primary`, `secondary` | `primary: '#00796B'`, `secondary: '#D81B60'` |
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
    'default_path': 'cadastros/itens',
    'menus': {
        'Cadastros': {
            'icon': 'journal',
            'submenus': {
                'Categorias': {'icon': 'tags'},
                'Itens': {'icon': 'box-seam'},
            },
        },
        'Operações': {
            'icon': 'gear',
            'submenus': {
                'Entradas': {'icon': 'arrow-down-circle', 'page': 'entradas'},
            },
        },
    },
}
```

Cada submenu com `'page'` aponta para uma rota existente; sem `page`, o nome vira o slug da rota (ex: `'Categorias'` → `/categorias/`).

### `SITE` — módulo público

Mesma estrutura de `SYS`, com `type: 'public'` e `default_path` para a área pública.

### `ADMIN` — módulo administrativo

`type: 'admin'`, `default_path: 'seguranca.painel'`, menus vazios (painel gerado pelo motor).

---

## 4. Model + Entity — `app/models/*.py`

Lido depois do config. Declara o model SQLAlchemy e o dicionário `Entity` (única fonte de campos).

### `Entity`

Dicionário `{nome_campo: {config}}`. Cada chave é um campo do model; o valor são as props do `Field`.

| Prop | Tipo | Declarações possíveis | Exemplo |
|------|------|----------------------|---------|
| `type` | `str` | `TEXT`, `MEMO`, `INT`, `NUM`, `PERCENT`, `PK`, `ID`, `DK`, `FK`, `RK`, `DATA`, `DATA_HORA`, `HORA`, `BOOL`, `FONE`, `CPF`, `CNPJ`, `LIST`, `MULT10`, `IMAGE` | `{'type': 'NUM', 'mask': MVALOR}` |
| `label` | `str` | texto ou `None` (usa `_auto_label(name)`) | `{'label': 'Valor (R$)'}` |
| `width` | `int` | colunas `ch` (ex: `6` ID, `12` NUM, `20` TEXT) | `{'width': 12}` |
| `align` | `str` | `left`, `center`, `right` (`NUM` → `right` automático) | `{'align': 'right'}` |
| `input` | `str` | nome do `Input` do catálogo (`text`, `number`, `date`, `select`, `textarea`, `email`, `tel`, `password`, `checkbox`, `toggle`, `multi`, `image`) | `{'input': 'toggle'}` |
| `input_props` | `dict` | override parcial do input neste campo | `{'input_props': {'cls': 'x'}}` |
| `options` | `dict` | `{valor: rótulo}` para `LIST`/`MULT10` | `{'options': {0: 'Inativo', 1: 'Ativo'}}` |
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
| `lookup` | `bool\|dict\|Lookup` | `True` ou `{display, fields, value, when, query}` | `{'lookup': {'model': 'Categoria', 'display': 'nome'}}` |
| `validate` | `str` | `cpf`, `cnpj`, `placa` | `{'validate': 'cpf'}` |
| `help` | `str\|list` | texto de ajuda | `{'help': 'Informe o CPF'}` |
| `on_set` | `dict` | `{replaces: {campo: fonte}, disables: [...]}` | `{'on_set': {'disables': ['cnpj']}}` |
| `calc` | `str\|callable\|dict` | `'qtd*preco'`, `lambda row:`, `{'type':'agg',...}`, `{'type':'call',...}` | `{'calc': 'valor - (desconto or 0)'}` |
| `carry` | `str` | campo origem no map do botão | `{'carry': 'categoria_id'}` |
| `memory` | `bool` | `True` → só de tela, não persiste | `{'memory': True}` |
| `tag` | `dict\|Tag` | `{colors, color, link, size, preset, text_field, outline, cls}` | `{'tag': {'link': 'itens.form', 'color': 'info'}}` |

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

#### `lookup` — configuração de FK

Para campos `FK`. O model alvo é inferido do FK automaticamente (**não existe `Lookup.model`**).

| Sub-prop | Tipo | Exemplo |
|----------|------|---------|
| `display` | `str` | campo exibido (`'nome'`) |
| `fields` | `str\|list` | campos retornados (`['nome']`) |
| `value` | `str` | campo gravado (`'id'`) |
| `when` | `str\|dict\|callable` | filtro das opções (`{'ativo': True}`) |
| `query` | `str` | busca declarada na rota (`'BUSCA_ITENS'`) |

`{'lookup': True}` usa os defaults, com o alvo inferido do FK.

#### `calc` — campo calculado

| Forma | Exemplo | Efeito |
|-------|---------|--------|
| `str` | `'qtd * preco'` | expressão avaliada no cliente |
| `callable` | `lambda row: row.valor * 2` | função Python (virtual, não persiste) |
| `dict` | `{'type': 'agg', 'source': 'sum(Item.valor)'}` | agregado SQL (coluna real) |
| `dict` | `{'type': 'call', 'source': 'calc_status'}` | callable do model |

> Um `calc` de tipo `property` do model **não pode ser persistido**. Use `calc` virtual (`str` ou `callable`) ou `memory: True`.

#### `tag` — etiqueta visual (usa dataclass `Tag`, seção 7)

| Sub-prop | Tipo | Exemplo |
|----------|------|---------|
| `colors` | `{valor: cor}` | `{True: 'success', False: 'warning'}` |
| `color` | `str` | `'info'` |
| `link` | `str\|callable` | `'itens.form'` |
| `size` | `str` | `'sm'` |
| `outline` | `bool` | `True` |
| `preset` | `str` | `'boolean'`, `'ativo'`, `'status'` |
| `text_field` | `str` | `'status_label'` |
| `cls` | `str` | `'badge-pill'` |

---

## 5. Rota + Schema + Page — `app/routes/sys/*.py`

Lido depois do model. Declara `Schema` (overrides de Entity por página) e `Page` (tipo e props).

### `Schema`

Dicionário `{NomeEntidade: {campo: {overrides}}}`. Schema vence sobre Entity.

```python
Schema = {
    'Item': {
        'valor': {'readonly': True},
        'ativo': {'input': 'toggle'},
    },
}
```

### `Page`

Declara o tipo da página e seus props.

| Prop | Tipo | Default | Declarações possíveis | Exemplo |
|------|------|---------|----------------------|---------|
| `label` | `str` | `None` | título da página | `{'label': 'Item'}` |
| `type` | `str` | `'crud'` | `crud`, `redirect`, `cart`, `showcase`, `contacts`, `custom` | `{'type': 'crud'}` |
| `props` | `dict` | `{}` | `{master, list, form, filter, report, sessions, scripts}` | `{'props': {...}}` |
| `props.master` | `str` | `None` | entidade mestre (pai) — obrigatório em inversões (`columns` nomeia entidade diferente da rota); opcional em listagens comuns | `{'master': 'Entidade'}` |
| `on_show` | `callable` | `None` | hook ao renderizar | `{'on_show': fn}` |
| `upload` | `dict` | `None` | política de upload | `{'upload': {'max_size': 5}}` |

#### `props.form` — Formulário

| Sub-prop | Tipo | Declarações possíveis | Exemplo |
|----------|------|----------------------|---------|
| `fields` | `str\|list\|dict` | `'Ent'`, `['c1','c2']`, `{'Ent': ['c1']}` | `'Entidade'`, `['nome','valor']` |
| `positions` | `dict` | `{bar, footer, body, hidden}` | `{'bar': ['status'], 'hidden': ['tipo']}` |
| `visible` | `dict` | `{campo: cond}` | `{'grupo_id': NOT_EMPTY}` |
| `sessions` | `dict` | `{Nome:{fields,table,...}}` | `{'Itens': {'fields': [...]}}` |
| `template` | `str` | `None` | caminho alternativo | `{'template': 'custom.html'}` |
| `flash_ok`/`flash_update` | `str` | mensagem de sucesso | `{'flash_ok': 'Salvo!'}` |
| `readonly` | `bool\|callable` | `False` ou callable | `{'readonly': lambda q: q.grupo_id}` |
| `delete` | `bool\|dict\|callable` | `False`, `{'when': [...]}` | `{'delete': {'when': [Item]}}` |
| `pre_save`/`post_save` | `callable` | hook antes/depois de salvar | `{'pre_save': fn}` |
| `buttons` | `str\|Button\|list` | tipos ou instâncias | `{'buttons': [BTN_SAVE]}` |
| `spacing` | `num` | gap entre campos | `{'spacing': 2}` |
| `max_width` | `num` | largura máxima | `{'max_width': 110}` |

**Slots do form** (onde cada campo aparece): `bar` (ícones/tags fora do corpo), `footer` (fora do `<form>`, toggles), `body` (corpo, default), `hidden` (não exibe, não grava). Precedência: `hidden > bar > footer > body`.

#### `props.list` — Listagem

| Sub-prop | Tipo | Declarações possíveis | Exemplo |
|----------|------|----------------------|---------|
| `columns` | `str\|list\|dict` | `'Ent'`, `['c1','c2']`, `{'Ent': ['*']}` | `'Item'`, `['id','nome']` |
| `line`/`card`/`hidden` | `list` | campos por slot | `line: ['id']`, `card: 'Categoria'` |
| `detail` | `str\|tuple\|dict` | entidade do detalhe (relacionamento inferido), `('Entidade', 'Título')`, `('Entidade', ['campos'])` ou `{'fields': [...], 'data': 'relacionamento', 'title': '...'}` | `detail: ('Item', 'Itens')` |
| `order` | `list` | ordem de classificação | `order: ['data', 'id']` |
| `prio` | `list` | posição ordinal dos campos da linha (filho e/ou pai). Item: `(posicao, 'campo')`. Posicao positiva (1-based) conta da esquerda; negativa (-1 = ultimo, -2 = penultimo, etc.) conta da direita. Nome qualificado `Entidade.campo` apenas quando há nomes idênticos entre master e detalhe. Label/width/align vêm da Entity/Schema; `prio` só posiciona. | `prio: [(1, 'id'), (2, 'Categoria.data'), (-1, 'status')]` |

**Slots da lista**: `line` (sempre na grade, vence `card`), `card` (linha expansória), `hidden` (fora da grade e card). Precedência: `hidden > line > card`. Na inversão (`columns` nomeia entidade diferente da rota), o campo não citado vai para `line` se for do filho e para `card` se for do pai. Um item de slot pode ser um **alias de apresentação** (`{'Categoria': 'Item.categoria_id'}`): o rótulo é a chave e o alvo é o caminho; aceita também `{'label': ..., 'width': ..., 'align': ...}` via forma longa `{'Categoria': {'field': 'Item.categoria_id', 'label': '...'}}`.

**Renderização da lista**: `columns` define as colunas da grade (a ordem vem de `prio`). Quando a largura disponível não comporta todas, as colunas da direita — nunca a de `Ações` — passam para a linha expansória (`▶`), junto com os campos de `card`; nada some. Se `detail` estiver declarado, a linha expansória mostra abaixo do card uma **tabela transposta** com carrossel horizontal: a coluna de rótulos fica fixa com a largura do maior rótulo, cada registro ocupa a largura do maior `width` entre os campos exibidos e o pager aparece à direita do título quando os registros não cabem. Clicar no `<th>` da grade ordena no cliente, mantendo cada linha de detalhe junto do seu registro.

#### `props.filter` — Painel de filtros

| Sub-prop | Tipo | Declarações possíveis | Exemplo |
|----------|------|----------------------|---------|
| `hidden` | fieldspec | campos ocultos do painel | `{'hidden': ['tipo']}` |
| `fixed` | `{campo: op}` ou `OR`/`AND` | `WHERE` fixo | `{'fixed': {'tipo': 'R'}}` |
| `default` | `{campo: val}` ou `OR`/`AND` | filtro inicial editável | `{'default': {'data': {'preset': 'mes_ano'}}}` |
| `types` | `{tipo: campo\|lista}` | override do tipo de widget | `{'types': {'checklist': 'status'}}` |
| `max_width` | `int\|string CSS` | cap de largura | `{'max_width': 88}` |

Operadores: `=`, `!=`, `>`, `>=`, `<`, `<=`, `like`, `<>`. Em `date`, `>`/`<` compilam inclusivos (`>=`/`<=`); `<>` abre De/Até.

#### `props.report` — ABA Relatórios (PDF por entrada)

| Sub-prop | Tipo | Declarações possíveis | Exemplo |
|----------|------|----------------------|---------|
| `report` | dict | spec do relatório | `{'report': RELATORIO}` |
| `filter` | `{campo: operador}` | campos/operadores do formulário | `{'filter': {'grupo_id': '=', 'data': '<'}}` |
| `variants` | `dict` | `{'<nível>:<rótulo>': [campos]}` — modos do relatório | `{'0:Por Cliente': ['cliente_id'], '1:Por Mês': ['data']}` |

**`variants`** monta o select **Modo** na aba Relatórios (`rp_variant`) e:

- a chave é `'<nível>:<rótulo>'` (`0` é o default); o nível seleciona o layout de `body.table` e `body.chart` com a mesma chave numérica;
- a lista restringe **quais filtros do formulário aparecem** naquele modo (os demais são ignorados, mesmo que enviados);
- o rótulo depois de `:` vira o 2º título do PDF.

O sintético é controlado pelo layout (`table.syn`/`chart.syn`) do nível selecionado, não por `variants`.

> O `Page.props.filter.fixed` (ex.: `{'tipo': 'R'}` em Contas a Receber) é **automaticamente herdado** pelo relatório — combinado via `AND` com `body.filter` e os filtros do formulário. Não é necessário repetir o filtro fixo no relatório.

#### `props.scripts` — Scripts JS da página

Lista de nomes de arquivos JS estáticos.

```python
'scripts': ['itens', 'rel/gerar']
```

---

## 6. Relatório — `app/reports/*.py`

Lido quando a página tem aba `Report`. Declara `Report`, `ReportBody`, `ReportColumn` (PDF).

### `Report` — `ajsystem/defs/report.py` `class Report`

| Prop | Tipo | Default | Declarações possíveis | Exemplo |
|------|------|---------|----------------------|---------|
| `label` | `str` | — | título | `{'label': 'Relatório de Itens'}` |
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
| `chart` | `dict` | gráfico como saída (aditivo ao `table`) | `{'chart': {'type': 'bar', 'cat': {...}, 'value': {...}}}` |
| `before`\|`after` | `object` | blocos antes/depois | `{'before': [...]}` |
| `filter` | `dict\|list\|OR\|AND\|callable` | filtro padrão; combinado com `Page.props.filter.fixed` da página (se houver) e com o filtro do formulário de relatório | `{'filter': {'tipo': 'R'}}` |
| `order` | `str\|list\|None` | nomes ou índices 1-based | `['data','id']` ou `[1, 3]` |
| `levels` | `dict` | numeração hierárquica | `{'pk': 'id', 'parent': 'pai_id'}` |
| `items` | `list` | itens inline antes da tabela | `['titulo', ('data', {'lf': 1})]` |

### `body.table` — declaração `title`/`pre`/`cols`/`post`

O motor lê `body.table` com **três formas possíveis**. Ordem das chaves = ordem de impressão.

#### Forma A — compacta (sem sintético, sem variantes)

Declara `title`/`pre`/`cols`/`post` direto na raiz de `table`:

```python
'table': {
    'title': {},                           # título externo (quebra a tabela)
    'pre': {                               # linhas antes da linha de dados (dentro da tabela)
        'grupo': {                         # campo com group: '*' vira nível de grupo
            'group': '*',
            'text': '{grupo}. {nome}',
            'on_start': {'lf': -1},
            'on_finish': {'lf': 1},
            'totals': {'align': 'R'},
        },
    },
    'cols': {                              # colunas da grade (ordem = impressão)
        'valor': {'agg': 'sum'},
        'desconto': {'agg': 'sum'},
        'total': {'agg': 'sum'},
    },
    'post': {},                            # linhas depois da linha de dados (ex: memo)
    'order': [...],                        # ordem das colunas/grupos (opcional)
    'totals': {'align': 'R'},              # totais gerais (opcional)
    'lf': [1, 1],                          # respiro antes/depois da tabela (opcional)
    'extend': [...],                       # linhas extras dentro do quadro (opcional)
}
```

#### Forma B — com sintético explícito (`syn`)

Mesma forma acima, mais a prop `syn` com layout alternativo:

```python
'table': {
    'title': {},
    'pre': {...},
    'cols': {...},
    'post': {},
    'syn': {                               # layout do modo sintético (não herda de detalhado)
        'title': {},
        'pre': {...},
        'cols': {...},
        'post': {},
        'order': [...],
        'totals': {'align': 'R'},
    },
}
```

Sem `syn` na raiz, o motor **nunca** gera modo sintético para aquele report.

#### Forma C — com variantes (chave numérica)

Chave numérica = nível de impressão (sem detalhado na raiz):

```python
'table': {
    '0': {                                 # variante 0 (default se não selecionada)
        'title': {},
        'pre': {...},
        'cols': {...},
        'post': {},
        'syn': {...}                       # sintético opcional desta variante
    },
    '1': {                                 # variante 1
        'title': {},
        'pre': {...},
        'cols': {...},
        'post': {},
        # sem syn -> checkbox de sintético não aparece nesta variante
    },
}
```

**Regras:**
- Não misture seções raiz (`title`/`pre`/`cols`/`post`) com chaves de variante.
- `syn` na raiz exige que não haja variantes (e vice-versa).
- `syn` exige `cols` com `agg` para agregar; sem `agg`, só troca de colunas.
- `title` quebra a tabela (fecha/abre).
- `pre`/`post` são linhas dentro da tabela, antes/depois da linha de dados.
- `group: '*'` é flag de field (não seção). Pode ficar em `title`/`pre`/`cols`/`post`.
- Props internas do grupo continuam no próprio field: `totals`, `text`, `on_start`, `on_finish`, `lf`.
- `POS_*` (POS_ROW, POS_INLINE, POS_TITLE, POS_TITLE_CENTER, POS_NONE) **não se declara mais**; é constante interna do renderer.
- Não existe mais `syn: False`/`syn: True` por coluna nem entrada de props.report.
- Não existe mais `columns` como alias de `fields`.
- Não existe mais `body.order` no nível do report; `order` vive dentro de cada nível (`det`/`syn`/variante).

### `ReportColumn` — `ajsystem/defs/report.py` `class ReportColumn`

Declara uma coluna de `body.table.cols` (ou `syn.cols`).

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
| `group` | `str` | `None` | `'*'` (grupo/break) ou `'<nome>'` | `{'group': '*'}` |
| `on_start` | `dict` | `None` | `{text, lf, align, style, cpi, pos}` | `{'on_start': {'lf': -1}}` |
| `on_finish` | `dict` | `None` | `{text, footer_text, lf, align, style, cpi, totals}` | `{'on_finish': {'totals': True}}` |
| `totals` | `object` | `None` | `None`, `True`, `dict` | `{'totals': {'align': 'R', 'span': 4}}` |
| `lf` | `object` | `None` | respiro antes/depois (`n`, `-n`, `[a,b]`) | `{'lf': -1}` |
| `transform` | `str` | `None` | `'U'`, `'L'`, `'C'` | `{'transform': 'U'}` |
| `bold` | `bool` | `False` | `True` | `{'bold': True}` |
| `when` | `str\|dict` | `None` | condição de exibição | `{'when': 'status > 0'}` |

### `body.chart` — gráfico como saída do relatório (PDF)

O gráfico é declarado no próprio report e impresso como **PNG dentro do PDF** (renderizado no servidor com Pillow — sem navegador, sem Chart.js). É **aditivo** ao `table`: não entra no XOR `form`/`table` e pode coexistir com ele.

`source`, `filter`, `titles`, `variants` e o sintético vêm do `Report`; o `chart` não declara fonte nem filtro próprios.

#### `Chart` — props de raiz

| Prop | Tipo | Default | Declarações possíveis | Exemplo |
|------|------|---------|----------------------|---------|
| `title` | `str` | `None` | título acima do plot; se omitido, o gráfico sai sem título (o título do report já está no cabeçalho) | `{'title': 'Saldo por Cliente'}` |
| `type` | `str` | `'col'` | `col` (colunas verticais), `bar` (barras horizontais), `pie`, `donut`; `line`, `area` e `scatter` são aceitos e, no PDF atual, caem no renderizador de colunas | `{'type': 'bar'}` |
| `cat` | `dict` | `{}` | **um** campo de categoria `{campo: ChartField}`; é o eixo de agrupamento. Omitido, cada campo de `value` vira uma categoria | `{'cat': {'cliente': {'order': 'desc', 'limit': 10}}}` |
| `value` | `dict` | `{}` | uma ou mais séries `{campo: ChartField}` | `{'value': {'saldo': {'color': '#dc3545'}}}` |
| `stack` | `dict` | `{}` | `{grupo: [campos]}` — campos do mesmo grupo são empilhados; fora de `stack`, ficam lado a lado | `{'stack': {'total': ['previsto', 'realizado']}}` |
| `label` | `dict` | `{}` | rótulos de eixo/dados (ver `ChartLabel`) | `{'label': {'cat': 'Cliente', 'value': 'Saldo (R$)'}}` |
| `options` | `dict` | `{}` | opções de renderização; `legend` (posição/`False` desliga), `shadow` (`True`→`(3,3)` ou tupla `(dx,dy)` cartesiana), `explode` (fatia destacada em `pie`/`donut`), `title_font` (`{size: int, bold: bool, family: str}`) | `{'options': {'legend': False, 'shadow': (5, -5), 'explode': 'saldo', 'title_font': {'size': 18, 'bold': False}}}` |
| `limit` | `int` | `None` | top N após a ordenação (também aceito em `cat.<campo>.limit`) | `{'limit': 10}` |
| `order` | `str\|list` | `None` | ordem da consulta: injeta `ORDER BY` na query de origem (igual `report.order`). Aceita campo (`'mes_ordem'`), lista (`['mes_ordem']`) ou índices 1-based (`[1, 2]`) | `{'order': 'mes_ordem'}` |
| `syn` | `dict` | `None` | layout alternativo do modo sintético (mesmas props de raiz; seu `options` é independente da raiz) | `{'syn': {'type': 'pie', ...}}` |

`cat` aceita só o **primeiro** campo declarado. `type`, `cat`, `value`, `stack`, `label` e `title` são da raiz — não existe `chart.options.stacked` (use `stack`). `legend`, `shadow` e `explode` vivem só em `options`; `legend` na raiz ainda é aceito como fallback depreciado.

- `shadow: bool | tuple[int, int]` (`True` padrão → offset `3,3`): desenha uma cópia deslocada em cinza claro (`#d1d5db`) atrás de cada fatia (`pie`/`donut`) ou barra (`col`/`bar`), dando sensação de relevo. `True` usa `(3, 3)`; uma tupla `(dx, dy)` segue o plano cartesiano: `dx` positivo à direita, `dy` positivo para cima; negativos invertem. Declara apenas para desligar: `{'options': {'shadow': False}}`.
- `explode: str | list[str]`: destaca a fatia(ões) nomeada(s) deslizando-a para fora do centro da pizza (`radius * 0.12`). Sombra e rótulos acompanham o deslocamento. Ignorado em `col`/`bar` e em nome inexistente.
- `title_font: dict` (`{size: int, bold: bool, family: str}`): configura a fonte do título do gráfico. Default: `size=24, bold=True`. Ex.: `{'options': {'title_font': {'size': 18, 'bold': False, 'family': 'Arial'}}}`.

Sem `cat`, os rótulos das categorias são os próprios campos de `value`: cada campo entra como uma categoria com o seu valor agregado (formato de "comparar totais", ex.: pizza com uma fatia por campo). O rótulo exibido vem do `label` do campo na Entity (fallback `_auto_label`) e é o mesmo usado na legenda.

#### `ChartField` — props de um campo de `cat`/`value`

| Prop | Tipo | Default | Declarações possíveis | Exemplo |
|------|------|---------|----------------------|---------|
| `agg` | `str` | `'sum'` | `sum`, `avg`, `min`, `max`, `count` (só em `value`) | `{'agg': 'avg'}` |
| `color` | `str` | paleta | cor hex da série | `{'color': '#0d6efd'}` |
| `bin` | `str` | `None` | `day`, `month`, `year` (só em `cat`, para campos de data) | `{'cat': {'vencimento': {'bin': 'month'}}}` |
| `order` | `str` | `None` | `asc`, `desc` (só em `cat`) | `{'cat': {'cliente': {'order': 'desc'}}}` |
| `limit` | `int` | `None` | top N da categoria (só em `cat`) | `{'cat': {'cliente': {'limit': 10}}}` |
| `variants` | `list` | `None` | níveis de variante em que o campo entra | `{'variants': [0, 1]}` |
| `syn` | `bool` | `None` | `False` omite o campo no sintético | `{'syn': False}` |
| `axis`/`format` | — | — | `format` em `cat` com `bin` formata a label da categoria (ex.: `'mmm/yyyy'` → `'Mai/2026'`); `axis` aceito mas sem efeito no PDF atual | `{'cat': {'vencimento': {'bin': 'month', 'format': 'mmm/yyyy'}}}` |

#### `ChartLabel` — rótulos

| Prop | Tipo | Default | Declarações possíveis | Exemplo |
|------|------|---------|----------------------|---------|
| `cat` | `bool\|str\|None` | `False` | `True` imprime a categoria na fatia (`pie`/`donut`); `str` é o rótulo do eixo de categoria (`col`/`bar`) | `{'cat': True}` |
| `value` | `str` | `None` | rótulo do eixo de valor | `{'value': 'Saldo (R$)'}` |
| `val` | `bool` | `True` | mostra o valor absoluto (sobre a barra/fatia) | `{'val': True}` |
| `perc` | `bool` | `True` | mostra a porcentagem (sobre a barra/fatia) | `{'perc': True}` |
| `pos` | `str` | `'O'` | posição do rótulo de dados: `O`=fora da fatia (com conector até a borda), `I`=dentro da fatia, centralizado | `{'pos': 'O'}` |
| `limit` | `bool\|str` | `None` | `True` → `"Top N"`; `str` → texto livre; `None` → sem texto | `{'limit': '10 maiores clientes'}` |

**Rótulo de dados** (`cat`/`val`/`perc`/`pos`):
- `cat=True` (só `pie`/`donut`) imprime o nome da categoria no topo do bloco de texto da fatia; `pos` (`O` fora, `I` dentro) se aplica ao bloco todo;
- `val` e `perc` saem **empilhados** (valor embaixo, porcentagem acima);
- `pos='O'` desenha o rótulo **fora** da fatia, com um conector cinza até a borda (texto escuro sobre fundo branco);
- `pos='I'` desenha o rótulo **dentro** da fatia, centralizado, com texto na cor de contraste da própria fatia;
- nas barras (`col`/`bar`), `val` escreve o valor sobre a barra e `cat` só vale se for `str` (título do eixo).

> `data` saiu: use `val` (valor) e/ou `perc` (porcentagem).

#### Formas de declaração (espelho de `body.table`)

**Forma A — layout único (sem sintético, sem variantes):**

```python
'chart': {
    'title': 'Saldo por Cliente',
    'type': 'bar',
    'cat': {'cliente': {'order': 'desc', 'limit': 10}},
    'value': {
        'previsto':  {'color': '#0d6efd'},
        'realizado': {'color': '#198754'},
        'saldo':     {'color': '#dc3545'},
    },
    'stack': {'total': ['previsto', 'realizado', 'saldo']},
    'label': {'cat': 'Cliente', 'value': 'Saldo (R$)', 'val': True},
    'options': {'legend': 'bottom'},
}
```

**Forma B — com sintético explícito (`syn`):**

```python
'chart': {
    'type': 'bar',
    'cat': {...},
    'value': {...},
    'syn': {                               # layout da visão sintética
        'title': 'Composição por Recurso',
        'type': 'pie',
        'cat': {'recurso': {}},
        'value': {'saldo': {}},
        'label': {
            'val': True,      # valor absoluto
            'perc': True,     # porcentagem
            'pos': 'O',       # fora da fatia (O) ou dentro, centralizado (I)
        },
    },
}
```

**Forma C — com variantes (chave numérica compartilhada com `table`):**

```python
'chart': {
    '0': {                                 # variante 0 (default)
        'type': 'bar',
        'cat': {...},
        'value': {...},
        'syn': {...},                      # sintético opcional desta variante
    },
    '1': {                                 # variante 1
        'type': 'line',
        'cat': {'vencimento': {'bin': 'month'}},
        'value': {'saldo': {}},
    },
}
```

**Regras:**
- Não misture props de raiz com chaves de variante no mesmo `chart`.
- `syn` não é herdado entre variantes: cada nível declara o seu.
- `variants`/`syn` por campo são aplicados **antes** da resolução dos dados (mesma lógica de `table.columns`).
- `stack` referencia apenas campos de `value`; campo repetido em dois grupos ou inexistente em `value` é erro de declaração.
- O `chart` usa o mesmo `rp_variant` da tabela (as duas declarações devem usar a mesma chave numérica).
- O `cat` é obrigatório; sem ele o motor tenta inferir a primeira coluna que não seja série.

#### Saída do PDF (`rp_output`)

Quando `body` declara `table` **e** `chart`, a aba Relatórios mostra o select **Saída** (`rp_output`):

| Valor | Conteúdo do PDF |
|-------|-----------------|
| `both` | tabela + gráfico (default) |
| `table` | somente a tabela |
| `chart` | somente o gráfico (cabeçalho/rodapé do report continuam) |

Com apenas um dos dois declarado, o select não aparece e a saída é sempre a disponível. O checkbox **Sintético** aparece quando `table.syn` **ou** `chart.syn` existe no layout ativo.

Falha ao montar o gráfico não invalida o relatório: o PDF sai sem o gráfico e o erro vai para o log (`warning`).

#### Fontes embutidas

O gráfico usa DejaVu Sans (normal/negrito) embutida em `ajsystem/static/fonts/`. A imagem `python:*-slim` não traz fontes TTF; sem os arquivos, o Pillow cai num bitmap fixo de 11px e todo o texto do gráfico sai minúsculo.

| Arquivo | Uso |
|---------|-----|
| `ajsystem/static/fonts/DejaVuSans.ttf` | eixos, legenda, rótulos |
| `ajsystem/static/fonts/DejaVuSans-Bold.ttf` | título do gráfico |

### Modo sintético

Quando `table.syn` (ou `chart.syn`) é declarado e o usuário marca o checkbox **"Sintético"** na tela de relatórios:

- O motor agrupa as linhas pelos campos com `group: '*'` (ordem de declaração).
- Colunas com `agg` (`sum`/`avg`/`min`/`max`/`count`) são agregadas por grupo (uma linha por grupo).
- Colunas sem `agg` recebem o valor da primeira linha do grupo.
- `count` no sintético conta grupos (não linhas totais).
- `avg/min/max` no total geral continuam como antes (não somam médias).
- No gráfico, `chart.syn` troca o layout (ex.: barras → pizza) e campos com `syn: False` são omitidos.

Se `syn` **não** for declarado no layout ativo, o checkbox de sintético não aparece no form de relatórios.

O botão **Limpar** desmarca o checkbox de sintético sem zerar seu `value`; **Gerar** reenvia `rp_sintetico=on` quando marcado, mesmo após limpar os filtros.

#### Calendário de data (Flatpickr)

Campos de `type: 'DATA'` usam Flatpickr (calendário nativo consistente em mobile e desktop). O input exibe sempre `dd/mm/aaaa`.

---

## 7. Componentes auxiliares

### `Tag` — `ajsystem/defs/tags.py` `class Tag`

Usado na prop `tag` de `Field`. Renderiza um badge/pill ao lado do valor.

| Sub-prop | Tipo | Valores possíveis | Exemplo |
|----------|------|-------------------|---------|
| `colors` | `dict` | `{valor: cor}` (cor ∈ `ghost`, `primary`, `success`, `warning`, `error`, `info`, `0-9`) | `{'colors': {True: 'success', False: 'warning'}}` |
| `color` | `str` | cor fixa | `{'color': 'info'}` |
| `link` | `str\|callable` | `'itens.form'` ou `lambda row: 'categorias.form'` | `{'link': 'itens.form'}` |
| `size` | `str` | `sm` (default) | `{'size': 'sm'}` |
| `outline` | `bool` | `True` → estilo outline | `{'outline': True}` |
| `preset` | `str` | `boolean`, `ativo`, `status` | `{'preset': 'ativo'}` |
| `text_field` | `str` | campo de onde vem o rótulo exibido | `{'text_field': 'status_label'}` |
| `cls` | `str` | classe CSS extra concatenada | `{'cls': 'badge-pill'}` |

### `Lookup` — `ajsystem/defs/data.py` `class Lookup`

Usado na prop `lookup` de `Field` (FK). **Não existe `Lookup.model`** — o model alvo é inferido do FK automaticamente.

| Sub-prop | Tipo | Default | Declarações possíveis | Exemplo |
|----------|------|---------|----------------------|---------|
| `display` | `str` | 1º campo após `id` do alvo | nome do campo exibido | `{'display': 'nome'}` |
| `fields` | `str\|list` | `[display]` | `'nome'` ou `['nome', 'documento']` | `{'fields': ['nome']}` |
| `value` | `str` | `'id'` | campo gravado no banco | `{'value': 'id'}` |
| `when` | `str\|dict\|callable` | `None` | filtro das opções | `{'when': {'ativo': True}}` |
| `query` | `str` | `None` | busca declarada na rota | `{'query': 'BUSCA_ITENS'}` |

### `Button` — `ajsystem/defs/buttons.py` `class Button`

Declara um botão no form.

| Prop | Tipo | Declarações possíveis | Exemplo |
|------|------|----------------------|---------|
| `type` | `str` | `'save'`, `'delete'`, `'print'`, `'send'` | `{'type': 'print'}` |
| `report` | dict | spec do relatório | `{'report': REL}` |
| `filter_field` | `str` | campo de filtro | `{'filter_field': 'tipo'}` |
| `label` | `str` | texto do botão | `{'label': 'Imprimir'}` |
| `icon` | `str` | ícone do sprite SVG (`ajsystem/templates/components/heroicons.svg`, id do `<symbol>` sem o prefixo `bi-`) | `{'icon': 'printer'}` |
| `color` | `str` | cor do botão | `{'color': 'info'}` |
| `action` | `str\|callable` | ação JS ou Python | `{'action': 'gerarItens'}` |
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

