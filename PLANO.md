## Resumo do Sistema **AlgoDoce**

### Visão Geral
Sistema completo em **Python/Flask** para gestão de uma **doceria/confeitaria** (pessoa jurídica). Possui site público (vitrine, orçamento) e painel administrativo completo. Banco **PostgreSQL 16** com SQLAlchemy, templates **Jinja2 + Bootstrap 5**, Docker Compose (PostgreSQL + App + ngrok).

---

### Estrutura de Diretórios
```
app/
├── models/       # Models (SQLAlchemy)
├── routes/       # Blueprints (Flask)
├── templates/    # Templates (Jinja2)
├── static/       # CSS, JS, imagens, uploads
├── migrations/   # Migrations (Alembic)
├── config.py     # Configurações
├── constants.py  # Enums (status, tipos)
├── crypto.py     # Fernet encryption
├── ntfy.py       # Notificações push
├── pdf.py        # Geração de PDF (fpdf2)
└── utils.py      # Filtros/helpers
```

---

### Tabelas do Banco

**Cadastros Básicos:**
| Tabela | Descrição |
|--------|-----------|
| `users` | Usuários do sistema (admin) |
| `conta` | Clientes / Fornecedores (nome, telefone, CPF/CNPJ, endereço) |
| `categories` | Categorias de produtos |
| `products` | Produtos (nome, preço, qtd_mínima, imagem, ativo) |
| `ingredients` | Insumos (nome, unidade_medida, tipo: insumo/forminha/embalagem) |
| `product_ingredients` | Receituário (produto x insumo + quantidade + etapa) |
| `unit_conversions` | Conversão de unidades por insumo |

**Comercial:**
| Tabela | Descrição |
|--------|-----------|
| `quotes` | Orçamentos (cliente, status, validade, forma_pagamento) |
| `quote_items` | Itens do orçamento |
| `orders` | Pedidos (cliente, status, datas, total, itens, evento, produção) |
| `order_items` | Itens do pedido |
| `compras` | Compras (PK sequencial, fornecedor, valor, itens) |
| `compra_itens` | Itens da compra (compra_id, insumo_id, qtd, preco) |
| `events` | Dados de evento (data, hora, local, tema, convidados) |

**Produção:**
| Tabela | Descrição |
|--------|-----------|
| `producao` | Batches de produção (descrição, período, status) |
| `producao_produtos` | Produtos em produção (com progresso por etapa) |
| `producao_insumos` | Insumos calculados para a produção |

**Financeiro:**
| Tabela | Descrição |
|--------|-----------|
| `rubrica` | Plano de contas (auto-referenciada, tipo: receita/despesa) |
| `transacao` | Transações financeiras (tipo P/R/C/V, link compra_id/pedido_id) |
| `previsao` | Parcelas/previsões de cada transação |
| `recurso` | Recursos financeiros (dinheiro, banco, cartão) |
| `movto` | Movimentações financeiras (entrada/saída por recurso) |
| `settings` | Configurações criptografadas (chave-valor) |

---

### Rotas / Páginas

#### Público (sem login)
| Rota | Função |
|------|--------|
| `/` | Landing page (redireciona se logado) |
| `/sobre` | Página institucional (Markdown) |
| `/contato` | Página de contato |
| `/vitrine/` | Vitrine de produtos (agrupados por categoria) |
| `/orcamento` | Montagem de orçamento público |
| `/orcamento/enviar` | Envio do orçamento (notificação push) |

#### Admin (login obrigatório)

**Dashboard:**
- `/dashboard` — Painel de produção

**Comercial:**
- `/pedidos` — CRUD de pedidos (inclui print, PDF, troca de status)
- `/orcamentos` — CRUD de orçamentos (converter em pedido, renovar, expirar)
- `/compras/` — CRUD de compras (controle de insumos, integração contas a pagar)

**Cadastros:**
- `/produtos` — CRUD + toggle ativo + upload foto + busca
- `/categorias` — CRUD + toggle ativo
- `/insumos` — CRUD + detalhe
- `/contas` — CRUD + toggle + busca

