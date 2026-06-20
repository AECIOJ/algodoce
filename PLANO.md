# Plano de Alterações — AlgoDoce 2.0

---

## 1. Arquitetura de Acesso

```
algodoce.sytes.net
│
├── /              → Landing page do SITE (banner fixo + logo + menu)
├── /sobre         → Página institucional (sobre a doceira)
├── /produtos      → Navegador de produtos com categorias, um por vez (banner)
├── /orcamento     → Lista de itens selecionados + finalizar pedido
├── /contato       → Página de contato / WhatsApp
│
├── [click no logo] → Popup JS pede senha
│
└── /sistema/      → Painel de gestão (mesmo header, menu funcional)
    ├── /sistema/
    ├── /sistema/pedidos
    ├── /sistema/produtos
    ├── /sistema/clientes
    ├── /sistema/insumos
    └── /sistema/relatorios
```

**Regras:**
- Visitante anônimo → vê o SITE público
- Doceira logada → `/` redireciona direto pra `/sistema/`
- Click no logo → popup de senha → se ok → `/sistema/`
- "Sair" no menu do sistema → limpa sessão → volta pro site público
- **Cardápio** foi renomeado para **Orçamento** (cliente adiciona produtos e solicita orçamento)

---

## 2. Fases de Implementação

### Fase 0 — Autenticação e Segurança

**Dependências novas:**
```txt
Flask-Login==0.6.3
```

**Novo model:** `User` (`app/models/user.py`)
```python
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password): ...
    def check_password(self, password): ...
```

**Novo blueprint:** `auth` (`app/routes/auth.py`)
- `POST /login` → AJAX: valida senha, retorna JSON `{success, redirect}`
- `GET /logout` → `logout_user()`, redireciona pra `/`

**Seeder:** Dentro de `create_app()`, criar usuário `doceira` com senha vinda de `ADMIN_PASSWORD` no `.env`

**Popup JS:** (`app/static/js/auth.js`)
- Click no logo → overlay centralizado com input de senha + botão "Entrar"
- POST `/login` com JSON `{password: "..."}`
- 200 → `window.location.href = data.redirect` (vai pra `/sistema/`)
- 401 → mostra erro "Senha incorreta" no popup
- Botão fechar / click fora pra cancelar

**Proteção:** Blueprint `sistema` + blueprints de gestão existentes (`clients`, `products`, `ingredients`, `orders`, `reports`) ganham `@bp.before_request @login_required`

**Atraso progressivo contra brute-force:**
- Após 3 falhas de login consecutivas por IP, impõe-se atraso progressivo: `min(2^(count - 3), 60)` segundos (4ª→2s, 5ª→4s, ..., 9ª+→60s)
- Janela deslizante de 15min; sucesso zera o contador
- Implementação: dicionário em memória `FAILED_ATTEMPTS[ip] = (count, first_attempt_time)`

**Auto-login na raiz:**
```python
@site_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('sistema.dashboard'))
    return render_template('site/index.html')
```

---

### Fase 1 — Site Público (Blueprints: `site` + `produtos` + `orcamento`)

**Blueprint `site`** (`app/routes/site.py`):

| Rota | Descrição | Conteúdo |
|------|-----------|----------|
| `GET /` | Landing page | Template estático: banner + boas-vindas |
| `GET /sobre` | Sobre a doceira | Template estático: história, fotos |
| `GET /contato` | Contato | Template estático: WhatsApp, endereço |

Templates em `app/templates/site/`, conteúdo "estático" (sem DB queries), mas usando Jinja para herdar o header.

**Header único** (`app/templates/site/base.html` e `app/templates/sistema/base.html`):
- Banner fixo no topo com logo
- Menu muda conforme contexto:
  - **Site:** Início | Sobre | Produtos | Orçamento | Contato
  - **Sistema:** Dashboard | Pedidos | Produtos | Clientes | Insumos | Relatórios | **Sair**
- Logo sempre visível; no site, click → popup de auth

**Blueprint `produtos`** (`app/routes/produtos.py`):

| Rota | Descrição |
|------|-----------|
| `GET /produtos` | Navegador de produtos com categorias (seleciona grupo + banner) |
| `POST /produtos/<id>/add` | Adiciona produto ao orçamento (sessão), retorna JSON |

O cliente navega por **categorias** (doces simples, doces finos, etc.). Dentro de cada categoria, os produtos aparecem **um por vez** como um banner/carrossel com:
- Foto grande do produto
- Nome e descrição
- Características e observações
- Botão "Incluir no Orçamento" → abre input de quantidade inline → confirma → adiciona à sessão
- Setas de navegação (anterior/próximo) para rolar os produtos da categoria

**Sticky bar no rodapé** (Bootstrap `fixed-bottom`): aparece assim que o primeiro item é adicionado, mostrando "🧾 N itens no orçamento · [Finalizar Orçamento]" — link direto pra `/orcamento`.

