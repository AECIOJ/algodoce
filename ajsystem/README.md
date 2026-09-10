# AJSYSTEM — framework declarativo de listas e formulários

O **ajsystem** é um framework web (Flask) para construir aplicações de gestão
de forma **declarativa**: você define *entidades*, *listas* e *formulários* em
dicionários Python e o framework monta blueprints, rotas, telas, menu e
autenticação automaticamente.

## Regra do contrato

- Este README documenta **apenas as props de fato exercitadas** (validadas em
  páginas já migradas). São descritas de forma **genérica**, sem citar qual app
  nem qual página as utiliza — valem para qualquer app.
- Props que **existem no dataclass mas não foram usadas** são consideradas
  **desaprovadas** e **não** aparecem aqui. À medida que uma nova prop passar a
  ser usada, ela é acrescentada a este documento.
- Para cada definição, primeiro é mostrada a **sintaxe** (como se escreve) e
  depois as **propriedades** (o que cada parte configura).
- O arquivo `README.old` contém o histórico detalhado anterior à padronização.

## Passos para construir um novo app

1. **Model** (`app/models/<entidade>.py`): classe SQLAlchemy + `Entity`
   (definição base dos campos) + relacionamentos (`relationship`) para sessões
   filhas.
2. **Route** (`app/routes/sys/<slug>.py`): `Schema` (overrides opcionais) +
   `Page` (`type` com `props` apropriados ao tipo de página).
3. **Menu** (`app/config.py`): registrar o módulo em `menus` (label → resolve o
   blueprint pelo slug).
4. **Teste**: reiniciar o container → acessar `/{slug}` (list), `/{slug}/novo`
   e `/{slug}/<id>/editar`.
5. **Opcional**: hooks e recursos extras são usados na medida em que a infra
   for alinhada.

---

## 1. Arquivo `config.py` — registro de módulos e menus

Cada **módulo** (área do app) é um dict que segue o dataclass `Module`
(`defs/config.py`). Os módulos são agregados em `APP['modules']`.

### Sintaxe

```python
MODULO = {                       # SYS, SITE, ADMIN, etc.
    'type': '<tipo>',            # tipo do módulo
    'default_path': '<menu>',    # destino padrão do módulo
    'triggers': {...},           # (opcional) triggers de UI
    'layout': {...},             # (opcional) header/footer
    'menus': {                   # árvore de menus
        'Grupo': {
            'icon': '...',
            'submenus': {
                'Submenu': {'icon': '...'},
            },
        },
    },
}

APP = {
    'name': '...',
    'title': '...',
    'logo': '...',
    'tema': '...',
    'modules': [SITE, SYS, ADMIN],   # módulos agregados na aplicação
}
```

### Propriedades do módulo

| Propriedade | Tipo | O que configura |
|---|---|---|
| `type` | str | **Tipo do módulo** — `'public'` (padrão), `'system'` ou `'admin'` (ou outro); devem ser únicos no app |
| `default_path` | str | **Menu padrão** do módulo — destino ao abrir o app: `'menu'` ou `'menu/submenu'` (ex.: `'cadastro/categorias'`) |
| `menus` | dict | Árvore de menus de navegação |
| `icon` | str | Ícone do menu (classe de ícone) |
| `submenus` | dict | Itens filho `{label: {icon}}`; o **label** é resolvido como slug para a rota do módulo |
| `page` | str | (em item de menu) Arquivo do módulo quando o rótulo ≠ nome do arquivo (ex.: menu `'Contas a Receber'`, `'page': 'receber'`) |
| `url` | str | (em item de menu) Escape de navegação — endpoint registrado ou caminho literal; **não** monta módulo |
| `triggers` | dict | (opcional) Triggers de UI (ex.: clique no logo) |
| `layout` | dict | (opcional) Layout visual do módulo (header/footer) |

### Propriedades do app (`APP`)

| Propriedade | Tipo | O que configura |
|---|---|---|
| `name` | str | Nome do app |
| `title` | str | Título exibido |
| `logo` | str | Caminho do logo |
| `tema` | str | Tema visual |
| `modules` | list | Módulos agregados na aplicação |
| `upload` | dict | Política global de upload: `{'path': '', 'max_size': 5242880, 'allowed': ['png','jpg','jpeg','gif','webp']}` (`path` = subdir em `dados/uploads`, `''` = raiz) |

Comportamento: o matcher entre o rótulo do menu e o módulo é feito pelo slug
(derivado do label); o framework monta a rota do blueprint automaticamente.

---

## 2. Model — a entidade e sua `Entity`

### Sintaxe

Definição de **uma** entidade (a do próprio módulo):

```python
class MinhaEntidade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    ...

Entity = {
    'id':    {'type': 'ID', 'width': 6},
    'nome':  {'type': 'TEXT', 'required': True},
    ...
}
```

Definição de **várias** entidades (chave = nome da entidade):

```python
Entity = {
    'MinhaEntidade': {'nome': {'type': 'TEXT'}},
    'OutraEntidade': {'nome': {'type': 'TEXT'}},
}
```

> **Migração (modelo antigo → modelo novo):** antes a `Entity` era definida na
> **rota** e podia conter **várias** entidades (chave = nome da entidade). Agora a
> `Entity` é definida no **model** e agrupa **uma** entidade por módulo (a do
> próprio módulo). Para migrar, mova a `Entity` para o model do módulo e restrinja
> o dicionário à entidade principal — as entidades auxiliares/filhas passam a ser
> resolvidas via relacionamento e sessões `table`/`query`.

