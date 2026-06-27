# Comercial — Relação Compras/Pedidos com Financeiro

## Objetivo

Reformular a integração entre **Compras**, **Pedidos** e o módulo financeiro (contas a pagar/receber), substituindo o acoplamento direto por uma tabela normalizada de formas de pagamento que define o fluxo financeiro automaticamente.

## Resumo das mudanças

- Criação da tabela `forma_pagamento(id, nome, uso, gerar)`
  - `uso`: 0=Pedido, 1=Ambos, 2=Compra
  - `gerar`: 0=Movimento (cria `Movto`), 1=Previsão (cria `Transacao+Previsoes`)
- `compra` e `order` ganham FK `forma_pagamento_id` (em vez do `Integer` atual e do `pagamento` planejado)
- `order` perde o `pagamento` planejado (derivado do FK)
- `transacao` perde `compra_id` e `pedido_id` — FKs movidas para `compra/order.transacao_id`
- `forma_pagamento.modo` → `forma_pagamento.gerar`
- `forma_pagamento.taxa_padrao` → `forma_pagamento.taxa_recebimento`
- Colunas reordenadas: gerar, prazo_recebimento, taxa_recebimento (nessa ordem)
- Botão "Gerar Financeiro" substitui criação automática no save do pedido
- **Status revisados**:
  - `ORDER_STATUS`: 0=Pendente, 1=Produzindo, 2=Pronto, 8=Cancelado, 9=Entregue
  - `COMPRA_STATUS` (novo): 0=Orçamento, 1=Pedido, 6=Cancelado, 8=Recebido, 9=Devolvido
  - Faturado **some dos enums** e passa a ser automático — deriva da presença de `movto_id` ou `transacao_id`
- **Trava**: edição de `forma_pagamento` bloqueada se já referenciada

## Tabela FormaPagamento

```sql
CREATE TABLE forma_pagamento (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(50) NOT NULL,
    uso  INTEGER NOT NULL DEFAULT 1,  -- 0=Pedido, 1=Ambos, 2=Compra
    gerar INTEGER NOT NULL DEFAULT 0,   -- 0=Movimento, 1=Previsão
    prazo_recebimento VARCHAR(100),
    taxa_recebimento NUMERIC(5,2) NOT NULL DEFAULT 0,
);
```

### Seed (migrates os valores atuais do dict `FORMA_PAGAMENTO`)

| Nome | uso | gerar |
|------|-----|-------|
| Dinheiro | 1 (ambos) | 0 (movimento) |
| Pix | 1 (ambos) | 0 (movimento) |
| Cartão Débito | 1 (ambos) | 0 (movimento) |
| Cartão Crédito | 1 (ambos) | 1 (previsão) |
| Boleto | 2 (compra) | 1 (previsão) |
| Depósito | 1 (ambos) | 0 (movimento) |

### Trava de edição

FormaPagamento não pode ser alterada se existir `Compra.forma_pagamento_id == id` ou `Order.forma_pagamento_id == id`. Liberar apenas se nenhuma referência existir. Se precisar alterar uma forma já usada, criar nova linha.

## Alterações no Banco de Dados

### `compras` — adicionar colunas

| Coluna | Tipo | Detalhe |
|--------|------|---------|
| `forma_pagamento_id` | `FK -> forma_pagamento.id, nullable` | Substitui o `pagamento` planejado |
| `transacao_id` | `FK -> transacao.id, nullable, unique` | Preenchido se gerar=1 (Previsão) |
| `movto_id` | `FK -> movto.id, nullable, unique` | Preenchido se gerar=0 (Movimento) |
| `status` | `Integer, nullable=False, default=0` | 0=Orçamento, 1=Pedido, 6=Cancelado, 8=Recebido, 9=Devolvido |
| `data_recepcao` | `Date, nullable` | Preenchido ao marcar Recebido |

### `orders` — adicionar/remover colunas

Adicionar:

| Coluna | Tipo | Detalhe |
|--------|------|---------|
| `forma_pagamento_id` | `FK -> forma_pagamento.id, nullable` | Migra do `order.forma_pagamento` (Integer) atual |
| `transacao_id` | `FK -> transacao.id, nullable, unique` | Preenchido se gerar=1 |
| `movto_id` | `FK -> movto.id, nullable, unique` | Preenchido se gerar=0 |

Remover:

- `forma_pagamento` (Integer) — migrado para FK

### `transacao` — remover colunas

- `compra_id` (FK -> compras.id)
- `pedido_id` (FK -> orders.id)

### `quote` — migrar `forma_pagamento` (Integer) para FK

