# PLANO — Refatoração do sistema

## Visão geral

Cada módulo de rota define seus próprios dicts de configuração.
O motor lê a config diretamente do módulo — sem registro central.

```
routes/sys/categorias.py
├── Entidade = { 'Category': { 'nome': {'type':'TEXT'}, ... } }
├── Lista    = { 'colunas': ['Category'], 'ordering': ['ordem'] }
└── @bp.route("/") → return render_list('Category', __name__)

Motor (engine/handle_list.py)
├── importlib do módulo passado
├── lê Entidade[entity_name] → fields com defaults de fields.py
├── lê Lista → colunas, detalhe, ordering
├── resolve model por convenção (Category → app.models.category.Category)
└── renderiza components/page_list_simple.html
```

---

## Stack frontend

| Tecnologia | Versão | Uso |
|-----------|--------|-----|
| Bootstrap 5.3 | vendored | compatibilidade templates existentes |
| Tailwind CSS 3 | build npm | utilitários novos |
| DaisyUI 4 | sem prefixo | componentes novos |
| HTMX 2 | `static/lib/htmx.min.js` | interações servidor |
| Alpine.js 3 | `static/lib/alpine.min.js` | estado cliente |

Build: `npm run build:css` (PostCSS → Tailwind + DaisyUI)

---

## Configuração de entidade

### `Entidade` — definição dos campos

```python
Entidade = {
    'Quote': {
        'ID':          {'type': 'PK'},
        'cliente_id':  {'type': 'FK', 'model': 'Conta', 'field': 'nome', 'width': 30},
        'data':        {'type': 'DATA'},
        'total':       {'type': 'NUMBER', 'currency': True},
    },
    'QuoteItem': {
        'ID':          {'type': 'PK'},
        'produto_id':  {'type': 'FK', 'model': 'Product', 'field': 'nome'},
        'quantidade':  {'type': 'NUMBER'},
        'preco':       {'type': 'NUMBER', 'currency': True},
        'valor':       {'type': 'NUMBER', 'currency': True, 'computed': 'quantidade * preco'},
    },
}
```

**Types** e seus defaults (definidos no motor):

| Type | Default |
|------|---------|
| `PK` | `{'input': 'number', 'edit': False, 'filter': FILTER_NUMBER}` |
| `TEXT` | `{'required': True}` |
| `INT` | `{'input': 'number', 'align': 'right'}` |
| `NUMBER` | `{'input': 'number', 'align': 'right', 'filter': FILTER_NUMBER}` |
| `BOOL` | `{'input': 'boolean', 'filter': FILTER_BOOLEAN}` |
| `DATA` | `{'input': 'date', 'filter': FILTER_DATE}` |
| `FK` | `{'input': 'select', 'filter': FILTER_SELECT}` |

Qualquer propriedade no dict do field sobrescreve o default.

### `Lista` — configuração da listagem

```python
Lista = {
    'colunas': ['Quote.cliente_id', 'Quote.data'],   # selecionados
    # ou
    'colunas': ['Quote'],                             # todos

    'linha': ['Quote.id', 'Quote.cliente_id'],        # campos sempre visíveis na linha
    'card': ['Quote.observacoes'],                    # campos extras no cartão expansível

    'detalhe': ['QuoteItem.produto_id', 'QuoteItem.quantidade'],  # selecionados
    # ou
    'detalhe': ['QuoteItem'],                         # todos

    'template': 'components/page_list_responsive.html',  # opcional (default = page_list_simple.html)
    'ordering': ['data'],          # ordenação padrão da query
    'new_endpoint': 'entity.form', # endpoint do botão Novo (opcional)
    'edit_endpoint': 'entity.form',# endpoint do link Editar (opcional)
}
```

- `colunas` / `detalhe` são listas de strings
- `'Entidade'` = todos os campos da entidade
- `'Entidade.campo'` = campo específico
- Ordenação por clique no cabeçalho: `.sortable` + JS em `page_sys.html`

---

## Motor (`engine/handle_list.py`)

