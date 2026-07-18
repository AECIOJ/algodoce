# AlgoDoce

## O que é isso? (Visão Geral)

Sistema web completo para gestão de **doceria/confeitaria** (pessoa jurídica).

**Stack:** Python/Flask, PostgreSQL 16, SQLAlchemy ORM, Jinja2 + Bootstrap 5, Docker Compose

**3 módulos:**

| Módulo | Função |
|--------|--------|
| **`site`** | Site público — landing page, vitrine de produtos, orçamento online, páginas sobre/contato |
| **`sys`** | Sistema gerencial — CRUDs de cadastro, comercial (orçamentos/pedidos/compras), produção (batches com cálculo automático de insumos), financeiro 2 camadas (transações+previsões / movimentações+recursos) |
| **`admin`** | Administração — gerenciamento de usuários, segurança, autenticação 2FA com chave dinâmica HMA, configurações criptografadas (Fernet AES) |

---

## Como rodo isso? (Setup/Instalação)

### Docker Compose (recomendado)

```bash
docker compose up
```

Três serviços:

| Serviço | Container | Porta |
|---------|-----------|-------|
| PostgreSQL 16 | `algodoce_db` | 5435 |
| App Flask | `algodoce` | 5000 |
| Pinggy tunnel | `algodoce_pinggy` | — |

### Manual

```bash
pipenv install
pipenv run flask run
```

Requer PostgreSQL rodando local e variáveis de ambiente configuradas.

### Variáveis de Ambiente (`.env`)

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `POSTGRES_DB` | `algodoce` | Nome do banco |
| `POSTGRES_USER` | `algodoce` | Usuário do banco |
| `POSTGRES_PASSWORD` | `algodoce123` | Senha do banco |
| `POSTGRES_HOST` | `pg_18` (Docker) / `localhost` (manual) | Host do PostgreSQL |
| `POSTGRES_PORT` | `5432` | Porta do PostgreSQL |
| `SECRET_KEY` | `dev-secret` | Chave secreta Flask |
| `ADMIN_USERNAME` | `admin` | Login admin padrão |
| `ADMIN_PASSWORD` | `admin` | Senha admin padrão |

Admin padrão (`admin`/`admin`) é criado automaticamente no startup. Migrations rodam automáticas via `flask db upgrade` dentro de `create_app()`.

---

## Como está estruturado? (Arquitetura)

### Estrutura de Diretórios

```
algodoce/
├── app/                            # Aplicação Flask
│   ├── __init__.py                 # Factory create_app()
│   ├── extensions.py               # SQLAlchemy, Migrate, LoginManager
│   ├── config.py                   # Configurações (DB, SECRET_KEY, sessão)
│   ├── constants.py                # Enums (status, tipos, conectores)
│   ├── filters.py                   # Helpers de filtros (resolve_filters, filtrar_vencimento, filtrar_vencimento_query)
│   ├── table.py                    # Sistema de campos + tabelas (Field, Table dataclasses)
│   ├── crypto.py                   # Criptografia Fernet (AES)
│   ├── ntfy.py                     # Notificação push (ntfy.sh)
│   ├── pdf.py                      # Geração de PDF (fpdf2) — DocPDFReport + gerar_pdf_relatorio()
│   ├── report.py                   # Dataclass Report (header dict, table dict) para relatórios declarativos
│   ├── utils.py                    # Helpers (formatação, parse, transformação)
│   ├── versao.py                   # Versão do sistema
│   │
│   ├── models/                     # SQLAlchemy models (24 models)
│   ├── routes/                     # Blueprints Flask (22 arquivos — 23 blueprints)
│   ├── reports/                    # Definições de relatórios (orcamento.py, pedido.py)
│   ├── templates/                  # Jinja2 (21 diretórios — 16 sys_*, site/, site_orcamento/, components/, admin/)
│   ├── static/                     # CSS, JS, ícones, uploads
│   │   ├── css/                    #   style.css
│   │   ├── icons/                  #   Ícones PNG (Logo, setas, etc.)
│   │   ├── js/                     #   iteMS.js, phone-mask.js
│   │   ├── lib/                    #   Bibliotecas locais (bootstrap, bootstrap-icons, qrcode-generator)
│   │   └── uploads/                #   Uploads de imagens
│   └── migrations/                 # Alembic (8 migrations)
│
├── dados/                          # Dados persistentes
│   ├── paginas/                    # Páginas Markdown (sobre.md)
│   ├── pgdata/                     # Dados PostgreSQL (volume Docker)
│   └── uploads/                    # Uploads de fotos
│
├── scripts/
│   └── pinggy_entrypoint.sh        # Script de entrada Pinggy
│
├── compose.yml                     # Docker Compose (db + app + pinggy)
├── Dockerfile                      # Imagem da aplicação
├── Dockerfile.pinggy               # Imagem do túnel Pinggy
├── Pipfile                         # Dependências Python
├── Pipfile.lock                    # Lock de dependências
├── requirements.txt                # Pip freeze
├── COMERCIAL.md                    # Docs comerciais
├── LAYOUT.md                       # Docs de layout
├── PLANO.md                        # Este arquivo
├── .env                            # Variáveis de ambiente
├── .dockerignore                   # Ignorados pelo Docker
└── .gitignore                      # Ignorados pelo Git
```

#### Models por Módulo

| Módulo | Models | Arquivos |
|--------|--------|----------|
| **admin** | User, Setting | `models/user.py`, `models/setting.py` |
| **site** | — (usa session/cookies) | — |
| **sys** | Conta, Category, Product, Ingredient, ProductIngredient, UnitConversion, Quote, QuoteItem, Order, OrderItem, Compra, CompraItem, Event, Producao, ProducaoProduto, ProducaoInsumo, Operacao, Carteira, Transacao, Previsao, Recurso, Movto | `models/*.py` |

#### Rotas por Módulo

