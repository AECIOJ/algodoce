## Resumo do Sistema **AlgoDoce**

### Visão Geral
Sistema completo em **Python/Flask** para gestão de uma **doceria/confeitaria** (pessoa jurídica). Possui site público (vitrine, orçamento) e painel administrativo completo. Banco **PostgreSQL 16** com SQLAlchemy, templates **Jinja2 + Bootstrap 5**, Docker Compose (PostgreSQL + App + ngrok).

---

### Estrutura de Diretórios
```
app/
├── __init__.py         # Factory create_app(), registra blueprints
├── extensions.py       # Inicializa SQLAlchemy, Migrate, LoginManager
├── models/             # Models (SQLAlchemy)
├── routes/             # Blueprints (Flask)
├── templates/          # Templates (Jinja2)
├── static/             # CSS, JS, imagens, uploads
├── migrations/         # Migrations (Alembic)
├── config.py           # Configurações
├── constants.py        # Enums (status, tipos)
├── crypto.py           # Fernet encryption
├── ntfy.py             # Notificações push
├── pdf.py              # Geração de PDF (fpdf2)
└── utils.py            # Filtros/helpers
```

---

### Tabelas do Banco

Não há **views**, **stored functions** ou **triggers** no banco — toda a lógica fica na aplicação Python.

---

#### Cadastros Básicos

---

##### `conta` (Model: `Conta` — `app/models/client.py`)

Clientes e fornecedores.

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `nome` | String(100) | | sim | | Title Case no save via `TRANSFORMAR_AO_SALVAR` |
| `email` | String(120) | UNIQUE | não | | |
| `telefone` | String(20) | | não | | |
| `endereco` | Text | | não | | |
| `cpf` | String(14) | | não | | |
| `cnpj` | String(18) | | não | | |
| `insc_estadual` | String(20) | | não | | |
| `ativo` | Boolean | | não | `True` | |
| `tipo` | Integer | | não | `0` | 0=Cliente, 1=Cliente/Fornecedor, 2=Fornecedor |

**Relacionamentos:**
- `orders` → `Order` (`backref="conta"`, `lazy=dynamic`)
- `transacoes` → `Transacao` (`backref="transacoes"`)
- `movtos` → `Movto` (`backref="movtos"`)

---

##### `carteira` (Model: `Carteira` — `app/models/carteira.py`)

Carteiras de pagamento/recebimento cadastráveis.

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `nome` | String(50) | | sim | | Title Case no save via `TRANSFORMAR_AO_SALVAR` |
| `uso` | Integer | | sim | `1` | 0=Pedido, 1=Ambos, 2=Compra |
| `gerar` | Integer | | sim | `0` | 0=Movimento (cria Movto), 1=Previsão (cria Transacao+Previsoes) |
| `prazo_recebimento` | String(100) | | não | | DSL de prazos: P/E, 1, 3x, 0/15. Apenas se gerar=1 |
| `taxa_recebimento` | Numeric(5,2) | | sim | `0` | Percentual de taxa (ex: 3.5 para cartão) |

**Seed data (migration `d5ff48124a39` — originalmente tabela `forma_pagamento`, renomeada pela migration `5096816c1660`):**

| id | nome | uso | gerar | prazo_recebimento | taxa_recebimento |
|----|------|-----|-------|-------------------|-----------------|
| 1 | Dinheiro | 1 (Ambos) | 0 (Movimento) | | 0 |
| 2 | Pix | 1 (Ambos) | 0 (Movimento) | | 0 |
| 3 | Cartão Débito | 1 (Ambos) | 0 (Movimento) | | 0 |
| 4 | Cartão Crédito | 1 (Ambos) | 1 (Previsão) | | 0 |
| 5 | Boleto | 2 (Compra) | 1 (Previsão) | | 0 |
| 6 | Depósito | 1 (Ambos) | 0 (Movimento) | | 0 |

**Referenciado por:** `Order.carteira_id`, `Quote.carteira_id`, `Compra.carteira_id`, `Previsao.carteira_id`

---

##### `categories` (Model: `Category` — `app/models/category.py`)

Categorias de produtos (ex: Bolos, Doces, Salgados).

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `nome` | String(100) | | sim | | Title Case no save |
| `ativo` | Boolean | | não | `True` | |
| `ordem` | Integer | | não | `0` | Ordem de exibição na vitrine |

**Relacionamentos:**
- `products` → `Product` (`backref="products"`, via `Product.category`)

---

##### `products` (Model: `Product` — `app/models/product.py`)

Produtos vendidos pela doceria.

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `nome` | String(100) | | sim | | Title Case no save |
| `descricao` | Text | | não | | |
| `preco` | Numeric(10,2) | | sim | | |
| `qtd_minima` | Integer | | sim | `0` | |
| `imagem` | String(255) | | não | | Caminho relativo da foto |
| `ativo` | Boolean | | não | `True` | |
| `category_id` | Integer | FK→categories.id | não | | |