Cada entidade é uma classe `db.Model` seguida de um dicionário `Entity` com a
definição base dos campos. É a **única fonte** de definição dos campos; o
`Schema` da route apenas faz *overrides* pontuais.

### Tipos de campo

| Tipo | Comportamento |
|---|---|
| `ID` | Chave primária (coluna `id`), exibida como identificador |
| `TEXT` | Texto de linha única |
| `MEMO` | Texto multilinha (textarea) |
| `INT` | Inteiro (input numérico) |
| `NUM` | Numérico decimal |
| `LIST` | Seleção a partir de `options` (select) |
| `BOOL` | Booleano (checkbox) |
| `FONE` | Telefone com máscara já definida: `'@R (99) 99999-9999'` |
| `CPF` / `CNPJ` | Documento com máscara já definida: `'@R 999.999.999-99'` / `'@R 99.999.999/9999-99'` |
| `FK` | Chave estrangeira — gera select com as opções do relacionamento |
| `DK` | Chave da linha-pai (campo oculto gerenciado pelo motor em sessões filhas) |
| `DATA` / `DATA_HORA` | Data / data e hora (input de calendário) |
| `IMAGE` | Upload de imagem |
| `MULT10` | Códigos concatenados (multivalorado, 0-9), editor genérico em modal; usa `options` para as opções |

### Props de campo (todas opcionais exceto `type`)

| Propriedade | Tipo | O que configura |
|---|---|---|
| `type` | str | Tipo do campo (obrigatório) |
| `label` | str | Rótulo exibido (senão usa o nome do campo) |
| `width` | int | Largura da coluna/campo em caracteres (`ch`) |
| `required` | bool | Impede salvar sem valor |
| `transform` | str | ~~Removido~~ — use `mask` com comando de texto (`'@T'`, `'@U'`, `'@L'`, `'@C'`) para transformação de exibição |
| `options` | dict | Opções de `LIST` e de `MULT10` `{valor: rótulo}` |
| `currency` | int | Moeda pelo código `CURRENCY` (`0` = sem moeda; `1` = padrão). `True`/`'brl'` legados equivalem ao padrão. Formatação e símbolo vêm do motor (filtro `money`) |
| `input_name` | str | Nome do input no HTML (default: o nome do campo). Usado como alvo de escrita dos totais; o save lê `input_name or name` |
| `tag` | dict | Badge do valor — `{'colors': {...}, 'color': ..., 'link': ...}` (ver `tag` abaixo) |
| `min` / `max` | int/float | Limites do valor |
| `step` | int | Passo do input numérico |
| `mask` | str | Máscara de formatação/exibição. **Tokens de caractere**: `9` = dígito; `A` = letra (A-Z, caixa como digitada); `N` = alfanumérico (letra/dígito, caixa como digitada); `#` = dígito/ espaço/ sinal (letra é bloqueada); demais caracteres são literais. Em campos de data/hora usa **tokens de data**: `dd`/`mm`/`aaaa` (ou `yyyy`)/`aa` (ou `yy`)/`mmm`/`ddd` p/ data, `hh`/`ii`/`ss` p/ hora (`ii` = minuto; `mm` = mês em máscaras com data). Ex.: `'dd/mm/aaaa'`, `'dd/mm/aaaa hh:ii'`, `'hh:ii'`. `ddd` (dia da semana) e `mmm` (mês abreviado, PT) são **derivados**: não se digita, o motor calcula da data e o save os ignora — ex.: `'ddd dd/mm/aaaa'` exibe `sáb 27/06/2026`. Com tokens, o campo vira input texto mascarado (em vez do picker nativo); na listagem/readonly o valor é exibido pela máscara. **Comandos** (`@X`, contíguos após `@`): `@R` = não gravar separadores (save guarda só os caracteres de token — ex.: CPF); `@U`/`@L`/`@C`/`@T` = transform do texto salvo (maiúscula/ minúscula/ inicial maiúscula/ Title; valido só em TEXT/MEMO, no máx. um); `@B` = exibir vazio quando zero; `@X` = sufixo exibido `'C'`/`'D'` conforme o sinal (`@B`/`@X` valem só p/ número e geram o texto de exibição, ex.: `'@BX 999,999.99'` → `1.234,50 C`). Sem comando de texto, o valor é salvo **como digitado**. Ex.: `'@UR AAA-9A99'` (placa maiúscula), `'@R AAA-9A99'` (placa como digitada), `'@R 999.999.999-99'` (CPF), `'@R (99) 99999-9999'` (telefone), `'@T'` (campo de nome: só o transform title, sem corpo) |
| `rows` | int | Altura (número de linhas) para campo de texto |
| `decimals` | int | Casas decimais (inputs numéricos exibem pt-BR com essas casas; `0` = inteiro; com decimais, a digitação é modo calculadora: dígitos à direita, vírgula alterna p/ fração, Backspace desfaz) |
| `pos_list` | int | Visibilidade na lista: `0` oculta; `2` vai para o card; `1`/`None` exibe |
| `pos_filter` | int | Filtro do painel: `0` fora; `1`/`2`/`3` modos; `9` fixo pelo `default` (aplica `WHERE` de igualdade, sem UI; força `pos_form: 0` + `pos_list: 0`) |
| `input` | str | Tipo de input (`'email'`, `'textarea'`, ...) |
| `align` | str | Alinhamento da célula (`'left'`, `'center'`, `'right'`...) |
| `lookup` | dict/`Lookup` | Complemento de FK para escolha/exibição por busca (ver abaixo) |
| `on_set` | dict | **Efeitos ao setar**: `{'replaces': {...}, 'disables': [...]}` — preenchimento (`{campo_alvo: fonte}`) e desabilitação mútua (lista de alvos) |

