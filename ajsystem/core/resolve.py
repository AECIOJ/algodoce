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
        found = field_spec_item(item)
        out[found[0] if found else '_%d' % i] = found[1] if found else dict(item)
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


def query_select_layer(entries, base_merged):
    """RQ — camada de uma fonte `query` (select do qspec) sobre os fields.

    Sobreposição autoritativa sobre o base já resolvido (Entity/Schema):
      - entrada computada (`over`/`agg`/`calc`) remove o `calc` herdado do base
        — o valor passa a vir da query;
      - props explícitas da entrada (`label`/`width`/`align`) sobrescrevem;
      - campo novo → cfg mínimo (`TEXT`).

    A entrada **não** posiciona campo: quem diz se algo é coluna, card ou
    oculto é a página, nos slots `line`/`card`/`hidden` (`resolve_slots`).
    Regra idêntica à da listagem, extraída para ser reutilizada (ex.: report,
    que também lê fontes qspec).
    """
    out = dict(base_merged)
    for e in entries:
        if e.name in out and select_entry_computed(e):
            out[e.name] = {k: v for k, v in out[e.name].items() if k != 'calc'}
        props = select_entry_props(e)
        if e.name not in out:
            cfg = {'type': 'TEXT', **props}
            cfg.setdefault('label', e.name)
            out[e.name] = cfg
        else:
            out[e.name] = {**out[e.name], **props}
    return out


# ── slots: onde cada field vai em cada superfície ────────────────────────────
# Onde um field aparece é uma afirmação da TELA, não do field: a pergunta
# "esse campo é coluna aqui?" só tem resposta no lugar onde a tela é montada.
# Por isso `Field.pos_list` (inteiro mágico espalhado em Entity e Schema) e
# `Field.pos_form` (o mesmo, mais o predicado de escrita do save) deram lugar a
# slots nomeados, declarados na PÁGINA e resolvidos aqui — um só lugar para a
# listagem, o form e as sessões de tabela.
#
# Cada superfície tem o seu conjunto de slots, porque tem as suas perguntas: a
# barra de uma sessão de tabela não é a barra do form. `default` é o slot de
# quem não é citado em nenhum.
#
# `precedence` resolve o campo citado em mais de um slot. `hidden` é sempre o
# mais forte (o campo não existe para a tela) e `default` o mais fraco.
SURFACES = {
    'list':   {'slots': ('line', 'card', 'hidden'), 'default': 'line',
               'precedence': ('hidden', 'line', 'card')},
    # `body` e slot E default: citar um campo nele e o que dispensa a regra de
    # motor da chave primaria (ver `apply_positions`), porque ai a declaracao
    # existe e ganha.
    'form':   {'slots': ('bar', 'footer', 'body', 'hidden'), 'default': 'body',
               'precedence': ('hidden', 'bar', 'footer', 'body')},
    # `body` existe como slot citável (embora seja o default) para a sessão
    # poder MOSTRAR um campo que a regra de motor esconderia — ex.: a chave do
    # filho, `body: ['id']`, como a Previsão id fazia.
    'sessao': {'slots': ('body', 'hidden'), 'default': 'body',
               'precedence': ('hidden', 'body')},
}

_SLOT_LABELS = {
    'line': 'coluna da linha', 'card': 'card',
    'bar': 'barra do form', 'footer': 'rodapé do form', 'hidden': 'oculto',
    'visible': 'visibilidade condicional',
}


def surface(surface_name):
    """Definição de uma superfície (`slots`/`default`/`precedence`), fail-fast."""
    try:
        return SURFACES[surface_name]
    except KeyError:
        raise ValueError(
            f"superfície {surface_name!r} desconhecida — "
            f"conhecidas: {', '.join(sorted(SURFACES))}") from None