**Relacionamentos:**
- `category` → `Category` (`backref="products"`)
- `ingredients` → `ProductIngredient` (`backref="product"`, `lazy=dynamic`, `cascade="all, delete-orphan"`)

---

##### `ingredients` (Model: `Ingredient` — `app/models/ingredient.py`)

Insumos usados na produção (ingredientes, forminhas, embalagens).

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `nome` | String(100) | | sim | | Title Case no save |
| `unidade_medida` | String(20) | | sim | | UPPERCASE no save |
| `tipo` | Integer | | sim | `0` | 0=Ingrediente, 1=Forminha, 2=Embalagem |

**Relacionamentos:**
- `products` → `ProductIngredient` (`backref="ingredient"`, `lazy=dynamic`)
- `conversions` → `UnitConversion` (`backref="conversions"`)

---

##### `product_ingredients` (Model: `ProductIngredient` — `app/models/product_ingredient.py`)

Receituário: associa produto aos insumos necessários com quantidade por etapa.

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `product_id` | Integer | PK, FK→products.id | sim | | Compõe PK composta |
| `ingredient_id` | Integer | PK, FK→ingredients.id | sim | | Compõe PK composta |
| `quantidade` | Numeric(10,3) | | sim | | |
| `unidade` | String(20) | | sim | `"un"` | |
| `etapa_id` | Integer | | não | | 0=Preparação, 1=Montagem, 2=Embalagem |

**Relacionamentos:**
- `product` → `Product` (`backref="ingredients"`)
- `ingredient` → `Ingredient` (`backref="products"`)

---

##### `unit_conversions` (Model: `UnitConversion` — `app/models/unit_conversion.py`)

Fator de conversão entre unidades de medida para um mesmo insumo.

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `ingredient_id` | Integer | FK→ingredients.id | sim | | |
| `unidade` | String(20) | | sim | | |
| `fator` | Numeric(10,6) | | sim | | Ex: 1 kg = 1000 g → fator=1000 |

**Relacionamentos:**
- `ingredient` → `Ingredient` (`backref="conversions"`)

---

#### Comercial

---

##### `quotes` (Model: `Quote` — `app/models/quote.py`)

Orçamentos feitos por clientes (público ou admin).

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `data_pedido` | DateTime | | sim | `now()` | |
| `cliente_nome` | String(100) | | sim | | Title Case no save |
| `cliente_telefone` | String(20) | | sim | | |
| `status` | Integer | | sim | `0` | 0=Pendente, 1=Negociação, 6=Renovado, 7=Expirado, 8=Reprovado, 9=Aprovado |
| `pedido_id` | Integer | FK→orders.id | não | | Preenchido após conversão |
| `total` | Numeric(10,2) | | não | | |
| `observacao` | Text | | não | | |
| `validade` | Integer | | sim | `3` | Dias de validade |
| `carteira_id` | Integer | FK→carteira.id | sim | |
| `data_renovacao` | DateTime | | não | |
| `forminhas` | Integer | | sim | `0` | 0=Simples, 1=Fornecidas pelo Cliente |

**Relacionamentos:**
- `carteira` → `Carteira` (`uselist=False`)
- `order` → `Order` (`foreign_keys=pedido_id`, `lazy=joined`)
- `event` → `Event` (`back_populates="quote"`, `uselist=False`, `lazy=joined`)
- `items` → `QuoteItem` (`back_populates="quote"`, `lazy=joined`)

---

##### `quote_items` (Model: `QuoteItem` — `app/models/quote_item.py`)

Itens de cada orçamento.

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `quote_id` | Integer | FK→quotes.id | sim | | |
| `product_id` | Integer | FK→products.id | sim | | |
| `quantidade` | Integer | | sim | | |
| `preco_unitario` | Numeric(10,2) | | não | | |
| `observacao` | Text | | não | | |

**Relacionamentos:**
- `product` → `Product` (`lazy=joined`)
- `quote` → `Quote` (`back_populates="items"`)

---

##### `orders` (Model: `Order` — `app/models/order.py`)

Pedidos convertidos de orçamentos ou criados manualmente.

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `client_id` | Integer | FK→conta.id | sim | | |
| `data_pedido` | DateTime | | sim | `now()` | |
| `data_previsao_entrega` | DateTime | | não | | |
| `data_entrega` | DateTime | | não | | |
| `status` | Integer | | sim | `0` | 0=Pendente, 1=Produzindo, 2=Pronto, 8=Cancelado, 9=Entregue |
| `observacao` | Text | | não | | |
| `total` | Numeric(10,2) | | não | | |
| `carteira_id` | Integer | FK→carteira.id | sim | |
| `transacao_id` | Integer | FK→transacao.id (UNIQUE) | não | | |
| `movto_id` | Integer | FK→movto.id (UNIQUE) | não | | |
| `forminhas` | Integer | | sim | `0` | 0=Simples, 1=Fornecidas |
| `producao_id` | Integer | FK→producao.id | não | | |
| `quote_id` | Integer | FK→quotes.id | não | | |