> **`lookup`** aplica-se a campos FK e substitui o `query`-de-campo. O motor infere
> da FK o model a pesquisar e o valor gravado é o da prop `value` (default `'id'`).
> A prop configura:
> - `display` (str): campo **exibido** na listagem e no form readonly (default: o
>   próprio `value`). A listagem resolve `item.<relacao>.<display>`.
> - `fields` (list[str]): campo(s) **listados ao escolher** — `1` campo vira
>   `<select>` no form; `>1` abrirá um gerador/modal de busca.
> - `value` (str): campo a **retornar e gravar** (default `'id'`).
> - `when` (dict|str): condição para listar nas opções, ex.: `{'ativa': True}`.
>   Dict aceita lista/tupla/set como `IN` (`{'tipo': [0, 1]}`; vazia ignora o
>   campo) e `None` como `IS NULL`. String aceita `=`, `!=`, `IN (...)`,
>   `NOT IN (...)`, `IS NULL`, `IS NOT NULL` unidas por `AND` (ex.:
>   `'ativo = true AND tipo IN (0, 1)'`).
> - `replaces` (em `on_set`): **preenchimento automático** de campos da linha
>   a partir do registro escolhido — `{campo_alvo: campo_fonte}`. O mesmo mapa
>   alimenta o botão de rodapé que reaplica o preenchimento (ex. botão de
>   "preços zerados" via `buttons`).
>   **Modo por-opção** (selects de LISTA): se o valor do mapa for um dict,
>   `{campo_alvo: {valor_opcao: literal}}`, cada opção estática carrega seu
>   próprio valor de preenchimento. Ex.:
>   ```python
>   'campo_origem': {'type': 'LIST', 'options': STATUS,
>                    'on_set': {'replaces': {'campo_alvo': {0: 'x', 1: 'y'}}}},
>   ```
>   **Modo constante**: valor escalar (string em LISTA, número/bool em qualquer
>   select) vira literal em todas as opções. Ex.:
>   ```python
>   'campo_origem': {'type': 'LIST', 'options': STATUS,
>                    'on_set': {'replaces': {'campo_alvo': 'fixo'}}},
>   ```
>   (Em select FK, string segue significando atributo-fonte do registro.)
> - `query` (str): nome de uma busca declarada na rota — em vez de `<select>`,
>   renderiza display + hidden + botão externo que abre modal de busca
>   (`GET /ajsystem/lookup-search?page=<slug>&query=<NOME>[&<param>=...]`).
>   A declaração tem `source` (entidade-raiz), `join`, `columns` (como fields),
>   `when` (fixos, com `>`/`<`/`IN`/etc.), `params` (`{arg: campo}` exigidos —
>   sem valor, o modal pede ao usuário) e `order` opcional. Colunas computadas
>   (`calc`/property) filtram e exibem em Python; o resto vai no SQL.
>
> Exemplo:
> ```python
> 'pai_id': {'type': 'FK', 'label': 'Superior',
>            'lookup': {'display': 'nome', 'fields': ['nome'], 'value': 'id'}},
> 'produto_id': {'type': 'FK', 'label': 'Produto', 'required': True,
>                'on_set': {'replaces': {'qtd': 'qtd_minima',
>                                        'preco': 'preco'}}},
> ```

> **Agregação (soma de coleção/agrupamento) não é prop de campo.** Valores
> calculados por linha a partir de atributos do próprio registro usam `calc`
> (callable ou expressão string). Agregações sobre relacionamentos (ex.: soma
> dos itens de um pedido) pertencem à sessão/`Query`, não ao `field`.

