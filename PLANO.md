# PLANO — Refatoração do sistema

## Visão geral

Sistema configurado por **dicts puros** lidos por um **motor genérico**.

```
APP dict
  ├── módulo SITE   → pastas routes/site/   (público)
  ├── módulo SYS    → pastas routes/sys/    (autenticado)
  └── módulo ADMIN  → pastas routes/admin/  (supervisor)
       │
       └── cada entidade tem:
            ├── ENTIDADES (fields)
            ├── LIST     (listagem)
            ├── FORM     (formulário)
            └── blueprint + rotas
```

---

## `APP` — configuração central

```python
# routes/app_defs.py

SITE = {
    'url_prefix': '/',
    'menus': {
        'Sobre':     {'endpoint': 'site.sobre',      'icon': 'bi-info-circle'},
        'Produtos':  {'endpoint': 'site_vitrine.index', 'icon': 'bi-gift'},
        'Orçamento': {'endpoint': 'site_orcamento.index', 'icon': 'bi-file-text'},
        'Contato':   {'endpoint': 'site.contato',    'icon': 'bi-whatsapp'},
    },
}

SYS = {
    'url_prefix': '/',
    'menus': {
        'Cadastro': {
            'icon': 'bi-journal',
            'submenus': {
                'Categorias': {'endpoint': 'categories.list', 'icon': 'bi-journal'},
                'Insumos':    {'endpoint': 'insumos.list',    'icon': 'bi-box-seam'},
                'Produtos':   {'endpoint': 'products.list',   'icon': 'bi-gift'},
                'Contas':     {'endpoint': 'contas.list',     'icon': 'bi-people'},
                'Operações':  {'endpoint': 'operacoes.list',  'icon': 'bi-tags'},
                'Carteiras':  {'endpoint': 'carteira.list',   'icon': 'bi-wallet2'},
            },
        },
        'Comercial': {
            'icon': 'bi-cart',
            'submenus': {
                'Orçamentos': {'endpoint': 'orcamentos.list', 'icon': 'bi-file-text'},
                'Pedidos':    {'endpoint': 'orders.list',     'icon': 'bi-cart'},
                'Compras':    {'endpoint': 'compras.list',    'icon': 'bi-bag'},
            },
        },
        'Produção': {
            'endpoint': 'producao.list',
            'icon': 'bi-gear',
        },
        'Financeiro': {
            'icon': 'bi-cash-stack',
            'submenus': {
                'Recursos':         {'endpoint': 'recursos.list',             'icon': 'bi-piggy-bank'},
                'Contas a Receber': {'endpoint': 'transacao.receber_list',    'icon': 'bi-arrow-down-circle'},
                'Contas a Pagar':   {'endpoint': 'transacao.pagar_list',      'icon': 'bi-arrow-up-circle'},
                'Recebimentos':     {'endpoint': 'movimentos.recebimentos_list', 'icon': 'bi-cash'},
                'Pagamentos':       {'endpoint': 'movimentos.pagamentos_list',   'icon': 'bi-credit-card'},
                'Transferências':   {'endpoint': 'transferencias.trf_list',      'icon': 'bi-arrow-left-right'},
            },
        },
    },
}

ADMIN = {
    'role': 'supervisor',
    'menus': {},   # interno do motor
}

APP = {
    'nome': 'AlgoDoce',
    'logo': 'icons/Logo.png',
    'versao': 'v1.25.3-1',
    'site': SITE,
    'system': SYS,
    'admin': ADMIN,
}
```

**Regras**:
- Menus usam `endpoint` (nunca `url`), motor resolve com `url_for()`
- Sem `submenus` → link direto
- Com `submenus` → item expansível
- Módulo desabilitado: `'site': 'none'`
- Seleção do módulo: `url_prefix + autenticação`

---

## `ENTIDADES` — definição de fields