**Relacionamentos:**
- `conta` → `Conta` (`backref="conta"`)
- `producao` → `Producao` (`lazy=select`)
- `quote` → `Quote` (`foreign_keys=quote_id`, `lazy=select`)
- `carteira` → `Carteira` (`uselist=False`)
- `transacao` → `Transacao` (`foreign_keys=transacao_id`, `uselist=False`)
- `movto` → `Movto` (`foreign_keys=movto_id`, `uselist=False`)
- `event` → `Event` (`back_populates="order"`, `uselist=False`, `lazy=select`)
- `items` → `OrderItem` (`back_populates="order"`, `lazy=select`)

---

##### `order_items` (Model: `OrderItem` — `app/models/order_item.py`)

Itens de cada pedido.

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `order_id` | Integer | FK→orders.id | sim | | |
| `product_id` | Integer | FK→products.id | sim | | |
| `quantidade` | Integer | | sim | | |
| `preco_unitario` | Numeric(10,2) | | não | | |
| `observacao` | Text | | não | | |

**Relacionamentos:**
- `product` → `Product` (`lazy=select`)
- `order` → `Order` (`back_populates="items"`)

---

##### `compras` (Model: `Compra` — `app/models/compra.py`)

Compras de insumos.

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `data` | Date | | sim | | |
| `fornecedor_id` | Integer | FK→conta.id | não | | |
| `valor` | Numeric(12,2) | | sim | | |
| `historico` | Text | | não | | |
| `status` | Integer | | sim | `0` | 0=Orçamento, 1=Pedido, 6=Cancelado, 8=Recebido, 9=Devolvido |
| `data_recepcao` | Date | | não | | |
| `carteira_id` | Integer | FK→carteira.id | não | | |
| `transacao_id` | Integer | FK→transacao.id (UNIQUE) | não | | |
| `movto_id` | Integer | FK→movto.id (UNIQUE) | não | | |

**Relacionamentos:**
- `fornecedor` → `Conta` (`foreign_keys=fornecedor_id`)
- `carteira` → `Carteira` (`uselist=False`)
- `transacao` → `Transacao` (`foreign_keys=transacao_id`, `uselist=False`)
- `movto` → `Movto` (`foreign_keys=movto_id`, `uselist=False`)
- `items` → `CompraItem` (`back_populates="compra"`, `cascade="all, delete-orphan"`)

---

##### `compra_itens` (Model: `CompraItem` — `app/models/compra_item.py`)

Itens de cada compra.

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `compra_id` | Integer | FK→compras.id | sim | | |
| `insumo_id` | Integer | FK→ingredients.id | sim | | |
| `quantidade` | Numeric(12,3) | | sim | | |
| `preco` | Numeric(12,2) | | sim | | |

**Relacionamentos:**
- `compra` → `Compra` (`back_populates="items"`)
- `insumo` → `Ingredient` (`lazy=joined`)

---

##### `events` (Model: `Event` — `app/models/event.py`)

Dados de evento associados a orçamentos e/ou pedidos (casamento, aniversário, etc.).

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `quote_id` | Integer | FK→quotes.id (UNIQUE) | não | | 1:1 com Quote |
| `order_id` | Integer | FK→orders.id (UNIQUE) | não | | 1:1 com Order |
| `tipo` | String(30) | | não | | Ex: Casamento, Aniversário |
| `tema` | String(200) | | não | | |
| `obs` | Text | | não | | |
| `data` | Date | | não | | Data do evento |
| `hora` | Time | | não | | |
| `local` | String(200) | | não | | |
| `convidados` | Integer | | não | | |
| `cerimonial` | String(200) | | não | | |

**Relacionamentos:**
- `quote` → `Quote` (`back_populates="event"`, `foreign_keys=quote_id`)
- `order` → `Order` (`back_populates="event"`, `foreign_keys=order_id`)

---

#### Produção

---

##### `producao` (Model: `Producao` — `app/models/producao.py`)

Batches de produção que agregam pedidos e calculam insumos automaticamente.

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `descricao` | String(200) | | sim | | Title Case no save |
| `data_fim` | DateTime | | não | | |
| `status` | Integer | | sim | `0` | 0=Executando, 9=Finalizado |
| `previsao_de` | Date | | não | | Início do período |
| `previsao_ate` | Date | | não | | Fim do período |

**Relacionamentos:**
- `insumos` → `ProducaoInsumo` (`back_populates="producao"`, `lazy=joined`, `cascade="all, delete-orphan"`)
- `produtos` → `ProducaoProduto` (`back_populates="producao"`, `lazy=joined`, `cascade="all, delete-orphan"`)

---

##### `producao_produtos` (Model: `ProducaoProduto` — `app/models/producao_produto.py`)

Produtos dentro de uma produção, com progresso por etapa.

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `producao_id` | Integer | FK→producao.id | sim | | |
| `order_id` | Integer | FK→orders.id | sim | | |
| `product_id` | Integer | FK→products.id | sim | | |
| `quantidade` | Integer | | sim | | |
| `producao_0` | Integer | | sim | `0` | Qtd concluída na etapa Preparação |
| `producao_1` | Integer | | sim | `0` | Qtd concluída na etapa Montagem |
| `producao_2` | Integer | | sim | `0` | Qtd concluída na etapa Embalagem |

