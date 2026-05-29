# Plano — Sistema de Gestão para Doceira (v1 sem autenticação)

## 1. Stack Tecnológica

| Camada | Tecnologia | Motivo |
|---|---|---|
| Backend | Flask (Python) | Leve, flexível, ótimo para CRUD + relatórios |
| ORM | Flask-SQLAlchemy | Abstração do banco, migrações facilitadas |
| Migrações | Flask-Migrate (Alembic) | Versionamento do schema |
| Frontend | Bootstrap 5 + Jinja2 | Responsivo nativo (desktop + mobile) |
| Banco | PostgreSQL | Relacional, suporte a agregações |
| Container | Docker Compose | App + banco em 2 serviços |

**Obs**: Versão inicial **sem autenticação** — acesso livre a todas as telas.

---

## 2. Estrutura de Diretórios

```
algodoce/
├── docker-compose.yml
├── Dockerfile
├── .env
├── requirements.txt
├── app/
│   ├── __init__.py          # create_app() factory
│   ├── config.py            # Config classes
│   ├── extensions.py        # db, migrate
│   ├── models/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── product.py
│   │   ├── ingredient.py
│   │   ├── product_ingredient.py
│   │   ├── order.py
│   │   └── order_item.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── clients.py
│   │   ├── products.py
│   │   ├── ingredients.py
│   │   ├── orders.py
│   │   └── reports.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── clients/
│   │   ├── products/
│   │   ├── ingredients/
│   │   ├── orders/
│   │   └── reports/
│   └── static/
│       └── css/
└── migrations/
```

---

## 3. Modelagem do Banco de Dados

### 3.1. Client
| Campo | Tipo | Descrição |
|---|---|---|
| id | Integer, PK | |
| nome | String(100) | |
| email | String(120), unique | |
| telefone | String(20) | |
| endereco | Text | |
| ativo | Boolean | |

### 3.2. Product
| Campo | Tipo | Descrição |
|---|---|---|
| id | Integer, PK | |
| nome | String(100) | |
| descricao | Text | |
| preco | Numeric(10,2) | |
| ativo | Boolean | |

### 3.3. Ingredient
| Campo | Tipo | Descrição |
|---|---|---|
| id | Integer, PK | |
| nome | String(100) | |
| unidade_medida | String(20) | kg, g, L, ml, un, etc |

### 3.4. ProductIngredient (receita)
| Campo | Tipo | Descrição |
|---|---|---|
| product_id | FK → product.id | |
| ingredient_id | FK → ingredient.id | |
| quantidade | Numeric(10,3) | Quantidade do ingrediente por **unidade** do produto |

PK composta (product_id, ingredient_id).

### 3.5. Order
| Campo | Tipo | Descrição |
|---|---|---|
| id | Integer, PK | |
| client_id | FK → client.id | |
| data_pedido | DateTime | auto_now |
| data_entrega | Date | **Data em que o cliente quer receber** |
| status | String(20) | pendente, em_producao, pronto, entregue, cancelado |
| observacao | Text | |
| total | Numeric(10,2) | Calculado pelos itens |

### 3.6. OrderItem
| Campo | Tipo | Descrição |
|---|---|---|
| id | Integer, PK | |
| order_id | FK → order.id | |
| product_id | FK → product.id | |
| quantidade | Integer | |
| preco_unitario | Numeric(10,2) | Snapshot do preço no momento do pedido |

---

## 4. Detalhamento por Funcionalidade

### 4.1. Estrutura Docker

**docker-compose.yml**:
- Serviço `web`: build da imagem Flask, porta 5000 mapeada, volume com código para hot reload
- Serviço `db`: imagem postgres:15, volume persistente para dados
- Variáveis de ambiente via `.env`: `DATABASE_URL`, `SECRET_KEY`, `FLASK_ENV`

**Dockerfile**:
- `python:3.11-slim`
- Instala dependências do `requirements.txt`
- Expõe porta 5000
- Comando: `flask run --host=0.0.0.0` (dev) / `gunicorn` (futuro)

### 4.2. Cadastro de Clientes