- `forma_pagamento_id` (FK -> forma_pagamento.id), remover `forma_pagamento` (Integer)

### Migração

1. Criar tabela `forma_pagamento` e popular com seed
2. Adicionar colunas em `compras`, `orders`, `quote`
3. Migrar dados: `order.forma_pagamento` (Integer) → `order.forma_pagamento_id` (FK)
4. Migrar dados: `quote.forma_pagamento` (Integer) → `quote.forma_pagamento_id` (FK)
5. Migrar dados: `transacao.compra_id` → `compra.transacao_id`, depois remover coluna
6. Migrar dados: `transacao.pedido_id` → `order.transacao_id`, depois remover coluna
7. Migrar `order.status`: 3 → 8 (Cancelado)
8. Remover colunas `forma_pagamento` de `orders` e `quote`
9. Atualizar constants.py: remover `ORDER_STATUS[8]="Faturado"`, adicionar `COMPRA_STATUS`, renumerar `ORDER_STATUS`

## Status — visão geral

### ORDER_STATUS (atualizado)

```python
ORDER_STATUS = {
    0: "Pendente",
    1: "Produzindo",
    2: "Pronto",
    8: "Cancelado",    # era 3 → migrar
    9: "Entregue",
}
```

**Faturado some do enum.** É calculado: se `order.transacao_id` ou `order.movto_id` estiver preenchido → badge "Faturado".

Fluxo: `0(Pendente) → 1(Produzindo) → 2(Pronto) → 9(Entregue)`
                                        → 8(Cancelado)

### COMPRA_STATUS (novo)

```python
COMPRA_STATUS = {
    0: "Orçamento",
    1: "Pedido",
    6: "Cancelado",
    8: "Recebido",
    9: "Devolvido",
}
```

Fluxo: `0(Orçamento) → 1(Pedido) → 8(Recebido)`
                              ↘              ↘
                            6(Cancelado)   9(Devolvido)

`data_recepcao` preenchida ao marcar Recebido (8). Orçamento (0) não tem cancelamento — é apenas rascunho, transiciona direto para Pedido (1).

### Faturado (calculado, não é enum)

Ambos Pedido e Compra têm o mesmo critério:

- `forma_pagamento.gerar == 0 (Movimento)`: Faturado = `movto_id` está preenchido
- `forma_pagamento.gerar == 1 (Previsão)`: Faturado = `transacao_id` está preenchido

Nas listas e detalhes, exibir badge "Faturado ✓" verde se a condição for satisfeita.

### PREVISAO_STATUS (inalterado)

```python
PREVISAO_STATUS = {
    0: "Editando",
    1: "Pendente",
    2: "Parcial",
    8: "Cancelado",
    9: "Quitado",
}
```

## Fluxo Financeiro

### gerar=0 (Movimento) — cria Movto

1. Salva Compra/Pedido com `forma_pagamento.gerar=0`
2. Redireciona para Movto com dados pré-preenchidos
3. Usuário preenche recurso/rubrica, confirma
4. Ao salvar: cria Movto e seta `compra/order.movto_id`
5. Badge "Faturado" aparece automaticamente

### gerar=1 (Previsão) — cria Transacao+Previsoes

1. Salva Compra/Pedido com `forma_pagamento.gerar=1`
2. Exibe seção de parcelas (como hoje)
3. Ao salvar: cria Transacao+Previsoes e seta `compra/order.transacao_id`
4. Badge "Faturado" aparece automaticamente

### Conversão orçamento→pedido (NÃO cria financeiro)

- `converter_orcamento()` cria apenas Order + Event
- Nenhuma Transacao é criada
- Financeiro é tratado depois (botão "Gerar Recebimento" ou "Gerar Parcelas")

## Fluxo de Telas

### Pedido detail — ações por contexto

| Condição | Botão |
|----------|-------|
| status 0/1/2 e `forma_pagamento.gerar=0` e sem `movto_id` | Gerar Movimento (→ Movto) |
| status 0/1/2 e `forma_pagamento.gerar=1` e sem `transacao_id` | Gerar Previsões (→ seção parcelas) |
| financeiro resolvido | badge "Faturado ✓" (apenas exibição) |
| status 2 | Entregue |
| status 0/1/2 | Cancelar |

### Compra detail — ações por contexto