**Relacionamentos:**
- `producao` → `Producao` (`back_populates="produtos"`)
- `order` → `Order` (`lazy=joined`)
- `product` → `Product` (`lazy=joined`)

---

##### `producao_insumos` (Model: `ProducaoInsumo` — `app/models/producao_insumo.py`)

Insumos agregados calculados para a produção (baseado no receituário dos produtos + quantidades nos pedidos).

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `producao_id` | Integer | FK→producao.id | sim | | |
| `insumo_id` | Integer | FK→ingredients.id | sim | | |
| `quantidade` | Numeric(10,3) | | sim | | Quantidade necessária total |
| `comprado` | Numeric(10,3) | | sim | `0` | Quantidade já comprada |
| `unidade` | String(20) | | sim | | |
| `tipo` | Integer | | sim | `0` | 0=Ingrediente, 1=Forminha, 2=Embalagem |

**Relacionamentos:**
- `producao` → `Producao` (`back_populates="insumos"`)
- `insumo` → `Ingredient` (`lazy=joined`)

---

#### Financeiro

---

##### `rubrica` (Model: `Rubrica` — `app/models/rubrica.py`)

Plano de contas (auto-referenciada para hierarquia de categorias financeiras).

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `nome` | String(100) | | sim | | |
| `tipo` | Integer | | sim | `1` | 1=Receitas, 2=Despesas |
| `pai_id` | Integer | FK→rubrica.id | não | | Auto-referência (hierarquia) |
| `ordem` | Integer | | sim | `0` | |
| `fator` | Integer | | sim | `1` | 1=normal, -1=inverter sinal |
| `ativa` | Boolean | | não | `True` | |

**Relacionamentos:**
- `pai` → `Rubrica` (`remote_side=Rubrica.id`, `backref="filhos"`) — auto-relacionamento
- `transacoes` → `Transacao` (`backref="transacoes"`)
- `movtos` → `Movto` (`backref="movtos"`)

---

##### `transacao` (Model: `Transacao` — `app/models/transacao.py`)

Transações financeiras — primeira camada do financeiro (contas a pagar/receber).

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `data` | Date | | sim | | |
| `tipo` | String(1) | | sim | | 'P'=Pagar, 'R'=Receber, 'C'=Compras, 'V'=Vendas |
| `conta_id` | Integer | FK→conta.id | não | | |
| `rubrica_id` | Integer | FK→rubrica.id | não | | |
| `fatura` | String(50) | | não | | Número da fatura |
| `valor` | Numeric(12,2) | | sim | | |
| `historico` | Text | | não | | |
| `cancelado` | Date | | não | | Se preenchido, transação cancelada |

**Relacionamentos:**
- `conta` → `Conta` (`backref="transacoes"`)
- `rubrica` → `Rubrica` (`backref="transacoes"`)
- `previsoes` → `Previsao` (`backref="transacao"`, `cascade="all, delete-orphan"`, `order_by="Previsao.vencimento, Previsao.id"`)

**Propriedades computadas:**

| Propriedade | Tipo | Lógica |
|-------------|------|--------|
| `status` | int | 8 se `cancelado` preenchido; 0 se não há `previsoes` ou `sum(previsto) < valor`; senão `max(p.status)` |
| `status_label` | str | Lookup em `PREVISAO_STATUS` |
| `compra` | `Compra` ou None | `Compra.query.filter_by(transacao_id=self.id).first()` |
| `pedido` | `Order` ou None | `Order.query.filter_by(transacao_id=self.id).first()` |

---

##### `previsao` (Model: `Previsao` — `app/models/previsao.py`)

Parcelas/previsões de pagamento ou recebimento de cada transação.

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `transacao_id` | Integer | FK→transacao.id | sim | | |
| `documento` | String(50) | | não | | UPPERCASE no save |
| `vencimento` | Date | | sim | | |
| `previsto` | Numeric(12,2) | | sim | | Valor previsto |
| `realizado` | Numeric(12,2) | | não | | Valor efetivamente pago/recebido |
| `variacao` | Numeric(12,2) | | não | `0` | Diferença (desconto/juros/multa) |
| `carteira_id` | Integer | FK→carteira.id | não | | Origem da forma de pagamento |
| `taxa` | Numeric(5,2) | | sim | `0` | Taxa vigente no momento da criação |

**Relacionamentos:**
- `transacao` → `Transacao` (`backref="previsoes"`)
- `movtos` → `Movto` (`backref="movtos"`)
- `carteira` → `Carteira` (`uselist=False`)

**Propriedades computadas:**

| Propriedade | Tipo | Lógica |
|-------------|------|--------|
| `status` | int | 8 se transação cancelada; 0 se `sum(previsto) < valor`; 1 se `realizado is None`; 9 se `realizado >= previsto+variacao`; senão 2 |
| `saldo` | float | `previsto + variacao - (realizado or 0)` |

