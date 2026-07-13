# Layout do Sistema

## Stack de Frontend
- **Bootstrap 5.3.2** (via CDN) — framework CSS/JS principal
- **CSS customizado** — `static/css/style.css` (279 linhas), cache-busting `?v=2`
- **JS vanilla** — sem jQuery, sem frameworks JS (apenas Bootstrap bundle + QRCode.js + Cropper.js)
- **QRCode.js** — geração de QR code no logo
- **Cropper.js** — recorte de imagem no formulário de produtos

## Paleta de Cores (CSS Variables)
| Token | Cor | Uso |
|-------|-----|-----|
| `--rosa` / `--cor-menu` | `#E91E63` | Navbar, botões primários, bordas, destaque |
| `--verde-menta` | `#26A69A` | Botões "verdes" no site público |
| `--bg-claro` | `#f5f5f5` | Fundo do site público |
| `body background` | `#fdf2f5` | Fundo rosado claro do admin |
| `table th` | `#fce4ec` | Cabeçalho de tabela |
| `.card-list-item` border-left | `#e91e63` | Borda lateral dos cards mobile |
| `.bg-expired` | `#d3d8de` | Registros expirados/vencidos |
| `.btn-validar` | `#ffc107` | Botão de validação |

---

## Topo Fixo (todas as páginas do admin)

### Desktop (>= 992px)
```
┌─────────────────────────────────────────────────┐
│                  LOGO (centro)                   │  ← header bg-white
├─────────────────────────────────────────────────┤
│  Cadastro │ Comercial │ Produção │ Financeiro   │  ← navbar bg-rosa, d-none d-lg-flex
├─────────────────────────────────────────────────┤
│  Categorias │ Insumos │ Produtos │ Contas ...   │  ← submenu, d-none (toggle por seção)
└─────────────────────────────────────────────────┘
```

O topo é **fixo** (`#top-fixed`, `position: fixed`, `z-index: 1030`). Um `#top-spacer` vazio é sincronizado dinamicamente com `syncTopSpacer()` via `ResizeObserver` + evento `resize` para evitar que o conteúdo fique atrás do topo fixo.

**Logo**: clicar abre modal com QR code da URL do sistema (tunnel Pinggy ou origin).

### Mobile (< 992px)
```
┌──────────────────────────────────────────────┐
│  ☰  │     Cadastro [select ▼]     │ [Fechar] │  ← barra-mobile, bg-rosa
└──────────────────────────────────────────────┘
```

O submenu vira um `<select class="form-select nav-select">` com `font-size: 0.85rem`, `color: #e91e63`, `background: #fff`. Existem 3 selects (um por seção), cada qual exibido conforme a seção ativa via JS.

O menu collapsível (`#mainNav`, `display:none` por padrão) é aberto pelo hamburger. Contém links: Cadastro, Comercial, Produção, Financeiro.

### Seções e Submenus

| Seção | Submenus (desktop) | Select (mobile) |
|-------|--------------------|-----------------|
| Cadastro | Categorias, Insumos, Produtos, Contas, Operações, Carteiras | `#cadastroNavSelect` |
| Comercial | Orçamentos, Pedidos, Compras | `#comercialNavSelect` |
| Financeiro | Recursos, C. a Receber, C. a Pagar, Recebimentos, Pagamentos | `#financeiroNavSelect` |
| Produção | (sem submenu — rota única) | (sem select) |

A seção ativa é detectada por JS ao carregar a página, baseada no `window.location.pathname`.

---

## Páginas de Listagem

### Componentes Usados
- `components/action_list.html` — `action_list(title, new_url, extra_actions)` (macro mestra)
- `components/action_table.html` — `action_table(data, fields, ctx, edit_endpoint, ...)` (tabela dinâmica)
- `components/action_filter.html` — `action_filter(caller_content)` (filtros)
- `components/action_edit.html` — `action_edit(url)` (botão editar)

### Estrutura HTML
```
base.html
  └── {% block content %}
        └── {% call action_list("Título", new_url=url_for('.new')) %}
              {% if section == "filtros" %}
                └── {% call action_filter() %}
                      selects/inputs de filtro
                └── {% endcall %}
              {% elif section == "dados" %}
                └── {{ action_table(items, fields=fields, ctx=ctx, edit_endpoint='.edit') }}
              {% endif %}
        └── {% endcall %}
```