```python
CATEGORIAS = {
    'Category': {
        'fields': {
            'id':    {**FIELD_ID_SHORT, 'pos': 1},
            'nome':  {**FIELD_NOME, 'width': 13, 'pos': 1},
            'ordem': FIELD_ORDEM,
            'ativo': {**FIELD_ATIVO, 'width': 5},
        },
    },
}

PEDIDOS = {
    'Order': {
        'fields': {
            'id':                    FIELD_ID,
            'cliente':               {'query': 'conta', 'card_path': 'conta.nome', 'edit': False},
            'client_id':             {'input': 'select', 'query': 'conta', 'required': True,
                                      'query_filter': {'ativo': True, 'tipo': [0, 1]}},
            'data_pedido':           {**FIELD_DATA_HORA},
            'data_previsao_entrega': {**FIELD_DATA_HORA, 'label': 'Prev. Entrega'},
            'data_entrega':          {**FIELD_DATA_HORA},
            'carteira':              {'query': 'carteira', 'edit': False},
            'carteira_id':           {'input': 'select', 'query': 'carteira',
                                      'query_filter': {'uso': [0, 1]}},
            'forminhas':             {'input': 'select', 'options': FORMINHAS},
            'total':                 {**FIELD_TOTAL},
            'status':                {**FIELD_STATUS, 'options': ORDER_STATUS},
        },
    },
    'OrderItem': {
        'fields': {
            'product_id':      {'label': 'Produto', 'input': 'select'},
            'quantidade':      {**FIELD_QUANTIDADE},
            'preco_unitario':  {**FIELD_PRECO},
        },
    },
    'Event': { ... },
    'Previsao': { ... },
    'Movto': { ... },
}
```

- Chave = nome da classe SQLAlchemy
- `label` omitido → motor deriva via `_auto_label()`
- `fields` é a única propriedade obrigatória (futuro: +)

---

## `TABLE` — colunas para tabela inline

Usado em sessões de formulário e detalhe de listagem.

```python
ITENS_TABLE = {
    'colunas': {'OrderItem': ['product_id', 'quantidade', 'preco_unitario']},
    'totais': ['preco_unitario'],
}

ITENS_TABLE_COM_VALOR = {
    'colunas': {
        'OrderItem': ['product_id', 'quantidade', 'preco_unitario'],
        '_calc':     [{'name': 'valor', 'label': 'Valor', 'function': _valor_item,
                        'input': 'number', 'currency': 'brl', 'align': 'right',
                        'aggregate': 'sum'}],
    },
    'totais': ['preco_unitario', 'valor'],
}
```

- `'OrderItem'` → todos os fields
- `{'OrderItem': ['c1', 'c2']}` → específicos
- `'_calc'` → campos calculados (`function`)

---

## `LIST` — listagem

```python
CATEGORIAS_LIST = {
    'colunas': {'Category': ['id', 'nome', 'ordem', 'ativo']},
}

PEDIDOS_LIST = {
    'colunas': {'Order': ['id', 'cliente', 'data_pedido', 'total', 'status']},
    'detalhe': ITENS_TABLE,      # opcional: master-detail
    'botoes': [],
}
```

---

## `FORM` — formulário

```python
CATEGORIAS_FORM = {
    'fields': 'Category',
    'redirect': 'categories.list',
    'entity_label': 'Categoria',
    'delete_when': {Product},
    'pre_save': _pre_save,
    'post_save': _post_save,
    'botoes': [...],
    'body_template': None,       # None → usa page_form.html genérico
}

PEDIDOS_FORM = {
    'fields': 'Order',
    'redirect': 'orders.list',
    'entity_label': 'Pedido',
    'pre_save': _orders_pre_save,
    'sessions': {
        'Itens do Pedido': {
            'fields': 'OrderItem',
            'table': ITENS_TABLE,
            'type': 'editable_table',
            'template': 'sys/pedidos/_itens.html',
        },
        'Evento': {'fields': 'Event'},
        '*Financeiro': {'botoes': [gerar_btn]},
        'A RECEBER': {
            'fields': 'Previsao',
            'type': 'table', 'attr': 'transacao.previsoes',
            'when': lambda i: i and i.transacao,
        },
        'RECEBIMENTO': {
            'fields': 'Movto',
            'type': 'table', 'attr': 'movto',
            'when': lambda i: i and i.movto,
        },
    },
    'body_template': 'sys/pedidos/_form_body.html',  # exceção: custom
}
```