---

##### `recurso` (Model: `Recurso` — `app/models/recurso.py`)

Recursos financeiros (contas correntes, caixa, cartões).

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `nome` | String(100) | | sim | | Title Case no save |
| `tipo` | Integer | | sim | `0` | 0=Caixa, 1=Banco, 2=Cartão |
| `saldo` | Numeric(12,2) | | sim | `0` | Saldo inicial |
| `data` | Date | | não | | |

**Relacionamentos:**
- `movtos` → `Movto` (`backref="movtos"`)

---

##### `movto` (Model: `Movto` — `app/models/movto.py`)

Movimentações financeiras — segunda camada do financeiro (fluxo de caixa real por recurso).

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `data` | Date | | sim | | |
| `recurso_id` | Integer | FK→recurso.id | sim | | |
| `tipo` | String(1) | | sim | | 'E'=Entrada, 'S'=Saída |
| `conta_id` | Integer | FK→conta.id | não | | |
| `previsao_id` | Integer | FK→previsao.id | não | | |
| `documento` | String(50) | | não | | UPPERCASE no save |
| `valor` | Numeric(12,2) | | sim | | |
| `variacao` | Numeric(12,2) | | não | `0` | |
| `sincronizar` | Boolean | | sim | `True` | |
| `rubrica_id` | Integer | FK→rubrica.id | não | | |
| `historico` | Text | | não | | Title Case no save |

**Relacionamentos:**
- `recurso` → `Recurso` (`backref="movtos"`)
- `conta` → `Conta` (`backref="movtos"`)
- `previsao` → `Previsao` (`backref="movtos"`)
- `rubrica` → `Rubrica` (`backref="movtos"`)

**Propriedades computadas:**

| Propriedade | Tipo | Lógica |
|-------------|------|--------|
| `historico_display` | str | Retorna `historico` se preenchido; senão auto-label: "Haver na data" se `variacao < 0`, "Acréscimos na data" se `variacao > 0`, "Pago na data" / "Recebido na data" |

---

#### Sistema

---

##### `users` (Model: `User` — `app/models/user.py`)

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `username` | String(80) | UNIQUE | sim | | |
| `password_hash` | String(256) | | sim | | Hash gerado por `werkzeug.security` |

**Métodos:**
- `set_password(password)`: Gera hash e armazena
- `check_password(password)`: Verifica senha contra o hash

---

##### `settings` (Model: `Setting` — `app/models/setting.py`)

Configurações criptografadas (chave-valor). Usa `Fernet` (AES) + `SHA256(SECRET_KEY)`.

| Coluna | Tipo | PK/FK | Obrig. | Padrão | Notas |
|--------|------|-------|--------|--------|-------|
| `id` | Integer | PK | sim | auto | |
| `key` | String(100) | UNIQUE | sim | | |
| `encrypted_value` | Text | | sim | `""` | AES-encrypted via Fernet |
| `updated_at` | DateTime | | não | `now()` | |

**Propriedades:**
- `value` (str): Faz encrypt/decrypt automático do `encrypted_value` no get/set
- `label` (str): Label legível a partir do KEYS dict

**Chaves conhecidas:** `doceira_telefone`, `doceira_email`, `doceira_nome`, `ntfy_topic`, `ntfy_token`, `painel_usuario`, `painel_senha`, `painel_chave`

---

---

### Rotas / Páginas

#### Público (sem login)

| Blueprint | Rota | Função |
|-----------|------|--------|
| `auth` | `/login` | Página de login (GET) / autenticação (POST) |
| `auth` | `/api/login-sistema` | Login do sistema com chave HMA |
| `auth` | `/api/login-admin` | Login admin com 2FA |
| `auth` | `/api/admin-config` | Verifica se admin está configurado |
| `auth` | `/api/check-chave` | Verifica se chave dinâmica está configurada |
| `auth` | `/logout` | Logout (limpa sessão e cookies) |
| `site` | `/` | Landing page (redireciona se logado) |
| `site` | `/sobre` | Página institucional (Markdown) |
| `site` | `/contato` | Página de contato |
| `vitrine` | `/vitrine/` | Vitrine de produtos (agrupados por categoria) |
| `vitrine` | `/vitrine/<id>/add` | Adiciona produto ao carrinho |
| `orcamento` | `/orcamento` | Montagem de orçamento público |
| `orcamento` | `/orcamento/enviar` | Envio do orçamento (notificação push) |
| `orcamento` | `/orcamento/remover/<id>` | Remove item do orçamento |
| `orcamento` | `/orcamento/atualizar/<id>` | Atualiza quantidade/obs de um item |
| `orcamento` | `/orcamento/salvar` | Salva todas as alterações |
| `orcamento` | `/api/cliente` | Identifica/cria cliente (ajax) |

#### Admin (login obrigatório)

**Dashboard:**
| Blueprint | Rota | Função |
|-----------|------|--------|
| `orders` | `/dashboard` | Painel de produção |