### Desktop (>= 992px)
```
┌─────────────────────────────────────────────────┐
│              Título da Página                    │  ← .barra-filtro (sticky)
│  [filtros]                        [+ Novo]      │
├─────────────────────────────────────────────────┤
│  # │ Nome │ Preço │ Ativo │ Ações               │  ← thead fixo (sticky top:0)
├─────────────────────────────────────────────────┤
│  1 │ Item │ R$ 10 │ Sim   │ [Editar] [Excluir]  │
│  2 │ Item │ R$ 20 │ Não   │ [Editar] [Excluir]  │  ← .table-scroll com overflow-y:auto
│ ...                                              │
│                                                  │
└─────────────────────────────────────────────────┘
```

- `<html>` recebe classe `list-page` (condicional via `{% if request.endpoint.endswith('.list') %}`)
- `body` com `height: 100%; overflow: hidden; display: flex; flex-direction: column`
- `<main>` com `flex: 1; display: flex; flex-direction: column` — ocupa espaço restante
- `.table-scroll` com `flex: 1; overflow-y: auto` — scroll interno na tabela
- `<thead th>` com `position: sticky; top: 0` — cabeçalho fixo
- Tabela ocupa 100% da altura disponível **sem scroll na página do navegador**
- Colunas com `data-field` permitem ordenação por clique (asc/desc)
- Suporte a ordenação de números (R$), datas (DD/MM/AAAA) e texto (localeCompare pt-BR)
- Atalho `Ctrl+Shift+0/1/2` com uma coluna ordenada transforma todos registros (lower/title/upper) via POST `/api/transformar-texto`

### Mobile (< 992px)
```
┌──────────────────────────────────────────────┐
│  [filtro]                         [+ Novo]   │  ← .barra-filtro (wrap, sem título)
├──────────────────────────────────────────────┤
│                                              │
│  ┌─── Borda Rosa ──────────────────────────┐ │
│  │  #001                    [Editar ícone] │ │  ← card-list-item
│  │  Nome do Item                           │ │
│  │  Preço: R$ 10       Ativo: Sim          │ │
│  └─────────────────────────────────────────┘ │
│  ┌─── Borda Rosa ──────────────────────────┐ │
│  │  #002                    [Editar ícone] │ │
│  │  ...                                     │ │
│  └─────────────────────────────────────────┘ │
│                                              │
├──────────────────────────────────────────────┤
│  N registro(s)                    [▲ painel]  │  ← .barra-report (expansível)
└──────────────────────────────────────────────┘
```

- Tabela desktop escondida (`display: none`)
- Cards aparecem via `{% call(item) card_list(items) %}` em `<div class="d-lg-none">`
- Cada card: `<div class="card mb-2 shadow-sm card-list-item">` com `border-left: 4px solid #e91e63`
- Labels em uppercase pequeno (`.card-label`: `font-size: 0.75rem`, `color: #6c757d`)
- Valores em `.card-value` (`font-size: 0.95rem`)
- `barra_report` na parte inferior — mostra contagem e ao clicar expande painel fullscreen

### Páginas que usam o padrão de listagem
- `sys_categories/list.html`
- `sys_products/list.html`
- `sys_ingredients/list.html`
- `sys_contas/list.html`
- `sys_operacoes/list.html`
- `sys_recursos/list.html`
- `sys_orders/list.html` (pedidos)
- `sys_orders/orcamentos.html`
- `sys_compras/list.html`
- `sys_a_pagar/list.html`
- `sys_a_receber/list.html`
- `sys_producao/list.html`
- `sys_movimentos/list.html`
- `sys_previsoes/list.html`

---

## Páginas de Formulário (Edição/Criação)

### Componentes Usados
- `components/action_nav.html` — `action_nav(back_url, nome, nav, edit_endpoint, entity_id, status, actions2)` (navegação entre registros)
- `components/barra_edicao.html` — `barra_edicao(back_url)` (barra inferior fixa com Salvar/Sair)

### Desktop (>= 992px)