**Blueprint `orcamento`** (`app/routes/orcamento.py`):

| Rota | Descrição |
|------|-----------|
| `GET /orcamento` | Lista itens + painel Evento + envia |
| `POST /orcamento/remover/<id>` | Remove item |
| `POST /orcamento/atualizar/<id>` | Atualiza quantidade |
| `POST /orcamento/enviar` | Salva dados do evento + envia pedido → status `rascunho` |

**Templates:** `app/templates/orcamento/`

**Rota auxiliar de cliente:**
| Rota | Descrição |
|------|-----------|
| `POST /api/cliente` | Recebe `{telefone, nome}`, busca ou cria `Client`, retorna `{client_id}` |

### Identificação do Cliente

Disparada no primeiro "Incluir no Orçamento":

```
1. Cliente acha um produto em /produtos, clica "Incluir"
2. Se session['cliente_id'] não existe:
      ┌──────────────────────┐
      │  📞 Dados para       │
      │     o Orçamento      │
      │                      │
      │  Telefone:           │
      │  [+55] [__________]  │ ← type="tel", autofill do celular
      │                      │
      │  Nome:               │
      │  [______________]    │
      │                      │
      │  [Continuar ✓]       │
      │                      │
      │  ou [Fechar]         │
      └──────────────────────┘
3. POST /api/cliente → busca Client por telefone ou cria novo
4. Salva cliente_id na sessão
5. Adiciona o item ao orçamento (salvo no banco, status rascunho)
6. Próximos itens → adiciona direto (já identificado)
```

**Recuperação:** Se a sessão expirar e o cliente voltar, ao clicar "Incluir" o popup reabre. Ao informar o mesmo telefone, o sistema recupera o orçamento pendente (`rascunho`) mais recente daquele cliente e continua adicionando itens.

**Dados persistidos no banco após o primeiro item:**
- `Client` com nome e telefone (criado ou atualizado)
- `Order` com `cliente_id`, status `rascunho`, `data_pedido`
- `OrderItem` com `product_id`, `quantidade`, `observacao`

---

### Fase 2 — Fluxo de Negociação

**Alterações no model `Order`:**
- `total` muda de `Numeric(10,2)` para nullable (só calculado após precificação)
- `evento_tipo` — `db.String(30)` — "aniversario", "casamento", "outros"
- `evento_complemento` — `db.Text`, nullable — texto livre quando tipo "outros" ou complemento
- `evento_data` — `db.Date`, nullable
- `evento_hora` — `db.Time`, nullable
- `evento_local` — `db.String(200)`, nullable
- `evento_convidados` — `db.Integer`, nullable

**Alterações no model `OrderItem`:**
- `preco_unitario` muda de `NOT NULL` para nullable (cliente envia sem preço)

**Novos status de `Order`:**
```
rascunho → negociando → orcamento_enviado → cliente_confirmou → pendente → em_producao → pronto → entregue
                                ↓
                    cliente_solicitou_alteracao
                           ↓
                     negociando (loop)
```

**Painel "Negociações" da Doceira no `/sistema/`:**
- Aba no dashboard mostrando pedidos em `rascunho` e `negociando`
- Botão "Precificar" → modal/tela para:
  - Ajustar quantidades
  - Inserir preço unitário de cada item
  - Adicionar observações
- Botão "Enviar para Cliente" → muda status para `orcamento_enviado` + gera link WhatsApp

---

### Fase 3 — WhatsApp

**Sem API, sem custo.** Usar link `wa.me`:

```
https://wa.me/55XXXXXXXXXXX?text=Olá! Orçamento AlgoDoce:
1x Brigadeiro
2x Bem Casado
Total: R$ 13,00

Confirme ou solicite alterações:
https://algodoce.sytes.net/cardapio/confirmar/XXX
```

**Onde usar:**
1. Botão "Enviar via WhatsApp" no painel da doceira → abre `wa.me` com orçamento
2. Botão "Confirmar" no link recebido pelo cliente → muda status para `cliente_confirmou`
3. Botão "Solicitar Alteração" → muda para `cliente_solicitou_alteracao` e notifica doceira

**Rota pública de confirmação (sem login):**
- `GET /orcamento/confirmar/<token>` → cliente confirma orçamento
- `GET /orcamento/alterar/<token>` → cliente solicita alteração

Token: `hashlib.md5(f"{order.id}{order.data_pedido}".encode()).hexdigest()[:12]`

---

### Fase 4 — Controle da Doceira (Melhorias)

**Estoque:**
- Campo `estoque_atual` (`Numeric(10,3)`) no `Ingredient`
- Campo `estoque_minimo` (`Numeric(10,3)`) no `Ingredient` — alerta quando abaixo
- Relatório "Compras" ganha coluna "Em Estoque" e "Faltante"