> **`on_set`** (dict) — **efeitos ao setar** o campo, com as chaves:
> - `replaces`: preenchimento `{campo_alvo: campo_fonte}` (modo fonte),
>   `{campo_alvo: {valor_opcao: literal}}` (modo por-opção, p/ LISTA) ou
>   `{campo_alvo: literal}` (modo constante). Exemplo — ao escolher o produto,
>   traz `qtd` (da `qtd_minima`) e `preco` (do `preco` do produto):
> ```python
> 'produto_id': {'type': 'FK', 'label': 'Produto', 'required': True,
>                'on_set': {'replaces': {'qtd': 'qtd_minima',
>                                        'preco': 'preco'}}},
> ```
> - `disables`: lista de campos desabilitados enquanto este tiver valor
>   (reabilita ao limpar). Guarda anti-deadlock: alvo com valor nunca é
>   desabilitado. Ex. — CPF × CNPJ:
> ```python
> 'cpf':  {'type': 'CPF', 'on_set': {'disables': ['cnpj', 'insc_estadual']}},
> 'cnpj': {'type': 'CNPJ', 'on_set': {'disables': ['cpf']}},
> ```
> Campos **`calc`** (virtual, não persistido) de uma tabela editável só são
> totalizados quando listados em `table.totals` (ver sessões).
>
> **Busca em modal (`lookup.query`)** — declaração na rota + referência no campo:
> ```python
> PREVISOES = {
>     'source': 'Previsao', 'join': 'transacao',
>     'columns': ['id', 'documento', 'vencimento', 'previsto',
>                 'realizado', 'variacao', 'saldo'],
>     'when': ["transacao.tipo = 'R'", 'saldo > 0'],
>     'params': {'conta_id': 'transacao.conta_id'},
>     'order': ['vencimento'],
> }
> 'previsao_id': {'lookup': {'display': 'id', 'query': 'PREVISOES'},
>                'on_set': {'replaces': {'valor': 'saldo'}}},
> ```
> Linhas trazem `raw` (valores crus) para o `replaces` aplicar ao escolher.
>
> **Validadores client-side** — genéricos em `ajsystem/static/js/validators.js`
> (`cpf`, `cnpj`, registro `window.FieldValidators`); customs do app em
> `app/static/js/validacoes.js` (arquivo do app, criar seguindo o modelo):
> ```js
> // app/static/js/validacoes.js
> FieldValidators.register('placa', function (v) {
>   return /^[A-Z]{3}[0-9]$/.test(String(v || ''));
> });
> ```
> ```python
> # declaração no campo: chave resolvida nos dois registros
> 'placa': {'type': 'TEXT', 'validate': 'placa'},
> ```
> ```html
> <!-- incluir APÓS validators.js (sys.html tem o slot marcado em comentário); bump no ?v= a cada mudança -->
> <script src="{{ url_for('static', filename='js/validacoes.js') }}?v=1"></script>
> ```
> Regras: a chave é resolvida em cada lado de forma independente — `validate`
> com chave desconhecida não bloqueia (fail-soft + aviso no console); a função
> custom recebe DÍGITOS (máscara já removida), então só serve a validações
> numéricas; para impor no POST, espelhe a regra em `defs/validators.py`
> (`VALIDATORS`), pois o client é só UX.
>
> **JS do framework (`ajsystem/static/js/`)** — um arquivo por domínio, IIFE +
> `'use strict'`, exportando em `window` o que templates/`onclick` consomem;
> carga via `<script src>` no bloco `scripts` do `sys.html` (ordem: libs,
> framework, app), com `?v=N` e bump a cada mudança (sem build; bind-mount
> reflete na hora, navegador cacheia). Regra: arquivo sem wiring e sem teste
> apodrece (precedente: `multi-ctl.js`, hoje sem inclusão) — todo `.js` novo
> entra já incluído e testado.
>
> **`formats.js`** — formatação e parse de valores no cliente (máscaras com
> tokens de caractere `9`/`A`/`N`/`#`, tokens de data/hora (`ddd`/`mmm`
> derivados), comandos `@R`/`@U`/`@L`/`@C`/`@T`/`@B`/`@X`; números/moeda pt-BR;
> data). Espelho do backend `core/formats.py`: **mesma ordem de tokens, mesmos
> comandos, mesmos `_PT_DOW`/`_PT_MES`** — ao adicionar/ajustar token ou comando,
> atualizar nos DOIS lados e conferir paridade (smoke na listagem/form).
> `_applyMask`/`_maskStrip`/`fmtMask`/`format`/`parseNum`/`fmtNumBR`/
> `fmtFieldInput`/`itFmtMoney`/`parseDate` vivem aqui e são usados pelo inline
> JS do `sys.html` (carregado ANTES do inline). `format(value, mask)` (idêntico
> no backend) formata número/data/string por qualquer máscara de uma vez só.
>
> **`modals.js`** (diálogos) e **`validators.js`** (validações CPF/CNPJ,
> `window.FieldValidators`) seguem o padrão. Candidatos futuros,
> **propositalmente ainda inline**: `totals.js` (cálculos e somas), `items.js`
> (linhas filhas), `search.js` (fluxo de busca), `shell.js`
> (menus/timeout/QR) — extrair um por vez, cada um com teste, nunca big-bang.

> **`tag`** — badge semântico do valor do campo (texto + cor), com
> navegação opcional:
> ```python
> 'status': {'type': 'LIST', 'options': {...},
>            'tag': {'colors': {0: 'warning', 9: 'success'}}},
> 'pedido_id': {'type': 'FK', 'tag': {'link': 'pedidos.form', 'color': 'info'}},
> ```
> - `colors` (dict): mapa VALOR → cor (nome DaisyUI ou índice 0–9).
> - `color` (str): cor **fixa** do badge; precedência: `colors[valor]` >
>   `color` > heurística do motor (texto/número).
> - `link` (str): endpoint que torna o badge **navegável**
>   (`url_for(link, id=valor)`); sem valor (`None`), não renderiza badge.
> - Onde renderiza: `pos_form: 4` leva o badge para a **barra do form** (e o
>   campo sai do corpo); na listagem, a célula vira badge. Rótulo da barra:
>   `label: texto` (label em texto normal, valor no badge).

---

## 3. Route — `Schema` e `Page`

### `Schema`

Dicionário de **overrides** de campos sobre a `Entity` do model. Está **vazio**
(`Schema = {}`) por padrão: quando vazio, os campos vêm integralmente da
`Entity`. Preencha apenas para sobrescrever/ajustar campos pontuais.

### `Page`

A `Page` descreve a página pelo seu `type`. Cada `type` usa um conjunto próprio
de `props` e gera rotas automaticamente.

#### Sintaxe

```python
Page = {
    'type': '<tipo>',
    'props': {
        ...
    },
}
```

#### Tipos de página