| Módulo | Blueprint | Arquivo | Rotas |
|--------|-----------|---------|-------|
| **site** | `site` | `routes/site.py` | `/`, `/sobre`, `/contato`, `/sistema`, `/admin` |
| **site** | `site_vitrine` | `routes/site_vitrine.py` | `/vitrine/`, `/vitrine/<id>/add` |
| **site** | `site_orcamento` | `routes/site_orcamento.py` | `/orcamento`, `/api/cliente`, `/orcamento/enviar` |
| **sys** | `auth`, `seguranca` | `routes/sys_auth.py` (unificado) | `/login`, `/logout`, `/seguranca/` (painel + settings) |
| **sys** | `contas`, `products`, `categories`, `ingredients`, `orders`, `compras`, `orcamentos`, `producao`, `operacoes`, `carteira`, `transacao`, `previsoes`, `movimentos`, `recursos`, `reports`, `api` | `routes/sys_*.py` | CRUDs de todas as entidades |
| **site** | `uploads` | `routes/uploads.py` | Uploads de imagens (sys + site) |

### Hierarquia de Componentes (Telas)

```
.
├── page_base.html                 ─ ─ Layout base (doctype, head, bootstrap local)
│   ├── page_sys.html              ─ ─ Layout do módulo sys (navbar, submenu, footer)
│   │   ├── page_form.html         ─   Página de formulário
│   │   └── (macros.html)          ─   Macros: action_list, action_table, action_filter, action_edit, action_nav
│   ├── page_site.html             ─ ─ Layout do módulo site (header, nav, footer)
│   └── admin/                     ─ ─ Módulo admin (via page_sys.html)
```

**Macros compartilhadas:**

| Macro | Arquivo | Descrição |
|-------|---------|-----------|
| `action_list(title, new_url=none, new_label='+ Novo', extra_actions=none, active_filters=none, filters=none, ctx=none)` | `macros.html` | Macro mestra de listagem: abas Dados/Filtros, tabela sortable, filtro JS config-driven (XXX_FILTERS) |
| `action_table(data, columns=none, fields=none, ctx=none, table=none, edit_endpoint=none, ...)` | `macros.html` | Tabela com colunas dinâmicas, ordenação, detalhe expansível, botão de ação centralizado |
| `action_filter(caller_content='')` | `macros.html` | Painel de filtros |
| `action_edit(url, label='Editar')` | `macros.html` | Botão de editar (ícone lápis) |
| `action_nav(back_url, nome, nav, edit_endpoint, entity_id=none, status=none, actions2=none)` | `macros.html` | Navegação entre registros (anterior/próximo, responsivo) |

**Sistema de Fields:** Cada blueprint define `*_FIELDS = [Field(name, label, width, input, options, filter, query, ...)]`. O dataclass `Field` configura colunas, filtros, máscaras, agregadores (soma), links e validação — usado para renderizar tabelas e formulários dinamicamente.

**Sistema de Filtros:** Cada blueprint define `*_FILTERS = {'campo': {'type': '...', 'options': {...}}}` — dict declarativo contendo TODOS os campos de `*_FIELDS` (exceto `filter=False`). O tipo é derivado do `input` do Field: `select` → `'select'` (com options), `boolean` → `'boolean'`, `date` → `'date'`, `number` → `'number'`, resto → `'text'`. O JS lê `data-filter-config` (JSON do FILTERS) e renderiza o painel automaticamente. Para esconder um filtro do painel, basta remover a entrada do dict. Sem valores default — o usuário define depois.

### Banco de Dados (PostgreSQL 16)

**24 tabelas**, sem views/stored procedures — toda lógica em Python.

| Grupo | Tabelas | Descrição |
|-------|---------|-----------|
| **Sistema (admin)** | `users`, `settings` | Login, configurações criptografadas |
| **Cadastros (sys)** | `conta`, `categories`, `products`, `ingredients`, `product_ingredients`, `unit_conversions` | Clientes/fornecedores, categorias, produtos, insumos, receituário, conversões |
| **Comercial (sys)** | `quotes`, `quote_items`, `orders`, `order_items`, `compras`, `compra_itens`, `events` | Orçamentos, pedidos, compras, eventos |
| **Produção (sys)** | `producao`, `producao_produtos`, `producao_insumos` | Batches de produção, produtos por batch, insumos calculados |
| **Financeiro (sys)** | `operacao`, `carteira`, `transacao`, `previsao`, `recurso`, `movto` | Plano de contas, formas de pagamento, transações, parcelas, recursos, movimentações |

**Relacionamentos chave:**

- `quotes` → `orders` (conversão orçamento→pedido via `quote.pedido_id`)
- `orders` → `producao` (pedido alocado em produção via `order.producao_id`)
- `orders`/`compras` → `carteira` (forma de pagamento via `carteira_id`)
- `carteira.gerar`: `0`=Movto (fluxo de caixa direto), `1`=Transacao+Previsoes (contas a pagar/receber)
- `transacao` → `previsao` (1:N parcelas)
- `previsao` → `movto` (baixa de previsão no fluxo de caixa)

**Hierarquia operacao:** Auto-referenciada (`operacao.pai_id` → `operacao.id`) para plano de contas em árvore.

**Status calculados:**

| Campo | Lógica |
|-------|--------|
| `Transacao.status` | 8 se cancelado; 0 se `sum(previsto) < valor`; senão `max(previsoes.status)` |
| `Previsao.status` | 8 se transação cancelada; 0=Editando; 1=Pendente; 2=Parcial; 9=Quitado |
| Faturado (pedido/compra) | Derivado: `True` se `transacao_id` ou `movto_id` preenchido |

#### Estrutura das Tabelas

##### `users` — User
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| username | VARCHAR(80) | UNIQUE, NOT NULL |
| password_hash | VARCHAR(256) | NOT NULL |

##### `settings` — Setting
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| key | VARCHAR(100) | UNIQUE, NOT NULL |
| encrypted_value | TEXT | NOT NULL, DEFAULT '' |
| updated_at | TIMESTAMP | DEFAULT now() |

##### `conta` — Conta
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| nome | VARCHAR(100) | NOT NULL |
| email | VARCHAR(120) | UNIQUE, NULLABLE |
| telefone | VARCHAR(20) | NULLABLE |
| endereco | TEXT | NULLABLE |
| cpf | VARCHAR(14) | NULLABLE |
| cnpj | VARCHAR(18) | NULLABLE |
| insc_estadual | VARCHAR(20) | NULLABLE |
| ativo | BOOLEAN | DEFAULT TRUE |
| tipo | INTEGER | DEFAULT 0 |