**Pendências:**
- Dashboard ganha cards:
  - "Negociações pendentes" → count de `rascunho`
  - "Orçamentos aguardando resposta" → count de `orcamento_enviado`
  - "Alterações solicitadas" → count de `cliente_solicitou_alteracao`

**Produção:**
- Visão "O que produzir hoje"
- Baseado em pedidos com status `pendente` ou `em_producao`
- Agrupado por produto, soma quantidades

---

## 3. Telas — Layout e Responsividade

Tema: rosa como cor principal (botões, destaques, gradientes), fundo branco/cinza claro, texto escuro. Bootstrap 5 responsivo. Sem frameworks JS pesados.

---

### 3.1 Site — Landing Page (`/`)

```
┌──────────────────────────────────────────────────────┐
│ [LOGO]        Início  Sobre  Produtos  Orçamento  Contato│  ← header fixo com blur
├──────────────────────────────────────────────────────┤
│                                                      │
│   ┌──────────────────────────────────────────────┐   │
│   │     🍰  Doces que encantam                   │   │
│   │     Bolos, brigadeiros e muito mais          │   │
│   │     [Ver Cardápio]  [Fale Conosco]           │   │
│   └──────────────────────────────────────────────┘   │
│                                                      │
│   ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐          │
│   │ 🎂   │  │ 🧁   │  │ 🍪   │  │ 🎀   │          │
│   │Bolos │  │Cupcakes│  │Biscoitos│  │Festas │          │
│   └──────┘  └──────┘  └──────┘  └──────┘          │
│                                                      │
│   ┌──────────────────────────────────────────────┐   │
│   │  Depoimentos / Redes                         │   │
│   │  [Insta]  [WhatsApp]                         │   │
│   └──────────────────────────────────────────────┘   │
│                                                      │
│   Footer: contato, endereço, ©                      │
└──────────────────────────────────────────────────────┘
```

- **Header:** fixo no topo com `backdrop-filter: blur`. Logo à esquerda (click → popup auth). No mobile vira sanduíche (offcanvas ou collapse).
- **Hero:** imagem de fundo com gradiente escuro, texto centralizado, dois CTAs.
- **Cards categoria:** 4 cards lado a lado (empilha em mobile via grid Bootstrap), ícone + nome, click leva ao cardápio filtrado.
- **Logo:** tem tooltip sutil "Área da doceira". Não é link comum — é um botão JS que abre popup de autenticação.

---

### 3.2 Site — Sobre (`/sobre`)

```
┌──────────────────────────────────────────────────────┐
│ [LOGO]    Início  Sobre  Produtos  Orçamento  Contato  │
├──────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────┐    │
│  │  📖  Nossa História                          │    │
│  │  Parágrafo contando...  [foto da doceira]    │    │
│  └──────────────────────────────────────────────┘    │
│  ┌──────────────┐ ┌──────────────┐                   │
│  │  5 anos      │ │  +2000     │                   │
│  │  de história │ │  pedidos    │                   │
│  └──────────────┘ └──────────────┘                   │
└──────────────────────────────────────────────────────┘
```

Template estático com foto, texto, números de destaque.

---

### 3.3 Site — Produtos (`/produtos`)

Navegador visual: cliente escolhe uma categoria, navega pelos produtos um por vez estilo carrossel/banner.

```
┌──────────────────────────────────────────────────────┐
│ [LOGO]    Início  Sobre  Produtos  Orçamento  Contato │
├──────────────────────────────────────────────────────┤
│                                                      │
│  [Doces Simples] [Doces Finos] [Bolos] [Festas]       │
│               ← chips de categorias                   │
│                                                      │
│  ┌──────────────────────────────────────────────────┐│
│  │  ◀                               ▶               ││
│  │                                                  ││
│  │         ┌──────────────────────┐                 ││
│  │         │    📸 Foto grande    │                 ││
│  │         │    do produto        │                 ││
│  │         └──────────────────────┘                 ││
│  │                                                  ││
│  │    🧁 Brigadeiro Gourmet                         ││
│  │    Chocolate belga com granulado                  ││
│  │    Características: tamanho, validade...          ││
│  │                                                  ││
│  │    Observação: [________________________]        ││
│  │                                                  ││
│  │    Qtd: [-]  12  [+]                             ││
│  │                                                  ││
│  │    [Incluir no Orçamento ✓]                      ││
│  │                                                  ││
│  └──────────────────────────────────────────────────┘│
│                                                      │
│     🧾  [5 itens no orçamento] ← link pra /orcamento │
│                                                      │
└──────────────────────────────────────────────────────┘
```

**Chips de categorias** no topo (rolagem horizontal em mobile). Ao selecionar, filtra os produtos.

**Carrossel:** um produto por vez. Setas ◀ ▶ nas laterais ou swipe em mobile. Transição suave.