def slot_spec_items(spec, slot, where='list'):
    """Nomes citados por um slot, normalizados em `[(entidade|None, campo)]`.

    Aceita a família de `columns` (`normalize_fieldspec`/`field_spec_item`):
      - `'Entidade'` → todos os campos da entidade;
      - `'campo'` → um campo (sem nome de entidade);
      - `'Entidade.campo'` → um campo qualificado;
      - `['campo', 'Entidade.campo']` → os dois;
      - `{'Entidade': ['campo', ...]}` → agrupado por entidade;
      - `{'Entidade': '*'}` → todos os campos da entidade.

    Props inline (`('campo', {props})`, `{alias: {props}}`) são aceitas e
    **descartadas**: o slot afirma posição, não apresentação — `label`/`width`/
    `align`/`mask` continuam morando em Entity/Schema.
    """
    if spec is None or spec is False:
        return []
    if spec is True:
        raise ValueError(f"{where}.{slot}: `True` não nomeia campo — use 'Entidade'")
    if isinstance(spec, str):
        return [(None, spec)]
    if isinstance(spec, dict):
        out = []
        for ent, names in spec.items():
            if names is True or names == '*':
                out.append((ent, '*'))
            elif isinstance(names, str):
                out.append((ent, names))
            elif isinstance(names, (list, tuple)):
                for n in names:
                    found = field_spec_item(n)
                    if found is None:
                        raise ValueError(
                            f"{where}.{slot}: item {n!r} não nomeia campo")
                    out.append((ent, found[0]))
            else:
                raise ValueError(
                    f"{where}.{slot}: entidade {ent!r} com valor {names!r} — "
                    "esperado '*' ou lista de nomes")
        return out
    if isinstance(spec, (list, tuple)):
        out = []
        for item in spec:
            found = field_spec_item(item)
            if found is None:
                raise ValueError(f"{where}.{slot}: item {item!r} não nomeia campo")
            name = found[0]
            if '.' in name:
                ent, _, campo = name.partition('.')
                out.append((ent, campo))
            else:
                out.append((None, name))
        return out
    raise TypeError(
        f"{where}.{slot}: esperava 'Entidade', lista ou dict; veio "
        f"{type(spec).__name__}")


def _pool_entities(pool):
    """Entidades presentes no pool, na ordem de aparição."""
    out = []
    for f in pool:
        ent = getattr(f, '_entity', None)
        if ent and ent not in out:
            out.append(ent)
    return out


def _slot_match(pool, entities, ent, name, slot, principal, where='list',
                missing_ok=False):
    """Field(s) do pool que um item de slot nomeia.

    Leitura de um nome **cru**, na ordem:

      1. `'Entidade'` → expande os campos dela (é o atalho de `card`);
      2. único na entidade de `columns` → é esse. É o caso comum: o autor
         está olhando o assunto da lista;
      3. único no **pool** → é esse, seja de onde vier. Com `master` as duas
         pontas entram no pool, então `hidden: ['previsao_id']` acha o campo
         do filho sem o autor ter que saber qual entidade é a dele;
      4. ambíguo → a entidade de `columns` decide; sem ela (lista de campos,
         fonte `query`) é **erro** nomeando as candidatas.

    `'Entidade.campo'` sempre qualifica, e é o que desambigua na mão.

    `missing_ok`: um nome/entidade **ausente** devolve `[]` em vez de levantar
    (usado por `fixed`, cujas folhas podem ser coluna crua do model — não um
    field do pool). Nome **ambíguo** continua levantando.
    """
    def _err(msg):
        return ValueError(f"{where}.{slot} ({_SLOT_LABELS.get(slot, slot)}): {msg}")

    if name == '*':
        if not ent:
            raise _err("'*' precisa de uma entidade: "
                       f"{{'Entidade': '*'}}, não um nome solto")
        return [f for f in pool if getattr(f, '_entity', None) == ent]
    if ent:
        if ent not in entities:
            if missing_ok:
                return []
            raise _err(f"entidade {ent!r} não está na listagem ("
                       f"{', '.join(entities) or '—'})")
        hits = [f for f in pool if getattr(f, '_entity', None) == ent
                and f.name == name]
        if not hits:
            if missing_ok:
                return []
            raise _err(f"campo {ent}.{name!r} não está na listagem")
        return hits
    if name in entities:
        return [f for f in pool if getattr(f, '_entity', None) == name]
    hits = [f for f in pool if f.name == name]
    if len(hits) == 1:
        return hits
    if not hits:
        if missing_ok:
            return []
        onde = (f' em {principal}' if principal else '')
        raise _err(f"campo {name!r} não está na listagem{onde} "
                   f"(entidades: {', '.join(entities) or '—'})")
    # Ambíguo: o assunto da lista desempata; sem assunto declarado, o autor
    # qualifica — devolver um dos dois em silêncio seria chute.
    if principal:
        do_assunto = [f for f in hits if getattr(f, '_entity', None) == principal]
        if len(do_assunto) == 1:
            return do_assunto
    onde = ' em ' + ' e '.join(sorted({getattr(f, '_entity', None) or '?' for f in hits}))
    raise _err(f"campo {name!r} é ambíguo{onde} — "
               f"qualifique com 'Entidade.campo'")


