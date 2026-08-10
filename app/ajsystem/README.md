# AJSYSTEM — framework declarativo de listas e formulários

O **ajsystem** é um framework web (Flask) para construir aplicações de gestão
(CRUD) de forma **declarativa**: você define *entidades*, *listas* e *formulários*
em dicionários Python e o framework monta blueprints, rotas, telas, autenticação
e menu automaticamente.

Este README ensina a criar um **novo app do zero** usando o framework e serve de
referência completa de configuração.

---

## Checklist de revisão

Estado de cada propriedade do contrato, validado página a página. A revisão
guia a reorganização deste README ao final: marcas somem e as seções de
referência (§5–§7) passam a refletir somente o contrato aprovado.

Legenda: `✓` aprovada · `✗` desaprovada (deprecada) · `~` quebrada (a corrigir) · `vazio` pendente.

| Propriedade | Estado | Onde validada |
|---|---|---|
| `attrs` (Field) | ✗ | Categorias — substituída por `min`/`max`/`step`; reavaliar se necessário |
| `type` (Field) | ✓ | Categorias — `ID`, `TEXT`, `INT`, `BOOL` |
| `width` (Field) | ✓ | Categorias — `id` |
| `mask` (Field) | ✓ | Categorias — `ordem` (`'999'`) |
| `min` (Field) | ✓ | Categorias — `ordem` |
| `max` (Field) | ✓ | Categorias — `ordem` |
| `step` (Field) | ✓ | Categorias — `ordem` (INT → `1`) |
| `fields` (List) | ✓ | Categorias — `['Category']` (renomeada de `columns`) |
| `ordering` (List) | ✓ | Categorias — `['ordem', 'nome']` |
| `title` (List) | ✓ | Categorias |
| `fields` (Form) | ✓ | Categorias — `'Category'` |
| `delete` (Form) | ✓ | Categorias — `when`, `msg_ok`, `msg_no` |
| `pre_save` (Form) | ✓ | Categorias — auto-ordenação `ordem` |
| `post_save` (Form) | ✓ | Categorias — reordenação |
| `buttons` (Form) | ✓ | Categorias — `on_off` |
| `DK` (Field) | ✓ | Insumos — `ingredient_id`/`product_id` (chave da linha-pai; oculto, `in_form=False`) |
| `MULT10` (Field) | ✓ | Insumos — `etapas` (códigos concatenados, máx. 10 opções 0-9; editor genérico abre em modal) |
| `masterkey` (Field·FK) | ✓ | Insumos — opcional: `product_id` sem `masterkey` (query derivado da relação) |
| `label` (Field) | ✓ | Insumos — `product_id` → 'Produto' |
| `required` (Field) | ✓ | Insumos — `product_id`, `unidade_medida`, `fator`, `unidade` |
| `decimals` (Field) | ✓ | Insumos — `fator` |
| `on_set` (Field) | ✓ | Produtos — `ingredient_id` (qtd/unidade); Orçamentos — `product_id` (preço); Insumos — `unidade` (fator=1) |
| `in_form` (Field) | ✓ | Gate do form (renomeada de `edit`): `False` exclui do form sem submeter — Operações `indice`; Orçamentos `valor`/`order_id`; Pedidos `cliente`/`carteira`/`transacao`/`quote_id`; Produtos `ativo`; defaults `ID`/`DK` |
| `in_list` (Field) | ✓ | Coluna na tabela e/ou card: `0` exclui da listagem/card/filtro; `1` coluna na linha (vai p/ o card quando não couber, padrão); `2` sempre no card — Produtos `descricao` (`in_list: 2`; `True`→`1`, `False`→`0`) |
| `readonly` (Field) |  | a validar — exibe valor sem edição no form, submete via hidden |
| `hidden` (Field) |  | a validar — campo invisível que submete via `<input type="hidden">` |
| `transform` (Field) | ✓ | Insumos — `nome` ('title') |
| `list` (Field) | ✓ | Insumos — `tipo`/`unidade_medida` (LIST) e `etapas` (MULT10) |
| `sessions` (Form) | ✓ | Insumos — `Conversões` e `Produtos` (explícitas) |
| `table` (Form·sessions) | ✓ | Insumos — `['UnitConversion']`, `['ProductIngredient']` |
| `readonly` (Form·sessions) | ✓ | Insumos — sessão `Produtos` renderizada como texto |
| `ID` em coluna FK (Field) | ✗ | Insumos — `ingredient_id`/`product_id` eram `ID`; usar `DK` (linha-pai) ou `FK` |
| `LIST` em campo multivalorado (Field) | ✗ | Insumos — `etapa` (valor único) → `MULT10` (`etapas`) |

---

## Índice