```python
def render_list(entity_name: str, module_name: str):
    mod = importlib.import_module(module_name)
    entidades = mod.Entidade
    lista = mod.Lista
    model = _resolve_model(entity_name)   # por convenção

    cols = _resolve_cols(lista['colunas'], entidades)
    card = _resolve_cols(lista.get('card', []), entidades) if 'card' in lista else None
    det = _resolve_cols(lista.get('detalhe', []), entidades) if 'detalhe' in lista else None

    fields = [Field(**cfg) for cfg in cols] + ([Field(**cfg) for cfg in card] if card else [])
    card_fields = [Field(**cfg) for cfg in card] if card else None
    detail_fields = [Field(**cfg) for cfg in det] if det else None

    # LINHA: resolve field names para indices nas master_fields
    linha_names = _resolve_field_names(lista.get('linha', []))
    linha_indices = [i for i, f in enumerate(cols_fields) if f.name in linha_names] if linha_names else None

    # FIELDS_MASTER: indices dos campos de colunas no array all_fields
    fields_master = list(range(1, len(cols) + 1)) if cols else None

    list_obj = List(
        fields=all_fields,
        fields_master=fields_master,
        linha=linha_indices,
        card_idx=(list(range(len(cols) + 1, len(all_fields) + 1)) if card else None),
    )

    # constrói List, query, filtros, render
    ...
```

### Resolução de model por convenção

`'Category'` → `app.models.category.Category`
`'Ingredient'` → `app.models.ingredient.Ingredient`
`'Product'` → `app.models.product.Product`
`'Conta'` → `app.models.client.Conta`
`'Operacao'` → `app.models.operacao.Operacao`
`'Carteira'` → `app.models.carteira.Carteira`

(Se precisar de um mapeamento diferente, usa-se `model_class` no `Entidade`.)

---

## Estado atual (implementado)

### Completado

1. **Estrutura de pastas**
   - `routes/site/`, `routes/sys/` com `__init__.py`
   - Rotas movidas (ex: `sys_categorias.py` → `sys/categorias.py`)
   - `old/` na raiz com arquivos obsoletos

2. **Motor (`app/engine/`)**
   - `menu.py`: `modulo_atual()`, `url_do_item()`, `item_ativo()`, `menus_para_json()`
   - `handle_list.py`: `render_list(entity_name, module_name)` — lê `Entidade` + `Lista` do módulo
   - `auth.py`: infraestrutura de login
   - `auth_routes.py`: blueprints `auth` e `seguranca`

3. **Templates base**
   - `page_base.html`: Bootstrap + Tailwind/DaisyUI + HTMX + Alpine
   - `page_sys.html`: menus dinâmicos, sub-menus com hover, modais `<dialog>`, rodapé flex
   - Submenu: seção atual fica sempre visível; `mouseenter` mostra o submenu do hover; `mouseleave` restaura o da seção atual (não esconde tudo)
   - Altura do nav e submenu alinhadas: `line-height: 32px` ambos; balão ativo com `line-height: 20px; margin: 4px 0`

4. **Categorias — primeira migração**
   - `routes/sys/categorias.py` com `Entidade`/`Lista` dicts
   - `Lista.colunas = ['Category']`, sem `detalhe`
   - Rotas form/delete/toggle mantidas
   - `app_defs.py`: `ENTIDADES` removido
   - `register_entity_model` removido de `__init__.py`

5. **DaisyUI sem prefixo**
   - `preflight: false` para conviver com Bootstrap
   - Classes DaisyUI sobrescrevem Bootstrap seletivamente

6. **Template de listagem (`page_list_simple.html`)**
   - Template inline, sem macros, sem `hx-target`
   - `handle_list.py` renderiza `page_list_simple.html`
   - **Sistema de abas via Alpine.js**: sem Bootstrap tabs (eliminou conflito `display: none`)
   - **Largura das colunas** em `ch`; container com `min-width: SOMA_TOTALch`
   - **Filtros funcionais**: painel de filtros com Alpine.js, submit via URL params
   - **Coluna `#` exibe `id` real do banco** (não número da linha)
   - **Ordenação por clique no cabeçalho**: classe `sortable` + JS em `page_sys.html`
   - Botão "Editar" com ícone pencil.svg

