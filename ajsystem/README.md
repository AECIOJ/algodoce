# AJSYSTEM v1.25.3-1 — Manual do Framework

> Documentação vinculada ao código em `app/config.py:APP['version']` (`v1.25.3-1`). Atualize a versão a cada release para evitar descompasso.

---

## 1. Introdução e Conceitos Básicos

1. **Propósito.** Framework Flask declarativo para apps de gestão. Você descreve dados e telas. O framework monta rotas, telas e menu.
2. **Problemas que resolve.**
   1. Elimina boilerplate de CRUD (lista, formulário, filtros).
   2. Centraliza definição de campos (`Entity`).
   3. Permite customização por página via `Schema` sem duplicar código.
   4. Gera relatórios PDF e validações com a mesma fonte.
3. **Conceitos centrais.**
   1. `Entity` — dicionário base de campos no `model` (única fonte).
   2. `Schema` — dicionário de overrides por página na `route` (`Entity ∪ Schema`).
   3. `Page` — tipo de página (`crud`, `custom`, `showcase`, `cart`, `contacts`).
   4. `Field` — `type`, `label`, `width`, `pos_form/pos_list/pos_filter`, `tag`, `calc`, `lookup`.
4. **Pré-requisitos de linguagem.**
   1. Python 3.11+.
   2. Python básico: `dict`, `class`, `lambda`, `decorator`.
   3. Flask básico: `Blueprint`, `request`, `url_for`.
   4. SQLAlchemy básico: `db.Model`, `db.Column`, `relationship`.
   5. Jinja2 básico: `{{ }}`, `{% %}`.

---

## 2. Guia de Instalação (Getting Started)

1. Clone o repositório.
   ```bash
   git clone <repo> && cd algodoce
   ```