def resolve_slots(spec, pool, principal=None, surface_name='list'):
    """Posiciona os fields do `pool` nos slots declarados por uma superfície.

    `spec` é a spec de slots (`Page.props.list`, `Page.props.form.positions`,
    ou a chave `hidden` da sessão). `surface_name` diz quais slots aquela tela
    tem e quem vence quando um campo é citado duas vezes.

    Devolve `{slot: [Field]}` para cada slot da superfície mais `'pinned'`
    (só na listagem: os campos declarados em `line`, que o cliente não tira
    quando a tela estreita). Cada lista sai na ordem do pool, e o campo não
    citado em nenhum slot vai para o `default` da superfície.

    `principal` é a entidade que um nome cru resolve — desempata quando duas
    entidades da tela têm o mesmo campo. É contra o `pool` (cada field com
    `_entity`) que todo nome é validado, sempre nomeando o erro.

    Cada field recebe `f._slot`, que é o que o render e o save leem: a
    posição deixou de ser um inteiro no dataclass e passou a ser um atributo
    posto aqui, pela página que conhece a tela.
    """
    cfg = surface(surface_name)
    pool = list(pool or [])
    entities = _pool_entities(pool)
    where = surface_name
    claimed = {}
    for slot in cfg['precedence']:
        if slot == 'default':
            continue
        for ent, name in slot_spec_items((spec or {}).get(slot), slot, where):
            for f in _slot_match(pool, entities, ent, name, slot, principal, where):
                claimed.setdefault(id(f), slot)
    out = {slot: [] for slot in dict.fromkeys(cfg['slots'] + (cfg['default'],))}
    out['pinned'] = []
    out['claimed'] = dict(claimed)
    for f in pool:
        slot = claimed.get(id(f), cfg['default'])
        f._slot = slot
        out[slot].append(f)
        if surface_name == 'list' and slot == 'line' and id(f) in claimed:
            out['pinned'].append(f)
    return out