**Incluir:** botão abre input de quantidade inline (sem sair da página). Confirma → feedback visual → item vai pra sessão. Quantidade padrão = 1.

**Sticky bar no rodapé** (`fixed-bottom`): aparece assim que o primeiro item é adicionado, mostrando "🧾 N itens no orçamento · [Finalizar →]" — link direto pra `/orcamento`.

---

### 3.4 Site — Contato (`/contato`)

```
┌──────────────────────────────────────────────────────┐
│ [LOGO]    Início  Sobre  Produtos  Orçamento  Contato  │
├──────────────────────────────────────────────────────┤
│  ┌───────────────┐    ┌────────────────────────┐    │
│  │ 💬 WhatsApp   │    │ 📍 Endereço            │    │
│  │ (11) 9XXXX    │    │ Rua Tal, 123           │    │
│  │ [Falar Agora] │    │ 📧 Email               │    │
│  └───────────────┘    │ doceira@email.com      │    │
│                       └────────────────────────┘    │
│  ┌───────────────┐                                   │
│  │ 📸 Instagram  │                                   │
│  │ @algodoce     │                                   │
│  │ [Seguir]      │                                   │
│  └───────────────┘                                   │
└──────────────────────────────────────────────────────┘
```

Dois cards lado a lado: WhatsApp (link `wa.me`) e endereço/email. Abaixo Instagram.

---

### 3.5 Site — Orçamento (`/orcamento`)

Lista de itens adicionados em `Produtos`. Ajusta quantidades, remove itens, finaliza pedido.

```
┌───────────────────────────────────────────────────────┐
│ [LOGO]    Início  Sobre  Produtos  Orçamento  Contato  │
├───────────────────────────────────────────────────────┤
│                                                       │
│  🧾 Meu Orçamento                                     │
│  Para: Maria Souza · (11) 99999-8888                  │
│                                                       │
│  ┌───────────────────────────────────────────────────┐│
│  │  🧁 Brigadeiro Gourmet         Qtd: 12            ││
│  │  Obs: sem granulado            [-]  [+]  [🗑️]     ││
│  ├───────────────────────────────────────────────────┤│
│  │  🎂 Bolo de Festa              Qtd: 1             ││
│  │  Obs: chocolate com morango    [-]  [+]  [🗑️]     ││
│  ├───────────────────────────────────────────────────┤│
│  │  🍪 Bem Casado                 Qtd: 20            ││
│  │  Obs:                           [-]  [+]  [🗑️]    ││
│  └───────────────────────────────────────────────────┘│
│                                                       │
│  [＋ Incluir mais itens]                               │ ← volta pra /produtos
│                                                       │
│  ─── Evento ───────────────────────────────────────  │
│                                                       │
│  Tipo do Evento:                                      │
│  ○ Aniversário   ○ Casamento   ○ Outros               │
│  [Complemento: _______________________________]       │
│                                                       │
│  Data: [________]   Hora: [________]                  │
│                                                       │
│  Local: [___________________________________]         │
│                                                       │
│  Nº de Convidados: [_______________]                  │
│                                                       │
│  ───────────────────────────────────────────────────  │
│                                                       │
│  [Enviar Orçamento 🚀]                                │
│                                                       │
└───────────────────────────────────────────────────────┘
```

Cada item: nome, observação, controles de quantidade (-/+) e botão remover. Atualiza via AJAX (ou POST).

Tudo na mesma página: itens → "Incluir + itens" → painel Evento → "Enviar Orçamento". Botão "Enviar Orçamento" salva dados do evento e muda status para `rascunho`. Cliente vê tela de confirmação "Orçamento enviado! Aguarde contato no WhatsApp."

---

### 3.7 Site — Orçamento — Popup de Identificação

Aparece ao clicar "Incluir no Orçamento" pela primeira vez (ou quando a sessão expirou):

```
┌──────────────────────────────────────────────────────┐
│                    ┌──────────────────┐               │
│                    │  📞 Dados para   │               │
│                    │     o Orçamento  │               │
│                    │                  │               │
│                    │  Telefone:       │               │
│                    │  [+55] [________]│ ← autofill   │
│                    │                  │               │
│                    │  Nome:           │               │
│                    │  [____________]  │               │
│                    │                  │               │
│                    │  [Continuar ✓]   │               │
│                    │                  │               │
│                    │  [Fechar]        │               │
│                    └──────────────────┘               │
│  (overlay com 50% opacidade)                         │
└──────────────────────────────────────────────────────┘
```

Após identificar, o popup nunca mais aparece (a menos que a sessão expire). Os itens seguintes são adicionados direto.

---

### 3.8 Site — Popup de Autenticação (Doceira)