**Telas**:
- Lista de clientes (tabela com nome, email, telefone, ativo)
- Formulário de criar / editar cliente
- Ação para ativar/desativar

**Rotas**:
- `GET /clientes` — listar
- `GET /clientes/novo` — formulário criar
- `POST /clientes/novo` — salvar
- `GET /clientes/<id>/editar` — formulário editar
- `POST /clientes/<id>/editar` — atualizar
- `POST /clientes/<id>/toggle` — ativar/desativar

### 4.3. Cadastro de Ingredientes

**Telas**:
- Lista de ingredientes (tabela com nome, unidade)
- Formulário criar / editar

**Rotas**:
- `GET /ingredientes` — listar
- `GET /ingredientes/novo` — formulário criar
- `POST /ingredientes/novo` — salvar
- `GET /ingredientes/<id>/editar` — formulário editar
- `POST /ingredientes/<id>/editar` — atualizar

### 4.4. Cadastro de Produtos

**Telas**:
- Lista de produtos (tabela com nome, preço, ativo)
- Formulário criar / editar (com seção para adicionar ingredientes da receita)
- Ação para ativar/desativar

**Rotas**:
- `GET /produtos` — listar
- `GET /produtos/novo` — formulário criar
- `POST /produtos/novo` — salvar
- `GET /produtos/<id>/editar` — formulário editar
- `POST /produtos/<id>/editar` — atualizar
- `POST /produtos/<id>/toggle` — ativar/desativar

### 4.5. Pedidos

**Telas**:
- Dashboard inicial: pedidos com data_entrega próxima (próximos 7 dias)
- Lista de pedidos (filtros: data, status, cliente)
- Criar pedido: selecionar cliente, data de entrega, adicionar produtos com quantidade
- Detalhe do pedido (itens, total, status)
- Alterar status (pendente → em_producao → pronto → entregue)

**Lembretes de produção**:
- No dashboard: tabela destacando pedidos com data_entrega nos próximos dias
- Status "pendente" ou "em_producao" são os que precisam atenção
- Ordenado por data_entrega (mais urgente primeiro)

**Rotas**:
- `GET /` — dashboard com lembretes
- `GET /pedidos` — listar
- `GET /pedidos/novo` — formulário criar
- `POST /pedidos/novo` — salvar
- `GET /pedidos/<id>` — detalhe
- `POST /pedidos/<id>/status` — alterar status
- `POST /pedidos/<id>/cancelar` — cancelar pedido

### 4.6. Relatório de Compras (Ingredientes)

**Objetivo**: Dado um período, calcular a quantidade total de cada ingrediente necessária para produzir todos os produtos de todos os pedidos com entrega naquele período.

**Lógica**:
```
1. Pedidos com data_entrega entre inicio e fim, status != "cancelado"
2. Para cada OrderItem:
   - Para cada ProductIngredient do produto:
     - total_ingrediente += product_ingredient.quantidade * order_item.quantidade
3. Agrupar por ingrediente
```

**Tela**: Formulário com data_inicio e data_fim → tabela:
| Ingrediente | Unidade | Quantidade Total |

**Rota**: `GET /relatorios/compras?data_inicio=...&data_fim=...`

### 4.7. Relatórios Futuros (ideias)

- Faturamento por período
- Produtos mais pedidos
- Produção diária prevista (grade dos próximos dias)

---

## 5. Fluxo de Telas (v1)

```
Dashboard (raiz /)
├── Clientes (/clientes)
├── Ingredientes (/ingredientes)
├── Produtos (/produtos)
├── Pedidos (/pedidos)
└── Relatório de Compras (/relatorios/compras)
```

Navegação por navbar no topo. Todas as telas responsivas (Bootstrap 5).

---

## 6. Observações Técnicas

- **CSRF**: Flask-WTF nos formulários
- **Responsividade**: Bootstrap 5 grid — funciona em desktop e mobile
- **API futura**: fácil adicionar rotas JSON depois
- **Migrações**: `flask db init && flask db migrate && flask db upgrade`
- **Backup do BD**: `pg_dump` via script ou volume persistente
