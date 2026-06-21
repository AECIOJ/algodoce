# Plano de Refatoração Mobile — AlgoDoce

## Problema

Tabelas com 5 a 11 colunas nas páginas de listagem são ilegíveis no mobile. O layout atual usa `table-scroll` horizontal e duplicação de filtros desktop/mobile com sincronização JS frágil.

## Estratégia: Card List no mobile, Tabela no desktop

**Mobile (< 992px)**: cada linha da tabela vira um **card empilhado** (`.card` Bootstrap) com labels + valores e botões em largura total.

**Desktop (≥ 992px)**: a tabela permanece **visualmente idêntica** ao que existe hoje.

### Mudanças por camada

| Camada | O que muda |
|--------|-----------|
| `style.css` | Adicionar `@media (max-width: 991.98px) { .table-scroll { display: none; } }` |
| List templates (7) | Cada um ganha um bloco `d-lg-none` com `/for/` em cards Bootstrap |
| Detail templates (3) | Tabelas internas viram listas simples no mobile |
| Form templates (2) | Tabelas de itens (produtos em pedidos/orçamentos) viram linhas empilhadas |
| Filtros | Unificar duplicação desktop/mobile |

### Templates afetados

| Template | Tipo | Colunas | Observação |
|----------|------|--------|------------|
| `categories/list.html` | Lista | 5 | Simples |
| `ingredients/list.html` | Lista | 5 | Simples |
| `products/list.html` | Lista | 8 | Imagem, badge status |
| `contas/list.html` | Lista | 6 | Filtro por tipo/ativo |
| `orders/list.html` | Lista | 11 | Badge status, forminhas, pagamento |
| `orders/orcamentos.html` | Lista | 10 | Badge status, validade |
| `producao/list.html` | Lista | 7 | Status produção |
| `reports/compras.html` | Lista | 3 | Relatório |
| `ingredients/detail.html` | Detalhe | — | 2 tabelas internas |
| `contas/detail.html` | Detalhe | — | 1 tabela de pedidos |
| `orders/detail.html` | Detalhe | — | 1 tabela de itens |
| `orders/form.html` | Form | — | Tabela de itens do pedido |
| `orders/quote_form.html` | Form | — | Tabela de itens do orçamento |

### O que NÃO muda

- Rotas Python (`app/routes/`)
- Models / banco de dados
- Lógica de negócio
- Visual desktop (idêntico ao atual)
- JavaScript de sortable table, filtros existentes

### Rollback

```bash
# Se usou branch:
git checkout backup-antes-mobile

# Se usou stash:
git stash pop
```

---

## Implementação

### 1. Backup

```bash
git checkout -b backup-antes-mobile && git checkout -
```

### 2. CSS (`style.css`)

Adicionar ao final do arquivo:

```css
/* Mobile: esconde tabela, mostra cards */
@media (max-width: 991.98px) {
  .table-scroll { display: none; }
}
```

### 3. Template — estrutura do card

```html
<div class="d-lg-none">
  {% for item in items %}
    <div class="card mb-2 shadow-sm">
      <div class="card-body py-2 px-3">
        <div class="d-flex justify-content-between align-items-start">
          <div>
            <span class="text-muted small">#{{ item.id }}</span>
            <h6 class="mb-1">{{ item.nome }}</h6>
            <!-- campos adicionais com label -->
          </div>
        </div>
        <div class="mt-2">
          <a href="{{ url_for('edit', id=item.id) }}"
             class="btn btn-sm btn-outline-primary w-100">Editar</a>
        </div>
      </div>
    </div>
  {% else %}
    <p class="text-muted text-center">Nenhum registro.</p>
  {% endfor %}
</div>
```

### 4. Unificar filtros

Filtros que estão duplicados (ex: `#filter-status` + `#filter-status-mobile`) viram **um único elemento** visível em ambos breakpoints, movido para fora do bloco `d-none d-lg-flex`.

### 5. Detail pages — tabelas internas

Tabelas dentro de detalhes usam Bootstrap `.table-responsive` normal + `d-none d-lg-table` / `d-lg-none` com lista simplificada.

### 6. Form pages — tabelas de itens

Tabelas de itens em `orders/form.html` e `orders/quote_form.html` recebem uma view mobile alternativa com cada item em card contendo selects/inputs em largura total.
