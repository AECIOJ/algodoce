"""
MODE_* — Tipos de filtro (base para herança em XXX_FILTERS).

Cada MODE_* define type + modes (lista de tuplas [valor, label]).

Uso em XXX_FILTERS:
  from app.filters import MODE_NUMBER, MODE_TEXT, MODE_SELECT

  XXX_FILTERS = {
      'valor':    MODE_NUMBER,                              # direto
      'status':   {**MODE_SELECT, 'options': STATUS},       # herda + options
      'documento': {**MODE_TEXT, 'modes': [('igual', 'Igual a')]},  # override modes
  }
"""
from datetime import date, timedelta


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MODE_* — Tipos de filtro
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MODE_TEXT = {
    'type': 'text',
    'modes': [
        ('igual',    'Igual a'),
        ('contains', 'Contém'),
        ('starts',   'Começa'),
    ],
}

MODE_NUMBER = {
    'type': 'number',
    'modes': [
        ('igual',       'Igual a'),
        ('entre',       'Entre'),
        ('maior_que',   'Maior que'),
        ('maior_igual', 'Maior ou igual a'),
        ('menor_que',   'Menor que'),
        ('menor_igual', 'Menor ou igual a'),
    ],
}

MODE_DATE = {
    'type': 'date',
    'modes': [
        ('hoje',           'Hoje'),
        ('periodo',        'Período'),
        ('ontem',          'Ontem'),
        ('ultimos_7_dias', 'Últimos 7 dias'),
        ('mes',            'Mês'),
        ('mes_atual',      'Mês Atual'),
        ('mes_anterior',   'Mês Anterior'),
        ('ano',            'Ano'),
        ('ano_atual',      'Ano Atual'),
        ('a_partir_de',    'A partir de'),
        ('ate_a_data_de',  'Até a data de'),
    ],
}

MODE_BOOLEAN = {
    'type': 'boolean',
    'modes': [
        ('',      'Todos'),
        ('true',  'Sim'),
        ('false', 'Não'),
    ],
}

MODE_SELECT = {
    'type': 'select',
}


def _deep_attr(obj, path):
    """Acessa attribute aninhado via dot notation (ex: 'conta.nome')."""
    for part in path.split('.'):
        if obj is None:
            return None
        obj = getattr(obj, part, None)
    return obj


def build_fk_options(model_class):
    """Query model and return {id: nome} dict for FK select filters."""
    items = model_class.query.order_by(model_class.nome).all()
    return {i.id: i.nome for i in items if i.nome}


def resolve_filters(config, request_args):
    """Lê query params da URL e retorna dict estruturado por tipo.

    - select / boolean → value direto (str):  {'status': '1'}
    - date → sub-dict:  {'vencimento': {'preset': 'mes_atual', 'from': '...', 'to': '...'}}
    - text → sub-dict:  {'nome': {'mode': 'contains', 'value': 'sugar'}}
    - number → sub-dict: {'valor': {'mode': 'entre', 'val1': '10', 'val2': '50'}}

    Se ausente, usa 'default' do config.
    """
    result = {}
    for field, cfg in config.items():
        ftype = cfg.get('type', 'text')

        # ── select / boolean: value direto ──
        if ftype in ('select', 'boolean'):
            val = request_args.get(field)
            if val is not None and val != '':
                result[field] = val
            elif 'default' in cfg:
                result[field] = cfg['default']

        # ── date: sub-properties (preset, from, to, mes, ano) ──
        elif ftype == 'date':
            preset = request_args.get(field + '_preset')
            fr = request_args.get(field + '_from')
            to = request_args.get(field + '_to')
            mes = request_args.get(field + '_mes')
            ano = request_args.get(field + '_ano')
            if preset:
                sub = {'preset': preset}
                if fr:
                    sub['from'] = fr
                if to:
                    sub['to'] = to
                if mes:
                    sub['mes'] = mes
                if ano:
                    sub['ano'] = ano
                result[field] = sub
            elif 'default' in cfg:
                result[field] = cfg['default']

        # ── text: sub-properties (mode, value) ──
        elif ftype == 'text':
            mode = request_args.get(field + '_mode')
            value = request_args.get(field + '_value')
            if value:
                result[field] = {'mode': mode or 'igual', 'value': value}
            elif 'default' in cfg:
                result[field] = cfg['default']

        # ── number: sub-properties (mode, val1, val2) ──
        elif ftype == 'number':
            mode = request_args.get(field + '_mode')
            val1 = request_args.get(field + '_val1')
            val2 = request_args.get(field + '_val2')
            if val1:
                sub = {'mode': mode or 'igual', 'val1': val1}
                if val2:
                    sub['val2'] = val2
                result[field] = sub
            elif 'default' in cfg:
                result[field] = cfg['default']

    return result