##### `categories` — Category
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| nome | VARCHAR(100) | NOT NULL |
| ativo | BOOLEAN | DEFAULT TRUE |
| ordem | INTEGER | DEFAULT 0 |

##### `products` — Product
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| nome | VARCHAR(100) | NOT NULL |
| descricao | TEXT | NULLABLE |
| preco | NUMERIC(10,2) | NOT NULL |
| qtd_minima | INTEGER | NOT NULL, DEFAULT 0 |
| imagem | VARCHAR(255) | NULLABLE |
| ativo | BOOLEAN | DEFAULT TRUE |
| category_id | INTEGER | FK→categories.id, NULLABLE |

##### `ingredients` — Ingredient
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| nome | VARCHAR(100) | NOT NULL |
| unidade_medida | VARCHAR(20) | NOT NULL |
| tipo | INTEGER | NOT NULL, DEFAULT 0 |

##### `product_ingredients` — ProductIngredient
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| product_id | INTEGER | FK→products.id, PK |
| ingredient_id | INTEGER | FK→ingredients.id, PK |
| quantidade | NUMERIC(10,3) | NOT NULL |
| unidade | VARCHAR(20) | NOT NULL, DEFAULT 'un' |
| etapa_id | INTEGER | NULLABLE |

##### `unit_conversions` — UnitConversion
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| ingredient_id | INTEGER | FK→ingredients.id, NOT NULL |
| unidade | VARCHAR(20) | NOT NULL |
| fator | NUMERIC(10,6) | NOT NULL |

##### `quotes` — Quote
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| data_pedido | TIMESTAMP | NOT NULL, DEFAULT now() |
| cliente_nome | VARCHAR(100) | NOT NULL |
| cliente_telefone | VARCHAR(20) | NOT NULL |
| status | INTEGER | NOT NULL, DEFAULT 0 |
| pedido_id | INTEGER | FK→orders.id, NULLABLE |
| total | NUMERIC(10,2) | NULLABLE |
| observacao | TEXT | NULLABLE |
| validade | INTEGER | NOT NULL, DEFAULT 3 |
| carteira_id | INTEGER | FK→carteira.id, NULLABLE |
| data_renovacao | TIMESTAMP | NULLABLE |
| forminhas | INTEGER | NOT NULL, DEFAULT 0 |

##### `quote_items` — QuoteItem
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| quote_id | INTEGER | FK→quotes.id, NOT NULL |
| product_id | INTEGER | FK→products.id, NOT NULL |
| quantidade | INTEGER | NOT NULL |
| preco_unitario | NUMERIC(10,2) | NULLABLE |
| observacao | TEXT | NULLABLE |

##### `orders` — Order
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| client_id | INTEGER | FK→conta.id, NOT NULL |
| data_pedido | TIMESTAMP | NOT NULL, DEFAULT now() |
| data_previsao_entrega | TIMESTAMP | NULLABLE |
| data_entrega | TIMESTAMP | NULLABLE |
| status | INTEGER | NOT NULL, DEFAULT 0 |
| observacao | TEXT | NULLABLE |
| total | NUMERIC(10,2) | NULLABLE |
| carteira_id | INTEGER | FK→carteira.id, NULLABLE |
| transacao_id | INTEGER | FK→transacao.id, UNIQUE, NULLABLE |
| movto_id | INTEGER | FK→movto.id, UNIQUE, NULLABLE |
| forminhas | INTEGER | NOT NULL, DEFAULT 0 |
| producao_id | INTEGER | FK→producao.id, NULLABLE |
| quote_id | INTEGER | FK→quotes.id, NULLABLE |

##### `order_items` — OrderItem
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| order_id | INTEGER | FK→orders.id, NOT NULL |
| product_id | INTEGER | FK→products.id, NOT NULL |
| quantidade | INTEGER | NOT NULL |
| preco_unitario | NUMERIC(10,2) | NULLABLE |
| observacao | TEXT | NULLABLE |

##### `events` — Event
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| quote_id | INTEGER | FK→quotes.id, UNIQUE, NULLABLE |
| order_id | INTEGER | FK→orders.id, UNIQUE, NULLABLE |
| tipo | VARCHAR(30) | NULLABLE |
| tema | VARCHAR(200) | NULLABLE |
| obs | TEXT | NULLABLE |
| data | DATE | NULLABLE |
| hora | TIME | NULLABLE |
| local | VARCHAR(200) | NULLABLE |
| convidados | INTEGER | NULLABLE |
| cerimonial | VARCHAR(200) | NULLABLE |

##### `compras` — Compra
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| data | DATE | NOT NULL |
| fornecedor_id | INTEGER | FK→conta.id, NULLABLE |
| valor | NUMERIC(12,2) | NOT NULL |
| historico | TEXT | NULLABLE |
| status | INTEGER | NOT NULL, DEFAULT 0 |
| data_recepcao | DATE | NULLABLE |
| carteira_id | INTEGER | FK→carteira.id, NULLABLE |
| transacao_id | INTEGER | FK→transacao.id, UNIQUE, NULLABLE |
| movto_id | INTEGER | FK→movto.id, UNIQUE, NULLABLE |

##### `compra_itens` — CompraItem
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| compra_id | INTEGER | FK→compras.id, NOT NULL |
| insumo_id | INTEGER | FK→ingredients.id, NOT NULL |
| quantidade | NUMERIC(12,3) | NOT NULL |
| preco | NUMERIC(12,2) | NOT NULL |

##### `producao` — Producao
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| descricao | VARCHAR(200) | NOT NULL |
| data_fim | TIMESTAMP | NULLABLE |
| status | INTEGER | NOT NULL, DEFAULT 0 |
| previsao_de | DATE | NULLABLE |
| previsao_ate | DATE | NULLABLE |

##### `producao_produtos` — ProducaoProduto
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| producao_id | INTEGER | FK→producao.id, NOT NULL |
| order_id | INTEGER | FK→orders.id, NOT NULL |
| product_id | INTEGER | FK→products.id, NOT NULL |
| quantidade | INTEGER | NOT NULL |
| producao_0 | INTEGER | NOT NULL, DEFAULT 0 |
| producao_1 | INTEGER | NOT NULL, DEFAULT 0 |
| producao_2 | INTEGER | NOT NULL, DEFAULT 0 |