def apply_positions(fields, positions, visible, surface_name='form',
                    principal=None, pk_names=(), extra_spec=None):
    """Slots + `visible` + a regra de motor dos campos de sistema.

    Um formulario nao edita a propria chave, entao o campo de sistema vai para
    `hidden` **sem ninguem declarar** -- `type` `ID` (a chave) ou `DK` (a chave
    derivada que o motor gerencia). Quem precisar do contrario cita o campo em
    `body`: a declaracao existe, e existir e o que ganha da regra (a diferenca
    entre "nao citado" e "citado" e o que `resolve_slots` devolve em `claimed`).

    `pk_names` e o fallback para um pool sem `type` declarado; `extra_spec` soma
    slots declarados fora do `positions` (a sessao `table` recebe o `hidden`).
    """
    cfg = surface(surface_name)
    pool = list(fields or [])
    spec = dict(positions or {})
    if extra_spec:
        spec.update({k: v for k, v in extra_spec.items() if k in cfg['slots']})
    buckets = resolve_slots(spec, pool, principal, surface_name)
    claimed = buckets.pop('claimed')
    # Campo de sistema escondido por regra: `type` `ID` (a chave) ou `DK` (a
    # chave derivada que o motor gerencia) — exatamente o que o catálogo de
    # tipos declarava como `pos_form: 0` antes dos slots. É por TIPO, e não por
    # nome: numa tabela de ligação (`ProdutoInsumo`), a chave é composta por
    # FKs `FK` que o autor PRECISA ver — a regra não pode comer as colunas dela.
    # Só a que É campo do pool: um `id` que uma lista `fields` não inclui não é
    # erro, é um campo que não existe nesta tela, e a regra não inventa um.
    system = set()
    pk = set(pk_names or ())
    for f in pool:
        t = getattr(f, '_type', None)
        if t in ('ID', 'DK'):
            system.add(f.name)
        elif t is None and f.name in pk:
            system.add(f.name)
    for f in pool:
        if f.name in system and id(f) not in claimed:
            buckets['hidden'].append(f)
            buckets[cfg['default']].remove(f)
            f._slot = 'hidden'
    # Input de barra tem que estar no slot `bar` — a regra que morava no
    # `Field.__post_init__` quando o destino era `pos_form: 3`. Um toggle que
    # fica no corpo renderiza como input comum e some da barra, que é o modo de
    # falha silencioso que a validação existe para evitar.
    if surface_name == 'form':
        for f in pool:
            inp = getattr(f, 'inp', None)
            if inp is not None and inp.slot == 'bar' and f._slot != 'bar':
                raise ValueError(
                    f"{surface_name}: campo {f.name!r} usa input de barra "
                    f"({f.input!r}), então tem que estar no slot 'bar' — "
                    f"está em {f._slot!r}")
    visible_map = resolve_visible(visible, pool, principal, surface_name)
    out = {slot: [getattr(f, 'name', None) for f in bucket]
           for slot, bucket in buckets.items()}
    out['visible'] = visible_map
    return out


def resolve_visible(spec, pool, principal=None, surface_name='form'):
    """Aplica a spec `visible` (`{campo: cond}`) e devolve `{nome: cond}`.

    A condição é uma resposta sobre o DADO (`not_empty`, `empty`, `field`/`op`/
    `value`, `callable`, `'not_empty'`), não sobre a posição — é por isso que
    não é um slot: um campo pode estar na barra e depender de `not_empty`, ou
    no corpo e depender do mesmo filtro.

    Grava `f._visible_when` (o que `is_visible_by_pos`/`_eval_pos_when` leem) e
    devolve o mapa por nome, que é o que o render consulta.
    """
    where = surface_name
    pool = list(pool or [])
    entities = _pool_entities(pool)
    out = {}
    for f in pool:
        f._visible_when = None
    if not spec:
        return out
    if not isinstance(spec, dict):
        raise TypeError(f"{where}.visible: esperava {{campo: condição}}; veio "
                        f"{type(spec).__name__}")
    for nome, cond in spec.items():
        ent, _, campo = nome.rpartition('.') if '.' in nome else (None, '', nome)
        hits = _slot_match(pool, entities, ent or None, campo, 'visible',
                           principal, where)
        if len(hits) > 1:
            raise ValueError(
                f"{where}.visible: campo {campo!r} é ambíguo entre "
                + ' e '.join(sorted({getattr(f, '_entity', None) or '?' for f in hits}))
                + " — qualifique com 'Entidade.campo'")
        f = hits[0]
        f._visible_when = cond
        out[f.name] = cond
    return out