- `fields: 'Order'` → todos os fields
- `fields: {'Order': ['c1', 'c2']}` → específicos
- `body_template` = `None` → template genérico; se preenchido → custom

---

## Templates

```
app/templates/
├── components/
│   ├── page_base.html          ← base HTML
│   ├── page_site.html          ← herda base, menus do SITE
│   ├── page_sys.html           ← herda base, menus do SYS
│   ├── page_list.html          ← GENÉRICO (lê LIST)
│   ├── page_form.html          ← GENÉRICO (lê FORM)
│   ├── macros.html             ← action_list (já existe)
│   └── form_macros.html        ← render_fields (já existe)
│
├── site/                       ← templates específicos do site
│   └── ...
│
├── sys/categorias/             ← templates específicos (exceções)
├── sys/pedidos/                ← templates específicos (exceções)
└── ...
```

- `page_list.html` genérico → cobre ~80% dos casos
- `page_form.html` genérico → cobre ~80% dos casos
- Template específico via `body_template` no FORM (exceção)

---

## Estrutura final dos arquivos

```
app/
├── fields.py                    ← FIELD_*, INPUT_* templates (inalterado)
├── filters.py                   ← FILTER_* (pode migrar p/ engine)
│
├── engine/                      ← motor genérico (INFRAESTRUTURA)
│   ├── __init__.py
│   ├── auth.py                  ← login_manager, user_loader, 2FA, sessão
│   ├── auth_routes.py           ← /login, /logout, /settings
│   ├── menu.py                  ← resolve menus, active, modulo_atual
│   ├── handle_list.py           ← renderiza qualquer LIST
│   └── handle_form.py           ← renderiza qualquer FORM
│
├── routes/
│   ├── app_defs.py              ← APP, SITE, SYS, ADMIN
│   │
│   ├── site/                    ← módulo público (NEGÓCIO)
│   │   ├── __init__.py
│   │   ├── publico.py           ← /, /sobre, /contato
│   │   ├── vitrine.py           ← /vitrine/
│   │   └── orcamento.py         ← /orcamento
│   │
│   ├── sys/                     ← módulo autenticado (NEGÓCIO)
│   │   ├── __init__.py
│   │   ├── categorias.py        ← CATEGORIAS + LIST + FORM + blueprint + rotas
│   │   ├── produtos.py
│   │   ├── pedidos.py
│   │   ├── compras.py
│   │   ├── contas.py
│   │   ├── insumos.py
│   │   ├── operacoes.py
│   │   ├── carteira.py
│   │   ├── recursos.py
│   │   ├── transacao.py
│   │   ├── movimentos.py
│   │   ├── transferencias.py
│   │   ├── orcamentos.py
│   │   ├── producao.py
│   │   ├── relatorios.py
│   │   ├── api.py
│   │   └── uploads.py
│   │
│   ├── admin/                   ← módulo supervisor (NEGÓCIO)
│   │   └── __init__.py          ← futuro (usuários, grupos)
│   │
│   └── __init__.py
│
└── __init__.py                  ← create_app()
```

---

## Como a rota fica (ex: Categorias)

```python
# routes/sys/categorias.py

from app.engine import handle_list, handle_form

CATEGORIAS = {
    'Category': {
        'fields': {
            'id':    {**FIELD_ID_SHORT, 'pos': 1},
            'nome':  {**FIELD_NOME, 'width': 13, 'pos': 1},
            'ordem': FIELD_ORDEM,
            'ativo': {**FIELD_ATIVO, 'width': 5},
        },
    },
}

CATEGORIAS_LIST = {
    'colunas': {'Category': ['id', 'nome', 'ordem', 'ativo']},
}

CATEGORIAS_FORM = {
    'fields': 'Category',
    'redirect': 'categories.list',
    'entity_label': 'Categoria',
    'delete_when': {Product},
    'pre_save': _pre_save,
    'post_save': _post_save,
}

bp = Blueprint("categories", __name__, url_prefix="/categorias")

@bp.route("/")
def list():
    return handle_list('Category', CATEGORIAS_LIST)

@bp.route("/novo", defaults={"id": None}, methods=["GET", "POST"])
@bp.route("/<int:id>/editar", methods=["GET", "POST"])
def form(id=None):
    return handle_form(CATEGORIAS_FORM, id)
```