| Tipo | Gera | Quando usar |
|---|---|---|
| `crud` | Lista + formulário (novo/editar) | Telas de cadastro/gestão de dados |
| `custom` | Uma página renderizada por `template` | Páginas de conteúdo/estáticas |
| `cart` | Página de carrinho declarativo | Fluxos de seleção e envio |
| `showcase` | Vitrine declarativa (catálogo) | Exibição de produtos/items ao cliente |
| `contacts` | Página de contatos | Canais de contato (whatsapp, e-mail, redes) |

#### Propriedades comuns

| Propriedade | Tipo | O que configura |
|---|---|---|
| `type` | str | Tipo da página (obrigatório; ver tabela acima) |
| `props` | dict | Configuração específica de cada `type` |
| `route` | str | Rota/subpasta da página (opcional) |
| `max_width` | int | Largura máxima da página (em caracteres) |
| `upload` | dict | Política de upload da página (sobrescreve `App.upload`); ausente = herda. Mesmas chaves e defaults do global |

### `type: 'crud'`

Página de lista + formulário. O `props` contém `tabs`, `list` e `form`.

```python
Page = {
    'type': 'crud',
    'props': {
        'tabs': {...},
        'list': {...},
        'form': {...},
    },
}
```

#### `tabs`

Aba(s) exibidas na página:

| Propriedade | Tipo | O que configura |
|---|---|---|
| `<label>` | dict | Cada aba, com `{'type': '...'}` |
| `.type` | str | Tipo da aba — `'List'` (lista de registros) ou `'Filter'` (filtros) |

#### `list`

Configuração da listagem:

| Propriedade | Tipo | O que configura |
|---|---|---|
| `columns` | str | Entidade (ex.: `'NomeDaEntity'`) — expande todos os campos |
| `order` | list | Ordenação por campos (ordem de precedência) |
| `detail` | list ou dict | Tabela transposta expansível por linha (label fixa + scroll horizontal + pager): lista = campos da própria entidade; dict `{'fields': [...], 'data': '<rel>'}` = campos da entidade filha resolvidos no relacionamento (ex.: previsões da transação; só renderiza com itens) |

#### `form`

Configuração do formulário (novo/editar):

| Propriedade | Tipo | O que configura |
|---|---|---|
| `fields` | str | Entidade — expande todos os campos em edição |
| `max_width` | int | Largura máxima do form (em caracteres); se ausente, herda a largura da list |
| `buttons` | list | Botões — `'on_off'` (ativar/desativar) ou dict custom (ver `Button` abaixo) |
| `sessions` | dict | Seções filhas (ver abaixo) |
| `delete` | ver abaixo | Regras de exclusão |
| `pre_save` | callable | `f(instance, request, is_new)` executado antes de salvar |
| `post_save` | callable | `f(instance, changed, old_vals)` executado após salvar |

##### `delete`

| Formato | O que configura |
|---|---|
| `True` | Sempre permite excluir |
| `False` | Sem exclusão |
| `{'when': {...}}` | Bloqueia a exclusão quando houver referência nas classes/modelos listados |
| `{'msg_ok': ..., 'msg_no': ...}` | Mensagens de sucesso / bloqueio |

##### `buttons` — botões do form (`Button`)

Dict custom (além do preset `'on_off'`):

| Propriedade | Tipo | O que configura |
|---|---|---|
| `label` | str | Texto do botão (obrigatório no dict custom) |
| `icon` | str | Ícone (heroicon) |
| `color` | str | Cor (`'success'`, `'info'`, ...) |
| `outline` | bool | Estilo outline (default `True`) |
| `endpoint` | str | Endpoint de destino (`url_for(endpoint, id=...)`) |
| `url_var` | str | Variável de URL (default `'id'`) |
| `method` | str | `'GET'` (link) ou `'POST'` (mini-form) |
| `action` | callable | `(instance) -> url` (navega) ou, com `render`, `-> html` (injeta) |
| `render` | str | Seletor CSS onde injetar o HTML da `action`; `'#report-content'` = container exclusivo de relatório do meio (overlay com Voltar funcional, padrão das impressões) |
| `js` | str | Chamada client-side (ex.: `'itUpdateZerados(this)'`) |
| `when` | callable | `(instance) -> bool` — exibe condicionalmente |
| `position` | str | `'nav_right'` (barra), `'footer_left'`, `'footer_right'` |
| `confirm_msg` | str | Confirmação antes de executar |

Botões com `endpoint`/`action` são ocultos em registro novo (sem instância).

> **Modal via `action` (`modal_script`)** — um callable Python pode abrir um
> modal JS numa página gerada: retorne `modal_script(...)` e aponte `render`
> para um container (ex.: `'#report-content'`); o `injectHTML` executa o
> `<script>` ao injetar. A `action` recebe a `instance` (pode ser `None`).
> ```python
> from ajsystem.defs.buttons import modal_script
>
> def _btn_detalhes(instance):
>     if instance is None:
>         return ''
>     return modal_script(
>         'Detalhes',
>         lines=[f'Cliente: {instance.cliente_nome}',
>                f'Total: {instance.total}'],
>         buttons=[{'label': 'Fechar', 'cls': 'btn-ghost', 'value': 'x'}],
>     )
>
> {'label': 'Detalhes', 'icon': 'eye', 'color': 'info', 'outline': True,
>  'action': _btn_detalhes, 'render': '#report-content',
>  'position': 'nav_right'},
> ```
> Regras: monta `ajModal({...})` com escape seguro (`json` + neutralização
> de `</`) — pode interpolar dado do banco sem risco de quebrar o JS;
> `instance=None` deve retornar `''`; só modal **informativo** (sem callbacks
> — confirmação com ação segue via `confirm_msg`/JS); para HTML arbitrário use
> `html=` (já sanitizado, por sua conta).