##### `producao_insumos` — ProducaoInsumo
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| producao_id | INTEGER | FK→producao.id, NOT NULL |
| insumo_id | INTEGER | FK→ingredients.id, NOT NULL |
| quantidade | NUMERIC(10,3) | NOT NULL |
| comprado | NUMERIC(10,3) | NOT NULL, DEFAULT 0 |
| unidade | VARCHAR(20) | NOT NULL |
| tipo | INTEGER | NOT NULL, DEFAULT 0 |

##### `operacao` — Operacao
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| nome | VARCHAR(100) | NOT NULL |
| tipo | INTEGER | NOT NULL, SERVER_DEFAULT '1' |
| pai_id | INTEGER | FK→operacao.id, NULLABLE |
| ordem | INTEGER | NOT NULL, SERVER_DEFAULT '0' |
| fator | INTEGER | NOT NULL, SERVER_DEFAULT '1' |
| ativa | BOOLEAN | DEFAULT TRUE |

##### `carteira` — Carteira
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| nome | VARCHAR(50) | NOT NULL |
| uso | INTEGER | NOT NULL, DEFAULT 1 |
| gerar | INTEGER | NOT NULL, DEFAULT 0 |
| prazo_recebimento | VARCHAR(100) | NULLABLE |
| taxa_recebimento | NUMERIC(5,2) | NOT NULL, DEFAULT 0 |

##### `transacao` — Transacao
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| data | DATE | NOT NULL |
| tipo | VARCHAR(1) | NOT NULL |
| conta_id | INTEGER | FK→conta.id, NULLABLE |
| operacao_id | INTEGER | FK→operacao.id, NULLABLE |
| fatura | VARCHAR(50) | NULLABLE |
| valor | NUMERIC(12,2) | NOT NULL |
| historico | TEXT | NULLABLE |
| cancelado | DATE | NULLABLE |
| total_previsto | NUMERIC(12,2) | NOT NULL, DEFAULT 0 |

##### `previsao` — Previsao
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| transacao_id | INTEGER | FK→transacao.id, NOT NULL |
| documento | VARCHAR(50) | NULLABLE |
| vencimento | DATE | NOT NULL |
| previsto | NUMERIC(12,2) | NOT NULL |
| realizado | NUMERIC(12,2) | NULLABLE |
| variacao | NUMERIC(12,2) | NULLABLE, SERVER_DEFAULT '0' |
| carteira_id | INTEGER | FK→carteira.id, NULLABLE |
| taxa | NUMERIC(5,2) | NOT NULL, DEFAULT 0 |

##### `recurso` — Recurso
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| nome | VARCHAR(100) | NOT NULL |
| tipo | INTEGER | NOT NULL, SERVER_DEFAULT '0' |
| saldo | NUMERIC(12,2) | NOT NULL, SERVER_DEFAULT '0' |
| data | DATE | NULLABLE |

##### `movto` — Movto
| Coluna | Tipo SQL | Constraints |
|--------|----------|-------------|
| id | INTEGER | PK |
| data | DATE | NOT NULL |
| recurso_id | INTEGER | FK→recurso.id, NOT NULL |
| tipo | VARCHAR(1) | NOT NULL |
| conta_id | INTEGER | FK→conta.id, NULLABLE |
| previsao_id | INTEGER | FK→previsao.id, NULLABLE |
| documento | VARCHAR(50) | NULLABLE |
| valor | NUMERIC(12,2) | NOT NULL |
| variacao | NUMERIC(12,2) | NULLABLE, DEFAULT 0 |
| sincronizar | BOOLEAN | NOT NULL, DEFAULT TRUE |
| operacao_id | INTEGER | FK→operacao.id, NULLABLE |
| historico | TEXT | NULLABLE |

### Funções Principais no Código

| Arquivo | Função | Descrição |
|---------|--------|-----------|
| `__init__.py` | `create_app()` | Factory: configura Flask, DB, blueprints, models, filters, executa upgrade(), cria admin |
| `__init__.py` | `_fetch_tunnel_url()` | Busca URL do túnel Pinggy |
| `utils.py` | `fmt_brl()`, `fmt_date()`, `fmt_id()`, `fmt_zero()`, `fmt_zero_int()`, `fmt_datetime()` | Formatação para templates (moeda, data, ID, decimais, datetime) |
| `utils.py` | `parse_brl()` | Parse de string BRL para float |
| `utils.py` | `preco_unit(valor, qtd)` | Calcula preço unitário |
| `utils.py` | `deep_attr()` | Acesso aninhado a atributos (`obj.conta.nome`) |
| `utils.py` | `parse_prazo_recebimento()` | DSL de prazos: "P/E", "3x", "30", "0/15" |
| `utils.py` | `aplicar_transformacao()` | Listener before_insert/update: Title Case/UPPERCASE automático |
| `utils.py` | `_title_case()` | Title Case respeitando conectores pt-BR |
| `utils.py` | `_save_event()` | Persiste dados de evento (quote/order) |
| `utils.py` | `render_pagina()` | Renderiza Markdown → HTML (páginas institucionais) |
| `utils.py` | `LinhaTransacao` | Wrapper para listar transações com/sem previsões. Properties: `transacao_id`, `compra_id`, `pedido_id`, `status_compra`, `carteira`, `fornecedor`, `cliente`, `conta`, `fatura`, `valor`, `faturado`, `id` (previsão), `vencimento`, `documento`, `previsto`, `realizado`, `variacao`, `saldo`, `status` |
| `table.py` | `Field` | Dataclass de definição de campo: `name`, `label`, `width`, `align`, `input`, `options`, `filter`, `filter_options`, `mask`, `query`, `validate`, `aggregate`, `aggregate_label`, `currency`, `hide_zero`, `card_path`, `pos`, `link`, `function` |
| `table.py` | `Table` | Dataclass com `fields`, `fields_master/detail`, `master_key`, `edit_endpoint`, `edit_id_field`, `edit_if_field`, `edit_endpoint_map`, `edit_endpoint_key`, `detail_data`. Properties: `master_fields`, `detail_fields` |
| `table.py` | `fields_to_columns()` | Converte Field[] para colunas de tabela HTML |
| `table.py` | `field_to_column()` | Converte um Field para dict de coluna |
| `table.py` | `field_filter_type()` | Deriva tipo de filtro do input do campo |
| `table.py` | `field_filter_options()` | Deriva opções de filtro do campo (dict para select, list para query dinâmica) |
| `table.py` | `field_grid()` | Mapeia largura do field para colunas Bootstrap |
| `table.py` | `get_field()` | Busca Field por nome numa lista |
| `table.py` | `build_field_context()` | Popula selects com dados do banco, inclui filter_options para select no painel |
| `table.py` | `register_model()` | Registra model para consulta via `Field.query` |
| `filters.py` | `resolve_filters(config, request_args)` | Lê query params da URL, usa 'default' do config se ausente |
| `filters.py` | `filtrar_vencimento(linhas, field, preset, hoje)` | Aplica preset de data em lista (em_atraso, hoje, a_vencer, mes_atual, etc.) |
| `filters.py` | `filtrar_vencimento_query(query, model_field, preset, hoje)` | Aplica preset de data em query SQLAlchemy |
| `crypto.py` | `encrypt()` / `decrypt()` | Fernet AES com chave derivada de SECRET_KEY |
| `ntfy.py` | `notificar()` | Envia notificação push de novo orçamento |
| `pdf.py` | `gerar_pdf_pedido()` | Gera PDF do pedido |
| `pdf.py` | `gerar_pdf_orcamento()` | Gera PDF do orçamento (legado) |
| `pdf.py` | `gerar_pdf_relatorio()` | Gera PDF genérico a partir de um Report |
| `report.py` | `Report` | Dataclass de relatório declarativo (header/table dicts) |
| `reports/orcamento.py` | `ORCAMENTO_REPORT` | Config do relatório de orçamento |
| `reports/pedido.py` | `ORDER_REPORT` | Config do relatório de pedido |
| `sys_auth.py` | `login_sistema()` | Login doceira (user+senha+chave HMA) |
| `sys_auth.py` | `login_admin()` | Login admin (user+senha+chave, 2FA) |
| `sys_auth.py` | `_impose_delay()` | Proteção brute-force (delay progressivo após 3 falhas) |
| `sys_auth.py` | `_gerar_chave()` | Gera chave HMA (Hora/Mês/Ano) para 2FA |
| `sys_orders.py` | `converter_orcamento()` | Converte quote → order (busca conta por nome/telefone) |
| `sys_producao.py` | `_calcular_qtd_produzir()` | Calcula quantidade a produzir (respeita qtd_minima) |
| `sys_producao.py` | `_calcular_insumos()` | Calcula insumos totais baseado no receituário |
| `sys_clients.py` | `_cpf_valido()` / `_cnpj_valido()` | Validação de CPF/CNPJ |