1. [Visão geral do framework](#1-visão-geral-do-framework)
2. [Criando um novo app do zero](#2-criando-um-novo-app-do-zero)
3. [Definições do App — APP, SITE, SYS, ADMIN e Temas](#3-definições-do-app)
4. [Módulos (rotas declarativas)](#4-módulos-rotas-declarativas)
5. [Entity — definição de campos](#5-entity--definição-de-campos)
6. [List — configuração](#6-list--configuração)
7. [Form — configuração](#7-form--configuração)
8. [Exemplo completo do zero](#8-exemplo-completo-do-zero)

---

## 1. Visão geral do framework

### 1.1 O que ele faz

A partir de três dicionários declarativos por módulo:

| Declaração | Para que serve |
|---|---|
| `Entity` | Define os **campos** (nome, tipo, máscara, referências, validação) |
| `List` | Define a **listagem** (colunas, ordenação, cards, detalhes, filtros) |
| `Form` | Define o **formulário** (campos, tabelas filhas, exclusão, hooks, botões) |

O framework cuida de todo o resto:

- Rotas de listagem, criação, edição, exclusão e *toggle* (ativa/desativa);
- Formulários com validação, máscaras, upload de imagens e campos de referência (FK);
- Autenticação (login, logout, "lembrar-me") e proteção `login_required` em todas as rotas CRUD;
- Menu dinâmico (site público, sistema e admin) com submenus e ícones;
- Templates prontos (Tailwind + DaisyUI + Heroicons) para página, lista e formulário;
- **Temas** de cores centralizados em um único dicionário;
- Filtros Jinja e globals utilitários (`fmtdate`, `brl`, `mask`, `deep_attr`, `CONECTORES`, `aj_uploads_endpoint`, ...).

### 1.2 O que você precisa fornecer (o "contrato")

O framework não conhece sua aplicação. Ele recebe tudo através de um **adaptador**
(`app_config.py`) e da declaração `APP`/`SYS`/`SITE`/`ADMIN`. Você deve entregar:

1. **O app Flask** criado (`create_app`) — o framework apenas faz `init_app(app)`.
2. **Um adaptador** `app_config.py` expondo `db`, `login_manager`, `User`, `Setting`, `APP`, `SYS` e o endpoint de uploads.
3. **Models SQLAlchemy** em `app/models/` (um por entidade).
4. **Módulos declarativos** em `app/routes/sys/` (Entity + List + Form).
5. **`app/routes/app_defs.py`** com `Temas`, `APP`, `SITE`, `SYS`, `ADMIN`.

### 1.3 Estrutura de pastas do framework

O framework é a pasta `app/ajsystem/`:

```
 ajsystem/
 ├── __init__.py           # exports (init_app; blueprint ajsystem; filtro heroicon)
 ├── init.py               # init_app(app): wiring de tudo
 ├── core/                 # motor/runtime do framework
 │   ├── app_config.py     # ADAPTADOR — único ponto de acoplamento com o app
 │   ├── auto.py           # auto.rota, montar_blueprint, registrar_modulos
 │   ├── menu.py           # url_do_item: resolve menus → endpoints
 │   ├── utils.py          # helpers (item_ref, deep_get, ...)
 │   ├── filters.py        # comportamento de filtros (resolve/apply_*)
 │   ├── form.py           # Form; sessions; hooks; handle_form
 │   ├── list.py           # listagem/colunas; usa defs.entities
 │   ├── report.py         # agregação/ordenação de relatórios
 │   └── edits.py          # assets de editores (rich text)
 ├── defs/                 # definições declarativas (sem lógica de request)
 │   ├── constants.py      # CONECTORES (conectivos de títulos)
 │   ├── fields.py         # FIELD_TYPES — tipos de campo base; VALIDATORS; fmt_mask
 │   ├── buttons.py        # Button/ConfirmModal; presets BTN_*
 │   ├── filters.py        # constantes FILTER_*/MODE_*
 │   └── entities.py       # Field/List; build_field_config; register_model; MODEL_MAP
 ├── handles/              # ações de request (handlers)
 │   ├── render_list.py    # render_list + resolvers de colunas/ordenação
 │   └── auth.py           # init_auth + blueprints auth e seguranca (login/logout/chave)
 ├── templates/
 │   ├── pages/            # base.html, sys.html, list.html, form.html, macros.html
 │   └── components/       # form_macros.html, item_table.html, image_widget.html, ...
 ```

 O bloco `defs/` contém as definições declarativas (estrutura de entidades,
 tipos, filtros e botões); `handles/` concentra os pontos de entrada de request
 (render_list, auth); `core/` reúne o motor/runtime. **Nenhum** deles deve ser
 importado diretamente pelo seu código de módulo — use apenas os exports de
 alto nível descritos aqui (em geral via `core`).

---

## 2. Criando um novo app do zero

### 2.1 Requisitos

- Python 3.10+
- PostgreSQL (o framework usa `psycopg2`)
- Node.js (apenas se você precisar rebuildar o CSS — ver §2.6)

Dependências mínimas (`requirements.txt`):

```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.0.5
Flask-WTF==1.2.1
WTForms==3.1.1
psycopg2-binary==2.9.9
python-dotenv==1.0.0
markdown==3.5.1
requests==2.31.0
Flask-Login
```

### 2.2 Estrutura de pastas do novo app

```
meu_app/
├── app/
│   ├── __init__.py          # create_app(): bootstrap + init_app(app)
│   ├── extensions.py        # db = SQLAlchemy(); login_manager; migrate
│   ├── config.py            # Config: SQLALCHEMY_DATABASE_URI, SECRET_KEY, ...
│   ├── ajsystem/            # o framework (esta pasta)
│   ├── app_config.py        # ADAPTADOR (dentro de ajsystem/ — edite)
│   ├── app_defs.py          # Temas, APP, SITE, SYS, ADMIN  ← comece aqui
│   ├── models/              # SQLAlchemy models (1 arquivo por entidade)
│   │   ├── __init__.py      # importa todos os models
│   │   ├── user.py          # User (obrigatório p/ autenticação)
│   │   ├── setting.py       # Setting (obrigatório p/ sessão/senha do painel)
│   │   ├── category.py
│   │   └── product.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── sys/             # módulos CRUD declarativos
│   │   │   ├── categorias.py
│   │   │   └── produtos.py
│   │   └── site/            # páginas públicas (opcional)
│   ├── templates/           # templates custom da app
│   │   └── sys/             # sessões/templates de módulos (ver §7.4)
│   ├── static/              # css, js, img (logo, favicon)
│   └── migrations/          # geradas pelo Flask-Migrate
├── dados/
│   ├── uploads/             # imagens enviadas (upload_path)
│   └── paginas/             # páginas markdown (render_pagina)
├── requirements.txt
├── .env                     # variáveis de ambiente
└── run.py                   # app = create_app(); app.run()
```

> **Ordem recomendada de implementação:** (1) `app_defs.py` → (2) `models/` →
> (3) `app/routes/sys/` com os 3 dicionários → (4) `app/__init__.py` →
> (5) `app_config.py`. As seções 3 a 7 explicam cada passo em detalhe.

### 2.3 Bootstrap — `app/__init__.py`

```python
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app():
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config.from_object('app.config.Config')

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    from app.ajsystem import init_app as init_ajsystem
    init_ajsystem(app)

    from app import models  # noqa: garante registro dos models
    from app.ajsystem.core.list import register_model
    from app.models.user import User
    from app.models.category import Category
    register_model('user', User)
    register_model('category', Category)

    return app
```

`init_app(app)` (em `app/ajsystem/init.py`) faz todo o wiring: registra os
blueprints (`ajsystem`, `auth`, `seguranca`), configura o `login_manager` com o
loader a partir do seu `User`, injeta filtros/globals no Jinja, registra os
módulos a partir de `SYS['menus']` e configura os endpoints de upload.

> O `register_model` registra a chave usada nas referências (`'category'`).
> Se você **não** registrar, o framework tenta importar automaticamente
> `app.models.<chave>` (§4.6).

### 2.4 Adaptador — `app_config.py`

Este é o **único ponto de acoplamento** entre o framework e a sua app. O
framework importa tudo daqui, nunca diretamente de `app.models` etc.:

```python
from app.extensions import db, login_manager
from app.models.user import User
from app.models.setting import Setting
from app.app_defs import APP, SYS, Temas   # que você define (seção 3)
from flask import url_for


def get_uploads_endpoint(app):
    """Endpoint usado para servir as imagens enviadas."""
    return app.config.get('AJ_UPLOADS_ENDPOINT') or 'uploads.uploaded_file'
```

O que o adaptador deve expor:

| Nome | Tipo | Para que serve |
|---|---|---|
| `db` | `SQLAlchemy` | queries feitas pelo motor |
| `login_manager` | `LoginManager` | autenticação |
| `User` | Model | login (deve ter `username`, `check_password`, `set_password`) |
| `Setting` | Model | armazenamento de `Setting.get('chave')` (painel, sessão) |
| `APP` | dict | definições do app (tema, nome, menus) |
| `SYS` | dict | alias de `APP['system']` (menus do sistema) |
| `get_uploads_endpoint(app)` | callable | endpoint das imagens |

O `get_uploads_endpoint` retorna `'uploads.uploaded_file'` por padrão. Você pode
mudar para um endpoint seu (ex.: `'media.serve'`) ou usar a config
`AJ_UPLOADS_ENDPOINT`. Os templates usam o global `aj_uploads_endpoint()` para
montar as URLs das imagens.

### 2.5 Variáveis de ambiente (`.env`)

```
SECRET_KEY=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...
POSTGRES_DB=...
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
ADMIN_PASSWORD=...            # senha padrão do usuário admin (primeiro login)
ADMIN_EMAIL=...
UPLOAD_PATH=dados/uploads     # pasta das imagens (upload_path)
```

> Variáveis de leitura adicional: `FLASK_APP=app`, `FLASK_DEBUG=1`.

### 2.6 Estáticos e CSS

Os templates usam **Tailwind CSS** e **DaisyUI**. Classes novas de tema podem
exigir rebuild:

```
npm install
npm run build:css
```

Se a sua app não tem build, use o CSS pré-compilado de `static/`. Os ícones vêm
de `components/heroicons.svg` (sprite inline, ícones por nome — ex.: `trash`,
`pencil-square`, `arrow-path`, `paper-airplane`, `check`, `xmark`, ...).

---

## 3. Definições do App

Todo o app é descrito em `app/app_defs.py`, começando pelos **temas** e depois
pelos dicionários `APP`, `SITE`, `SYS` e `ADMIN`.

### 3.1 Temas (tokens de cor)

```python
Temas = {
    'doceira': {
        'marca':   {'cor': '#e06f98', 'suave': '#fbe5ed'},
        'neutras': {'topo': '#f7f5f3', 'corpo': '#fff', 'texto': '#333',
                    'texto_inv': '#fff', 'card': '#fff', 'borda': '#eee',
                    'topbar': '#fff', 'card_header': '#faf7f6', 'tabela_alt': '#faf7f6'},
        'feedback': {'ok': '#3e9e6c', 'erro': '#d9534f', 'aviso': '#e0a800',
                     'info': '#4096b5'},
        'apoio':   {'novo': '#6c4f9e', 'excluir': '#d9534f', 'salvar': '#3e9e6c'},
        'barras':  {'vermelha': '#c0392b', 'laranja': '#e67e22', 'amarela': '#f1c40f',
                    'verde': '#27ae60', 'azul': '#2980b9', 'azul_escuro': '#1f3a5f',
                    'cinza': '#95a5a6'},
    },
}
```

Cada grupo alimenta classes CSS no template base:

| Grupo | Uso |
|---|---|
| `marca.cor` / `marca.suave` | cor da marca e variação suave |
| `neutras` | topo/corpo/texto/cards/bordas/tabelas |
| `feedback` | mensagens ok/erro/aviso/info |
| `apoio` | botões padrão (novo, excluir, salvar) |
| `barras` | cores de badges/barras (ex.: botões `color='azul'`) |

### 3.2 `APP` — as propriedades e o que pode ser inserido

O dicionário `APP` descreve a aplicação. **Cada propriedade** abaixo indica o que
pode ser inserido e a referência para a definição completa:

```python
APP = {
    'nome': 'Algodocê',          # nome exibido no topo/menu
    'logo': 'logo.png',          # arquivo em app/static/
    'versao': '1.0.0',           # versão exibida no rodapé
    'tema': 'doceira',           # chave do dicionário Temas  →  §3.1
    'site':  {...},              # menus públicos            →  §3.3 (SITE)
    'system': {...},             # menus do sistema (CRUD)   →  §3.3 (SYS)
    'admin': {...},              # menus administrativos     →  §3.3 (ADMIN)
}
```

| Propriedade | Tipo | O que pode ser inserido | Ver § |
|---|---|---|---|
| `nome` | str | Nome do app exibido no cabeçalho e nos títulos | — |
| `logo` | str | Nome do arquivo em `app/static/` (ex.: `'logo.png'`). Vazio para não exibir | — |
| `versao` | str | Versão mostrada no rodapé (ex.: `'1.0.0'`) | — |
| `tema` | str | Chave do dicionário `Temas`; define todas as cores | [§3.1](#31-temas-tokens-de-cor) |
| `site` | dict | Menu público (home, vitrine). Mesma estrutura de menu de `SYS` | [§3.3](#33-menus-site-sys-admin) |
| `system` | dict | Menu do sistema — cada item vira um módulo CRUD | [§3.3](#33-menus-site-sys-admin) |
| `admin` | dict | Menu administrativo (sessão, configurações) | [§3.3](#33-menus-site-sys-admin) |

> As propriedades `site`, `system` e `admin` são acessadas pelos blueprints para
> o redirect após login e para a construção do menu (sidebar + topbar). O acesso
> de `system` também está disponível como `SYS` (adaptador).

### 3.3 Menus (SITE, SYS, ADMIN)

A estrutura de cada menu é um dict:

```python
'system': {
    'url_prefix': '/',            # prefixo das rotas CRUD
    'home': 'pagina_inicial',     # endpoint da home após login
    'menus': [
        {'endpoint': 'categorias.list', 'icon': 'tag'},        # sem submenu
        {'label': 'Estoque', 'icon': 'archive-box', 'submenus': [  # com submenu
            {'endpoint': 'insumos.list', 'label': 'Insumos'},
            {'endpoint': 'produtos.list', 'label': 'Produtos'},
        ]},
    ],
}
```

Propriedades de um item de menu:

| Propriedade | Obrigatória | O que é |
|---|---|---|
| `endpoint` | uma das duas | Nome do endpoint do módulo (ex.: `'produtos.list'`). Se ausente, usa o `label` |
| `label` | sim* | Rótulo exibido; usado para derivar o slug do módulo quando `endpoint` ausente |
| `icon` | não | Nome do ícone Heroicon (ex.: `'tag'`, `'archive-box'`, `'users'`) |
| `submenus` | não | Lista de itens-filhos com `endpoint`/`label`/`icon` |
| `url` | não | URL fixa (se não for módulo do framework) |

> O **slug** do item (derivado do `endpoint` — ou do `label`, normalizado sem
> acentos) define o módulo Python em `app.routes.sys.<slug>` — veja §4.4. Por
> isso itens com `submenus` ou sem `endpoint` precisam de `label`.

---

## 4. Módulos (rotas declarativas)

### 4.1 O que é um módulo

Um módulo é um arquivo Python em `app/routes/sys/` que declara os dicionários
`Entity`, `List` e (opcionalmente) `Form`:

```python
# app/routes/sys/categorias.py
Entity = {
    'Category': {
        'id':    {'type': 'ID'},
        'nome':  {'type': 'TEXT'},
        'ativo': {'type': 'BOOL'},
    },
}

List = {
    'fields': ['Category'],
    'ordering': ['nome'],
}

Form = {
    'fields': 'Category',
    'buttons': ['on_off'],
}
```

Sem `bp = Blueprint(...)` o framework **monta o blueprint automaticamente** e
cria, protegidas por `login_required`:

| Rota | Endpoint | Método | Quando |
|---|---|---|---|
| `/<slug>/` | `<slug>.list` | GET | sempre |
| `/<slug>/novo` e `/<slug>/<id>/editar` | `<slug>.form` | GET/POST | sempre |
| `/<slug>/<id>/excluir` | `<slug>.delete` | POST | se `Form['delete']` |
| `/<slug>/<id>/toggle` | `<slug>.toggle` | GET | se `Form['toggle']` ou botão `on_off` |

### 4.2 Modo declarativo vs modo legado

| Modo | Como | Quando usar |
|---|---|---|
| Declarativo | Apenas `Entity`/`List`/`Form` (+ `@auto.rota` para rotas extras) | módulos novos — recomendado |
| Legado | Definir `bp = Blueprint('x', __name__)` e rotas próprias | integrar módulos existentes; o menu continua apontando para `x.list` |

Se você definir `bp`, o framework **respeita o blueprint e não sobrescreve** as
suas rotas.

### 4.3 As três declarações

- **`Entity`** — mapa `nome_da_entidade → campos`. Cada campo é um dict de
  propriedades ([§5](#5-entity--definição-de-campos)). Pode ter **várias
  entidades** no mesmo módulo (ex.: `Product` e `ProductIngredient`).
- **`List`** — dict com `fields`, `ordering`, `title`, etc. ([§6](#6-list--configuração)).
- **`Form`** — dict com `fields`, `sessions`, `delete`, `buttons` e hooks
  ([§7](#7-form--configuração)). Também pode ser `Form(...)` da dataclass
  (`app.ajsystem.core.form`); `handle_form` aceita ambos.

### 4.4 Registro do módulo (menu → blueprint)

O framework percorre `SYS['menus']` (via `registrar_modulos(app, menus)`) e, para
cada item sem `url` fixa:

1. Deriva o slug (do `endpoint`, ou do `label` normalizado);
2. Importa o módulo `app.routes.sys.<slug>`;
3. Se o módulo **não** tem `bp`, monta o blueprint declarativo e o registra com
   `url_prefix = SYS['url_prefix'] + slug`.

> O menu e o blueprint usam o mesmo slug, então a ordem das seções **3.3 → 4.4**
> é consistente: `label`/`endpoint` no menu, `Entity`/`List`/`Form` no módulo.

### 4.5 Rotas custom — `@auto.rota`

```python
from app.ajsystem.core.auto import auto
from flask import jsonify

@auto.rota("/search")
def search():
    q = request.args.get("q", "").strip()
    items = Product.query.filter(Product.nome.ilike(f"%{q}%")).limit(10).all()
    return jsonify([{"id": p.id, "nome": p.nome} for p in items])
```

O decorator registra a rota no blueprint **do módulo atual** (detectado pelo
arquivo). O `endpoint` padrão é o nome da função.

> Você pode **substituir uma rota gerada** declarando-a com o mesmo endpoint —
> ex.: `@auto.rota('/<int:id>/excluir', methods=['POST'], endpoint='delete')`
> implementa a exclusão manualmente (a rota gerada é ignorada).

### 4.6 Modelos e `MODEL_MAP`

O framework resolve a model de uma entidade em duas etapas:

1. **`MODEL_MAP`** — registro explícito via `register_model('category', Category)`
   em `app/__init__.py` (recomendado);
2. **Fallback** — importa `app.models.<chave>` e busca a classe com o nome da
   entidade.

> Use `register_model` para evitar import dinâmico (mais rápido e sem erro de
> circular import).

---

## 5. Entity — definição de campos

### 5.1 Tipos de campo (`FIELD_TYPES`)

Cada campo é `{'type': '<TIPO>', ...}` — **sempre em maiúsculas**. Tipos
disponíveis (`app/ajsystem/defs/fields.py`):

| Tipo | input | Props base aplicadas |
|---|---|---|
| `TEXT` | `text` | — |
| `MEMO` | `textarea` | `rows` p/ altura |
| `INT` | `number` | `align: right`, `width: 5`, `decimals: 0` |
| `NUM` | `number` | `align: right`, `width: 10`, `decimals: 2` |
| `ID` | `number` | PK da tabela; `in_form: False`, `label: '#'`, `filter` numérico |
| `DK` | `number` | Ligação filho→pai (sessão); `in_form: False`, preenchido pelo motor |
| `DATA` | `date` | `filter` por data |
| `DATA_HORA` | `datetime-local` | `filter` por data |
| `HORA` | `time` | — |
| `BOOL` | `boolean` | `filter` Sim/Não (checkbox) |
| `FONE` | `text` | `mask: '(99) 99999-9999'`, `digits_only: True` |
| `CPF` | `text` | `mask: '999.999.999-99'`, `digits_only`, `validate: 'cpf'` |
| `CNPJ` | `text` | `mask: '99.999.999/9999-99'`, `digits_only`, `validate: 'cnpj'` |
| `FK` | `select` | `filter` select; referência a outra entidade — `masterkey` opcional, veja §5.2 |
| `LIST` | `select` | `filter` select; opções fixas via `list`/`options` |
| `MULT10` | `multi` | Opções fixas via `list`/`options` (máx. 10, códigos 0-9); editor genérico em modal; persiste códigos concatenados |
| `IMAGE` | `image` | `filter: False`, widget de preview/upload |

> As props base do tipo são **mescladas** com as da entidade e do form — você
> pode sobrescrever/estender qualquer uma (ex.: `{'type': 'BOOL', 'in_form': False}`).
> `required` é sempre **opt-in** (`'required': True`), nunca herdado do tipo.
> No formulário, a referência de um campo `*_id` pode ser **derivada da relação**
> do model (em vez de `masterkey`) — veja §5.4.

### 5.2 Referência de propriedades de campo

| Propriedade | Tipo | Uso |
|---|---|---|
| `type` | str | O tipo, da tabela §5.1, em maiúsculas. **Obrigatória** |
| `label` | str | Rótulo exibido (auto-derivado do nome se ausente) |
| `width` | int | Largura em caracteres (colunas/listagem) |
| `align` | str | `'left'` (padrão) \| `'right'` \| `'center'` |
| `input` | str | Sobrescreve o widget (`text`, `textarea`, `number`, `date`, `boolean`, `select`, `image`, ...) |
| `required` | bool | Obrigatório (validação de presença) |
| `in_form` | bool | `False` não renderiza o campo no form (nem exibe nem submete) |
| `in_list` | int | `0` exclui o campo da listagem, do card e do filtro; `1` coluna na linha (vai p/ o card quando não couber); `2` sempre no card; padrão `1`. `True`→`1`, `False`→`0` |
| `readonly` | bool | Exibe o valor como texto estático no form (sem edição); o valor é submetido via `<input type="hidden">` (preserva valores preenchidos por `on_set`) |
| `hidden` | bool | Invisível no form; submete o valor via `<input type="hidden">` (controle interno) |
| `default` | any | Valor inicial de novos registros |
| `attrs` | dict | Atributos HTML do input (ex.: `{'min': 0, 'step': 1}`) |
| `mask` | str | Máscara de formatação (ex.: `'999.999'`) |
| `digits_only` | bool | Remove não-dígitos antes de aplicar a máscara |
| `decimals` | int | Casas decimais (gera máscara se `mask` ausente) |
| `currency` | bool | Formata como moeda (`brl`) |
| `derived` | dict | Campo **virtual** (sem coluna no banco): `{'sum': '<caminho>'}` soma as folhas do caminho, atravessando coleções (ex.: `'items.quantidade'`). Calculado na renderização (células, colunas e agregados) |
| `hide_zero` | bool | Ocultar valores zero na listagem (padrão `True`) |
| `masterkey` | str | **FK (opcional)**: chave do `MODEL_MAP` (ex.: `'category'`) — popula o select, e `card_path`/`filter_path` viram `<chave>.nome`. Sem ele, a referência é derivada da relação do model no form (§5.4). Em campos `DK` o padrão é a **primeira tabela da `Entity`** |
| `list` | dict | **LIST/MULT10**: opções fixas `{valor: rótulo}` (alias de `options`) |
| `options` | dict | Opções do select (ou `{'model': ..., 'order': ...}`) |
| `query` | str | Chave do `MODEL_MAP` p/ popular opções do banco |
| `query_filter` | dict | Filtro aplicado na query de opções |
| `filter` | dict/str/False | Filtro de lista. `False` desabilita; senão inferido do `input` |
| `filter_options` | list | Opções customizadas do filtro select |
| `filter_path` | str | Atributo usado no filtro de referência (padrão `'<chave>.nome'` via masterkey) |
| `card_path` | str | Acesso aninhado de exibição (padrão `'<chave>.nome'` via masterkey) |
| `validate` | str/callable | `'cpf'`/`'cnpj'` ou função `(valor) -> bool` |
| `transform` | str/callable | Transformação ao salvar: `'title'` (padrão em textos editáveis), `'cap'` (só o 1º caractere maiúsculo), `'upper'`, `'lower'`, `'none'` ou callable `(val, field)` |
| `rows` | int | Altura do textarea (MEMO) |
| `upload_path` | str | Pasta relativa dos uploads de IMAGE |
| `link` | str | Endpoint p/ link da célula (ex.: `'produtos.list'`) |
| `function` | callable | Valor computado na coluna: `f(item) -> valor` |

### 5.3 Filtros de lista

Campos com filtro habilitado ganham widget na tela de lista. O filtro é inferido
do `input` do campo (text → busca, number → intervalo, date → período,
boolean/select → Sim/Não/listas) e pode ser forçado/desabilitado com `filter`:

```python
{'type': 'TEXT', 'filter': 'text'}        # explícito
{'type': 'MEMO', 'filter': False}         # desabilita
```

Referências (`FK`/`masterkey`) geram select com as opções do banco
automaticamente. O rótulo de cada filtro na aba **Filtros** segue o
`label`/`display_label` do campo (não o nome cru — ex.: `carteira_id` →
"Carteira").

### 5.4 Chave reservada `__meta__`, referências derivadas e `aggregate`

**`__meta__`** — toda entrada da `Entity` é um dict de campos; chaves que
começam com `__` são **reservadas** e não viram campos. Hoje existe apenas
`__meta__`:

```python
'ProductIngredient': {
    '__meta__': {'label': 'Insumos', 'readonly': True},  # rótulo/readonly da sessão derivada
    'ingredient_id': {'type': 'FK', 'required': True},
    ...
}
```

- `label` — rótulo da sessão no form (padrão: nome da relação);
- `readonly` — sessão somente-leitura (sem adicionar/remover).

**Referência derivada da relação** — um campo `*_id` sem `masterkey`/`query` tem
o `query` resolvido automaticamente pelo motor a partir da relação do model do
filho (ex.: `product_id` em `quote_item` → `query='product'`). Vale para campos
de sessões **e** do form principal (ex.: `category_id` em `Product` →
`query='category'`). O alvo precisa estar em `MODEL_MAP` (§4.6).

**Selects `LIST` com valor fora do padrão** — o select e o rótulo aceitam o
valor salvo mesmo que a caixa/maiúscula não bata com a chave da `list`
(ex.: `'kg'` salvo → mostra a opção `'Kg'` selecionada). Ao salvar o registro,
o valor é normalizado para a chave padrão.

**Campo `DK` (detail key)** — marca a coluna que liga a linha filha à **tabela
principal da `Entity`** (a primeira chave da `Entity`, ex.: `ingredient_id` na
sessão "Conversões" de um Insumo). É `in_form: False`, não participa de validação
e é preenchido automaticamente pelo motor ao salvar (FK para o pai). Se
`masterkey`/`query` não forem dados, o padrão é a chave `MODEL_MAP` da primeira
tabela da `Entity`:

```python
'UnitConversion': {
    'id':            {'type': 'ID'},   # PK
    'ingredient_id': {'type': 'DK'},   # ligação com o Insumo (pai)
    ...
}
```

**Campo `MULT10`** — múltiplas opções fixas (`list`/`options`), limitadas a
**10 opções com códigos de 1 caractere (0-9)**; o valor persistido é a
concatenação dos códigos marcados, sem separador (ex.: `"01"` = etapas 0 e 1).
Na exibição, os códigos são traduzidos para os rótulos
(ex.: `"01"` → "Preparação, Montagem"). O limite é validado em runtime
(`build_field_config`): mais de 10 opções ou código multichar lança `ValueError`.

O editor é **genérico e incluso no framework**: em campos do form e em células
de sessões editáveis, o `MULT10` é um controle `multi-ctl` (rótulo + lápis que
aparece no hover); o clique abre o modal `multiModal` com as opções verticais
e botões Cancelar/OK. O modal grava o valor concatenado (ordenado) num hidden
único — o servidor recebe o mesmo contrato de antes (códigos concatenados).
Em sessões `readonly`, o campo é renderizado apenas como texto, sem editor.

**`aggregate` dict no form** — além do `'sum'` de rodapé na listagem, `aggregate`
aceita um dict para o motor **recalcular o campo do pai ao salvar** os filhos:

```python
'total': {'type': 'NUM', 'currency': 'brl',
          'aggregate': {'table': 'items', 'sum': 'preco_unitario * quantidade'}},
```

O motor soma a expressão (avaliada com namespace restrito aos atributos de cada
filho) e atribui ao campo do pai após persistir as sessões.

---

## 6. List — configuração

A `List` define como a listagem é renderizada.

### 6.1 Exemplo

```python
List = {
    'fields': ['Product'],
    'ordering': ['nome'],
    'title': 'Produtos cadastrados',
    'new_endpoint': None,     # esconde o botão "Novo" (sem criação)
}
```

### 6.2 Referência de propriedades

| Propriedade | Tipo | O que configura | Padrão |
|---|---|---|---|
| `fields` | list[str]/dict | Colunas da tabela. Formato `'Entity'` (todos os campos), `'Entity.campo'` (campo específico), nome simples (resolvido via entity principal) ou `{'name': ..., 'label': ...}` (override); campos com `in_list: 0` são omitidos e com `in_list: 2` vão direto para o card | `[entidade]` |
| `card` | list[str] | Campos do card de destaque (primeira coluna, com id + imagem) | — |
| `linha` | list[str] | Campos destacados nas linhas (utilizado com filtros) | — |
| `detail` | list[str] | Campos de detalhe expandível; o framework busca itens na relação `<entity>_items` (viewonly) do model | — |
| `ordering` | list[str] | Nomes de **atributos** da model p/ `ORDER BY` (ex.: `['ordem', 'nome']`) | — |
| `title` | str | Título da página | nome da entidade |
| `template` | str | Template alternativo da página | `pages/list.html` |
| `new_endpoint` | str/None | Endpoint do botão "Novo". Ausente → `'<blueprint>.form'`; `None` → esconde; string → usa esse endpoint | — |
| `edit_endpoint` | str/None | Endpoint do link de edição da linha. Ausente → `'<blueprint>.form'`; `None` → esconde | — |
| `edit_id_field` | str | Campo usado no `id=` do link de edição | `'id'` |

### 6.3 Semântica de endpoints (importante)

O padrão "ausente → default" permite comportamento por omissão, e o `None`
explícito **esconde** o botão/link:

```python
List = {
    'fields': ['Category'],
    'edit_endpoint': None,   # listagem somente-leitura
}
```

> Quando `new_endpoint`/`edit_endpoint` são `None`, o respectivo botão/link não é
> renderizado. Útil para módulos de consulta ou detalhe.

---

## 7. Form — configuração

O `Form` é um dict com a configuração completa do formulário:

```python
Form = {
    'fields': 'Category',
    'delete': {
        'when': {Product},
        'msg_ok': 'Categoria excluída',
        'msg_no': 'Em uso',
    },
    'buttons': ['on_off'],
    'pre_save': _pre_save,
}
```

> Equivalente à dataclass `Form(...)` de `app.ajsystem.core.form` — `handle_form`
> aceita ambos. Os módulos do projeto usam o dict.

### 7.1 Formato de `fields`

| Formato | Sintaxe | Quando usar |
|---|---|---|
| string | `'fields': 'Category'` | todos os campos da entidade `Category` |
| lista | `'fields': ['nome', 'preco']` | campos específicos (por nome) |
| dict com `fields` | `'fields': {'fields': {'nome': {...}}}` | campos explícitos |
| dict com `entity` | `'fields': {'entity': 'Encomenda', 'only': ['data', 'cliente'], 'overrides': {...}}` | entidade + seleção + ajustes |

> `field_overrides` (propriedade da dataclass) é o equivalente de `overrides` em
> nível de form: `{campo: {props}}` mesclado sobre os campos da entidade.

### 7.2 Referência de propriedades

| Propriedade | Tipo | O que configura | Padrão |
|---|---|---|---|
| `fields` | ver §7.1 | Campos do form | — |
| `model` | Model | Model principal (derivado de `entity_name`/`fields` se ausente) | — |
| `redirect` | str | Endpoint após salvar | `'<blueprint>.list'` |
| `label` | str | Nome do registro (botões/flash) | auto: menu singularizado → entidade |
| `new_label` | str | Rótulo do "Novo"/título novo | `label` |
| `new_title` | str | Título da página em modo criação | `label` |
| `flash_ok` | str | Mensagem de sucesso (criação) | `'{label} incluído!'` |
| `flash_update` | str | Mensagem de sucesso (atualização) | `'{label} atualizado!'` |
| `nav` | bool | Barra de navegação superior | `True` |
| `nav_right_extra` | str/HTML | HTML extra à direita da barra | — |
| `back_url` | str | URL do botão "Voltar" | `url_for(<bp>.list)` |
| `readonly_when` | dict | `{campo: valor}` — todos iguais ⇒ form readonly. Valor também aceita callable `(valor_atual) -> bool` ou lista/set de valores | — |
| `defaults` | dict | Valores iniciais `{campo: valor}` em novos registros | — |
| `pre_save` | callable | `(instance, request, is_new) -> bool` (§7.6) | — |
| `post_save` | callable | `(instance, changed, old_vals)` (§7.6) | — |
| `pre_get` | callable | `(mod, id) -> dict` de contexto extra (§7.6) | — |
| `sessions` | dict | Tabelas filhas (§7.3) | — |
| `delete` | bool/dict | Exclusão (§7.4) | `False` |
| `delete_when` | dict/list | Alias de `delete['when']` | — |
| `toggle` | str | Campo booleano do botão ativar/desativar | via `buttons` (`'ativo'`) |
| `buttons` | list | Botões (§7.5) | — |
| `template` | str | Template completo alternativo | `pages/form.html` |
| `body_template` | str | Template parcial do corpo (campos) | — |
| `form_tail` | str/HTML | HTML antes dos botões de ação | — |
| `footer_left` | str/HTML | Rodapé (coluna esquerda) | — |
| `page_scripts` | str/HTML | Scripts adicionais da página | — |
| `spacing` | int | Espaçamento do grid de campos | `2` |
| `badge`/`tag` | dict/HTML | Badge no cabeçalho do form | — |
| `children` | list | (legado) itens filhos | — |

### 7.3 `sessions` — tabelas filhas

**Derivação automática (recomendado)** — se `sessions` não for declarado, o motor
deriva as sessões dos **relacionamentos** do model do form:

```python
Form = {
    'fields': 'Product',
    # sem 'sessions' → o motor gera a sessão 'ingredients'
}
```

Regras da derivação (`Form._auto_sessions`):

- cada relação **ONETOMANY/ONETOONE** cujo model alvo tenha uma entrada em
  `Entity` vira uma sessão (`attr` = nome da relação);
- relações `MANYTOONE`, auto-referências e `secondary`/`viewonly` são ignoradas;
- o **rótulo** vem de `__meta__['label']` (ou do nome da relação) e `readonly`
  de `__meta__['readonly']` — veja §5.4;
- **campos gerenciados ficam ocultos** (`in_form: False`): PKs simples (`id`) e FKs
  que apontam ao model pai (ex.: `quote_id`). O motor os preenche pela relação;
- FKs para outros models têm o `query` derivado da relação (§5.4);
- sessão `single: True` quando a relação é 1:1 (ex.: o `event` de um orçamento).

**Sessões explícitas** — como antes, com `table`/`model`/`fields`/`attr`:

```python
Form = {
    'fields': 'Product',
    'sessions': {
        'Insumos': {'table': ['ProductIngredient'], 'attr': 'ingredients'},  # automático
        'Eventos': {'model': Event, 'fields': {'tipo': {'type': 'TEXT'}}},   # explícito
        'Obs': 'sys_produtos/_obs.html',                                     # template só
    },
}
```

Propriedades de cada sessão:

| Propriedade | Tipo | O que configura |
|---|---|---|
| `table` | list | Entidades da `Entity` do módulo (ex.: `['ProductIngredient']`) — monta colunas automaticamente |
| `model` | Model/str | Model dos itens (ou nome da entidade do módulo) |
| `fields` | dict/list | Campos explícitos (mesmo formato de `Form.fields`) |
| `attr` | str | Atributo/relação no model pai (usado p/ ler/salvar itens) |
| `readonly` | bool | Sessão somente-leitura (sem adicionar/remover) |
| `template` | str | Template parcial do form filho (ex.: `sys_x/_itens.html`) |
| `label` | str | Rótulo da sessão | nome da chave |
| `prefix` | str | Prefixo dos campos de formulário | `'<attr>_'` |
| `order_by` | str | Ordenação dos itens |
| `buttons` | list | Botões da tabela de itens |

Uma sessão com apenas string equivale a `{'attr': <nome>, 'template': <string>}`.

**Sessões `query`** — tabela **somente-leitura** (sem adicionar/remover) para
apresentação, com agrupamento e subtotais — um "mini-relatório" na tela:

```python
Form = {
    'fields': 'Conta',
    'sessions': {
        'Pedidos': {
            'query': ['Order'],                   # entidades p/ colunas (como 'table')
            'group_by': 'status',                 # agrupa por este campo
            'group_totals': {                     # rótulo -> agregado
                'Qtd':   'count',                 # conta linhas
                'Valor': {'sum': 'total', 'currency': True},  # soma (currency => BRL)
            },
        },
    },
}
```

- `query` aceita **lista** de entidades no formato legado (string = chave de
  `Query` nomeada — ver §12); a sessão vira `readonly` (não persistida pelo
  motor);
- `group_by` (opcional): campo de agrupamento. Grupos ordenados pelas `options`
  do campo (ex. `ORDER_STATUS`), senão por valor; só aparecem grupos com itens.
  A coluna do campo agrupado some das linhas de detalhe;
- `group_totals` (opcional): agregados por grupo **e** total geral. `'count'`
  conta linhas; `{'sum': '<campo>', 'currency': bool}` soma o campo (ignora
  `None`); com `currency: True` formata como moeda (`fmt_brl`).

> Hoje o formato inline acima (lista/string de entidades) é um caminho
> **legado**: o formato recomendado é uma `Query` nomeada — ver §12.

**Persistência genérica** — as sessões derivadas (e as de `table` com entidade
resolvida) são persistidas pelo motor no `pre_save` (inputs
`child_<rel>_<rid>_<campo>`, ver `Form._save_session_children`):

- **linha ignorada** quando todos os campos editáveis estão vazios **ou** falta
  valor em um campo `required`;
- `rid` numérico = registro existente (**upsert**); `n*` = novo; FKs para o pai
  são preenchidas pela relação; existentes não submetidos são excluídos;
- sessões `single` são criadas/atualizadas e nunca apagadas por um envio vazio;
- `aggregate` dict (§5.4) é recalculado após salvar.

> As sessões renderizam uma tabela de itens com adicionar/remover
> (`components/item_table.html`). O padrão canônico de persistência é **o do
> motor** — não declare mais `pre_save` para parsear filhos.

### 7.4 `delete` — exclusão com proteção

```python
'delete': {
    'when': {Product},          # blocos: não exclui se existir filho
    'msg_ok': 'Categoria excluída',
    'msg_no': 'Não é possível excluir — está em uso.',
}
```

| Propriedade | Tipo | O que configura |
|---|---|---|
| `when` | set/list/dict/callable | `{Model}` ou `[Model...]` → checa FK e bloqueia; `{campo: valor}` → bloqueia se campo ≠ valor; callable `(instance)->bool`; `True` permite sempre; `False` desabilita |
| `msg_ok` | str | Mensagem de sucesso |
| `msg_no` | str | Mensagem ao bloquear |
| `callback` | callable | (custom) lógica extra antes de excluir — use numa rota `delete` custom |

> O motor usa `can_delete(instance, when)` internamente, monta o modal de
> confirmação (`ConfirmModal`) e cria a rota `/<id>/excluir`. Com `delete=False`
> a rota não é criada. Para limpar uploads etc., declare a rota `delete` custom
> (veja §4.5).

### 7.5 Botões (`buttons`)

Os botões vêm de `app/ajsystem/defs/buttons.py` (presets `BTN_*`) ou `Button(...)`.
Três formas no `Form`:

```python
'buttons': ['on_off'],                      # ação padrão (toggle ativo/inativo)
'buttons': [{'on_off': {'field': 'publicado'}}],   # ação padrão com campo custom
'buttons': [BTN_SALVAR, Button(label='Imprimir', icon='printer', color='info')],
```

| Propriedade de `Button` | Tipo | Uso |
|---|---|---|
| `label` | str | Texto do botão |
| `icon` | str | Nome do ícone (Heroicon) |
| `color` | str | `success`, `danger`, `primary`, `secondary`, `info`, `warning`, ... |
| `outline` | bool | Estilo outline |
| `size` | str | `sm`/`md`/`lg` |
| `endpoint` / `url` | str | Destino do link |
| `method` | str | `GET`/`POST` (para ações) |
| `confirm_msg` | str | Mensagem do modal de confirmação |
| `on_off` | bool | Botão de toggle ativo/inativo |
| `field` | str | Campo booleano do toggle (padrão `'ativo'`) |
| `label_off`/`icon_off` | str | Rótulo/ícone no estado "off" |
| `show_if` / `hide_if` | tuple/dict | Mostrar/ocultar conforme condição `(campo, valor)` |
| `position` | str | `nav_right`, `nav_left`, ... |
| `extra_params` | dict | Parâmetros extras na URL |

Presets: `BTN_SALVAR`, `BTN_ENVIAR`, `BTN_EXCLUIR`, `BTN_NOVO`, `BTN_VOLTAR`,
`BTN_EDITAR`, `BTN_CANCELAR`, `BTN_CONVERTER`, `BTN_LISTA`, `BTN_IMPRIMIR`,
`BTN_DETALHES`, `BTN_ADICIONAR`, `BTN_ADICIONAR_ITEM`, `BTN_FINALIZAR`,
`BTN_ATUALIZAR`, `BTN_REMOVER`, `BTN_RELATORIO`, etc.

> O `buttons: ['on_off']` gera a rota `/<id>/toggle` (campo `'ativo'` por
> convenção) — o mesmo efeito de `Form['toggle'] = 'ativo'`.

### 7.6 Hooks de ciclo de vida

```python
def _pre_save(instance, request, is_new):
    if instance.ordem is None and is_new:
        last = db.session.query(db.func.max(Category.ordem)).scalar() or 0
        instance.ordem = last + 1
    return True            # False cancela o salvamento (rollback + redirect)

def _post_save(instance, changed, old_vals):
    if 'ordem' not in changed:
        return
    # reordena demais registros após a mudança
    ...
```

| Hook | Assinatura | Quando | Retorno |
|---|---|---|---|
| `pre_save` | `(instance, request, is_new)` | antes do commit | `False` cancela |
| `post_save` | `(instance, changed, old_vals)` | depois do commit | — |
| `pre_get` | `(mod, id)` | ao abrir o form de edição | dict mesclado no contexto do template |

> `changed` é o conjunto de nomes de campos cujo valor mudou (inclui imagens).
> `old_vals` é o mapa `campo → valor_anterior`.

### 7.7 Templates custom

Você pode sobrescrever partes sem recriar a página inteira:

- `template` — página completa;
- `body_template` — só a área de campos;
- `form_tail` — HTML antes dos botões de ação;
- `footer_left` — rodapé à esquerda (ex.: status);
- `page_scripts` — JS extra da página;
- `nav_right_extra` — HTML extra na barra de navegação.

Componentes reutilizáveis: `components/form_macros.html` (`fm.render_fields`,
`fm.render_widget`, ...), `components/item_table.html`,
`components/image_widget.html`.

---

## 8. Exemplo completo do zero

### Passo 1 — Model (categoria)

```python
# app/models/category.py
from app.extensions import db


class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    ordem = db.Column(db.Integer, default=0)
    ativo = db.Column(db.Boolean, default=True)
```

### Passo 2 — Módulo declarativo

```python
# app/routes/sys/categorias.py
from app.extensions import db
from app.models.category import Category
from app.models.product import Product


def _pre_save(instance, request, is_new):
    if instance.ordem is None and is_new:
        last = db.session.query(db.func.max(Category.ordem)).scalar() or 0
        instance.ordem = last + 1


Entity = {
    'Category': {
        'id':    {'type': 'ID'},
        'nome':  {'type': 'TEXT'},
        'ordem': {'type': 'INT', 'attrs': {'min': 0, 'max': 99}},
        'ativo': {'type': 'BOOL'},
    },
}

List = {
    'fields': ['Category'],
    'ordering': ['ordem', 'nome'],
    'title': 'Categorias',
}

Form = {
    'fields': 'Category',
    'delete': {
        'when': {Product},
        'msg_ok': 'Categoria excluída!',
        'msg_no': 'Não é possível excluir — está em uso.',
    },
    'buttons': ['on_off'],
    'pre_save': _pre_save,
}
```

> `delete['when'] = {Product}` bloqueia a exclusão enquanto existirem produtos
> referenciando a categoria (checagem automática de FKs).

### Passo 3 — registrar o módulo no menu

```python
# app/app_defs.py
'system': {
    'url_prefix': '/',
    'home': 'categorias.list',
    'menus': [
        {'endpoint': 'categorias.list', 'label': 'Categorias', 'icon': 'tag'},
    ],
},
```

### Passo 4 — rodar

```bash
flask db init
flask db migrate -m "initial"
flask db upgrade
python run.py
```

Acesse `/categorias/` (listagem), `/categorias/novo` (form) e o menu. Para uma
entidade com referência, imagem, tabela filha e rotas custom, veja o padrão de
`Product` em `app/routes/sys/produtos.py` (tipos `FK`, `LIST`, `IMAGE`, `NUM`,
sessão `ingredients` **derivada automaticamente** dos relacionamentos e
`@auto.rota`).

---

## 9. Referências rápidas

### Globals do Jinja (injetados por `init_app`)

| Nome | Descrição |
|---|---|
| `aj_uploads_endpoint()` | endpoint de uploads (do adaptador) |
| `SYS` / `APP` / `Temas` | definições do app |
| `CONECTORES` | conectivos usados na geração de títulos |
| `current_user` | usuário logado (flask-login) |

### Filtros úteis

| Filtro | Uso |
|---|---|
| `fmtdate` | formata data/hora |
| `brl` | formata moeda brasileira |
| `mask` | aplica máscara (com `digits_only`) |
| `deep_attr` | acessa atributo aninhado (ex.: `item|deep_attr('Encomenda.id')`) |
| `title_case` | transforma nome em título (usando `CONECTORES`) |

### Convenções importantes

- **Tipos em maiúsculas** (`TEXT`, `NUM`, `FK`, `LIST`, `IMAGE`, ...).
- **Referências** usam `masterkey: '<chave do MODEL_MAP>'` (FK) ou são derivadas
  da relação do model no form; opções fixas com `list`/`options` (LIST).
- **Sessões** derivadas dos relacionamentos quando `Form['sessions']` ausente
  (§7.3); chaves `__*` na `Entity` são reservadas (`__meta__`).
- **Slug do menu** = slug do módulo (`label`/`endpoint` → módulo em
  `app.routes.sys.<slug>`).
- **Endpoints gerados**: `<slug>.list`, `<slug>.form`, `<slug>.delete`,
  `<slug>.toggle`.
- **`None` desliga** (`new_endpoint`, `edit_endpoint`, `delete`, `toggle`).
- **`ordering` usa atributos da model**, não `'Entity.campo'`.
- **`login_required`** em todas as rotas CRUD geradas.

---

## 12. Consultas nomeadas (`Query`), campos derivados e agregados

### `Query` — consultas em um só lugar

Uma `Query` é um **dict nomeado** (mesmo estilo de `Entity`/`List`/`Form`), sem
função de definição, que descreve uma consulta agrupada reutilizável. O rótulo
padrão vem do nome da chave (`label` opcional para sobrescrever).

```python
Query = {
    'pedidos': {
        'fields': ['Order'],              # strings = entidades; dicts = campos explícitos
        'group_by': 'status',
        'order_by': 'data_pedido desc',
        'totals': {
            'Qtd':          {'sum': 'qtd'},
            'Valor':        {'sum': 'total', 'currency': True},
            'Média/Pedido': {'avg': 'total', 'currency': True},
            'Média/Item':   {'avg': 'total', 'by': 'qtd', 'currency': True},
        },
        # fonte SQL global (fase 2): join / where / raw ('with x as (...) select ...')
    },
}

Form = {
    'fields': 'Conta',
    'sessions': {'Pedidos': {'query': 'pedidos'}},
}
```

- `query` aceita **string = chave da `Query`** (dict nomeado do mesmo módulo, ver
  §12) ou **lista/string de entidades** (formato legado, §7.3). O valor string
  é resolvido no registro `Query` do módulo — `KeyError` se a chave não existir.
- `fields`: **strings = nomes de Entity** (campos vêm da Entity, sem redefinição);
  **dicts = campos explícitos** (`{'name': 'conta.nome', 'label': 'Cliente'}` —
  caminhos dotted funcionam via `deep_attr`).
- `group_by`: campo de agrupamento (ordem das `options` quando houver).
- `order_by`: ordem das linhas (`'campo'`, `'campo desc'` ou lista).
- `totals`: agregados por grupo/geral (ver spec abaixo).
- O motor (`app/ajsystem/core/report.py`) é consumido por sessões de Form; na fase 2
  também por List/PDF. Sessões de form buscam os itens por **relacionamento**; a
  fonte SQL global (`join`/`where`/`raw`) é extensão futura.
- O formato inline legado (§7.3, `'query': ['Order']` + `group_by`/`group_totals`)
  continua suportado pelo motor.

### Campo derivado (`Field.derived`)

Campo **virtual** (sem coluna no banco) calculado por item pelo motor:

```python
'qtd': {'type': 'INT', 'derived': {'sum': 'items.quantidade'}},
```

- `{'sum': '<caminho>'}` — soma das folhas do caminho, percorrendo coleções
  (`items.quantidade` = soma das quantidades dos itens do registro).
- Resolvido por `field_value` (global Jinja e helper Python) em renderização e
  em agregados.

### Spec de agregados (`totals` / `group_totals`)

| Spec | Resultado |
|---|---|
| `'count'` | número de itens (linhas) |
| `{'sum': 'campo'}` | soma (resolve derivados e dotted) |
| `{'avg': 'campo'}` | média sobre itens com valor (soma ÷ nº de itens com valor) |
| `{'avg': 'campo', 'by': 'divisor'}` | soma(campo) ÷ soma(divisor) — média ponderada (ex.: Valor ÷ Qtd) |

- `'currency': True` — formata como BRL na renderização.
- Divisor zero ou valor ausente → renderiza `—`.

### Summary

- Definir campos **uma vez** na Entity (incl. derivados) e referenciá-los na
  `Query` — sem redefinição.
- `Query` nomeada = mesma definição para Form hoje, List/PDF depois.
- Agregação/agrupamento rodam **em Python** sobre as linhas buscadas (preserva
  derivados, média ponderada e formatação da Entity).
- A sessão referenciada por `query` (dict `Query` ou lista/string de entidades)
  vira `readonly` e não é persistida pelo motor.