```
┌──────────────────────────────────────────────────────┐
│                    ┌──────────────┐                   │
│                    │  🔐          │                   │
│                    │  Acesso da   │                   │
│                    │  Doceira      │                   │
│                    │              │                   │
│                    │  Senha:      │                   │
│                    │  [_________] │                   │
│                    │              │                   │
│                    │  [Entrar]    │                   │
│                    │  [Fechar]    │                   │
│                    └──────────────┘                   │
│  (overlay fullscreen com 50% opacidade)              │
└──────────────────────────────────────────────────────┘
```

Overlay fullscreen + card centralizado com animação fade. Erro "Senha incorreta" aparece inline.

---

### 3.9 Sistema — Dashboard (`/sistema/`)

```
┌──────────────────────────────────────────────────────┐
│ [LOGO]  Dashboard Pedidos Prod. Clientes Insum. Relat. Sair │
├──────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ 🕐 Pend. │ │ 💬 Negoc.│ │ ✅ Hoje  │ │ ⚠️ Estq │ │
│  │   3      │ │   5      │ │   2      │ │   1    │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘ │
│                                                      │
│  ┌──────────────────────────────────────────────────┐│
│  │  Negociações Pendentes              [Ver todas]  ││
│  │  🧁 Maria - Brigadeiro 20un - 10min              ││
│  │     [Precificar] [Ignorar]                       ││
│  │  🎂 João - Bolo Festa - 1h                       ││
│  │     [Precificar] [Ignorar]                       ││
│  └──────────────────────────────────────────────────┘│
│                                                      │
│  ┌──────────────────────────────────────────────────┐│
│  │  Produção Hoje                     [Ver detalhes]││
│  │  🧁 Brigadeiro .............. 40un               ││
│  │  🎂 Bolo Festa ............... 2un               ││
│  └──────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────┘
```

4 cards de métricas no topo com números grandes. Abaixo, listas de ação rápida (negociações, produção). Empilha verticalmente em mobile.

---

### 3.10 Sistema — Páginas de Gestão

Mantêm layout atual de tabelas Bootstrap, mas com novo header do sistema. Em mobile, tabela horizontal com scroll ou cards empilhados.

```
┌──────────────────────────────────────────────────────┐
│ [LOGO]  Dashboard Pedidos Prod. Clientes Insum. Relat. Sair │
├──────────────────────────────────────────────────────┤
│  Pedidos                                             │
│  [🔍 Buscar...]  [Filtrar por status ▼]             │
│                                                      │
│  ┌────┬────────┬──────────┬──────┬──────────┬─────┐ │
│  │ #  │ Cliente│  Status  │ Total│  Data    │ Ação│ │
│  ├────┼────────┼──────────┼──────┼──────────┼─────┤ │
│  │ 42 │ Maria  │ pendente │R$85  │ 10/06    │ [>] │ │
│  │ 41 │ João   │ entregue │R$120 │ 09/06    │ [>] │ │
│  └────┴────────┴──────────┴──────┴──────────┴─────┘ │
│  (em mobile: cards empilhados)                       │
└──────────────────────────────────────────────────────┘
```

---

## 4. Paleta de Cores

### 4.1 Cores principais

| Cor | Hex | Uso |
|-----|-----|-----|
| Rosa | `#E91E63` | Header, títulos, badges, bordas |
| Verde menta | `#26A69A` | Botões, CTAs, links, destaques |
| Cinza claro | `#F5F5F5` | Fundo de página |
| Branco | `#FFFFFF` | Cards, containers, modais |
| Texto escuro | `#212529` | Corpo do texto (padrão Bootstrap) |

### 4.2 Por quê

- **Rosa** → já é a identidade visual existente, cor mais associada a doces e confeitaria
- **Verde menta** → contraste moderno e fresco, destaca ações (botões "Incluir", "Enviar", "Salvar") sem competir com o rosa
- **Cinza + branco** → fundo neutro que deixa as fotos dos produtos e as cores de destaque respirarem

### 4.3 Aplicação prática

```css
/* Variáveis CSS para usar no template */
:root {
  --rosa: #E91E63;
  --verde-menta: #26A69A;
  --bg-claro: #F5F5F5;
}
```

No Bootstrap, basta sobrescrever as variáveis `$primary` e `$success`:

```scss
$primary: #E91E63;     /* rosa = cor principal */
$success: #26A69A;      /* verde menta = ações positivas */
```

Ou via CSS customizado no `base.html`:

```html
<style>
  .btn-primary { background-color: #E91E63; border-color: #E91E63; }
  .btn-success { background-color: #26A69A; border-color: #26A69A; }
  .bg-primary { background-color: #E91E63 !important; }
  .text-primary { color: #E91E63 !important; }
</style>
```

---

## 5. Imagens — Armazenamento e Upload

### 5.1 Onde ficam

```
algodoce/
├── app/            ← código (versionado no git)
├── dados/
│   └── uploads/    ← imagens (NÃO versionado, backup independente)
└── .gitignore
```