### Constantes (`constants.py`)

| Constante | Tipo | Descrição |
|-----------|------|-----------|
| `TIPO_CONTA` | dict | `{0: "Cliente", 1: "Cliente/Fornecedor", 2: "Fornecedor"}` |
| `TIPO_INGREDIENTE` | dict | `{0: "Ingrediente", 1: "Forminha", 2: "Embalagem"}` |
| `ORDER_STATUS` | dict | `{0: "Pendente", 1: "Produzindo", 2: "Pronto", 8: "Cancelado", 9: "Entregue"}` |
| `ORDER_STATUS_FILTER` | list | 6 tuplas de filtro |
| `COMPRA_STATUS` | dict | `{0: "Orcamento", 1: "Pedido", 6: "Cancelado", 8: "Recebido", 9: "Devolvido"}` |
| `COMPRA_STATUS_FILTER` | list | 6 tuplas de filtro |
| `QUOTE_STATUS` | dict | `{0: "Pendente", 1: "Negociacao", 6: "Renovado", 7: "Expirado", 8: "Reprovado", 9: "Aprovado"}` |
| `QUOTE_STATUS_FILTER` | list | 7 tuplas de filtro |
| `PRODUCAO_STATUS` | dict | `{0: "Executando", 9: "Finalizado"}` |
| `PRODUCAO_ETAPAS` | dict | `{0: "Preparação", 1: "Montagem", 2: "Embalagem"}` |
| `FORMINHAS` | dict | `{0: "Simples", 1: "Fornecidas pelo Cliente"}` |
| `TIPO_OPERACAO` | dict | `{1: "Receitas", 2: "Despesas"}` |
| `TIPO_PREVISAO` | dict | `{"P": "Pagar", "R": "Receber"}` |
| `TIPO_TRANSACAO` | dict | `{"P": "Contas a Pagar", "R": "Contas a Receber", "C": "Compras", "V": "Vendas"}` |
| `PREVISAO_STATUS` | dict | `{0: "Editando", 1: "Pendente", 2: "Parcial", 8: "Cancelado", 9: "Quitado"}` |
| `TIPO_RECURSO` | dict | `{0: "Caixa", 1: "Banco", 2: "Cartão"}` |
| `CONECTORES` | set | 42 palavras conectoras pt-BR (usadas pelo `_title_case`) |
| `TRANSFORMAR_AO_SALVAR` | dict | Mapping model → campos com modo de transformação (Title Case/UPPERCASE) |

### Casos de Uso

| Caso de Uso | Módulo | Fluxo |
|-------------|--------|-------|
| **Navegar na vitrine** | site | Cliente acessa `/vitrine/` → vê produtos por categoria → adiciona ao carrinho (session) |
| **Solicitar orçamento** | site | Cliente informa nome/telefone → adiciona itens → envia → notificação push (ntfy.sh) |
| **Login doceira** | admin | 1 click no logo → popup → user+senha + chave HMA (hora/mês/ano) |
| **Login admin** | admin | 2 clicks rápidos no logo → popup admin → user+senha+chave |
| **Gerenciar cadastros** | sys | CRUD: categorias, insumos, produtos, contas, operacoes, carteiras |
| **Gerenciar orçamentos** | sys | Listar, editar, validar (expiração automática), renovar, converter para pedido |
| **Converter orçamento** | sys | Sistema busca conta por nome+telefone → perfect_match (1 clique) ou phone_conflict (modal) |
| **Gerenciar pedidos** | sys | CRUD, alterar status (Pendente→Produzindo→Pronto→Entregue), gerar financeiro |
| **Gerenciar compras** | sys | CRUD, fluxo Orçamento→Pedido→Recebido, gerar financeiro |
| **Produção** | sys | Criar batch com período → adicionar pedidos → sistema calcula insumos automático → acompanhar 3 etapas (preparo, montagem, embalagem) |
| **Financeiro (2 camadas)** | sys | Pedido/Compra → seleciona Carteira → `gerar=0`: Movto direto; `gerar=1`: Transacao+Previsoes → parcelas → baixa cria Movto |
| **Contas a pagar/receber** | sys | Transações tipo P/C (pagar) ou R/V (receber) com parcelamento |
| **Fluxo de caixa** | sys | Movimentações por recurso (caixa, banco, cartão) com saldo |
| **Painel de segurança** | admin | Configurar credenciais, chave HMA, integrações (ntfy, email, telefone) |
| **Dashboard produção** | sys | Visão geral de pedidos por data de entrega, status, forma de pagamento |
| **Relatórios** | sys | Relatório de compras, produção consolidada |