##### Estrutura visual dos modais (3 zonas)

Todo modal segue a mesma estrutura visual, tanto os gerados por `ajModal()`
quanto os estáticos (`choice_modal`, `modalCrop`, `timeoutModal`):

```
modal-box (p-0, border:1px solid cor_do_tom)
  ├── barra   (cor do tom, padding:.75rem 1.5rem — título + ícone)
  ├── corpo   (padding:1rem 1.5rem — conteúdo)
  └── rodapé  (cinza oklch(var(--b2)) — botões, encosta nas bordas)
       └── modal-action (margin:0, padding:.5rem 1.5rem)
```

Regras de texto:
- **Título** (barra): informativo, sem `?` (ex.: `Há alterações não salvas.`)
- **Mensagem** (corpo): pode conter `?` quando for pergunta ao usuário
- **Botões** (rodapé): ação direta (`OK`, `Fechar`, `Sair`, `Salvar`...
  nunca `Sim`/`Não` isolados — o contexto vem na mensagem)

##### `sessions` — seções filhas

Uma sessão é uma seção do formulário que trata um **filho** (outra entidade
relacionada por FK). Ela pode combinar as props `fields`, `table` e `query` —
podendo ser definida **uma, duas ou todas**, conforme o caso:

| Propriedade | Tipo | O que configura |
|---|---|---|
| `fields` | list | Formulário editável — se o 1º item é **Entity** do filho (`['Evento']`), sessão 1:1 child; se é **campo do pai** (`['total','carteira_id']`), sessão de campos do pai (sem child) |
| `table` | dict | Tabela **editável** (detalhe) — com `columns`; persiste as linhas do relacionamento |
| `query` | dict | Exibição **somente leitura** — com `columns`, `groups`, `order` |
| `buttons` | list | Botões de rodapé da tabela editável — cada um como um `Button` (ver `buttons`); uso comum: ação client-side via `js` |

- **`fields` sozinho** — detecta automaticamente o tipo de sessão:
  - **Child 1:1**: o 1º item é um **nome de Entity** (ex. `['Evento']`) — renderiza
    o child único como formulário; aparece mesmo sem dados para permitir a
    inclusão; o motor persiste o child (criar/atualizar) no submit vinculando a
    FK do pai. Itens subsequentes restringem as colunas.
  - **Campos do pai**: o 1º item é um **campo da própria Entity** (ex.
    `['total', 'carteira_id']`) — renderiza campos do registro pai agrupados numa
    seção; útil para expor campos ocultos (`pos_form: 0`) numa área dedicada.
    O motor grava esses campos no pai durante o submit. Ex.:
    ```python
    'Financeiro': {'fields': ['total', 'carteira_id']},   # campos do pai
    'Evento':     {'fields': ['Evento']},                   # child 1:1
    ```
- `query` e `table` são **mutuamente exclusivos**. A coluna de uma sessão aceita
  o nome da entidade (expande todos os campos) ou lista de campos específicos; o
  vetor de colunas é resolvido contra o `Entity` + `Schema` da entidade filha,
  preservando a ordem de definição.
- `table.columns`: colunas da tabela editável; o motor persiste as linhas
  (adicionar/remover) do relacionamento.
- `table.totals`: lista que define a **linha de totais** no rodapé da tabela
  editável. Aceita item string (só totaliza) ou dict `{coluna: input_name}`
  (totaliza **e** grava no input do master cujo `input_name` é o valor). Ex.:
  `['qtd', {'valor': 'eTotal'}]` — soma `qtd` e soma `valor`
  propagando ao campo do master com `input_name: 'eTotal'`. Sem `totals`, nenhuma
  linha de totais é exibida. Campos com `calc` podem ser totalizados — o total
  soma, para cada linha, o valor calculado (não apenas o campo cru). O rótulo
  `Total` ocupa as colunas até a primeira coluna totalizada. A célula do total
  usa a mesma fonte das células do corpo (difere só o fundo da linha). Totais
  não-moeda formatam com as casas da coluna (`decimals` declarado, senão a
  escala NUM do banco, senão número puro) — igual ao exibido na linha.
- Para reaplicar o preenchimento de um FK numa tabela editável, declare um botão
  em `sessions.<nome>.buttons` com `js` apontando para a ação genérica do motor:
  `{'label': 'Atualizar preços zerados', 'icon': 'currency-dollar',
  'color': 'secondary', 'js': 'itUpdateZerados(this)'}` — preenche, para cada
  linha cujo campo esteja vazio/zerado, o valor do atributo da opção selecionada,
  seguindo o mapa `on_set` do FK. Nota: `buttons` só renderiza na
  tabela editável (`table`).
- `query.columns`: colunas da exibição somente leitura (mini-relatório).
- `query.groups`: campo de agrupamento; a leitura é exibida agrupada (na ordem
  das `options` quando houver), sem edição.
- `query.order`: ordem das linhas (`'campo'`, `'campo desc'` ou lista).
- Em form **readonly**, as linhas da tabela exibem texto mas emitem `hidden`s
  com os valores crus (`child_<rel>_<id>_<campo>`), para que os `calc` e
  `totals` client-side continuem calculando.