def filtrar_vencimento(linhas, field, preset, hoje=None):
    """Aplica preset de data em lista (LinhaTransacao ou obj c/ atributo de data).

    Presets suportados: em_atraso, hoje, a_vencer, mes_atual, mes_anterior, ano_atual
    Exclui automaticamente status in (0, 8, 9) quando aplicável.
    """
    if not preset:
        return linhas
    if hoje is None:
        hoje = date.today()

    if preset == 'em_atraso':
        return [l for l in linhas
                if getattr(l, field) and getattr(l, field) < hoje
                and l.status not in (0, 8, 9)]

    elif preset == 'hoje':
        w = hoje.weekday()
        if w == 5:
            dias = [hoje, hoje + timedelta(1), hoje + timedelta(2)]
        elif w == 6:
            dias = [hoje, hoje - timedelta(1), hoje + timedelta(1)]
        elif w == 0:
            dias = [hoje, hoje - timedelta(1), hoje - timedelta(2)]
        else:
            dias = [hoje]
        return [l for l in linhas
                if getattr(l, field) in dias
                and l.status not in (0, 8, 9)]

    elif preset == 'a_vencer':
        return [l for l in linhas
                if getattr(l, field) and getattr(l, field) > hoje
                and l.status not in (0, 8, 9)]

    elif preset == 'mes_atual':
        return [l for l in linhas
                if getattr(l, field)
                and getattr(l, field).month == hoje.month
                and getattr(l, field).year == hoje.year
                and l.status not in (0, 8, 9)]

    elif preset == 'mes_anterior':
        m = hoje.month - 1 or 12
        y = hoje.year if hoje.month > 1 else hoje.year - 1
        return [l for l in linhas
                if getattr(l, field)
                and getattr(l, field).month == m
                and getattr(l, field).year == y
                and l.status not in (0, 8, 9)]

    elif preset == 'ano_atual':
        return [l for l in linhas
                if getattr(l, field)
                and getattr(l, field).year == hoje.year
                and l.status not in (0, 8, 9)]

    return linhas


def filtrar_vencimento_query(query, model_field, preset, hoje=None):
    """Aplica preset de data em query SQLAlchemy.

    Presets suportados: em_atraso, hoje, a_vencer, mes_atual, mes_anterior, ano_atual
    """
    from sqlalchemy import extract
    if not preset:
        return query
    if hoje is None:
        hoje = date.today()

    if preset == 'em_atraso':
        return query.filter(model_field < hoje)

    elif preset == 'hoje':
        w = hoje.weekday()
        if w == 5:
            dias = [hoje, hoje + timedelta(1), hoje + timedelta(2)]
        elif w == 6:
            dias = [hoje, hoje - timedelta(1), hoje + timedelta(1)]
        elif w == 0:
            dias = [hoje, hoje - timedelta(1), hoje - timedelta(2)]
        else:
            dias = [hoje]
        return query.filter(model_field.in_(dias))

    elif preset == 'a_vencer':
        return query.filter(model_field > hoje)

    elif preset == 'mes_atual':
        return query.filter(
            extract('month', model_field) == hoje.month,
            extract('year', model_field) == hoje.year,
        )

    elif preset == 'mes_anterior':
        m = hoje.month - 1 or 12
        y = hoje.year if hoje.month > 1 else hoje.year - 1
        return query.filter(
            extract('month', model_field) == m,
            extract('year', model_field) == y,
        )

    elif preset == 'ano_atual':
        return query.filter(extract('year', model_field) == hoje.year)

    return query


def apply_text_filter(linhas, field, text_cfg):
    """Aplica filtro de texto em lista de objetos.

    text_cfg: {'mode': 'contains'|'exact'|'starts', 'value': '...'}
    """
    if not text_cfg or not text_cfg.get('value'):
        return linhas
    mode = text_cfg.get('mode', 'contains')
    needle = str(text_cfg['value']).lower()
    result = []
    for item in linhas:
        raw = getattr(item, field, None)
        if raw is None:
            continue
        val = str(raw).lower()
        if mode == 'igual' and val == needle:
            result.append(item)
        elif mode == 'starts' and val.startswith(needle):
            result.append(item)
        elif mode == 'contains' and needle in val:
            result.append(item)
    return result


def apply_number_filter(linhas, field, number_cfg):
    """Aplica filtro numérico em lista de objetos.

    number_cfg: {'mode': 'entre'|'maior_que'|etc, 'val1': '...', 'val2': '...'}
    """
    if not number_cfg or not number_cfg.get('val1'):
        return linhas
    mode = number_cfg.get('mode', 'igual')
    try:
        v1 = float(number_cfg['val1'])
    except (ValueError, TypeError):
        return linhas
    v2 = None
    if number_cfg.get('val2'):
        try:
            v2 = float(number_cfg['val2'])
        except (ValueError, TypeError):
            pass
    result = []
    for item in linhas:
        raw = getattr(item, field, None)
        if raw is None:
            continue
        try:
            val = float(raw)
        except (ValueError, TypeError):
            continue
        if mode == 'entre' and v2 is not None and (val < v1 or val > v2):
            continue
        elif mode == 'maior_que' and val <= v1:
            continue
        elif mode == 'maior_igual' and val < v1:
            continue
        elif mode == 'menor_que' and val >= v1:
            continue
        elif mode == 'menor_igual' and val > v1:
            continue
        elif mode == 'igual' and val != v1:
            continue
        result.append(item)
    return result