**Por que não no PostgreSQL:** Imagens bloat o banco, lentificam backups, dificultam cache e CDN. Sistema de arquivos é o padrão correto.

**Por que separado do `app/`:** Backup do `dados/` é independente do código. Pode até estar em disco/dispositivo diferente.

### 5.2 Como são servidas

**Nova rota customizada** (`app/routes/uploads.py`):

```python
@uploads_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    dir = os.path.join(current_app.root_path, '..', 'dados', 'uploads')
    return send_from_directory(dir, filename)
```

Templates usam `url_for('uploads.uploaded_file', filename=product.imagem)` em vez do antigo `url_for('static', filename='uploads/' + ...)`.

### 5.3 Upload no Desktop

**File picker (explorer):** Já funciona — `<input type="file">` abre o seletor nativo do sistema.

**Copiar/Colar (novo):** JavaScript escuta o evento `paste` na página:

```js
document.addEventListener('paste', (e) => {
    const item = e.clipboardData.items[0]
    if (item.type.startsWith('image/')) {
        const file = item.getAsFile()
        // cria FormData e envia via fetch para a mesma rota de upload
    }
})
```

O usuário tira um print (Printscreen), copia uma imagem (Ctrl+C), e cola diretamente no formulário.

### 5.4 Upload no Mobile

**Câmera / Galeria:** Basta adicionar `capture="environment"` no `<input type="file">` atual. No celular, abre a câmera diretamente; se o usuário quiser galeria, usa o seletor normal.

```html
<input type="file" name="imagem" class="form-control"
       accept="image/png,image/jpeg,image/gif,image/webp"
       capture="environment">
```

### 5.5 Docker

A pasta `dados/` precisa ser montada como volume no container para persistir:

```yaml
services:
  app:
    volumes:
      - ./dados:/app/dados       # imagens persistem
      - .:/app                   # código (ou só o necessário)
```

O `compose.yml` atual usa bind mount `.:/app`, que já inclui `dados/`. Se quiser, pode isolar só `dados/` com um named volume depois.

---

## 6. Banco de Dados

### 6.1 Modelo antigo

Banco PostgreSQL rodando em container compartilhado (`pg_18`) com dados em `./pg_18/` — fora do projeto, fora do `dados/`, dependência externa.

### 6.2 Modelo novo

Cada projeto tem seu próprio container PostgreSQL com dados dentro de `dados/`:

```
algodoce/
└── dados/
    ├── uploads/       ← imagens
    └── pgdata/        ← PostgreSQL data (volume Docker)
```

### 6.3 compose.yml final

```yaml
services:
  db:
    container_name: algodoce_db
    image: postgres:16-alpine
    restart: unless-stopped
    volumes:
      - ./dados/pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    networks:
      - internal

  app:
    container_name: algodoce
    restart: unless-stopped
    build: .
    ports:
      - "5010:5000"
    env_file:
      - .env
    environment:
      POSTGRES_HOST: db          # override: nome do service no compose
    volumes:
      - ./dados/uploads:/app/dados/uploads
    depends_on:
      - db
    networks:
      - internal
      - proxy

  ngrok:
    container_name: algodoce_ngrok
    image: ngrok/ngrok:latest
    restart: unless-stopped
    environment:
      NGROK_AUTHTOKEN: ${NGROK_AUTHTOKEN}
    command:
      - 'http'
      - 'algodoce:5000'
      - '--host-header=algodoce.local'
    depends_on:
      - app
    networks:
      - internal
      - proxy

networks:
  internal:                      # nova: comunicação app ↔ db
  proxy:
    external: true
```

### 6.4 Mudanças na rede

- Sai da rede `db` (externa, compartilhada entre projetos)
- Usa rede `internal` (criada pelo compose, só algodoce enxerga)
- Rede `proxy` permanece (Nginx Proxy Manager)

### 6.5 Config (`app/config.py`)

Continua lendo `POSTGRES_HOST` da env. No Docker o compose injeta `db`, localmente pode ser `localhost`:

```python
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
```

### 6.6 Migração dos dados existentes

Os dados atuais estão no PostgreSQL compartilhado (`pg_18`, dados em `../pg_18/`). Para migrar para o novo banco autônomo:

```bash
# 1. Dump do banco antigo (executar no host, fora do container)
pg_dump -h localhost -U algodoce -d algodoce > /tmp/algodoce_dump.sql

# 2. Iniciar apenas o novo banco
docker compose up -d db

# 3. Aguardar PostgreSQL ficar pronto
docker compose exec -T db pg_isready -U algodoce

# 4. Restaurar o dump no novo banco
docker compose exec -T db psql -U algodoce -d algodoce < /tmp/algodoce_dump.sql

# 5. Iniciar o app
docker compose up -d app
```

> **Nota:** O dump inclui apenas dados (schema + registros). As imagens dos produtos precisam ser copiadas separadamente de `app/static/uploads/` para `dados/uploads/`.

