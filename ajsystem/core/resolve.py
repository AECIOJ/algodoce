"""RESOLVE — máquina genérica de camadas de fields (RL/RQ/RS/RE).

Cada dataclass (list/form/report) orquestra a sua rotina de resolução; as
etapas são funções genéricas deste módulo, reutilizadas entre rotinas para
evitar a repetição de merge/validação (`{**a, **b}` ad hoc) espalhada.

Nomenclatura das rotinas (ex.: list):
  - `RL` — monta a lista `L` de fields (parse de `columns`/`fields` → nomes
    ordenados; o build do `Field` fica em `core.list.resolve_column_configs`);
  - `RQ` — camada de uma fonte `query` sobre `L` (`query_select_layer`);
  - `RS`/`RE` — camadas Schema/Entity (e `card`) sobre `L` (`apply_field_layers`).

`apply_field_layers` aplica camadas em **fill-gap**: quem declara primeiro
vence; as camadas seguintes só acrescem props ainda não declaradas. A ordem é
informada pelo chamador — ex.: `[Schema, layer, Entity]` = Schema vence nos
conflitos, equivalente exato ao `{**Entity, **layer, **Schema}` atual (prova:
a projeção por chave é idêntica, pois todo conflito é decidido pela camada mais
alta que declara a chave, em qualquer um dos dois modelos).

O report não usa `apply_field_layers` — o merge dele é *overlay* (a camada mais
alta é a última a ser aplicada: Entity/Schema < select < inline do relatório) e
lida `format`, prop que a listagem não tem. O que ele toma emprestado da máquina
são as primitivas da fonte `select` (`select_entry_props`/
`select_entry_computed`), compartilhadas com `query_select_layer`: o que era
`_disp_map`/`_computed` reimplementados à mão em `do_report`.
"""
from ajsystem.defs.data import validate_field_config

# Props de apresentação que uma entrada de `select` pode declarar sobre a
# Entity. `format` fica de fora porque é prop do report e não da listagem —
# quem precisa dele passa a chave (ver `select_entry_props`).
SELECT_PROPS = ('label', 'width', 'align')


def select_entry_props(entry, keys=SELECT_PROPS):
    """Props declaradas por uma entrada do select (`label`/`width`/`align`).

    Sai só o que a entrada declara: entrada sem a prop não gera a chave.
    `keys` deixa o report pedir também o `format`, que a listagem não tem.
    """
    props = {}
    for k in keys:
        v = getattr(entry, k, None)
        if v is not None:
            props[k] = v
    return props


def select_entry_computed(entry):
    """A entrada traz o valor pronto da query (`over`/`agg`/`calc`)?"""
    return entry.over is not None or bool(entry.agg) or bool(entry.calc)


# ── o que é um item que enumera field ────────────────────────────────────────
# Toda prop que elenca fields (list.columns, form.fields, report.columns, os
# FIELDS do report, o select de uma query) tem que responder a mesma pergunta
# sobre cada item: qual é o NOME do field e quais são os OVERRIDES. A resposta
# estava escrita em três lugares com subconjuntos diferentes de formas aceitas;
# aqui é uma só, e cada chamador decide a POLÍTICA (aceitar, recusar ou manter
# o item como está).
def field_spec_item(item):
    """`(nome, overrides)` de um item que enumera field, ou `None`.

    Formas aceitas (as de `list.columns`):
        'campo'                       → ('campo', {})
        ('campo', {props})            → ('campo', props)
        {alias: {props}}              → (alias, props)
        {'field': 'campo', **props}   → ('campo', props)
        {'name': 'campo', **props}    → ('campo', props)

    `None` = o item não nomeia um field (dict de props sem nome, por exemplo).
    O chamador decide o que fazer: o report guarda como `_0`, `_1`…; `FIELDS`
    recusa; `parse_select` só conhece as duas primeiras formas.
    """
    if isinstance(item, str):
        return item, {}
    if isinstance(item, tuple) and len(item) == 2 \
            and isinstance(item[0], str) and isinstance(item[1], dict):
        return item[0], dict(item[1])
    if isinstance(item, dict):
        nome = item.get('field') or item.get('name')
        if isinstance(nome, str) and nome:
            return nome, {k: v for k, v in item.items() if k not in ('field', 'name')}
        if len(item) == 1:
            (alias, cfg), = item.items()
            if isinstance(alias, str) and alias:
                return alias, dict(cfg) if isinstance(cfg, dict) else {}
    return None


def field_spec_items(spec):
    """Normaliza um spec que enumera fields em `{nome: overrides}`.

    Aceita a lista de itens ou o dict `{nome: overrides}`. Item que não nomeia
    um field cai em `_0`, `_1`… — a forma legada do report, em que um dict de
    props sem nome ainda é um campo e o nome é a posição. Quem não quer essa
    forma usa `field_spec_item` e decide por conta (é o que o report faz nos
    itens de layout).
    """
    out = {}
    if isinstance(spec, dict):
        for nome, cfg in spec.items():
            out[nome] = dict(cfg) if isinstance(cfg, dict) else {}
        return out
    if not isinstance(spec, (list, tuple)):
        return out
    for i, item in enumerate(spec):
        achado = field_spec_item(item)
        out[achado[0] if achado else '_%d' % i] = achado[1] if achado else dict(item)
    return out