| Condição | Ação |
|----------|------|
| status 0 (Orçamento) | Converter (data=hoje, status→1) |
| status 1 (Pedido) | Receber (+ data_recepcao, status→8) |
| status 1 (Pedido) | Cancelar (status→6) |
| status 8 (Recebido) | Devolver (status→9) |
| status 1 e `forma_pagamento.gerar=0` e sem `movto_id` | Gerar Pagamento (→ Movto) |
| status 1 e `forma_pagamento.gerar=1` e sem `transacao_id` | Gerar Parcelas (→ seção parcelas) |
| financeiro resolvido | badge "Faturado ✓" |

## Arquivos a Modificar

| Arquivo | Mudanças |
|---------|----------|
| `app/models/forma_pagamento.py` | NOVO — model FormaPagamento |
| `app/models/compra.py` | +forma_pagamento_id, transacao_id, movto_id, status, data_recepcao; -pagamento; ajustar relationships |
| `app/models/order.py` | +forma_pagamento_id, transacao_id, movto_id; -forma_pagamento (Integer); -pagamento; ajustar relationships |
| `app/models/transacao.py` | -compra_id, -pedido_id (colunas + backrefs) |
| `app/models/quote.py` | Substituir `forma_pagamento` (Integer) por `forma_pagamento_id` (FK) |
| `app/constants.py` | Renumerar ORDER_STATUS (8=Cancelado, sem Faturado); adicionar COMPRA_STATUS; manter FORMA_PAGAMENTO? (talvez só para exibição legada) |
| `app/routes/compras.py` | +status, data_recepcao; forma_pagamento como FK; se gerar=1 criar Transacao; se gerar=0 redir para Movto; rota Receber/Cancelar/Devolver |
| `app/routes/orders.py` | Remover Transacao em converter_orcamento; substituir forma_pagamento por FK; remover backfill Transacao em edit(); ajustar status route (cancelar=8, faturar removido); se gerar=1 criar Transacao; se gerar=0 redir para Movto; ajustar locked/references |
| `app/routes/movimentos.py` | Aceitar query params `compra_id`/`pedido_id`; pós-criação setar `movto_id` na origem |
| `app/routes/contas_a_pagar.py` | Ajustar locked: de `transacao.compra_id` para `compra.transacao_id` |
| `app/routes/contas_a_receber.py` | Ajustar locked: de `transacao.pedido_id` para `order.transacao_id` |
| `app/routes/forma_pagamento.py` | NOVA — CRUD de FormaPagamento com trava de edição |
| `app/templates/compras/form.html` | +forma_pagamento select (filtrado por uso), +status, +data_recepcao; parcelas visível só se gerar=1 |
| `app/templates/compras/list.html` | +colunas: status, forma_pagamento, data_recepcao, Faturado badge |
| `app/templates/compras/detail.html` | Se existir, atualizar |
| `app/templates/orders/form.html` | forma_pagamento passa a ser FK select; parcelas só se gerar=1 |
| `app/templates/orders/list.html` | +colunas: forma_pagamento, Faturado badge; Faturado some do filtro |
| `app/templates/orders/detail.html` | Botão Faturar vira "Gerar Movimento"/"Gerar Previsões"; badge Faturado automático |
| `app/templates/orders/dashboard.html` | Remover filtro Faturado; add filtro Cancelado |
| `app/templates/orders/print_order.html` | forma_pagamento via FK (ou manter como está para impressão legada) |
| `app/templates/orders/print_quote.html` | Idem |
| `app/templates/contas_a_pagar/list.html` | Ajustar locked: `compra.transacao_id` |
| `app/templates/contas_a_receber/list.html` | Ajustar locked: `order.transacao_id` |
| `app/templates/forma_pagamento/` | NOVOS — list, form para CRUD |
| `migrations/` | Nova migration com tudo acima |

## Observações / Edge Cases

- **Edit com mudança de `forma_pagamento_id`**: se gerar mudar (0↔1), deve migrar entre Movto e Transacao (ou bloquear edição se financeiro já existir).
- **Delete de Compra/Pedido**: deve cascatear para Transacao (se gerar=1) ou Movto (se gerar=0).
- **Contas_a_pagar/Receber**: páginas filtram por `transacao.tipo`. Compras/Pedidos gerar=0 não aparecem nessas listas (não têm Transacao). Gerar=1 aparecem normalmente.
- **Trava edição**: FormaPagamento referenciada por qualquer Compra/Order/Quote não pode ter nome/uso/gerar alterados. Sugerir ao usuário criar novo registro.
- **Dashboard de produção**: Faturado some dos filtros de produção (não é status de produção).
- **Relatórios financeiros**: Devem considerar tanto `movto_id` (gerar=0) quanto `transacao_id` (gerar=1) para determinar se algo está faturado.
