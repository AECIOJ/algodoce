# AGENTS.md — Contexto e Diretrizes AJSYSTEM

## 🚨 REGRAS DE SEGURANÇA E RESTRIÇÕES ABSOLUTAS (OBRIGATÓRIO SEGUIR)
1. **README E GIT (APENAS SOB DEMANDA EXPLICITA):** NUNCA altere o `README.md`, NUNCA faça commits e NUNCA faça push a menos que o usuário solicite EXPLICITAMENTE na mensagem atual.
2. **PROIBIDO ALTERAR O MOTOR SEM PERMISSÃO:** `ajsystem/` é o motor base. Se um pedido exigir um comportamento que o motor atual não suporta, NUNCA altere a pasta `ajsystem/` diretamente. **Proponha a alteração/evolução necessária no `ajsystem/` no texto e aguarde aprovação explícita** do usuário antes de implementar.
3. **PROIBIDO PROPS EXTRAS:** NUNCA invente, adicione ou altere propriedades (`props`) em campos, models ou schemas sem aprovação prévia explícita.
4. **ZERO TESTES AUTÔNOMOS:** NUNCA crie scripts de teste ou execute validações sem solicitação direta. Sempre entregue apenas o código e sugira que o usuário faça os testes e aprove.

## 1. Padrão Arquitetural
- Framework Flask declarativo. Dicionários `Entity`/`Schema`/`Page` montam Blueprints, rotas, telas e menu.
- `app/` é o código do hospedeiro (`app/models/`, `app/routes/sys/`, `app/config.py`).
- `ajsystem/` é o motor base.
- `Model` (`app/models/*.py` + `Entity`) -> Dados.
- `Schema` (`app/routes/sys/*.py`) -> Overrides por página (`Entity ∪ Schema`).
- `Page` (`app/routes/sys/*.py`) -> Tipo e layout da página (`crud`, `redirect`, `cart`, `showcase`, `contacts`, `custom`).

## 2. Regras Estritas do Framework
1. **Posição e Visibilidade:** Pertencem à `Page` (slots do form: `bar`, `footer`, `body`, `hidden`; slots de lista: `line`, `card`, `hidden`), NUNCA ao `Field` nem ao `Schema`.
2. **Campos Virtuais/Calc:** Se um campo for `property` do Model ou expressão agregada (`agg`), ele NUNCA pode ser persistido. Deve usar `calc` virtual (`lambda row:` ou `string`) ou ser de memória.
3. **Moeda:** Não existe prop `currency` em `Field`. O formato de moeda sai da `mask` (`@M(BRL)` ou `MVALOR`).
4. **Bloco MEMORY:** Chaves em MAIÚSCULAS no `Schema` representam grupos de memória (`memory=True` automático).
5. **Git e Documentação:** Apenas quando solicitado explicitamente, atualize o `README.md` com as novas implementações, execute o commit descritivo e faça o push para o repositório.

## 3. Diretrizes de Resposta (Modo Caveman / Economia de Tokens)
- Sem cumprimentos, saudações ou explicações teóricas óbvias.
- Respostas ultra diretas: entregue o código funcional imediatamente.
- Explicações apenas se estritamente necessárias e em tópicos curtos de 1 linha.
- Respeite a estrutura:
  * Models em `app/models/`
  * Rotas em `app/routes/sys/`
  * Menus em `app/config.py`

## 4. Padrões de UI/UX (Tailwind & DaisyUI)
- Use utilitários nativos do Tailwind CSS e componentes DaisyUI configurados no projeto.
- Mantenha formulários e tabelas limpos, responsivos e otimizados para desktop e mobile.