Exemplo (orçamento com Evento 1:1 e Itens em tabela editável, totalizando a
coluna `valor` — um campo `calc` = `qtd * preco`):

```python
'form': {
    'sessions': {
        'Evento': {'fields': ['Evento']},                       # form 1:1 editável
        'Itens do Orçamento': {'table': {
            'columns': ['OrcamentoItem'],
            'totals': ['valor'],                               # linha de totais
        }},
    },
}
```

### `type: 'custom'`

Página de conteúdo renderizada por `template` (markdown ou html).

```python
Page = {
    'type': 'custom',
    'template': {'type': 'markdown', 'file': 'nome'},
}
```

| Propriedade | Tipo | O que configura |
|---|---|---|
| `template` | dict | Template da página — `{'type': 'markdown'\|'html', 'file': '...'}` |
| `template.type` | str | `'markdown'` (renderiza markdown) ou `'html'` (template html) |
| `template.file` | str | Arquivo do template (sem extensão para markdown) |

### `type: 'cart'`

Página de carrinho declarativo (seleção + envio), com sessões child e ação de
envio.

```python
Page = {
    'type': 'cart',
    'max_width': 48,
    'props': {
        'sessions': {...},      # sessões table/form do carrinho
    },
}
```

### `type: 'showcase'`

Vitrine declarativa para exibir um catálogo ao cliente.

```python
Page = {
    'type': 'showcase',
    'props': {
        'fields': 'Produto',
        'filter': 'Categoria',
        'layout': 'carousel',
    },
}
```

### `type: 'contacts'`

Página de contatos; cada `props` é um canal de contato.

```python
Page = {
    'type': 'contacts',
    'props': {
        'Telefone': {'type': 'whatsapp', 'value': '...'},
    },
}
```

---

## 5. Report — relatório PDF declarativo

Um relatório é declarado como `dict` puro e renderizado pelo motor
`ajsystem.core.pdf.gerar_pdf_relatorio(report, ...)`.

### Sintaxe

```python
REPORTE = {
    'label': 'Título do Relatório',
    'header': {...},
    'body': {...},
    'footer': {...},
}
```

### Props de `Report` (top-level)

| Propriedade | Tipo | O que configura |
|---|---|---|
| `label` | str | Título do relatório (obrigatório) |
| `header` | dict | Cabeçalho do relatório (logo, título, campos) |
| `body` | dict | Corpo — datasource + formato de impressão |
| `footer` | dict | Rodapé de cada página |
| `page_size` | str | Tamanho da página (default `'A4'`) |
| `orientation` | str | `'portrait'` ou `'landscape'` |
| `orientation_mutable` | bool | Permite trocar orientação na UI |
| `margin_top/bottom/left/right` | float | Margens em mm |
| `show_table_lines` | bool | Linhas horizontais entre linhas de dados |
| `logo_path` | str | Caminho da logo (relativo ao root do app) |
| `print_fragment_template` | str | Template do fragmento HTML injetado pelo botão (default `'components/print_fragment.html'`) |

### Props de `header`

| Propriedade | Tipo | O que configura |
|---|---|---|
| `logo` | dict | Configuração do logo — `{'position': 'C'}` (centro, esquerda, direita) |
| `title` | dict | Título do cabeçalho — `{'label': '...'}` |
| `fields` | list | Campos adicionais no cabeçalho |

### Props de `body`

| Propriedade | Tipo | O que configura |
|---|---|---|
| `source` | str ou dict | Dados — string: nome da Entity; dict: `{'entity': '...', 'order': '...'}` |
| `table` | dict | Formato tabela — `columns` + `hierarchy` (+ `footer`, `after`) |
| `form` | dict | Formato campo/valor (futuro) |
| `before` / `after` | callable ou list | Linhas antes/depois da tabela — callable `f(instance) -> linhas` (`[{'text': ..., 'font_size': ...}]`) |
| `filter` | dict ou callable | Filtro aplicado à query na impressão — `{campo: valor}` (igualdade, `None` = ignora) ou callable `f(model) -> critério` |

### Props de `body.source` (quando dict)

| Propriedade | Tipo | O que configura |
|---|---|---|
| `entity` | str | Nome da Entity para buscar dados |
| `order` | str | Campo de ordenação — aceita campo `calc` (python sorted) ou coluna SQL |
| `data_attr` | str | Atributo alternativo nos dados (para sessões filhas) |

### Props de `body.table.columns` (dict de colunas)

Cada chave é o nome do campo; o valor é um dict:

| Propriedade | Tipo | O que configura |
|---|---|---|
| `width` | float | Largura da coluna (em mm ou chars) |
| `label` | str | Rótulo do cabeçalho da coluna |
| `align` | str | Alinhamento — `'left'`, `'center'`, `'right'` |
| `agg` | str | Agregação — `'sum'`, etc. (gera subtotais/totais) |
| `function` | callable | Função calculada por linha — `f(row) -> valor` |
| `footer` | bool | (em `body.table`) Exibe linha de total com a soma das colunas `agg` |
| `footer_label` | str | (em `body.table`) Rótulo da linha de total (default `'Total'`) |
| `after` | callable ou str | (em `body.table`) Texto impresso após a tabela — callable `f(instance) -> str` |

> Quando o campo na Entity tem `calc` (callable), o motor resolve
> automaticamente a `function` da coluna. `BOOL` formata como Sim/Não;
> `LIST` usa `options` para rótulo.