---

## Como contribuo? (Regras de Desenvolvimento)

### Convenções Gerais

- **Models:** SQLAlchemy declarative, `__tablename__` explícito em snake_case. Transformação automática via `TRANSFORMAR_AO_SALVAR` (SQLAlchemy event listeners `before_insert`/`before_update`).
- **Views:** Blueprints Flask com nome em inglês (`products`, `orders`). Rotas em português (`/produtos`, `/pedidos`). `@login_required` via `before_request` no blueprint.
- **Templates:** Jinja2 com macros (`{% macro %}`, `{% call %}`). **Sem `{% include %}`** — todo reuso é via macros. Herança via `{% extends %}`.
- **JS:** Vanilla JavaScript. Sem jQuery, sem frameworks JS. Bootstrap bundle servido localmente em `static/lib/`. Dependências externas: Cropper.js (CDN). QR code gerado via `qrcode-generator` (local em `lib/qrcode.min.js`) no cliente.
- **CSS:** Customizado em `static/css/style.css`. Cache-busting manual `?v=N`. Variáveis CSS: `--rosa`, `--cor-menu`, `--verde-menta`, `--bg-claro`. Bootstrap 5.3.2 + Bootstrap Icons servidos localmente em `static/lib/` (sem CDN). Tema claro fixo (`data-bs-theme="light"`).

### Separação dos Módulos

| Diretório | Deve conter | Não deve conter |
|-----------|-------------|-----------------|
| `templates/site/` | Páginas públicas (index, sobre, contato) | Telas do sistema |
| `templates/admin/` | Gerenciamento de usuários/config | CRUDs de negócio |
| `templates/sys_*/` (sys) | Telas de cadastro, comercial, produção, financeiro | Telas públicas ou admin |
| `routes/sys_auth.py` | Autenticação, segurança (unificado) | Lógica de negócio |
| `routes/site*.py` | Rotas públicas | Rotas protegidas |
| `routes/*.py` (demais) | Rotas protegidas (sys) | Lógica de autenticação |

### Boas Práticas

- **Listagens:** Definir array `*_FIELDS = [Field(...)]` usando o dataclass `Field` em vez de HTML fixo. Usar `build_field_context()` para populares selects. Usar `Table(fields=..., edit_endpoint=...)` e passar `table=XXX_TABLE` para `action_table` em vez de `fields=`, `edit_endpoint=` individuais.
  - `Table.fields_master`/`fields_detail` (listas de ints 1‑based) para split master/detail com properties `master_fields`/`detail_fields`.
  - `Table.master_key` ativa `groupby()` no Jinja: primeiro item do grupo é a linha mestre, todos os itens são o detalhe (cards).
- **Formulários:** Usar `page_form.html` (herda `page_sys.html`), `action_nav` + `page_form` (barra inferior fixa com Salvar/Sair). Para formulários com itens dinâmicos, usar JS em `static/js/itens.js`.
- **Financeiro:** Respeitar 2 camadas: `carteira.gerar=0` → Movto (fluxo de caixa), `carteira.gerar=1` → Transacao+Previsoes (contas a pagar/receber). Não criar financeiro manualmente fora do fluxo de carteira.
- **Migrations:** Usar `flask db migrate -m "mensagem"` + `flask db upgrade`. Migrations rodam automáticas no startup, mas devem ser versionadas.
- **Autenticação:** 3 níveis. Anônimo → site. Doceira (login + chave HMA) → sys. Admin (login + chave + 2FA) → `/seguranca/`. Proteção contra força bruta com delay progressivo.
- **Nomenclatura:** Models em inglês (`Conta`, `Order`, `Product`), rotas em português (`/contas`, `/pedidos`, `/produtos`), blueprints em inglês (`contas`, `orders`, `products`).
- **Pastas de templates:** Diretórios de templates do módulo **sys** prefixados com `sys_` (`sys_orders/`, `sys_products/`, `sys_auth/`). Módulos **site** e **admin** sem prefixo (`site/`, `admin/`). Componentes compartilhados em `components/`.
- **Estilo de código:** Sem comentários desnecessários. Código limpo e auto-documentado.

---

## Histórico de Alterações

### Sessão 2026-07-10

#### `app/fields.py` → `app/table.py`
- Renomeado para `table.py`. Adicionado dataclass `Table` com campos `fields_master`/`fields_detail`, `master_key`, `edit_endpoint`, etc.
- Properties `master_fields` e `detail_fields` derivam das listas de índices 1‑based.
- `fields.py` removido. Todos os imports atualizados (15 rotas + `__init__.py`).

#### Migração de rotas para `table=`
- 15 rotas: definem `XXX_TABLE = Table(fields=..., edit_endpoint=...)` e passam `XXX_TABLE=XXX_TABLE` para o template.
- 14 templates: `action_table(data, table=XXX_TABLE, ctx=ctx)` em vez de parâmetros individuais.
- `sys_movimentos` manteve padrão antigo (`edit_endpoint_map` dinâmico).
- `sys_categories` mantém `build_field_context(FIELDS, {})`.

#### Master-detail com `master_key`
- Adicionado campo `master_key` ao `Table`.
- Template usa `data | groupby(table.master_key)` no Jinja: primeiro item do grupo é a linha mestre, todos os itens são detalhe.
- Compras: dados achatados via `LinhaTransacao(transacao, previsao, compra)`, `master_key='compra_id'`.
- Contas a pagar/receber: `master_key='transacao_id'`.
- Adicionadas properties `transacao_id`, `status_compra`, `carteira` a `LinhaTransacao`.
- Removida classe `CompraLinha` (substituída por `LinhaTransacao`).

