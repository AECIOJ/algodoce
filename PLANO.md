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
| `orders` | `status` | 0=Pendente, 1=Produzindo, 2=Pronto, 3=Cancelado, 8=Faturado, 9=Entregue |
| `orders` | `forma_pagamento` | 0=À vista, 1=50% Pedido + 50% Entrega, 2=Na Entrega |
| `orders` | `forminhas` | 0=Simples, 1=Fornecidas pelo Cliente |
| `quotes` | `status` | 0=Pendente, 1=Negociação, 6=Renovado, 7=Expirado, 8=Reprovado, 9=Aprovado |
| `quotes` | `forma_pagamento` | (mesmo de orders) |
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
Cadastro   → Categorias | Insumos | Produtos | Contas | Rubricas
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
| `FORMA_PAGAMENTO` | Formulários de pedido e orçamento |
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
    "FormaPagamento":  {"nome": 1},
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
2. **Conversão orçamento→pedido:** Doceira ajusta preços → converte → cria conta do cliente + transação tipo V
3. **Produção:** Doceira cria batch com período → sistema calcula insumos automaticamente (baseado no receituário) → acompanha progresso em 3 etapas (preparo, montagem, embalagem)
4. **Compras:** Doceira registra compra de insumos → informa itens (insumo+qtd+preço) → gera transação tipo C + parcelas → integra com contas a pagar
5. **Financeiro 2 camadas:** Transações+Previsões (contas a pagar/receber) e Movimentações+Recursos (fluxo de caixa real). Transações com compra_id ou pedido_id são travadas (editáveis só as Previsões).