7. **Migração completa do módulo Cadastro** (ver seção abaixo)

---

## Cadastro — Entidades migradas

| Submenu | Entidade | Model | `__name__` | `Lista.colunas` | `Lista.ordering` |
|---------|----------|-------|------------|----------------|-------------------|
| Categorias | `Category` | `app.models.category.Category` | `categories` | `['Category']` | `['ordem', 'nome']` |
| Insumos | `Ingredient` | `app.models.ingredient.Ingredient` | `insumos` | `['Ingredient']` | `['nome']` |
| Produtos | `Product` | `app.models.product.Product` | `products` | `['Product']` | `['nome']` |
| Contas | `Conta` | `app.models.client.Conta` | `contas` | `['Conta']` | `['nome']` |
| Operações | `Operacao` | `app.models.operacao.Operacao` | `operacoes` | `['Operacao']` | `['ordem', 'nome']` |
| Carteiras | `Carteira` | `app.models.carteira.Carteira` | `carteira` | `['Carteira']` | `['nome']` |

### Definições `Entidade` por submenu

```python
# Insumos
Entidade = {
    'Ingredient': {
        'id':              {'type': 'PK', 'width': 6},
        'nome':            {'type': 'TEXT', 'width': 18, 'transform': 'title'},
        'tipo':            {'type': 'FK', 'width': 12, 'options': TIPO_INGREDIENTE},
        'unidade_medida':  {'label': 'Und', 'width': 8, 'input': 'select', 'options': UND_MAP},
    },
}
Lista = {'colunas': ['Ingredient'], 'ordering': ['nome'],
         'new_endpoint': 'insumos.form', 'edit_endpoint': 'insumos.form'}

# Produtos
Entidade = {
    'Product': {
        'id':          {'type': 'PK', 'width': 6},
        'nome':        {'type': 'TEXT', 'width': 20, 'transform': 'title'},
        'descricao':   {'type': 'TEXT', 'input': 'textarea'},
        'preco':       {'type': 'NUMBER', 'width': 10, 'currency': True},
        'qtd_minima':  {'label': 'Qtd. Mín.', 'width': 8, 'input': 'number'},
        'imagem':      {'width': 15, 'filter': False},
        'categoria':   {'query': 'category', 'card_path': 'category.nome', 'filter_path': 'category.nome'},
        'ativo':       {'type': 'BOOL', 'width': 8},
    },
}
Lista = {'colunas': ['Product'], 'ordering': ['nome'],
         'new_endpoint': 'products.form', 'edit_endpoint': 'products.form'}

# Contas
Entidade = {
    'Conta': {
        'id':             {'type': 'PK', 'width': 7},
        'nome':           {'type': 'TEXT', 'width': 20, 'transform': 'title'},
        'tipo':           {'type': 'FK', 'width': 12, 'options': TIPO_CONTA},
        'telefone':       {'width': 14},
        'email':          {},
        'cpf':            {'label': 'CPF'},
        'cnpj':           {'label': 'CNPJ'},
        'insc_estadual':  {'label': 'Inscrição Estadual'},
        'endereco':       {'input': 'textarea'},
        'ativo':          {'type': 'BOOL'},
    },
}
Lista = {'colunas': ['Conta'], 'ordering': ['nome'],
         'new_endpoint': 'contas.form', 'edit_endpoint': 'contas.form'}

# Operações
Entidade = {
    'Operacao': {
        'id':     {'type': 'PK', 'width': 6},
        'nome':   {'type': 'TEXT', 'width': 20, 'transform': 'title'},
        'tipo':   {'type': 'FK', 'width': 12, 'options': TIPO_OPERACAO},
        'fator':  {'type': 'INT', 'width': 8},
        'pai_id': {'label': 'Pai', 'type': 'FK', 'model': 'Operacao', 'field': 'nome',
                   'query_filter': {'ativa': True, 'pai_id': None}, 'width': 30},
        'ordem':  {'type': 'INT', 'width': 8},
        'ativa':  {'type': 'BOOL', 'width': 8},
    },
}
Lista = {'colunas': ['Operacao'], 'ordering': ['ordem', 'nome'],
         'new_endpoint': 'operacoes.form', 'edit_endpoint': 'operacoes.form'}

# Carteiras
Entidade = {
    'Carteira': {
        'id':                 {'type': 'PK', 'width': 6},
        'nome':               {'type': 'TEXT', 'width': 50, 'transform': 'title'},
        'uso':                {'type': 'FK', 'width': 10, 'options': {0: 'Pedido', 1: 'Ambos', 2: 'Compra'}},
        'gerar':              {'type': 'FK', 'width': 10, 'options': {0: 'Movimento', 1: 'Previsão'}},
        'prazo_recebimento':  {'label': 'Prazo', 'width': 5},
        'taxa_recebimento':   {'label': 'Taxa', 'width': 8, 'type': 'NUMBER'},
    },
}
Lista = {'colunas': ['Carteira'], 'ordering': ['nome'],
         'new_endpoint': 'carteira.form', 'edit_endpoint': 'carteira.form'}
```