def field_options(cfg):
    """Catálogo de rótulos de um campo `LIST`/`MULT10` (`options`), ou `{}`.

    Aceita as duas chaves que a Entity usa — `list` e `options` — e dá a
    precedência de `build_field_config` (`list` sobrescreve `options`). Ler isso
    à mão estava em seis pontos do report, um deles com a ordem invertida.
    """
    cfg = cfg or {}
    return cfg.get('list') or cfg.get('options') or {}


def field_display_fn(cfg, name, i18n=None):
    """`function(row)` que traduz o valor bruto de um field para exibição.

    `LIST` vira o rótulo do catálogo (código fora do catálogo cai no valor
    cru, como a listagem) e `BOOL` vira Sim/Não. `None` quando o field não é
    nenhum dos dois — quem chama aí não precisa traduzir nada.

    Um único passo, antes escrito inline só dentro de `_resolve_map`: as
    colunas do report traduziam e os itens de layout (`FIELDS`) imprimiam o
    código, porque passavam por `_field_item`, que não conhecia o catálogo.
    """
    cfg = cfg or {}
    tipo = cfg.get('type')
    if tipo == 'LIST':
        opts = field_options(cfg)
        if opts:
            return lambda row, f=name, o=opts: o.get(getattr(row, f, None),
                                                     getattr(row, f, ''))
    elif tipo == 'BOOL' and i18n is not None:
        return lambda row, f=name: (
            i18n.FILTER_YES if getattr(row, f, None) else i18n.NO)
    return None


# ── apresentação inferida de um campo (a decisão, não o texto final) ─────────
# Um único lugar decide o que a cfg de um campo significa para exibição. Antes
# isso estava escrito duas vezes com o mesmo encadeamento: `do_report`
# (`_infer_presentation`, que produz `format`/`align`) e `search` (`_fmt_cell`,
# que formata o valor). Divergir entre os dois era só questão de tempo.
def field_presentation(cfg):
    """`(format, align)` inferidos da cfg de um campo, ou `None` se não houver.

    A ordem é a precedência de exibição do motor: a `mask` manda (moeda via
    `@M(id)`, alinhado à direita), depois o `type`/`input` do campo, e o tipo
    semalignamento próprio fica sem `format` (o chamador decide o texto).
    """
    from ajsystem.core.formats import mask_money_id
    from ajsystem.core.utils import normalize_currency
    cfg = cfg or {}
    cur = mask_money_id(cfg.get('mask'))
    if cur:
        return normalize_currency(cur), 'right'
    t, inp = cfg.get('type'), cfg.get('input')
    if t == 'NUM':
        return 'brl', 'right'
    if t == 'DATA' or inp == 'date':
        return 'datetime', 'right'
    if t == 'INT':
        return None, 'center'
    return None, None


def apply_field_layers(field_names, layers):
    """RS/RE — preenche props de `field_names` por camadas (fill-gap + validação).

    `layers` = sequência `(cfg_por_campo, rótulo)` na ordem de precedência
    (a primeira declara e vence). `cfg_por_campo` pode ser callable
    `field -> props` (p/ camadas inferidas). Cada camada acrescenta somente as
    props ainda não declaradas — quem declara primeiro não é sobrescrito.
    Valida cada config contra o dataclass `Field`. Devolve `{campo: cfg}`
    preservando a ordem de `field_names`.
    """
    out = {}
    for name in field_names:
        acc = {}
        for layer, rotulo in layers:
            if callable(layer):
                cfg = layer(name)
            else:
                cfg = (layer or {}).get(name)
            if not isinstance(cfg, dict):
                continue
            validate_field_config(cfg, rotulo, name)
            for k, v in cfg.items():
                if k not in acc:
                    acc[k] = v
        out[name] = acc
    return out


def query_select_layer(entries, base_merged, schema_entity):
    """RQ — camada de uma fonte `query` (select do qspec) sobre os fields.

    Sobreposição autoritativa sobre o base já resolvido (Entity/Schema/Entity):
      - entrada computada (`over`/`agg`/`calc`) remove o `calc` herdado do base
        — o valor passa a vir da query;
      - props explícitas da entrada (`label`/`width`/`align`) sobrescrevem;
      - campo novo → cfg mínimo (`TEXT`) com o `pos_list` da entrada;
      - `pos_list: 0` da entrada força 0 no base, salvo override do Schema.

    Regras idênticas ao fluxo original da listagem (do_list), extraídas para
    serem reutilizáveis (ex.: report, que também lê fontes qspec).
    """
    out = dict(base_merged)
    for e in entries:
        if e.name in out and select_entry_computed(e):
            out[e.name] = {k: v for k, v in out[e.name].items() if k != 'calc'}
        props = select_entry_props(e)
        if e.name not in out:
            cfg = {'type': 'TEXT', 'pos_list': e.pos_list, **props}
            cfg.setdefault('label', e.name)
            out[e.name] = cfg
        else:
            base = out[e.name]
            if e.pos_list == 0 and 'pos_list' not in schema_entity:
                base = {**base, 'pos_list': 0}
            out[e.name] = {**base, **props}
    return out