#### Detalhe expansível
- Substituído Bootstrap Collapse por click handler JS customizado com `data-expand-target`.
- Classes `detail-row` + `collapsed` para controle de visibilidade.
- `data-expand-bound` para evitar duplicação de handlers em múltiplas chamadas de `ajustarTabela()`.

#### Carrossel de detalhe
- Cards com header fixo (labels) + track rolável com dados.
- Layout flex: `‹` 24px + header 88px + track flex + `›` 24px.
- Lazy init na primeira expansão (`car._ready`).
- Setas visíveis apenas quando `scrollWidth > clientWidth`.

#### QR code
- Troca de `qrcodejs@1.0.0` CDN (ilegível) para geração server-side Python `qrcode` + fallback `qrcode-generator` JS.
- Sanitização da URL com regex `https?:\/\/[^\s]+`.
- Adicionados `qrcode==8.2` e `Pillow==10.2.0` ao `requirements.txt` e `Pipfile`.
- Modal não fecha mais ao clicar no QR code.

#### Performance
- Bootstrap CSS/JS + Bootstrap Icons + `qrcode-generator` baixados para `app/static/lib/`.
- `page_base.html` atualizado para servir localmente (sem CDN).
- `Cache-Control: public, max-age=31536000, immutable` para `/static/*`.

### Sessão 2026-07-13

#### Fix `TypeError: list()` — sombreamento de builtin
- `sys_orcamentos.py`: handler `def list()` sombreava o builtin `list()`, causando `TypeError` em `list(quote.items)`.
- Renomeado para `def orcamento_list()` com `endpoint="list"` para preservar compatibilidade com `url_for("orcamentos.list")`.

#### Menu desktop — destaque do item selecionado
- CSS: `.navbar .nav-link.active` — fundo branco + texto rosa + bold (menu principal).
- CSS: `.bar-link-lg.active` — fundo rosa semi-transparente + texto branco (sub-menu).
- Template `page_sys.html`: removidos estilos inline `style="...border-bottom:2px solid transparent;"` dos links `.bar-link-lg` — estilos movidos para CSS.
- Estilos base `.bar-link-lg` definidos em CSS (cor, padding, border-radius, hover).

#### Menu/sub-menu fixo no desktop
- CSS: `.area-menu` alterado de `margin-top: 100px` para `position: fixed; top: 100px;` (fixo abaixo do header).
- CSS: `main` recebeu `padding-top: 200px` no desktop para compensar header (100px) + navbar (~48px) + submenu (~40px).

#### Intensidade decrescente dos destaques (topo → rodapé)
- Menu ativo: fundo branco + texto rosa (mais forte).
- Sub-menu ativo: `background: rgba(233,30,99,0.75)` (suave).
- Header da tabela: `background: #e9a6b9; color: #880e4f;` (opaco, suave).
- Rodapé (`.sistema-rodape`): `background: rgba(233,30,99,0.08)` (mais suave).

#### Nota: `position: sticky` no `.page-list-header`
- Tentativa de fixar aba Dados/Filtros abaixo do menu com `sticky; top: 190px` causou reorder dentro do flex container (tabs abaixo da lista).
- Revertido — `padding-top: 200px` no `main` é suficiente para manter as tabs visíveis.

#### Rename Rubrica → Operação
- Model `rubrica.py` renomeado para `operacao.py` (classe `Rubrica` → `Operacao`, tabela `rubrica` → `operacao`).
- FK columns renomeadas: `rubrica_id` → `operacao_id` em `transacao` e `movto`.
- Constante `TIPO_RUBRICA` renomeada para `TIPO_OPERACAO`.
- Blueprint `rubricas` renomeado para `operacoes`, rota `sys_rubricas.py` → `sys_operacoes.py`.
- Templates `sys_rubricas/` renomeados para `sys_operacoes/`.
- Migration `a1b2c3d4e5f6_rename_rubrica_to_operacao.py` criada.
- 22 arquivos atualizados (model, routes, templates, __init__.py, docs).

#### Unificação financeiro: a_pagar + a_receber → transacao
- Blueprints `a_pagar` e `a_receber` unificados em `transacao` (prefixo `/transacao`).
- Arquivo único `sys_transacao.py` com helpers compartilhados: `_list(tipo)`, `_detail(id, tipo)`, `_excluir(id, tipo)`, `_filtrar_vencimento()`, `_build_submitted()`, `_salvar_previsoes()`, `_build_nav()`.
- `TRANSACAO_FIELDS` unificado com `Field(name='conta')` usando property `LinhaTransacao.conta`.
- Sub-rotas: `/pagar/` e `/receber/`. Endpoints: `transacao.pagar_list`, `transacao.pagar_edit`, `transacao.receber_list`, etc.
- Templates renomeados: `sys_a_pagar/` + `sys_a_receber/` → `sys_transacao/pagar/` + `sys_transacao/receber/`.
- `LinhaTransacao` em `utils.py`: adicionada property `conta` (combina `transacao.conta.nome` e `compra.fornecedor.nome`).
- Todas as referências `financeiro.*` → `transacao.*` atualizadas: `page_sys.html`, `sys_compras/form.html`, `sys_orders/form.html`, `__init__.py`, PLANO.md, LAYOUT.md.

### Sessão 2026-07-14

#### Relatório declarativo `Report` (`app/report.py`)
- Dataclass `Report` com `header: dict` e `table: dict` (tudo dict, sem tuples).
- `header`: `show_logo`, `logo_width`, `layout` (`centered`/`logo_left`), `title`, `subtitle`, `title_font_size`, `title_font_style`, `title_align`, `fields` (lista de dicts), `field_columns`, `on_each_page` (default `True`).
- `table`: `columns` (dict raw), `groups`, `footer`, `footer_label`, `after` (callable/text pós-tabela).
- Defaults em `_HEADER_DEFAULTS`.
- `_build_header()`, `_build_table()`, `_build_footer()` resolvem defaults.