### 6.7 Backup

```bash
tar czf backup-$(date +%Y%m%d).tar.gz dados/
```

Um único arquivo com **imagens + banco de dados** completos.

### 6.8 Schema Atual do Banco

```
┌─────────────────────────────────────────────────────────┐
│                       clients                           │
├─────────────────────────────────────────────────────────┤
│ id          │ INTEGER       │ PK, SERIAL                │
│ nome        │ VARCHAR(100)  │ NOT NULL                  │
│ email       │ VARCHAR(120)  │ UNIQUE, NOT NULL          │
│ telefone    │ VARCHAR(20)   │                           │
│ endereco    │ TEXT          │                           │
│ ativo       │ BOOLEAN       │ DEFAULT true              │
└─────────────────────────────────────────────────────────┘
     │
     └──< orders.client_id

┌─────────────────────────────────────────────────────────┐
│                       orders                             │
├─────────────────────────────────────────────────────────┤
│ id           │ INTEGER       │ PK, SERIAL               │
│ client_id    │ INTEGER       │ FK → clients.id          │
│ data_pedido  │ TIMESTAMP     │ NOT NULL, DEFAULT now()  │
│ data_entrega │ DATE          │                           │
│ status       │ INTEGER       │ NOT NULL, DEFAULT 0      │
│ observacao   │ TEXT          │                           │
│ total        │ NUMERIC(10,2) │                           │
│ quote_id     │ INTEGER       │ FK → quotes.id           │
└─────────────────────────────────────────────────────────┘
     │
     ├──< order_items.order_id
     │
     └──┐
         │ (FK pedido_id)
         ▼
┌─────────────────────────────────────────────────────────┐
│                       quotes                             │
├─────────────────────────────────────────────────────────┤
│ id              │ INTEGER       │ PK, SERIAL             │
│ data_pedido     │ TIMESTAMP     │ NOT NULL, DEFAULT now()│
│ cliente_nome    │ VARCHAR(100)  │ NOT NULL               │
│ cliente_telefone│ VARCHAR(20)   │ NOT NULL               │
│ status          │ INTEGER       │ NOT NULL, DEFAULT 0    │
│ pedido_id       │ INTEGER       │ FK → orders.id         │
│ total           │ NUMERIC(10,2) │                        │
│ observacao      │ TEXT          │                        │
└─────────────────────────────────────────────────────────┘
     │
     └──< quote_items.quote_id

┌─────────────────────────────────────────────────────────┐
│                    order_items                           │
├─────────────────────────────────────────────────────────┤
│ id             │ INTEGER       │ PK, SERIAL              │
│ order_id       │ INTEGER       │ FK → orders.id          │
│ product_id     │ INTEGER       │ FK → products.id        │
│ quantidade     │ INTEGER       │ NOT NULL                │
│ preco_unitario │ NUMERIC(10,2) │                         │
│ observacao     │ TEXT          │                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    quote_items                           │
├─────────────────────────────────────────────────────────┤
│ id             │ INTEGER       │ PK, SERIAL              │
│ quote_id       │ INTEGER       │ FK → quotes.id          │
│ product_id     │ INTEGER       │ FK → products.id        │
│ quantidade     │ INTEGER       │ NOT NULL                │
│ preco_unitario │ NUMERIC(10,2) │                         │
│ observacao     │ TEXT          │                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                      products                            │
├─────────────────────────────────────────────────────────┤
│ id          │ INTEGER       │ PK, SERIAL                │
│ nome        │ VARCHAR(100)  │ NOT NULL                  │
│ descricao   │ TEXT          │                           │
│ preco       │ NUMERIC(10,2) │ NOT NULL                  │
│ qtd_minima  │ INTEGER       │ NOT NULL, DEFAULT 0       │
│ imagem      │ VARCHAR(255)  │                           │
│ ativo       │ BOOLEAN       │ DEFAULT true              │
│ category_id │ INTEGER       │ FK → categories.id        │
└─────────────────────────────────────────────────────────┘
     │
     ├──< product_ingredients.product_id
     ├──< order_items.product_id
     ├──< quote_items.product_id
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│                   categories                             │
├─────────────────────────────────────────────────────────┤
│ id          │ INTEGER       │ PK, SERIAL                │
│ nome        │ VARCHAR(100)  │ NOT NULL                  │
│ ativo       │ BOOLEAN       │ DEFAULT true              │
│ ordem       │ INTEGER       │ DEFAULT 0                 │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                   ingredients                            │
├─────────────────────────────────────────────────────────┤
│ id             │ INTEGER       │ PK, SERIAL              │
│ nome           │ VARCHAR(100)  │ NOT NULL                │
│ unidade_medida │ VARCHAR(20)   │ NOT NULL                │
└─────────────────────────────────────────────────────────┘
     │
     ├──< product_ingredients.ingredient_id
     └──< unit_conversions.ingredient_id

┌─────────────────────────────────────────────────────────┐
│                product_ingredients                       │
├─────────────────────────────────────────────────────────┤
│ product_id     │ INTEGER       │ PK, FK → products.id   │
│ ingredient_id  │ INTEGER       │ PK, FK → ingredients.id│
│ quantidade     │ NUMERIC(10,3) │ NOT NULL                │
│ unidade        │ VARCHAR(20)   │ NOT NULL, def. 'un'    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                  unit_conversions                        │
├─────────────────────────────────────────────────────────┤
│ id            │ INTEGER       │ PK, SERIAL               │
│ ingredient_id │ INTEGER       │ FK → ingredients.id     │
│ unidade       │ VARCHAR(20)   │ NOT NULL                │
│ fator         │ NUMERIC(10,6) │ NOT NULL                │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                       events                             │
├─────────────────────────────────────────────────────────┤
│ id         │ INTEGER       │ PK, SERIAL                 │
│ quote_id   │ INTEGER       │ FK → quotes.id, UNIQUE     │
│ order_id   │ INTEGER       │ FK → orders.id, UNIQUE     │
│ tipo       │ VARCHAR(30)   │                            │
│ tema       │ VARCHAR(200)  │                            │
│ obs        │ TEXT          │                            │
│ data       │ DATE          │                            │
│ hora       │ TIME          │                            │
│ local      │ VARCHAR(200)  │                            │
│ convidados │ INTEGER       │                            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                        users                             │
├─────────────────────────────────────────────────────────┤
│ id            │ INTEGER       │ PK, SERIAL               │
│ username      │ VARCHAR(80)   │ UNIQUE, NOT NULL         │
│ password_hash │ VARCHAR(256)  │ NOT NULL                 │
└─────────────────────────────────────────────────────────┘
```