2. Crie ambiente Python.
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   ```
3. Instale dependências Python.
   ```bash
   pip install -r requirements.txt  # Flask==3.0.0, Flask-SQLAlchemy==3.1.1, psycopg2-binary==2.9.9, fpdf2==2.8.7
   ```
4. Instale dependências CSS.
   ```bash
   npm install  # tailwindcss + daisyUI
   npm run build:css  # gera tailwind.daisyui.json a partir de app/config.py
   ```
5. Configure ambiente.
   ```bash
   cp .env.example .env  # ajuste DATABASE_URL, SECRET_KEY
   ```
6. Suba o banco.
   ```bash
   docker compose up -d db  # ou use Postgres local
   flask db upgrade
   ```
7. Rode o app.
   ```bash
   flask run  # http://localhost:5000/categorias
   ```
8. Crie o primeiro CRUD.
   1. `app/models/tarefa.py` — crie `class Tarefa(db.Model)` + `Entity`.
   2. `app/routes/sys/tarefas.py` — crie `Schema = {}` + `Page = {'type':'crud','props':{'list':{'columns':'Tarefa'},'form':{'fields':'Tarefa'}}}`.
   3. `app/config.py` — adicione `'Tarefas': {'icon':'bi-check'}` em `SYS.menus.Cadastro.submenus`.
   4. Reinicie: `GET /tarefas/`, `/tarefas/novo`, `/tarefas/<id>/editar`.

---

## 3. Arquitetura e Padrões

1. **Padrão principal: Declarativo sobre MVC.**
   1. `Model` (`app/models/*.py`) define dados + `Entity`.
   2. `View` (`ajsystem/templates/pages/*.html` + `components/form_macros.html`) renderiza a partir de `Field`.
   3. `Controller` (`ajsystem/core/auto.py` + `do_list.py` + `do_form.py`) monta `Blueprint` a partir de `Page`/`Schema`.
2. **Injeção via registro.**
   1. `app/__init__.py:register_model('pedido',Pedido)` → `ajsystem/defs/data.py:MODEL_MAP`.
   2. `ajsystem/defs/data.py:resolve_entity_fields(schema, model, entity)` faz `Entity ∪ Schema` (Schema vence).
3. **Fluxo de resolução.**
   ```
   config.py:menus → auto.py:registrar_modulos → Page/Schema → resolve_entity_fields → Field → form/list/report
   ```
4. **Diagrama visual: camadas.**
   ```
   ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
   │  app/models │────▶│ ajsystem/defs│────▶│ ajsystem/core│
   │  Entity     │     │ Field/Schema │     │ do_list/form │
   └─────────────┘     └──────────────┘     └──────┬───────┘
          ▲                    ▲                    │
          │                    │                    ▼
   app/routes/sys/Page+Schema──┘            ┌──────────────┐
                                            │  templates   │
                                            │ form/list/pdf│
                                            └──────────────┘
   ```
5. **Diagrama: merge de campos.**
   ```
   Entity (model) ──┐
                    ├─► {**Entity, **Schema} ──► Field ──► column/form/report
   Schema (route) ──┘          (Schema vence)
   ```
6. **Diagrama: ciclo de form.**
   ```
   GET /novo ──▶ Page.fields='Entidade' ──▶ resolve_column_configs ──▶ render_fields
       ▲                                                              │
       └──────── POST ──▶ _coerce ──▶ calc(agg/call) ──▶ db.commit ──┘
   ```

---

## 4. Exemplos Práticos (Snippets)

1. **Model + Entity mínima.**
   ```python
   # app/models/tarefa.py
   class Tarefa(db.Model):
       id = db.Column(db.Integer, primary_key=True)
       titulo = db.Column(db.String(100), nullable=False)
       feito = db.Column(db.Boolean, default=False)
   Entity = {
       'id': {'type':'ID'},
       'titulo': {'type':'TEXT','required':True,'width':20},
       'feito': {'type':'BOOL'},
   }
   ```

2. **Schema override (exclusivamente via Schema).**
   ```python
   # app/routes/sys/tarefas.py
   from ajsystem.defs.constants import POS_EXPLICIT_NOT_EMPTY
   Schema = {
       'Tarefa': {
           'feito': {'tag': {'colors':{True:'success',False:'ghost'}}},
           'titulo': {'pos_list':1},
       }
   }
   ```

3. **Page CRUD com sessão filha.**
   ```python
   Page = {
       'type':'crud',
       'props':{
           'list':{'columns':'Tarefa','order':['titulo']},
           'form':{
               'fields':'Tarefa',
               'sessions':{
                   'Itens':{'table':{'columns':['TarefaItem'],'totals':['qtd']}},
                   'Financeiro':{'fields':['total','carteira_id']}  # pos_form:0 explícito só quando valor<>null via POS_EXPLICIT_NOT_EMPTY no Schema
               }
           }
       }
   }
   ```

4. **Campo calculado e tag com link dinâmico.**
   ```python
   # Entity
   'transacao_id': {'type':'INT','label':'Transação','calc':lambda row: row.transacao_id}
   # Schema (pos_form dict com when)
   'transacao_id': {'pos_form':POS_EXPLICIT_NOT_EMPTY,'pos_list':0,'tag':{'link':'receber.form','color':'info'}}
   # total
   'total': {'type':'NUM','calc':'valor + acrescimo - desconto','pos_form':0}
   ```

5. **Menu.**
   ```python
   # app/config.py
   SYS = {'menus':{'Cadastro':{'icon':'bi-journal','submenus':{'Tarefas':{'icon':'bi-check'}}}}}
   ```

6. **Relatório PDF.**
   ```python
   # app/reports/tarefas.py
   REL = {'label':'Tarefas','body':{'source':'Tarefa','table':{'columns':{'titulo':{'width':50},'feito':{'width':10}}}}}
   # botão
   {'label':'Imprimir','action':lambda _: print_report(REL, filter_select('feito'))}
   ```

7. **Pos condicional.**
   ```python
   # pos_form dict (novo) – só form, só quando valor não vazio
   'pedido_id': {'pos_form':{'pos':0,'when':{'not_empty':True}},'tag':{'link':'pedidos.form'}}
   ```

---

## 5. Referência de API

1. **Defs: `ajsystem/defs/data.py`**
   1. `class Field(name, type, label, width, pos_form, pos_list, pos_filter, tag, calc, lookup, ...)` — `pos_form` aceita `int` ou `dict{pos,when}`; `_pos_form_when` interno.
   2. `FIELD_TYPES: dict` — `TEXT, MEMO, INT, NUM, ID, DK, FK, LIST, BOOL, DATA, IMAGE, MULT10`.
   3. `build_field(name,cfg) -> Field` — aplica `FIELD_TYPES` + `mask→decimals`.
   4. `resolve_entity_fields(schema, model, entity) -> dict` — merge `Entity ∪ Schema`.
   5. `resolve_lookup(field, model) -> dict` — resolve `lookup` FK.

2. **Defs: `ajsystem/defs/constants.py`**
   1. `CURRENCY: dict` — `0:None, 1:R$ pt-BR`.
   2. `POS_EXPLICIT_NOT_EMPTY = {'pos':0,'when':{'not_empty':True}}` — `pos:0` explícito só quando valor não vazio (form).

3. **Defs: `ajsystem/defs/tags.py`**
   1. `class Tag(link, color, colors, size)` — `badge_cls(color)`, `resolve_link(instance)`.
   2. `parse_tag(spec)`, `resolve_tag(spec,value,options,instance)`.

4. **Defs: `ajsystem/defs/report.py`**
   1. `class Report(label, header, body, footer, page_size)` — `parse_report(spec)`.
   2. `class ReportColumn(field,label,width,agg,function)`.

5. **Core: `ajsystem/core/auto.py`**
   1. `registrar_modulos(app, menu)` — monta `Blueprint` por `Page`.
   2. `montar_blueprint(mod, slug)` — gera `list/form/delete/toggle` (`list:GET /`, `form:GET/POST /novo e /<id>/editar`).
   3. `rota(path, endpoint)` — decorator para rotas custom (`orcamentos.aprovar`).

6. **Core: `ajsystem/core/do_form.py` / `do_list.py` / `do_report.py`**
   1. `do_form(form, id, extra_ctx)` — respeita `pos_form`, `calc`, `tag`, `POS_EXPLICIT_NOT_EMPTY`.
   2. `do_list(entity, mod)` — respeita `pos_list`, `pos_filter==9` (`fixed_filters`).
   3. `print_report(report, instance, filter_select)` — `Entity∪Schema` para colunas.

7. **Templates: `ajsystem/templates/components/form_macros.html`**
   1. `render_field(field, data)` — `field.tag` → `tag-pill` (`width: field.width+3 ch`, `border-radius:9999px`).
   2. `render_fields(fields, data)` — filtra via `field.is_visible_by_pos(fv, data, is_explicit)`.

8. **JS: `ajsystem/static/js/formats.js`**
   1. `parseNum(v)` — aceita `R$ 1.234,56` → `1234.56`.
   2. `itEval(expr, vars)` — avalia `valor + acrescimo - desconto`, `divide(a,b)`.
   3. `formCalcRefresh()` — atualiza `input.aj-calc[data-calc]`.

9. **Configuração: `app/config.py`**
   1. `APP['version']` — vincule docs a `git tag` (ex: `v1.25.3-1`).
   2. `APP['modules'] = [SITE, SYS, ADMIN]` — `menus` com `icon`, `page`, `submenus`.
   3. `Temas['algodoce']` — `marca/neutras/feedback/barras` → `npm run build:css`.

> **Versionamento:** toda mudança em `Field`/`Schema`/`Page` exige bump em `APP['version']` e neste README. Histórico anterior em `README.old`.