**Cadastros:**
| Blueprint | Rota | Função |
|-----------|------|--------|
| `products` | `/produtos` | Lista de produtos (com busca) |
| `products` | `/produtos/novo` | Cadastrar novo produto |
| `products` | `/produtos/<id>/editar` | Editar produto |
| `products` | `/produtos/<id>/excluir` | Excluir produto |
| `products` | `/produtos/<id>/toggle` | Ativar/desativar produto |
| `products` | `/produtos/<id>/uso` | Verificar se produto está em uso |
| `products` | `/produtos/search` | Busca de produtos (JSON) |
| `products` | `/produtos/upload-temp` | Upload temporário de imagem (base64) |
| `products` | `/produtos/<id>/upload-foto` | Upload definitivo de foto |
| `categories` | `/categorias/` | Lista de categorias |
| `categories` | `/categorias/novo` | Cadastrar nova categoria |
| `categories` | `/categorias/<id>/editar` | Editar categoria |
| `categories` | `/categorias/<id>/excluir` | Excluir categoria |
| `categories` | `/categorias/<id>/toggle` | Ativar/desativar categoria |
| `categories` | `/categorias/<id>/uso` | Verificar se categoria tem produtos |
| `ingredients` | `/insumos` | Lista de insumos |
| `ingredients` | `/insumos/novo` | Cadastrar novo insumo |
| `ingredients` | `/insumos/<id>/editar` | Editar insumo |
| `ingredients` | `/insumos/<id>` | Detalhe do insumo (produtos que o usam) |
| `ingredients` | `/insumos/<id>/uso` | Produtos que usam este insumo |
| `ingredients` | `/insumos/<id>/excluir` | Excluir insumo |
| `clients` | `/contas` | Lista de contas (com busca) |
| `clients` | `/contas/novo` | Cadastrar nova conta |
| `clients` | `/contas/<id>/editar` | Editar conta |
| `clients` | `/contas/<id>/toggle` | Ativar/desativar conta |
| `clients` | `/contas/search` | Busca de contas (JSON) |
| `rubricas` | `/rubricas/` | Lista de rubricas (flat) |
| `rubricas` | `/rubricas/plano` | Plano de contas em árvore |
| `rubricas` | `/rubricas/novo` | Nova rubrica |
| `rubricas` | `/rubricas/<id>/editar` | Editar rubrica |
| `rubricas` | `/rubricas/<id>/uso` | Verificar uso da rubrica |
| `rubricas` | `/rubricas/<id>/excluir` | Excluir rubrica |
| `rubricas` | `/rubricas/<id>/toggle` | Ativar/desativar rubrica |
| `carteira` | `/carteira/` | Lista de carteiras |
| `carteira` | `/carteira/novo` | Cadastrar nova carteira |
| `carteira` | `/carteira/<id>/editar` | Editar carteira |
| `carteira` | `/carteira/<id>/excluir` | Excluir carteira |

**Comercial:**
| Blueprint | Rota | Função |
|-----------|------|--------|
| `orders` | `/pedidos` | Lista de pedidos |
| `orders` | `/pedidos/novo` | Criar novo pedido |
| `orders` | `/pedidos/<id>/editar` | Editar pedido |
| `orders` | `/pedidos/<id>/status` | Alterar status do pedido |
| `orders` | `/pedidos/<id>/cancelar` | Cancelar pedido |
| `orders` | `/pedidos/<id>/print` | Versão para impressão |
| `orders` | `/pedidos/<id>/pdf` | PDF do pedido |
| `orders` | `/orcamentos` | Lista de orçamentos |
| `orders` | `/orcamentos/<id>` | Detalhe do orçamento |
| `orders` | `/orcamentos/novo` | Criar novo orçamento |
| `orders` | `/orcamentos/<id>/editar` | Editar orçamento |
| `orders` | `/orcamentos/<id>/converter` | Converter orçamento em pedido |
| `orders` | `/orcamentos/<id>/status` | Alterar status do orçamento |
| `orders` | `/orcamentos/validar` | Validação/expiracão automática |
| `orders` | `/orcamentos/<id>/renovar` | Renovar orçamento expirado |
| `orders` | `/orcamentos/<id>/excluir` | Excluir orçamento |
| `orders` | `/orcamentos/<id>/print` | Impressão do orçamento |
| `orders` | `/orcamentos/<id>/pdf` | PDF do orçamento |
| `compras` | `/compras/` | Lista de compras |
| `compras` | `/compras/novo` | Nova compra |
| `compras` | `/compras/<id>/editar` | Editar compra |

