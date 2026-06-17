# Layout do Sistema

## Topo (fixo em todas as paginas)

- Imagem do logo centralizada horizontalmente
- Abaixo, menu horizontal com fundo rosa e links em branco: Cadastro, Comercial, Sair
- Abaixo do menu, submenu horizontal que aparece conforme a secao:
  - Cadastro: links Categorias, Ingredientes, Produtos, Contas
  - Comercial: links Orcamentos, Pedidos, Compras
- No mobile, o submenu vira um select (dropdown) com os links, e um espaco para botoes de acao à direita.
  - O select de submenu tem `font-size: 1rem` (menor que o padrao) para economizar espaco.
  - Os botoes de acao usam `btn-sm` e o filtro (quando ha apenas um) fica na mesma linha, entre o select de submenu e o botao.
  - O espacamento interno do select de submenu usa o padding padrao do `.form-select` para que a seta do dropdown nao sobreponha o texto.

## Paginas de Listagem

- Abaixo do topo, aparece o titulo da pagina (h2) com o nome da entidade (ex: "Categorias", "Produtos")
  - Desktop: titulo + filtros + botao "Novo" — tudo centralizado horizontalmente na mesma linha.
  - Mobile: o titulo some. O select de submenu, o filtro (quando ha apenas um) e o botao "Novo" ficam todos na mesma linha no toolbar do submenu.
  - Mobile (multiplos filtros): quando ha dois ou mais filtros, eles aparecem em uma linha separada abaixo do toolbar, centralizados horizontalmente.
  - Essa linha (titulo + filtros + Novo) fica sempre visivel — nao rola junto com a tabela.
- Abaixo, uma tabela que ocupa todo o espaco restante da tela ate o fim
  - O cabecalho da tabela (thead) fica fixo e nunca desaparece ao rolar as linhas
  - A rolagem vertical acontece SOMENTE dentro da area da tabela — a pagina do navegador em si nao tem scroll. Toda a tela é ocupada pelo topo + linha de titulo + tabela, sem sobras.
- Implementacao tecnica:
  - `<html>` recebe classe `list-page` nas paginas de listagem (via template `{% if request.endpoint.endswith('.list') %}`)
  - CSS usa flexbox no `<body>` com `height: 100%; overflow: hidden`
  - `<main>` com `flex: 1; display: flex; flex-direction: column` — preenche automaticamente o espaco restante entre o topo fixo e o fim da tela
  - `.table-scroll` com `flex: 1; overflow-y: auto` — preenche o espaco dentro do `<main>` e faz scroll interno
  - Funciona igual em desktop e mobile (CSS puro, sem calculos JS de altura)

## Paginas de Edicao

O panel de edicao tem ate 3 linhas, dependendo do contexto:

### Desktop
1. **Linha de submenu** (se houver): links horizontais da secao (ex: Categorias, Ingredientes, Produtos, Contas).
2. **Linha de navegacao** (form_nav): `[Voltar]` alinhado à esquerda / navegador centralizado / `[botoes de edicao]` à direita.
   - Navegador: `[Primeiro][Anterior]` **item #X** (editavel ao clicar) `[Proximo][Ultimo]`
   - Botoes de edicao: status (select) e acoes (excluir, cancelar, converter).
3. **Linha de edicao**: a primeira linha de campos do formulario (row) gruda abaixo do form_nav.

### Mobile
1. **Linha de navegacao** (form_nav): `[Voltar]` alinhado à esquerda / navegador centralizado / `[botoes de edicao]` à direita.
   - Navegador: botoes Primeiro/Ultimo escondidos, botoes Anterior/Proximo com icones de 18px, titulo limitado a 130px com "..." no final.
   - Fundo branco com cantos arredondados.
2. **Linha de edicao**: o primeiro campo da primeira linha gruda abaixo do form_nav, ocupando toda a largura (com 1 ou mais campos que couberem).

### Comportamento
- As 2 ou 3 linhas ficam sempre visiveis ao rolar — nao somem.
- Os campos fixos tem fundo igual ao fundo da pagina para nao mostrar conteudo atras.
- O formulario rola normalmente abaixo das linhas fixas.