---

## 7. Estrutura de Arquivos (Novos/Modificados)

```
app/
├── __init__.py              # Factory: registra blueprints, seeder admin
├── extensions.py            # + login_manager
├── models/
│   └── user.py              # NOVO: model User
├── routes/
│   ├── site.py              # NOVO: rotas públicas do site
│   ├── auth.py              # NOVO: POST /login (AJAX) + GET /logout
│   ├── sistema.py           # NOVO: blueprint do sistema (dashboard)
│   ├── produtos.py          # NOVO: navegador de produtos (categorias + carrossel)
│   ├── orcamento.py         # NOVO: orçamento (itens + finalizar)
│   ├── uploads.py           # NOVO: GET /uploads/<filename> serve imagens
│   ├── clients.py           # + @login_required
│   ├── products.py          # + @login_required (refatorar _handle_imagem)
│   ├── ingredients.py       # + @login_required
│   ├── orders.py            # + @login_required
│   └── reports.py           # + @login_required
├── static/
│   ├── js/
│   │   ├── auth.js          # NOVO: popup de login
│   │   ├── paste.js         # NOVO: captura colar de imagem
│   │   └── orcamento.js     # NOVO: add/remove itens via AJAX
│   └── images/
│       └── logo.png         # Logo da empresa
├── templates/
│   ├── site/
│   │   ├── base.html        # NOVO: header fixo + menu site
│   │   ├── index.html       # NOVO: landing page
│   │   ├── sobre.html       # NOVO: sobre
│   │   └── contato.html     # NOVO: contato
│   ├── sistema/
│   │   ├── base.html        # NOVO: header fixo + menu sistema
│   │   └── dashboard.html   # NOVO: dashboard do sistema
│   └── orcamento/
│       ├── navegador.html   # NOVO: categorias + carrossel de produtos
│       └── lista.html       # NOVO: itens + painel evento + enviar
└── config.py                # (inalterado)
dados/
├── uploads/                 # NOVO: imagens dos produtos
└── pgdata/                  # NOVO: dados do PostgreSQL (volume Docker)
```

**`.gitignore`:**
```
dados/
app/static/uploads/
```

---

## 8. O que NÃO muda

- Dockerfile — inalterado
- PostgreSQL (modelo, queries) — inalterado
- Models existentes (`Client`, `Product`, `Ingredient`, `UnitConversion`) — só adições
- Blueprints atuais (`clients`, `products`, `ingredients`, `reports`) — só ganham `@login_required`
- Tema visual (rosa Bootstrap) — mantido
- Navegação entre registros — mantida

---

## 9. Seed de Admin

Criado automaticamente em `create_app()`:

```python
from app.models.user import User
if not User.query.first():
    admin = User(username="doceira")
    admin.set_password(os.getenv("ADMIN_PASSWORD", "1234"))
    db.session.add(admin)
    db.session.commit()
```

Variável no `.env`:
```env
ADMIN_PASSWORD=sua-senha-aqui
```