#### PDF genérico (`app/pdf.py`)
- `DocPDFReport` com `_build_header()`, `_build_table()`, `_build_footer()`.
- Header: `_render_header_logo_left()` (logo à esquerda, título+campos à direita), `_render_header_centered()`, `_render_header_fields()` com `x_start`/`area_width`.
- Tabela: `_render_table()` centralizada, linhas horizontais (`_draw_hline`), page break com repetição de colunas (`_check_page_break`, `_render_column_headers`), `_render_data_row()`, `_render_footer_row()`, `_calc_col_widths()` (proporcional), shrink-to-fit (`MIN_COL_WIDTH=15mm`).
- Cada célula usa `set_x()` explícito + `new_x="LMARGIN", new_y="NEXT"` na última coluna (mesmo padrão do `gerar_pdf_pedido` que funciona).
- `_render_grouped_tables()`: passa `draw_top_line=False` em contexto de grupo.
- `gerar_pdf_relatorio()`: usa `report.header` dict para logo, `tbl.after` para pós-tabela.

#### Relatório Orçamento (`app/reports/orcamento.py`)
- `ORCAMENTO_REPORT = Report(label='Orçamento', header={...}, table={...})`.
- Header: `layout='logo_left'`, `title='Orçamento #{id}'`, campos (cliente, data, telefone, validade).
- Table: 4 colunas (produto, qtd, preço, valor), footer com total, `after=_forminhas_carteira`.
- Helpers: `_valor_item()`, `_validade_text()`, `_forminhas_carteira()`.

#### Exibição do relatório
- Botão "Enviar" no `form.html` e botão imprimir no `detail.html` apontam para `print_quote` (rota HTML).
- `print.html`: renderiza iframe com `pdf_quote` (PDF FPDF inline) dentro de `{% block content %}` → posicionado naturalmente dentro de `<main>`, abaixo do menu, acima do footer.
- Sem overlay, sem `position:fixed`, sem z-index.

#### Textos
- Rodapé PDF: removido prefixo "Usuário:" — mostra só o nome.
- "Carteira:" → "Forma de Pagamento:" (PDF + HTML detail).
- Default "Forma de Pagamento": "50% no pedido + 50% na entrega" quando não informado.
- `show_user` default `False` (em `Report` e `_ReportFooter`).
- Username em uppercase no rodapé PDF: `user_name.upper()`.

#### Relatório Pedido (`app/reports/pedido.py`)
- `ORDER_REPORT` — mesmo padrão do orçamento.
- Header: `logo_left`, título "Pedido #{id}", campos (cliente via function, data, telefone via function, previsão entrega).
- Table: 4 colunas (produto, qtd, preço, valor com aggregate sum), footer "Total".
- After: "Forminhas: X | Forma de Pagamento: Y".
- `routes/sys_orders.py`: `pdf_order` usa `gerar_pdf_relatorio(ORDER_REPORT, ...)`.
- `print_order.html`: iframe com `pdf_order` dentro de `{% block content %}`, botão "Voltar".

### Sessão 2026-07-15

#### Sistema de Filtros Config-Driven (`XXX_FILTERS`)
- Criado `app/filters.py` com `resolve_filters()`, `filtrar_vencimento()`, `filtrar_vencimento_query()`.
- Cada blueprint define `XXX_FILTERS = {'campo': {'type': '...', ...}}` — TODOS os campos de `XXX_FIELDS` (exceto `filter=False`).
- Painel de filtros (aba "Filtros") lê `data-filter-config` (JSON do FILTERS) e renderiza automaticamente.
- Tipos: `text`, `number`, `select` (dict=checklist, array=dropdown), `boolean`, `date` (presets + inputs).
- Para esconder filtro: remover entrada do dict. Sem defaults — usuário define depois.
- Botão "Limpar": reseta campos in-place. Botão "Aplicar": navega com query params.
- Todos os 15 módulos sys_* com `XXX_FILTERS` completos + `resolve_filters()` + `active_filters` no template.

#### Botões do painel de filtros
- Ordem invertida: "Limpar" (outline-danger) primeiro, "Aplicar" (primary) segundo.
- "Limpar" não navega — apenas reseta campos do formulário e zera badge.

#### `build_field_context()` atualizado
- Retorna `ctx['filter_options']` com opções de select para o JS renderizar no painel.

### Sessão 2026-07-18

#### Sistema de status por eventos (CompraHistorico)
- Criado model `CompraHistorico` (tabela `compra_historico`, coluna `status` em vez de `evento`) substituindo `CompraEvento`.
- Removidos campos de data do model `Compra` (`autorizacao`, `aquisicao`, `cancelado`, `devolucao`, `data_recepcao`).
- Adicionada relação `Compra.historicos` e método `calc_status()` que deriva o status pela precedência: devolucao(9) > recepcao(8) > cancelado(6) > aquisicao(2) > autorizacao(1) > 0.
- Migração: tabela `compra_eventos` renomeada para `compra_historico`, coluna `evento` renomeada para `status`.
- Modal de adição de Histórico com select dinâmico via JS (apenas opções válidas conforme status já existentes).

#### Relatório de Compra — título e texto por status
- `Report` ganhou campos `before_table` e `after_table` (lista de linhas ou callable).
- Cada linha: `text` (string ou callable), `font_size`, `font_style`, `align`, `width`.
- `pdf.py`: título do cabeçalho aceita callable; nova `_render_table_lines()` para renderizar `before_table`/`after_table`.
- `COMPRA_REPORT` usa título dinâmico: Orçamento/Pedido/Cancelamento de Pedido/Devolução de Pedido/Compra conforme `compra.status`.
- `before_table`: espaçamento + fornecedor + texto descritivo (com motivo do histórico atual). Vazio para status sem texto (2, 8).
- `after_table`: espaçamento + linha de assinatura + responsável do histórico do status atual.
- `table.after` mantido como fallback para reports existentes (orcamento, pedido).

#### Formulário de Compra
- Removido campo Operação do formulário (era lido mas nunca persistido na criação).
- Removidas queries e imports de `Operacao` das rotas `new()` e `edit()`.
- Fix: `redirect_after` removido do hidden input no carregamento da página — só é definido ao clicar em "Gerar", evitando redirect acidental para pagamentos ao salvar.
- JS do Histórico: filtro do select reconstroi opções do zero no `show.bs.modal`, usando `data-status` nas linhas da tabela em vez de comparar labels.