Em modo **edição** (registro existente):
```
┌─────────────────────────────────────────────────┐
│  Categorias │ Insumos │ Produtos │ Contas ...   │  ← submenu (se houver)
├─────────────────────────────────────────────────┤
│  [← Voltar]   ◀ 4 ▶  [▲ 5 ▼]  [Status: Ativo] │  ← .form-nav-wrap (sticky)
│              Nome do Item                       │
├─────────────────────────────────────────────────┤
│  Nome: [______________]  Preço: [________]      │  ← primeira linha gruda no nav
│  Descrição: [___________________________]       │
│  ...                                            │  ← formulário rola normalmente
│                                                 │
├─────────────────────────────────────────────────┤
│  [Excluir]                    [Salvar] [Sair]   │  ← .form-bottom-bar (position: fixed)
└─────────────────────────────────────────────────┘
```

Em modo **novo** (sem `action_nav`):
```
┌─────────────────────────────────────────────────┐
│              Novo Registro                       │
├─────────────────────────────────────────────────┤
│  Campos do formulário...                        │
├─────────────────────────────────────────────────┤
│                         [Salvar] [Sair]         │
└─────────────────────────────────────────────────┘
```

- `action_nav` tem `position: sticky; top: 0; z-index: 102` (sempre visível)
- A primeira linha de campos (`row.mb-3`) também fica sticky abaixo do nav (`top: navHeight`)
- A `barra_edicao` fica `position: fixed; bottom: 0` com fundo branco, `box-shadow: 0 -2px 4px rgba(0,0,0,0.08)`
- `.form-bottom-spacer` com `height: 56px` evita que o conteúdo fique atrás da barra

### Mobile (< 992px)

```
┌──────────────────────────────────────────────┐
│  [← Voltar]   ◀ Nome do Item ▶   [Status]   │  ← .form-nav-wrap bg-white, radius
│  [Ações extras]                              │  ← actions2 em linha separada
├──────────────────────────────────────────────┤
│  Nome: [________________________]            │  ← primeira coluna vira clone fixed
│  Preço: [______]                             │     quando o sticky do pai falha
│  ...                                         │
│                                              │
├──────────────────────────────────────────────┤
│  [Excluir]               [Salvar] [Sair]     │  ← .form-bottom-bar
└──────────────────────────────────────────────┘
```

- Nav: fundo branco, cantos arredondados, `flex-wrap: wrap`
- Botões Primeiro/Último escondidos; Anterior/Próximo com ícones 16x16px
- Título (`nav-title`) com `max-width: 220px`, `text-overflow: ellipsis`, `overflow: hidden`
- `actions2` renderizada em linha separada (fora do `action_nav`, chamada pelo caller)
- **Sticky fields**: a primeira coluna da primeira `row.mb-3` é clonada como `position: fixed` quando o scroll a levaria para trás do nav. O input do clone é sincronizado com o original via eventos `input`/`change`.

### Páginas que usam este padrão de formulário
- `sys_categories/form.html`
- `sys_products/form.html` (com Cropper.js para recorte de imagem)
- `sys_ingredients/form.html`
- `sys_contas/form.html`
- `sys_operacoes/form.html`
- `sys_recursos/form.html`
- `sys_carteira/form.html`
- `sys_orders/form.html` (pedidos — com lista dinâmica de itens)
- `sys_orders/quote_form.html` (orçamentos)
- `sys_compras/form.html` (com lista dinâmica de itens)
- `sys_a_pagar/form.html` (com lista de parcelas)
- `sys_a_receber/form.html` (com lista de parcelas)
- `sys_movimentos/form.html`
- `sys_previsoes/form.html`

---

## Páginas de Detalhe

### Produção (detail.html — híbrido com tabs)
Usa `action_nav` + abas Bootstrap (`nav-tabs`) para organizar seções:
- **Pedidos**: lista de pedidos na produção com progresso
- **Compras**: insumos calculados com qtd comprada
- **Etapas**: progresso por etapa (preparo, montagem, embalagem)
- **Conclusão**: ações de finalização
- **Resumo**: relatório consolidado

Não usa `barra_edicao` — a edição é inline via JavaScript/AJAX.