def apply_select_filter(linhas, field, display_value, options_dict, filter_path=None):
    """Aplica filtro select em lista de objetos.

    display_value: valor display (ex: 'Pendente') ou CSV vindo do JS.
    options_dict: dict {chave: display_label} para reverse-lookup,
                  ou set/list de valores diretos para match direto.
    filter_path: dot notation para acessar valor no item (ex: 'conta.nome').
    """
    if not display_value:
        return linhas
    display_parts = [s.strip() for s in str(display_value).split(',') if s.strip()]
    accessor = (lambda item: _deep_attr(item, filter_path)) if filter_path else (lambda item: getattr(item, field, None))

    if isinstance(options_dict, dict) and options_dict:
        first_val = next(iter(options_dict.values()))
        if isinstance(first_val, str):
            keys = set()
            for part in display_parts:
                for k, v in options_dict.items():
                    if str(v) == part:
                        keys.add(k)
                        break
            if not keys:
                return linhas
            keys_str = {str(k) for k in keys}
            return [item for item in linhas if str(accessor(item)) in keys_str]
        else:
            vals = {str(v) for v in options_dict.values() if str(v) in display_parts}
            return [item for item in linhas if str(accessor(item)) in vals]

    vals = {str(v) for v in display_parts}
    return [item for item in linhas if str(accessor(item)) in vals]


def apply_boolean_filter(linhas, field, bool_value):
    """Aplica filtro booleano em lista de objetos.

    bool_value: 'true', 'false', ou None/'' (Todos).
    """
    if not bool_value:
        return linhas
    target = bool_value == 'true'
    return [item for item in linhas if getattr(item, field, None) == target]


def apply_date_filter(linhas, field, date_cfg):
    """Aplica filtro de data em lista de objetos.

    date_cfg: {'preset': 'mes_atual', ...} ou value direto.
    """
    if not date_cfg:
        return linhas
    preset = date_cfg.get('preset') if isinstance(date_cfg, dict) else date_cfg
    if preset in ('periodo', 'período'):
        fr = date_cfg.get('from') if isinstance(date_cfg, dict) else None
        to = date_cfg.get('to') if isinstance(date_cfg, dict) else None
        return _filter_date_range(linhas, field, fr, to)
    elif preset == 'hoje':
        return filtrar_vencimento(linhas, field, 'hoje')
    elif preset == 'ontem':
        return _filter_date_preset(linhas, field, 'ontem')
    elif preset in ('últimos 7 dias', 'ultimos 7 dias'):
        return _filter_date_last_n_days(linhas, field, 7)
    elif preset in ('mês', 'mes'):
        mes = date_cfg.get('mes') if isinstance(date_cfg, dict) else None
        return _filter_date_month(linhas, field, mes)
    elif preset in ('mês atual', 'mes atual'):
        return filtrar_vencimento(linhas, field, 'mes_atual')
    elif preset in ('mês anterior', 'mes anterior'):
        return filtrar_vencimento(linhas, field, 'mes_anterior')
    elif preset == 'ano':
        ano = date_cfg.get('ano') if isinstance(date_cfg, dict) else None
        return _filter_date_year(linhas, field, ano)
    elif preset == 'ano atual':
        return filtrar_vencimento(linhas, field, 'ano_atual')
    elif preset in ('a partir de',):
        fr = date_cfg.get('from') if isinstance(date_cfg, dict) else None
        return _filter_date_range(linhas, field, fr, None)
    elif preset in ('até a data de', 'ate a data de'):
        to = date_cfg.get('to') if isinstance(date_cfg, dict) else None
        return _filter_date_range(linhas, field, None, to)
    return linhas


def _parse_date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _parse_month(s):
    if not s:
        return None, None
    try:
        parts = s.split('-')
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return None, None


def _filter_date_range(linhas, field, fr, to):
    d_from = _parse_date(fr)
    d_to = _parse_date(to)
    result = []
    for item in linhas:
        raw = getattr(item, field, None)
        if not raw:
            continue
        if d_from and raw < d_from:
            continue
        if d_to and raw > d_to:
            continue
        result.append(item)
    return result


def _filter_date_preset(linhas, field, preset):
    hoje = date.today()
    if preset == 'ontem':
        d = hoje - timedelta(days=1)
        return [l for l in linhas if getattr(l, field) == d]


def _filter_date_last_n_days(linhas, field, n):
    hoje = date.today()
    start = hoje - timedelta(days=n - 1)
    return [l for l in linhas if getattr(l, field) and getattr(l, field) >= start]


def _filter_date_month(linhas, field, mes_str):
    y, m = _parse_month(mes_str)
    if not m:
        return linhas
    return [l for l in linhas if getattr(l, field) and getattr(l, field).month == m and getattr(l, field).year == y]


def _filter_date_year(linhas, field, ano_str):
    try:
        y = int(ano_str)
    except (ValueError, TypeError):
        return linhas
    return [l for l in linhas if getattr(l, field) and getattr(l, field).year == y]