Observações:
- `type: 'PK'` → field `id` com `edit: False, filter: FILTER_NUMBER`
- `type: 'TEXT'` → `required: True`  (texto padrão)
- `type: 'INT'` → `input: 'number', align: 'right'`
- `type: 'NUMBER'` → `input: 'number', align: 'right', filter: FILTER_NUMBER`
- `type: 'BOOL'` → `input: 'boolean', filter: FILTER_BOOLEAN`
- `type: 'FK'` → `input: 'select', filter: FILTER_SELECT` (mais `options` se fornecido)
- `width` em `ch`, usado para largura da coluna e `min-width` do container

---

## Pendências / Melhorias futuras

1. **Re-adicionar funcionalidades da listagem** (em ordem de prioridade):
   - [x] Botão de filtros + painel de filtros (Alpine.js + URL params)
   - [x] Ordenação por clique no cabeçalho (`.sortable` + JS)
   - [x] Colunas posicionáveis (show/hide por largura — JS `ajustarTabela` do original)
   - [x] Linhas de detalhe expansíveis (para entidades com `detalhe`)
   - [x] Sistema `linha`/`card`/`colunas` (substitui `pos`)
   - [ ] Totais (tfoot com agregadores)
   - [ ] Badge de contagem de filtros ativos

2. **Migrar entidade complexa**: **Pedidos** ou **Compras** (master-detail com `detalhe`)

3. **Criar `engine/handle_form.py`** (genérico, lê `Form` dict do módulo e renderiza formulário DaisyUI)

4. **Migrar demais módulos** (Comercial, Produção, Financeiro)

5. **Remover Bootstrap** e migrar templates restantes para DaisyUI puro

---

## O que NÃO muda

- `app/fields.py`: `FIELD_ID`, `FIELD_NOME`, `INPUT_*`, etc. (usados como defaults por tipo)
- `app/filters.py`: `FILTER_NUMBER`, `FILTER_DATE`, etc. (ainda usado pelo motor)
- `app/list.py`: classe `List`, `Field`, `build_filter_config`, `build_field_context` (usado pelo motor)
  - `Field.pos` removido — substituído por `List.linha` + `List.card_idx`
  - `List.linha`: índices 0-based dentro de `master_fields` que ficam na linha
  - `List.card_idx`: índices 1-based dentro de `fields` para campos exclusivos do cartão
  - `List.linha_fields` / `List.card_fields`: properties que retornam objetos `Field`
  - `fields_to_columns` não ordena mais por `pos`
- `app/form.py`: `handle_form`, `can_delete` (ainda usado pelas rotas form)
- `app/utils.py`: filtros Jinja (`brl`, `fmtid`, etc.)
- Propriedades dos fields (`input`, `query`, `options`, `filter`, `transform`, `currency`, `aggregate`, etc.)
