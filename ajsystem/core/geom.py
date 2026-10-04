"""Geometria em grade — conversão e validação de posicionados do relatório.

Convenção travada (ordem cartesiana x,y, em unidades de grade):
  pos      = [col, lin]              (âncora; [0,0] = fluxo automático)
  location = conforme o tipo:
    IMAGE  = [c1, r1, c2, r2]        (cantos; proporção via fit futuro)
    LINE   = [col, lin, caracteres, linhas] (origem + deltas com sinal;
              linhas omitida/0 = horizontal; caracteres 0 = vertical;
              ambos 0 = fail-fast "linha nula")
    BOX    = [col, lin, largura, altura?] (âncora + extensão; altura
              omitida = quadrado de verdade, altura_mm = largura_mm)
    CIRCLE = [col_centro, lin_centro, raio, achata] (raio em cols;
              achata 0/ausente = círculo compensado; >0 multiplica a
              altura por F; <0 multiplica a largura por |F|)

Genérico: sem model, sem relatório, sem app. A grade é anisotrópica
(1 lin != 1 col em mm); a compensação usa a métrica real da fonte.
"""
from math import isclose

KINDS = ('IMAGE', 'LINE', 'BOX', 'CIRCLE')

# Âncoras de topo p/ location enxuta ([âncora, linhas]). Sem 'N': ausente não
# renderiza. Altura em linhas (como o antigo logo.lines), largura pela
# proporção real da figura.
ANCHORS = ('C', 'L', 'R')


def resolve_anchor(anchor, lines, img_w, img_h, line_h, col_w, area_cols):
    """Âncora -> caixa em grade [c1, r1, c2, r2] (topo, floats).

    img_w/img_h = dimensões reais da figura (px); line_h/col_w = métrica real
    (mm); area_cols = largura útil em cols.
    """
    if anchor not in ANCHORS:
        raise ValueError(f"âncora '{anchor}' desconhecida {list(ANCHORS)}")
    lines = _num(lines, 'location')
    if lines <= 0:
        raise ValueError(f"location: linhas deve ser > 0, veio {lines!r}")
    if img_w <= 0 or img_h <= 0:
        raise ValueError("location: figura sem dimensão legível")
    h_mm = lines * line_h
    w_cols = h_mm * img_w / img_h / col_w
    if anchor == 'C':
        c1 = (area_cols - w_cols) / 2
    elif anchor == 'R':
        c1 = area_cols - w_cols
    else:
        c1 = 0  # 'L'
    return [c1, 0, c1 + w_cols, lines]


def _num(v, where):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"{where}: esperado número, veio {v!r}")
    return v


def normalize(kind, location):
    """Valida e normaliza location -> tupla canônica. fail-fast nomeando."""
    if kind not in KINDS:
        raise ValueError(f"elemento '{kind}' desconhecido {sorted(KINDS)}")
    if not isinstance(location, (list, tuple)):
        raise ValueError(f"{kind}: location deve ser lista, veio {type(location).__name__}")
    loc = list(location)
    if kind == 'LINE':
        if len(loc) == 3:
            loc.append(0)
        if len(loc) != 4:
            raise ValueError(f"LINE: location [col, lin, caracteres, linhas], veio {list(location)!r}")
        c, r, w, h = (_num(v, 'LINE') for v in loc)
        if isclose(w, 0) and isclose(h, 0):
            raise ValueError("LINE: linha nula ([col, lin, 0, 0])")
        return ('LINE', c, r, w, h)
    if kind == 'BOX':
        if len(loc) == 3:
            loc.append(None)  # quadrado: altura_mm = largura_mm
        if len(loc) != 4:
            raise ValueError(f"BOX: location [col, lin, largura, altura?], veio {list(location)!r}")
        c, r, w, h = loc
        c, r, w = (_num(v, 'BOX') for v in (c, r, w))
        if h is not None:
            h = _num(h, 'BOX')
        if w <= 0 or (h is not None and h <= 0):
            raise ValueError(f"BOX: largura/altura devem ser > 0, veio {list(location)!r}")
        return ('BOX', c, r, w, h)
    if kind == 'IMAGE':
        if len(loc) == 2 and isinstance(loc[0], str):
            if loc[0] not in ANCHORS:
                raise ValueError(f"IMAGE: âncora '{loc[0]}' desconhecida {list(ANCHORS)}")
            return ('IMAGE_ANCHOR', loc[0], _num(loc[1], 'IMAGE'))
        if len(loc) != 4:
            raise ValueError(f"IMAGE: location [c1, r1, c2, r2] ou [âncora, linhas], veio {list(location)!r}")
        c1, r1, c2, r2 = (_num(v, 'IMAGE') for v in loc)
        if c2 <= c1 or r2 <= r1:
            raise ValueError(f"IMAGE: exige c2>c1 e r2>r1, veio {list(location)!r}")
        return ('IMAGE', c1, r1, c2, r2)
    # CIRCLE
    if len(loc) == 3:
        loc.append(0)
    if len(loc) != 4:
        raise ValueError(f"CIRCLE: location [col, lin, raio, achata?], veio {list(location)!r}")
    c, r, rad, f = (_num(v, 'CIRCLE') for v in loc)
    if rad <= 0:
        raise ValueError(f"CIRCLE: raio deve ser > 0, veio {list(location)!r}")
    return ('CIRCLE', c, r, rad, f)


def to_mm(norm, line_h, col_w):
    """Tupla normalizada + métrica real (mm) -> geometria em mm p/ o FPDF.

    Retorna dict por tipo: LINE {x1,y1,x2,y2}; BOX/IMAGE {x,y,w,h};
    CIRCLE {x, y, rx, ry} (rx==ry = círculo perfeito).
    """
    kind = norm[0]
    if kind == 'LINE':
        _, c, r, w, h = norm
        x1, y1 = c * col_w, r * line_h
        return {'x1': x1, 'y1': y1, 'x2': x1 + w * col_w, 'y2': y1 + h * line_h}
    if kind in ('BOX', 'IMAGE'):
        if kind == 'BOX':
            _, c, r, w, h = norm
            w_mm = w * col_w
            h_mm = w_mm if h is None else h * line_h
        else:
            _, c1, r1, c2, r2 = norm
            c, r, w_mm, h_mm = c1, r1, (c2 - c1) * col_w, (r2 - r1) * line_h
            return {'x': c * col_w, 'y': r * line_h, 'w': w_mm, 'h': h_mm}
        return {'x': c * col_w, 'y': r * line_h, 'w': w_mm, 'h': h_mm}
    # CIRCLE: raio em cols; achata 0 = compensa (círculo); sgn = eixo.
    _, c, r, rad, f = norm
    rx = rad * col_w
    if not f:
        ry = rx  # círculo perfeito independente da anisotropia
    elif f > 0:
        ry = rx * f
    else:
        rx, ry = rx * abs(f), rx
    return {'x': c * col_w, 'y': r * line_h, 'rx': rx, 'ry': ry}