**Produção:**
| Blueprint | Rota | Função |
|-----------|------|--------|
| `producao` | `/producao/` | Lista de produções |
| `producao` | `/producao/nova` | Criar nova produção |
| `producao` | `/producao/<id>` | Detalhe da produção |
| `producao` | `/producao/<id>/add-pedido` | Adicionar pedido à produção |
| `producao` | `/producao/<id>/remove-pedido/<order_id>` | Remover pedido da produção |
| `producao` | `/producao/<id>/update-comprado` | Atualizar qtd comprada de insumo |
| `producao` | `/producao/<id>/update-produto` | Atualizar progresso de produto |
| `producao` | `/producao/<id>/finalizar` | Finalizar produção |
| `producao` | `/producao/<id>/reativar` | Reativar produção finalizada |
| `producao` | `/producao/<id>/atualizar` | Atualizar com dados recentes |
| `producao` | `/producao/<id>/editar` | Editar descrição/período |
| `producao` | `/producao/<id>/relatorio` | Relatório de produção |

**Financeiro:**
| Blueprint | Rota | Função |
|-----------|------|--------|
| `contas_a_pagar` | `/contas-a-pagar/` | Transações a pagar (tipo P e C) |
| `contas_a_pagar` | `/contas-a-pagar/<id>/detalhes` | Detalhe da transação |
| `contas_a_pagar` | `/contas-a-pagar/novo` | Nova conta a pagar |
| `contas_a_pagar` | `/contas-a-pagar/<id>/editar` | Editar conta a pagar |
| `contas_a_receber` | `/contas-a-receber/` | Transações a receber (tipo R e V) |
| `contas_a_receber` | `/contas-a-receber/<id>/detalhes` | Detalhe da transação |
| `contas_a_receber` | `/contas-a-receber/novo` | Nova conta a receber |
| `contas_a_receber` | `/contas-a-receber/<id>/editar` | Editar conta a receber |
| `previsoes` | `/previsoes/` | Lista de previsões financeiras |
| `previsoes` | `/previsoes/novo` | Nova previsão |
| `previsoes` | `/previsoes/<id>/editar` | Editar previsão |
| `previsoes` | `/previsoes/<id>/excluir` | Excluir previsão |
| `movimentos` | `/movimentos/recebimentos` | Lista de recebimentos |
| `movimentos` | `/movimentos/recebimentos/novo` | Novo recebimento |
| `movimentos` | `/movimentos/recebimentos/<id>/editar` | Editar recebimento |
| `movimentos` | `/movimentos/pagamentos` | Lista de pagamentos |
| `movimentos` | `/movimentos/pagamentos/novo` | Novo pagamento |
| `movimentos` | `/movimentos/pagamentos/<id>/editar` | Editar pagamento |
| `movimentos` | `/movimentos/<id>/excluir` | Excluir movimentação |
| `movimentos` | `/movimentos/api/previsoes` | API de previsões para o form |
| `recursos` | `/recursos/` | Lista de recursos financeiros |
| `recursos` | `/recursos/novo` | Novo recurso |
| `recursos` | `/recursos/<id>/editar` | Editar recurso |

**Segurança:**
| Blueprint | Rota | Função |
|-----------|------|--------|
| `seguranca` | `/seguranca/` | Painel de segurança (requer 2FA: chave dinâmica HMA) |
| `seguranca` | `/seguranca/salvar` | Salvar configurações |
| `seguranca` | `/seguranca/sair` | Sair do painel de segurança |
| `seguranca` | `/seguranca/api/chave` | Verificar chave dinâmica (API) |

**Utilitários:**
| Blueprint | Rota | Função |
|-----------|------|--------|
| `uploads` | `/uploads/<path:filename>` | Servir arquivos de upload |
| `uploads` | `/paginas/<path:filename>` | Servir arquivos de páginas (Markdown) |
| `api` | `/api/transformar-texto` | Transformar valores de campos (upper/lower/title) |

---

### Status e Tipos por Tabela

| Tabela | Campo | Valores |
|--------|-------|---------|
| `conta` | `tipo` | 0=Cliente, 1=Cliente/Fornecedor, 2=Fornecedor |
| `ingredients` | `tipo` | 0=Ingrediente, 1=Forminha, 2=Embalagem |
| `product_ingredients` | `etapa_id` | 0=Preparação, 1=Montagem, 2=Embalagem |
| `orders` | `status` | 0=Pendente, 1=Produzindo, 2=Pronto, 8=Cancelado, 9=Entregue |
| `orders` | `forminhas` | 0=Simples, 1=Fornecidas pelo Cliente |
| `quotes` | `status` | 0=Pendente, 1=Negociação, 6=Renovado, 7=Expirado, 8=Reprovado, 9=Aprovado |
| `quotes` | `forminhas` | (mesmo de orders) |
| `quotes` | `validade` | Dias de validade (default 3) |
| `producao` | `status` | 0=Executando, 9=Finalizado |
| `rubrica` | `tipo` | 1=Receitas, 2=Despesas |
| `transacao` | `tipo` | 'P'=Contas a Pagar, 'R'=Contas a Receber, 'C'=Compras, 'V'=Vendas |
| `previsao` | `status` (calc.) | 0=Editando, 1=Pendente, 2=Parcial, 8=Cancelado, 9=Quitado |
| `recurso` | `tipo` | 0=Caixa, 1=Banco, 2=Cartão |
| `movto` | `tipo` | 'E'=Entrada, 'S'=Saída |
| `producao_insumos` | `tipo` | (mesmo de ingredients) |
| `producao_produtos` | `producao_0/1/2` | Contadores por etapa |