**Produção:**
- `/producao/` — CRUD de batches (adicionar/remover pedidos, finalizar, relatório)

**Financeiro:**
- `/contas-a-pagar/` — Transações a pagar (tipo P e C), coluna COMPRA
- `/contas-a-receber/` — Transações a receber (tipo R e V), coluna PEDIDO
- `/movimentos/` — Movimentações (recebimentos/pagamentos)
- `/recursos/` — Recursos financeiros
- `/rubricas/plano` — Plano de contas em árvore

**Segurança:**
- `/seguranca/` — Painel de segurança (requer 2FA: chave dinâmica HMA)

---

### Status e Tipos por Tabela

| Tabela | Campo | Valores |
|--------|-------|---------|
| `conta` | `tipo` | 0=Cliente, 1=Cliente/Fornecedor, 2=Fornecedor |
| `ingredients` | `tipo` | 0=Ingrediente, 1=Forminha, 2=Embalagem |
| `product_ingredients` | `etapa_id` | 0=Preparação, 1=Montagem, 2=Embalagem |
| `orders` | `status` | 0=Pendente, 1=Produzindo, 2=Pronto, 3=Cancelado, 8=Faturado, 9=Entregue |
| `orders` | `forma_pagamento` | 0=À vista, 1=50%+50%, 2=Na Entrega |
| `orders` | `forminhas` | 0=Simples, 1=Fornecidas pelo Cliente |
| `quotes` | `status` | 0=Pendente, 1=Negociação, 6=Renovado, 7=Expirado, 8=Reprovado, 9=Aprovado |
| `quotes` | `forma_pagamento` | (mesmo de orders) |
| `quotes` | `forminhas` | (mesmo de orders) |
| `quotes` | `validade` | Dias de validade (default 3) |
| `producao` | `status` | 0=Executando, 9=Finalizado |
| `rubrica` | `tipo` | 1=Receitas, 2=Despesas |
| `transacao` | `tipo` | 'P'=Pagar, 'R'=Receber, 'C'=Compra, 'V'=Venda |
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
Cadastro   → Categorias | Insumos | Produtos | Contas | Rubricas
Comercial  → Orçamentos | Pedidos | Compras
Produção   → (lista de produções)
Financeiro → Recursos | Contas a Receber | Contas a Pagar | Recebimentos | Pagamentos
```

### Mapa de Status por Página

| Constante | Onde aparece |
|-----------|--------------|
| `ORDER_STATUS` | Lista/detalhe/form de pedidos, dashboard, produção |
| `QUOTE_STATUS` | Lista/detalhe/form de orçamentos, validação automática |
| `PRODUCAO_STATUS` | Lista/relatório de produção |
| `TIPO_CONTA` | Formulário de contas (cliente/fornecedor) |
| `TIPO_INGREDIENTE` | Formulário de insumos |
| `TIPO_RUBRICA` | Plano de contas em árvore |
| `TIPO_RECURSO` | Formulário de recursos financeiros |
| `PRODUCAO_ETAPAS` | Detalhe da produção (progresso) |
| `FORMA_PAGAMENTO` | Formulários de pedido e orçamento |
| `FORMINHAS` | Formulários de pedido e orçamento |
| `PREVISAO_STATUS` | Lista de contas a pagar/receber (calculado) |
| `TIPO_PREVISAO` | Direção financeira: P=Pagar, R=Receber |
| `TIPO_TRANSACAO` | Origem: P=Pagar, R=Receber, C=Compra, V=Venda |

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
2. **Conversão orçamento→pedido:** Doceira ajusta preços → converte → cria conta do cliente + transação tipo V
3. **Produção:** Doceira cria batch com período → sistema calcula insumos automaticamente (baseado no receituário) → acompanha progresso em 3 etapas (preparo, montagem, embalagem)
4. **Compras:** Doceira registra compra de insumos → informa itens (insumo+qtd+preço) → gera transação tipo C + parcelas → integra com contas a pagar
5. **Financeiro 2 camadas:** Transações+Previsões (contas a pagar/receber) e Movimentações+Recursos (fluxo de caixa real). Transações com compra_id ou pedido_id são travadas (editáveis só as Previsões).