### Outras páginas de detalhe (read-only)
- `orders/detail.html` — detalhe do pedido
- `orders/quote_detail.html` — detalhe do orçamento
- `contas_a_pagar/detalhes.html` — detalhe da transação
- `contas_a_receber/detalhes.html` — detalhe da transação
- `contas/detail.html` — detalhe da conta
- `ingredients/detail.html` — detalhe do insumo

---

## Componentes Macro

### 1. `action_list(title, new_url, new_label, extra_actions)`
Macro mestra que estrutura a página de listagem:
```
┌─ Título (h2)  [Dados | Filtros]  [extra_actions]  [+ Novo] ─┐
│                                                                │
│  caller("dados") = {{ action_table(...) }}                     │
│  ou caller("filtros") = {{ action_filter(...) }}               │
└────────────────────────────────────────────────────────────────┘
```
- Abas Dados/Filtros via Bootstrap tabs (`nav-underline`)
- Cabeçalho com título (desktop apenas), botões de ação, link "+ Novo"
- Responsivo: empilha elementos em mobile

### 2. `action_table(data, fields, ctx, edit_endpoint, edit_id_field, edit_if_field, edit_endpoint_map, edit_endpoint_key)`
Tabela com colunas dinâmicas a partir de `*_FIELDS`:
- Colunas definidas pelo dataclass `Field` (label, width, input, filter, query)
- Ordenação por clique no `<th>` (asc/desc) via JS
- Linha de detalhe expansível via colapso Bootstrap (`collapse`)
- Ações: botão editar centralizado via `action_edit`
- Suporta `edit_endpoint` (string), `edit_endpoint_map` (dict), `edit_if_field` (condicional)

### 3. `action_filter(caller_content)`
Painel de filtros reutilizável (ex-painel_filter):
- Inputs/selects de filtro passados via caller
- Botão "Limpar Filtros" com JS para reset

### 4. `action_edit(url)`
Botão editar (ícone lápis Bootstrap):
- Link para `url` dentro do `<td>` de ações

### 5. `action_nav(back_url, nome, nav, edit_endpoint, entity_id, status, actions2)`
Barra de navegação entre registros (sticky):
```
[← Voltar]  [◀ Anterior]  Nome do Item  [Próximo ▶]  [Status badge]
```
- Mobile: Primeiro/Último escondidos, setas com ícones 16px, título truncado em 220px
- Nome clicável: transforma em input para pular para outro ID
- Recebe `actions2` para renderizar abaixo em mobile

### 6. `page_form(back_url, title)`
Barra inferior fixa com botões Salvar + Sair (ex-barra_edicao):
- Detecta modificações via eventos `input`/`change`
- Ao sair, exibe modal de confirmação "Descartar alterações?"

---

## Comportamentos JavaScript

### Scripts Globais (base.html)

| Comportamento | Descrição |
|--------------|-----------|
| `syncTopSpacer()` | Ajusta `#top-spacer` com altura de `#top-fixed` via `ResizeObserver` + `resize` |
| **QR Code** | Clique no logo gera QR code com URL do sistema via QRCode.js e exibe em modal Bootstrap |
| `showConfirm(msg, onConfirm)` | Modal Bootstrap reutilizável (`#confirmModal`) com título, corpo e callback |
| `showAlert(msg)` | Modal de alerta (apenas OK) |
| `confirmFormSubmit(form, msg)` | Confirma antes de submeter formulário |
| `confirmRemove(el, msg)` | Confirma antes de remover item de lista inline |
| **Ordenação de tabela** (`table.sortable`) | Clique em `<th>` ordena asc/desc. Suporta números (R$), datas (DD/MM/AAAA) e texto (pt-BR) |
| **Transformação em massa** (`Ctrl+Shift+0/1/2`) | Com coluna ordenada, transforma todos registros (minúsculas/título/maiúsculas) via POST `/api/transformar-texto` |
| **Navegação por ID** (`#nav-title` click) | Permite digitar ID e pular direto para o registro |
| **Seção ativa** | Detecta path atual e ativa seção correta (Cadastro/Comercial/Produção/Financeiro) + exibe select correto no mobile |
| **Sticky fields (formulários)** | Em mobile, clona primeira coluna como `position: fixed` quando scroll a esconderia |

### Scripts Específicos

