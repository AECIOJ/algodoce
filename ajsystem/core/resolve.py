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