### Props de `body.table.hierarchy` (lista de níveis)

Cada elemento é um dict com **um** par `campo: config`. Define níveis
visuais de quebra (agrupamento) na tabela.

```python
'hierarchy': [
    {'indice': {'left': 1, 'pos': 2, 'text': '{indice}. {tipo}'}},
    {'indice': {'left': 2, 'pos': 1, 'text': '{indice} {nome}'}},
]
```

#### Config de cada nível

| Propriedade | Tipo | O que configura |
|---|---|---|
| `left` | int | N° de segmentos do código a agrupar/troncar (`'1.2.01'/2 → '1.2'`) e base da indentação visual |
| `label` | str | Rótulo do nível (auto-derivado do campo quando ausente) |
| `pos` | int | **`2` = título** — renderiza **fora da tabela**, como título (fecha a tabela anterior, imprime e abre a próxima); **`1` = linha** — renderiza **interno à tabela**, como uma linha de texto corrido na largura da tabela (a row que abre o nível é consumida, filhos entram como dados nas colunas); **`0` = oculto** — agrupa/totaliza sem imprimir |
| `text` | str | Formato do texto — `{campo}` resolve valor do registro; usado em `pos=2` (título) |
| `transform` | str | Transformação — `'upper'`, `'title'`, etc. |
| `eject` | bool | Força nova página ao abrir este nível |
| `total` | bool | Exibe total ao fechar o nível (quando `agg` está definido) |
| `bold` | bool | Negrito (default `True`) |

> **Fluxo de renderização:**
> - `pos=2` (título): **fora da tabela** — fecha a tabela anterior, imprime o
>   título e prepara os cabeçalhos de coluna para a próxima tabela.
> - `pos=1` (linha): **interno à tabela** — garante a tabela aberta (imprime os
>   cabeçalhos se necessário) e renderiza uma linha de texto corrido na largura
>   da tabela. A row que **abre** o nível é consumida como a própria linha e não
>   repete como dado; as rows seguintes (filhos) entram como dados nas colunas.
> - `pos=0` (oculto): detecta mudança de valor e totaliza, mas não imprime nada.

### Props de `footer`

| Propriedade | Tipo | O que configura |
|---|---|---|
| `show_user` | bool | Exibe o nome do usuário |
| `show_datetime` | bool | Exibe data/hora da impressão |
| `show_page_number` | bool | Exibe número da página |

### Impressão filtrada via escolha do usuário (`filter_select`)

Quando um relatório deve ser impresso com um **filtro escolhido pelo usuário**
(ex.: "só Receitas" ou "só Despesas"), o app usa o predicado `filter_select`:
o motor assume todo o fluxo (modal de escolha + aplicação do `WHERE`), sem rota
nova e sem configurar nada além do botão:

```python
from ajsystem.core.do_report import print_report, filter_select

'list': {
    'buttons': [
        {'label': 'Plano', 'icon': 'printer', 'color': 'info',
         'action': lambda _: print_report(PLANO, filter_select('tipo'))},
    ],
}
```

Fluxo (100% no motor):

1. `filter_select(campo)` referencia um **campo da Entity** (`tipo`). A action
   é chamada **a cada render** da lista; enquanto a request não tem valor para o
   campo, `print_report` devolve um **modal de escolha** (nunca o PDF — o template
   do botão fica limpo e permite reimprimir com outro critério).
2. As **options do `<select>` vêm da própria Entity** — do `options` do campo na
   Entity (ex. `TIPO_OPERACAO` = `{1: "Receitas", 2: "Despesas"}`); há um item
   "Todos" implícito (vazio). O modal contém um hidden `_r=<id>` (marcador
   interno, consumido uma única vez).
3. Ao escolher, o form faz GET para a mesma URL com `?_r=<id>&<campo>=<valor>`.
   O `do_list` detecta `_r`, consome o registro pendente e gera o **fragmento do
   PDF já filtrado**, que é injetado automaticamente no load (via `reportRender`)
   sobrepondo a lista — sem rota nova.
4. Aplicação do filtro: `WHERE campo = valor` é injetado no `source` do relatório
   **antes** da ordenação. Valor vazio/"Todos" = sem filtro (relatório completo).
5. "Voltar" no relatório fecha via `closeReport()` (sem recarregar e sem apagar
   o estado) e o botão continua devolvendo o modal, permitindo escolher de novo.

O marcador interno (`_r`) e o registro em memória são transparentes para o app;
o botão devolve sempre o modal e a tag do PDF embutido são gerados pelo motor.
Reutilizável em qualquer página: basta trocar o relatório e o campo na Entity.

> **Formatação centralizada** — `core/formats.py` é a fonte única (backend) de
> máscaras (exibição + parse, incluindo derivados `ddd`/`mmm`), número/moeda/
> percentual pt-BR, data/hora, transforms de texto e validadores CPF/CNPJ. Os
> módulos `defs.data`, `core.utils`, `core.form`, `defs.validators` e
> `defs.transformers` re-exportam dela (shims) — consumidores seguem importando
> de onde importavam. Espelho no cliente em `static/js/formats.js` (ver seção
> de JS abaixo): tokens e locais PT devem permanecer idênticos nos dois lados.
>
> ---
>
> ## 4. Globals e convenções

- Labels de menu e rótulos são derivados automaticamente do slug/nome quando não
  informados explicitamente.
- Campos definidos uma vez na `Entity` são reutilizados na lista, no form e nas
  sessões — sem redefinição.