| Arquivo | Função |
|---------|--------|
| `js/itens.js` | Gerenciamento de itens de pedido/orçamento: captura preço do produto selecionado, calcula valor total, formata BRL |
| `js/auth.js` | Popup de autenticação no site público (login admin/doceira com overlay, animação, submit via fetch) |
| `js/phone-mask.js` | Máscaras de input: telefone `(XX) XXXXX-XXXX`, CPF `XXX.XXX.XXX-XX`, CNPJ `XX.XXX.XXX/XXXX-XX` |
| `js/paste.js` | Colagem de imagem da clipboard no input de foto do produto |

---

## Responsividade

**Único breakpoint:** `max-width: 991.98px` (equivale ao `lg` do Bootstrap)

| Componente | Desktop (>= 992px) | Mobile (< 992px) |
|-----------|-------------------|-------------------|
| Navbar principal | Links horizontais | Hamburger + collapsível + select dropdown |
| Submenu | Links horizontais visíveis | Select dropdown escondido, exibido conforme seção ativa |
| Logo | 100px altura | 72px altura |
| Tabela de listagem | Visível com scroll interno | Escondida (`display: none`) |
| Cards de listagem | Escondidos (`d-lg-none`) | Visíveis como `.card-list-item` |
| Barra de filtro | Título visível, filtros centralizados | Título escondido, filtros em wrap, sticky |
| Form nav | Linha única com navegação completa | Wrap, setas menores, título truncado, actions2 em linha separada |
| Form sticky fields | Primeira linha sticky normal | Clone fixed com sincronização de input |
| Bottom bar | `.form-bottom-bar` fixa | Mesma, com `safe-area-inset-bottom` |

---

## Menus de Navegação

### Site Público
```
Sobre | Produtos | Orçamento | Contato
```
- Navbar rosa fixa, logo com subtítulo "O doce sabor do seu evento!"
- Mobile: links menores (`font-size: 0.82rem`), `padding: 0.3rem`
- `#produtosBar` some no mobile quando dentro da vitrine (`display: none !important`)
- Clica no logo: 1 click = popup login doceira, 2 clicks rápidos = popup login admin

### Painel Admin
```
Cadastro   → Categorias | Insumos | Produtos | Contas | Operações | Carteiras
Comercial  → Orçamentos | Pedidos | Compras
Produção   → (sem submenu)
Financeiro → Recursos | Contas a Receber | Contas a Pagar | Previsões | Recebimentos | Pagamentos
Segurança  → Painel de Segurança (rota /seguranca/)
```
- Segurança não está no navbar principal — acesso via rota direta `/seguranca/`
- Menu ativo é detectado por JS; submenu correspondente é exibido abaixo da navbar
- Mobile: o título da seção ativa aparece no topo (`#mobileMenuTitle`)

---

## Autenticação (Site Público)

### Popup de Login (Doceira)
- Overlay semi-transparente + card centralizado com `border-radius: 16px` e `box-shadow: 0 20px 60px rgba(0,0,0,0.3)`
- Campos: Usuário, Senha, Chave (HMA — exibido condicionalmente conforme `api/check-chave`)
- Enter no input submete formulário
- Erro exibido em `.auth-error` vermelho

### Popup de Login (Admin)
- Mesmo overlay, card com ícone 🔑
- Campos: Usuário (condicional), Senha (condicional), Chave
- Configurações de visibilidade obtidas via `api/admin-config`

---

## Observações Técnicas

- **Sem `{% include %}`**: todo reuso é via macros Jinja2 com `{% from ... import ... %}` e `{% call %}{% endcall %}`
- **Tema escuro**: não suportado (`data-bs-theme="light"` fixo)
- **Ícones**: PNG 24x24, sem ícones vetoriais (Font Awesome, Bootstrap Icons, etc.)
- **Uploads**: diretório `static/uploads/` com nome padrão `prod_{id}_{slug}.jpg`
- **Cache-busting**: manual (`style.css?v=2`)
- **Safe area**: `padding-bottom: calc(8px + env(safe-area-inset-bottom, 0px))` na `.form-bottom-bar`
- **Dead code**: existe `static/icons/arrow-list.png`, `panel-up.png`, `panel-down.png` sem uso identificado nos templates