---

## Motor — fluxo `handle_list()`

```
handle_list('Category', CATEGORIAS_LIST)
  │
  ├── 1. Acha ENTIDADES que contém 'Category' (busca em todos os módulos)
  ├── 2. Lê colunas: {'Category': ['id','nome','ordem','ativo']}
  ├── 3. Monta Field[]: merge colunas + fields da entidade
  ├── 4. Constrói filtros (de input/options de cada field)
  ├── 5. Query: Category.query.all()
  ├── 6. Aplica filtros ativos da URL
  ├── 7. Formata colunas (currency, mask, link, aggregate)
  ├── 8. Template = CATEGORIAS_LIST.template or 'components/page_list.html'
  └── 9. Renderiza com dados + LIST + módulo ativo (menus no template)
```

---

## Motor — fluxo `handle_form()`

```
handle_form(CATEGORIAS_FORM, id)
  │
  ├── 1. Pega model de CATEGORIAS['Category']
  ├── 2. Lê fields: 'Category' → todos os fields da entidade
  ├── 3. GET  → renderiza formulário (fields + sessions)
  ├── 4. POST → valida, aplica transform, pre_save, salva, post_save
  ├── 5. Template = FORM.body_template or 'components/page_form.html'
  └── 6. Renderiza com FORM config + dados do instance
```

---

## Motor — auth

```python
# engine/auth.py
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id): ...

@login_manager.unauthorized_handler
def unauthorized(): ...   # redireciona para site
```

```python
# engine/auth_routes.py
bp = Blueprint("auth", __name__)

@bp.route("/login", methods=["GET", "POST"])
def login(): ...

@bp.route("/logout")
def logout(): ...

@bp.route("/settings")
def settings(): ...
```

Blueprint registrado automaticamente em `create_app()`.

---

## Motor — menu

```python
# engine/menu.py

def modulo_atual():
    """Retorna SITE, SYS ou ADMIN baseado em url_prefix + auth."""
    ...

def menu_ativo(modulo, path):
    """Retorna menu/submenu com classe 'active' para o path."""
    ...

def url_do_item(item):
    """Resolve endpoint via url_for() ou retorna url direta."""
    ...

def menus_para_json(modulo):
    """Serializa menus para JS (mobile nav)."""
    ...
```

Context processors em `create_app()`:

```python
@app.context_processor
def inject_app():
    return {
        'APP': APP,
        'modulo': modulo_atual(),
        'modulo_menus_json': json.dumps(menus_para_json(modulo_atual())),
    }
```

---

## O que NÃO muda

- `app/fields.py`: `FIELD_ID`, `FIELD_NOME`, `INPUT_*`, etc.
- `app/filters.py`: `FILTER_NUMBER`, `FILTER_DATE`, etc.
- `app/list.py`: `MODEL_MAP`, `register_model()`, helpers
- Propriedades dos fields (`input`, `query`, `options`, `filter`, `transform`, `currency`, `aggregate`, etc.)
- `engine/handle_form.py`: reusa lógica de `handle_form()` atual (validação, transform, save)

---

## Ordem de implementação

1. Criar pastas `routes/site/`, `routes/sys/`, `routes/admin/`
2. Mover arquivos existentes para as pastas (sem alterar conteúdo)
3. Criar `routes/app_defs.py` com `APP`, `SITE`, `SYS`, `ADMIN`
4. Criar `engine/menu.py` + context processor (injetar `modulo` nos templates)
5. Adaptar `page_sys.html` para ler menus do `modulo` (remover hardcoded)
6. Adaptar `page_site.html` para ler menus do `modulo`
7. Remover `SUB_NAV_SECTIONS` do JS inline
8. Criar `engine/handle_list.py` + `components/page_list.html` genérico
9. Migrar **Categorias** primeiro (entidade simples)
10. Migrar uma entidade complexa (Pedidos ou Compras)
11. Criar `engine/auth.py` + `engine/auth_routes.py` (extrair de `routes/sys_auth.py`)
12. Migrar demais entidades gradualmente
