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
│   ├── table.py                    # Sistema de campos + tabelas (Field, Table dataclasses)
│   ├── crypto.py                   # Criptografia Fernet (AES)
│   ├── ntfy.py                     # Notificação push (ntfy.sh)
│   ├── pdf.py                      # Geração de PDF (fpdf2)
│   ├── utils.py                    # Helpers (formatação, parse, transformação)
│   ├── versao.py                   # Versão do sistema
│   │
│   ├── models/                     # SQLAlchemy models (24 models)
│   ├── routes/                     # Blueprints Flask (23 arquivos)
│   ├── templates/                  # Jinja2 (21 diretórios — 17 sys_*, components/, site/, admin/)
│   ├── static/                     # CSS, JS, imagens, uploads
│   │   ├── lib/                    #   Bibliotecas locais (bootstrap, bootstrap-icons, qrcode-generator)
│   └── migrations/                 # Alembic (6 migrations)
│
├── dados/                          # Dados persistentes
│   ├── paginas/                    # Páginas Markdown (sobre.md)
│   ├── pgdata/                     # Dados PostgreSQL (volume Docker)
│   └── uploads/                    # Uploads de fotos
│
├── compose.yml                     # Docker Compose (db + app + pinggy)
├── Dockerfile                      # Imagem da aplicação
├── Pipfile                         # Dependências Python
└── requirements.txt                # Pip freeze
```

#### Models por Módulo

| Módulo | Models | Arquivos |
|--------|--------|----------|
| **admin** | User, Setting | `models/user.py`, `models/setting.py` |
| **site** | — (usa session/cookies) | — |
| **sys** | Conta, Category, Product, Ingredient, ProductIngredient, UnitConversion, Quote, QuoteItem, Order, OrderItem, Compra, CompraItem, Event, Producao, ProducaoProduto, ProducaoInsumo, Rubrica, Carteira, Transacao, Previsao, Recurso, Movto | `models/*.py` |

#### Rotas por Módulo

| Módulo | Blueprint | Arquivo | Rotas |
|--------|-----------|---------|-------|
| **site** | `site` | `routes/site.py` | `/`, `/sobre`, `/contato`, `/sistema`, `/admin` |
| **site** | `site_vitrine` | `routes/site_vitrine.py` | `/vitrine/`, `/vitrine/<id>/add` |
| **site** | `site_orcamento` | `routes/site_orcamento.py` | `/orcamento`, `/api/cliente`, `/orcamento/enviar` |
| **sys** | `auth`, `seguranca` | `routes/sys_auth.py` (unificado) | `/login`, `/logout`, `/seguranca/` (painel + settings) |
| **sys** | `clients`, `products`, `categories`, `ingredients`, `orders`, `compras`, `orcamentos`, `producao`, `rubricas`, `carteira`, `a_pagar`, `a_receber`, `previsoes`, `movimentos`, `recursos`, `reports`, `api` | `routes/sys_*.py` | CRUDs de todas as entidades |
| **site** | `uploads` | `routes/uploads.py` | Uploads de imagens (sys + site) |

### Hierarquia de Componentes (Telas)

```
.
├── page_base.html                 ─ ─ Layout base (doctype, head, bootstrap CDN)
│   ├── page_sys.html              ─ ─ Layout do módulo sys (navbar, submenu, footer)
│   │   ├── action_list.html (macro) ─ Página de listagem com abas Dados/Filtros
│   │   │   ├── action_filter.html  ─   Painel de filtros
│   │   │   └── action_table.html   ─   Tabela com colunas dinâmicas
│   │   └── page_form.html         ─   Página de formulário
│   │       └── action_nav.html    ─     Navegação entre registros (sticky)
│   ├── page_site.html             ─ ─ Layout do módulo site (header, nav, footer)
│   └── admin/page_admin.html      ─ ─ Placeholder do módulo admin
```

**Macros compartilhadas:**

| Macro | Arquivo | Descrição |
|-------|---------|-----------|
| `action_list(title, new_url, extra_actions)` | `action_list.html` | Macro mestra de listagem: abas Dados/Filtros, tabela sortable, filtro JS client-side |
| `action_table(data, fields, ctx, edit_endpoint, ...)` | `action_table.html` | Tabela com colunas dinâmicas, ordenação, detalhe expansível, botão de ação centralizado |
| `action_filter(caller_content)` | `action_filter.html` | Painel de filtros |
| `action_edit(url)` | `action_edit.html` | Botão de editar (ícone lápis) |
| `action_nav(back_url, nome, nav, edit_endpoint, entity_id, status, actions2)` | `action_nav.html` | Navegação entre registros (anterior/próximo, sticky, responsivo) |

**Sistema de Fields:** Cada blueprint define `*_FIELDS = [Field(name, label, width, input, options, filter, query, ...)]`. O dataclass `Field` configura colunas, filtros, máscaras, agregadores (soma), links e validação — usado para renderizar tabelas e formulários dinamicamente.

### Banco de Dados (PostgreSQL 16)

**24 tabelas**, sem views/stored procedures — toda lógica em Python.

| Grupo | Tabelas | Descrição |
|-------|---------|-----------|
| **Sistema (admin)** | `users`, `settings` | Login, configurações criptografadas |
| **Cadastros (sys)** | `conta`, `categories`, `products`, `ingredients`, `product_ingredients`, `unit_conversions` | Clientes/fornecedores, categorias, produtos, insumos, receituário, conversões |
| **Comercial (sys)** | `quotes`, `quote_items`, `orders`, `order_items`, `compras`, `compra_itens`, `events` | Orçamentos, pedidos, compras, eventos |
| **Produção (sys)** | `producao`, `producao_produtos`, `producao_insumos` | Batches de produção, produtos por batch, insumos calculados |
| **Financeiro (sys)** | `rubrica`, `carteira`, `transacao`, `previsao`, `recurso`, `movto` | Plano de contas, formas de pagamento, transações, parcelas, recursos, movimentações |

**Relacionamentos chave:**

- `quotes` → `orders` (conversão orçamento→pedido via `quote.pedido_id`)
- `orders` → `producao` (pedido alocado em produção via `order.producao_id`)
- `orders`/`compras` → `carteira` (forma de pagamento via `carteira_id`)
- `carteira.gerar`: `0`=Movto (fluxo de caixa direto), `1`=Transacao+Previsoes (contas a pagar/receber)
- `transacao` → `previsao` (1:N parcelas)
- `previsao` → `movto` (baixa de previsão no fluxo de caixa)

**Hierarquia rubrica:** Auto-referenciada (`rubrica.pai_id` → `rubrica.id`) para plano de contas em árvore.

**Status calculados:**

| Campo | Lógica |
|-------|--------|
| `Transacao.status` | 8 se cancelado; 0 se `sum(previsto) < valor`; senão `max(previsoes.status)` |
| `Previsao.status` | 8 se transação cancelada; 0=Editando; 1=Pendente; 2=Parcial; 9=Quitado |
| Faturado (pedido/compra) | Derivado: `True` se `transacao_id` ou `movto_id` preenchido |

### Funções Principais no Código

| Arquivo | Função | Descrição |
|---------|--------|-----------|
| `__init__.py` | `create_app()` | Factory: configura Flask, DB, blueprints, models, filters, executa upgrade(), cria admin |
| `__init__.py` | `_fetch_tunnel_url()` | Busca URL do túnel Pinggy |
| `utils.py` | `fmt_brl()`, `fmt_date()`, `fmt_id()` | Formatação para templates (moeda, data, ID) |
| `utils.py` | `deep_attr()` | Acesso aninhado a atributos (`obj.conta.nome`) |
| `utils.py` | `parse_prazo_recebimento()` | DSL de prazos: "P/E", "3x", "30", "0/15" |
| `utils.py` | `aplicar_transformacao()` | Listener before_insert/update: Title Case/UPPERCASE automático |
| `utils.py` | `_title_case()` | Title Case respeitando conectores pt-BR |
| `utils.py` | `_save_event()` | Persiste dados de evento (quote/order) |
| `utils.py` | `render_pagina()` | Renderiza Markdown → HTML (páginas institucionais) |
| `utils.py` | `LinhaTransacao` | Wrapper para listar transações com/sem previsões. Properties: `transacao_id`, `compra_id`, `pedido_id`, `status_compra`, `carteira`, `fornecedor`, `cliente`, `fatura`, `valor`, `faturado`, `id` (previsão), `vencimento`, `documento`, `previsto`, `realizado`, `variacao`, `saldo`, `status` |
| `table.py` (ex‑`fields.py`) | `Field` | Dataclass de definição de campo |
| `table.py` | `Table` | Dataclass com `fields`, `fields_master/detail`, `master_key`, `edit_endpoint`, `detail_data` |
| `table.py` | `fields_to_columns()` | Converte Field[] para colunas de tabela HTML |
| `table.py` | `build_field_context()` | Popula selects com dados do banco |
| `table.py` | `register_model()` | Registra model para consulta via `Field.query` |
| `constants.py` | `TRANSFORMAR_AO_SALVAR` | Mapping model → campos com modo de transformação |
| `crypto.py` | `encrypt()` / `decrypt()` | Fernet AES com chave derivada de SECRET_KEY |
| `ntfy.py` | `notificar()` | Envia notificação push de novo orçamento |
| `pdf.py` | `gerar_pdf_pedido()` | Gera PDF do pedido |
| `pdf.py` | `gerar_pdf_orcamento()` | Gera PDF do orçamento |
| `sys_auth.py` | `login_sistema()` | Login doceira (user+senha+chave HMA) |
| `sys_auth.py` | `login_admin()` | Login admin (user+senha+chave, 2FA) |
| `sys_auth.py` | `_impose_delay()` | Proteção brute-force (delay progressivo após 3 falhas) |
| `sys_auth.py` | `_gerar_chave()` | Gera chave HMA (Hora/Mês/Ano) para 2FA |
| `sys_orders.py` | `converter_orcamento()` | Converte quote → order (busca conta por nome/telefone) |
| `sys_producao.py` | `_calcular_qtd_produzir()` | Calcula quantidade a produzir (respeita qtd_minima) |
| `sys_producao.py` | `_calcular_insumos()` | Calcula insumos totais baseado no receituário |
| `sys_clients.py` | `_cpf_valido()` / `_cnpj_valido()` | Validação de CPF/CNPJ |

### Casos de Uso

| Caso de Uso | Módulo | Fluxo |
|-------------|--------|-------|
| **Navegar na vitrine** | site | Cliente acessa `/vitrine/` → vê produtos por categoria → adiciona ao carrinho (session) |
| **Solicitar orçamento** | site | Cliente informa nome/telefone → adiciona itens → envia → notificação push (ntfy.sh) |
| **Login doceira** | admin | 1 click no logo → popup → user+senha + chave HMA (hora/mês/ano) |
| **Login admin** | admin | 2 clicks rápidos no logo → popup admin → user+senha+chave |
| **Gerenciar cadastros** | sys | CRUD: categorias, insumos, produtos, contas, rubricas, carteiras |
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
- **JS:** Vanilla JavaScript. Sem jQuery, sem frameworks JS. Bootstrap bundle servido localmente em `static/lib/`. Dependências externas: Cropper.js (CDN). QR code gerado via `qrcode-generator` (CDN) no cliente.
- **CSS:** Customizado em `static/css/style.css`. Cache-busting manual `?v=N`. Variáveis CSS: `--rosa`, `--verde-menta`, `--bg-claro`. Bootstrap 5.3.2 + Bootstrap Icons servidos localmente em `static/lib/` (sem CDN). Tema claro fixo (`data-bs-theme="light"`).

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
- **Nomenclatura:** Models em inglês (`Conta`, `Order`, `Product`), rotas em português (`/contas`, `/pedidos`, `/produtos`), blueprints em inglês (`clients`, `orders`, `products`).
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