### Menus e Sub-menus

#### Site Público
```
Sobre | Produtos | Orçamento | Contato
```

#### Painel Admin
```
Cadastro   → Categorias | Insumos | Produtos | Contas | Rubricas | Carteiras
Comercial  → Orçamentos | Pedidos | Compras
Produção   → (lista de produções)
Financeiro → Recursos | Contas a Receber | Contas a Pagar | Previsões | Recebimentos | Pagamentos
Segurança  → Painel de Segurança
```

### Mapa de Constantes e Utilitários

| Constante | Onde aparece |
|-----------|--------------|
| `ORDER_STATUS` | Lista/detalhe/form de pedidos, dashboard, produção |
| `QUOTE_STATUS` | Lista/detalhe/form de orçamentos, validação automática |
| `QUOTE_STATUS_FILTER` | Filtro de select/combobox de orçamentos (inclui "todos") |
| `PRODUCAO_STATUS` | Lista/relatório de produção |
| `TIPO_CONTA` | Formulário de contas (cliente/fornecedor) |
| `TIPO_INGREDIENTE` | Formulário de insumos |
| `TIPO_RUBRICA` | Plano de contas em árvore |
| `TIPO_RECURSO` | Formulário de recursos financeiros |
| `PRODUCAO_ETAPAS` | Detalhe da produção (progresso) |
| `FORMINHAS` | Formulários de pedido e orçamento |
| `PREVISAO_STATUS` | Lista de contas a pagar/receber (calculado) |
| `TIPO_PREVISAO` | Direção financeira: P=Pagar, R=Receber |
| `TIPO_TRANSACAO` | Origem: P=Contas a Pagar, R=Contas a Receber, C=Compras, V=Vendas |
| `CONECTORES` | Conjunto de stopwords/ conectores pt-BR (formatação de texto) |
| `TRANSFORMAR_AO_SALVAR` | Mapeia models a instruções de transformação (title/upper case) ao salvar |

**Modos de transformação (`app/constants.py:41-51`, lógica em `app/utils.py:113-128`):**

| Modo | Efeito | Aplicação |
|------|--------|-----------|
| `0` | `lowercase` | (reservado) |
| `1` | `Title Case` | `nome`, `cliente_nome`, `descricao`, `historico` |
| `2` | `UPPERCASE` | `documento`, `unidade_medida` |

```python
TRANSFORMAR_AO_SALVAR = {
    "Category":        {"nome": 1},
    "Product":         {"nome": 1},
    "Ingredient":      {"nome": 1, "unidade_medida": 2},
    "Conta":           {"nome": 1},
    "Quote":           {"cliente_nome": 1},
    "Carteira":  {"nome": 1},
    "Recurso":         {"nome": 1},
    "Producao":        {"descricao": 1},
    "Previsao":        {"documento": 2},
    "Movto":           {"documento": 2, "historico": 1},
}
```

---

### Autenticação e Acesso

**3 níveis:**
1. **Anônimo** — Site público (vitrine, orçamento)
2. **Doceira** — Todo painel admin (login com usuário/senha + chave dinâmica "HMA": H=hora, M=mês, A=ano)
3. **Admin** — Painel de segurança (`/seguranca/`) com autenticação adicional

**Proteção:** Todos os blueprints admin usam `@login_required` + proteção contra força bruta (delay progressivo após 3 falhas, janela de 15min).

---

### Fluxos Principais

1. **Orçamento público:** Cliente navega na vitrine → adiciona itens → informa dados → envia → notificação push para doceira
2. **Conversão orçamento→pedido:** Sistema busca conta por nome+telefone; se `perfect_match` (nome e telefone idênticos) → conversão direta (1 clique); se não → modal com sugestão e/ou alerta de telefone duplicado (`phone_conflict`). Ao converter: cria conta (se nova) + pedido (sem financeiro — passo manual separado)
3. **Produção:** Doceira cria batch com período → sistema calcula insumos automaticamente (baseado no receituário) → acompanha progresso em 3 etapas (preparo, montagem, embalagem)
4. **Compras:** Doceira registra compra de insumos → informa itens (insumo+qtd+preço) → gera transação tipo C + parcelas → integra com contas a pagar
5. **Financeiro do pedido:** Doceira seleciona forma de pagamento no pedido → clica "Gerar Financeiro" → se gerar=0: formulário de Movto (recurso, valor líquido c/ taxa) → se gerar=1: revisão das previsões (geradas pelo `parse_prazo_recebimento`) → confirma → sistema cria Movto ou Transacao+Previsoes
6. **Financeiro 2 camadas:** Transações+Previsões (contas a pagar/receber) e Movimentações+Recursos (fluxo de caixa real). Transações com compra_id ou pedido_id são travadas (editáveis só as Previsões).
