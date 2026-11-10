"""Renderer Pillow: gera PNG do `ChartDataset` para embutir no PDF.

Usa apenas Pillow (já instalada no projeto) — sem nova dependência.

Fontes: as DejaVu ficam embutidas em `ajsystem/static/fonts/` para não
depender das fontes do sistema (a imagem `python:*-slim` não traz nenhuma;
sem elas o Pillow cai no bitmap de 11px e todo texto sai minúsculo).
"""
import math
import os
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from ajsystem.defs.chart import Chart, ChartDataset

_PALETTE = (
    '#0d6efd', '#198754', '#ffc107', '#dc3545', '#6f42c1',
    '#0dcaf0', '#fd7e14', '#20c997', '#d63384', '#6c757d',
)

# Relevo: cópia deslocada em cinza claro atrás do desenho (sem alpha).
_SHADOW_COLOR = '#d1d5db'


def _shadow_offset(chart) -> tuple[int, int] | None:
    """Resolve o deslocamento da sombra (dx, dy) em px.

    Convenção de plano cartesiano: dx positivo vai para a direita,
    dy positivo vai para cima; negativos invertem. Internamente o eixo y
    do Pillow cresce para baixo, então o sinal de dy é invertido ao desenhar.

    True -> (3, 3); tupla (dx, dy) customizada; False/None -> sem sombra.
    """
    shadow = getattr(chart.options, 'shadow', True)
    if shadow is False or shadow is None:
        return None
    if shadow is True:
        return (3, 3)
    return shadow  # ja validado como tupla de 2 inteiros em ChartOptions

_FONT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'static', 'fonts')
_FONT_DIRS = (
    _FONT_DIR,
    '/usr/share/fonts/truetype/dejavu',
    '/usr/share/fonts/dejavu',
    '/usr/local/share/fonts',
)
_FONT_NAMES = {
    False: ('DejaVuSans.ttf',),
    True: ('DejaVuSans-Bold.ttf', 'DejaVuSans.ttf'),
}
_FONT_CACHE = {}


def _font(size: int, bold: bool = False, family: str | None = None):
    """Carrega a fonte no tamanho pedido (embutida → sistema → default)."""
    key = (int(size), bool(bold), family)
    cached = _FONT_CACHE.get(key)
    if cached is not None:
        return cached
    for folder in _FONT_DIRS:
        for name in _FONT_NAMES[bold]:
            path = os.path.join(folder, name)
            try:
                font = ImageFont.truetype(path, int(size))
            except Exception:
                continue
            _FONT_CACHE[key] = font
            return font
    # Último recurso: default escalável (Pillow >= 10.1).
    try:
        font = ImageFont.load_default(size=int(size))
    except TypeError:
        font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


def _text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), str(text), font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _hex(color: str | None, fallback: str) -> str:
    if color:
        return color
    return fallback


def _contrast(color: str) -> str:
    """Texto claro ou escuro conforme a luminância do fundo."""
    try:
        c = color.lstrip('#')
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    except Exception:
        return '#ffffff'
    return '#111827' if (0.299 * r + 0.587 * g + 0.114 * b) > 150 \
        else '#ffffff'


class MatplotlibRenderer:
    """Gera um `BytesIO` com o PNG do gráfico (para o fpdf2 embutir)."""

    def __init__(self, dpi: int = 150, figsize: tuple = (7.2, 3.6)):
        self.dpi = dpi
        self.width = int(figsize[0] * dpi)
        self.height = int(figsize[1] * dpi)

    def render(self, ds: ChartDataset, chart: Chart) -> BytesIO:
        img = Image.new('RGB', (self.width, self.height), 'white')
        draw = ImageDraw.Draw(img)

        labels = list(ds.labels or [])
        series = list(ds.series or [])
        meta = ds.meta or {}
        lbl = meta.get('label', {}) or {}
        limit_info = meta.get('limit', {}) or {}

        pad_l, pad_r, pad_t, pad_b = 90, 60, 90, 110
        # Barras horizontais: a margem esquerda acomoda o nome da categoria.
        if chart.type == 'bar' and labels:
            f_cat = _font(10)
            widest = max(_text_size(draw, str(v)[:16], f_cat)[0]
                         for v in labels)
            pad_l = max(pad_l, min(widest + 24, self.width // 3))
        plot_x, plot_y = pad_l, pad_t
        plot_w = self.width - pad_l - pad_r
        plot_h = self.height - pad_t - pad_b
        plot = (plot_x, plot_y, plot_w, plot_h)

        # Título do gráfico (chart.title na raiz da declaração).
        # `anchor='ma'`: o y informado é o TOPO do texto — por isso 16px,
        # dentro da margem superior (pad_t=90), sem invadir a área de plot.
        if chart.title:
            tf = chart.options.title_font or {}
            size = tf.get('size', 24)
            bold = tf.get('bold', True)
            family = tf.get('family', None)
            f_title = _font(size, bold=bold, family=family)
            draw.text((plot_x + plot_w // 2, 16), chart.title,
                      fill='#111827', font=f_title, anchor='ma')

        if not labels or not series:
            draw.text((plot_x, plot_y + plot_h // 2 - 8), 'Sem dados',
                      fill='#6b7280', font=_font(14))
            buf = BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return buf

        if chart.type in ('pie', 'donut'):
            self._pie(draw, plot, labels, series[0], chart, lbl, limit_info)
        elif chart.type == 'bar':
            self._bars_horizontal(draw, plot, labels, series, chart, lbl,
                                  limit_info)
        else:
            # 'col' e demais: colunas verticais
            self._bars_vertical(draw, plot, labels, series, chart, lbl,
                                limit_info)

        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf

    # ------------------------------------------------------------------ pie
    def _pie(self, draw, plot, labels, series, chart, lbl, limit_info):
        x0, y0, w, h = plot
        data = list(series.get('data') or [])
        if not data:
            return
        total = sum(v or 0 for v in data)
        if total <= 0:
            return

        # Rótulo da fatia: categoria (label.cat=True), valor e porcentagem
        show_cat = lbl.get('cat') is True
        show_val = lbl.get('val', True)
        show_perc = lbl.get('perc', True)
        pos = lbl.get('pos', 'O')  # O=fora da fatia, I=dentro (centralizado)
        outside = (pos == 'O')
        has_text = show_cat or show_val or show_perc
        n_lines = (int(bool(show_cat)) + int(bool(show_val))
                   + int(bool(show_perc)))

        line_h = 12
        f = _font(12)
        font_h = _text_size(draw, '0', f)[1] if has_text else 12
        half_h = ((n_lines - 1) * line_h + font_h) / 2 if n_lines else 0

        # Respiro entre a pizza e os rótulos externos: encolhe a pizza para
        # a faixa do texto. A metade de baixo (`half_h`) cai na margem
        # inferior e é compensada no gap da legenda.
        label_gap = 22 if (outside and has_text) else 0
        label_band = (label_gap + half_h) if label_gap else 10

        cx, cy = x0 + w // 2, y0 + h // 2
        radius = max(10, min(w, h) // 2 - label_band)
        radius_label = radius * 0.58

        fixed = list(series.get('colors') or [])
        colors = [fixed[i] if i < len(fixed) and fixed[i]
                  else _PALETTE[i % len(_PALETTE)] for i in range(len(data))]
        explode = list(series.get('explode') or [])
        explode_r = radius * 0.12

        # Sombra por fatia, desenhada primeiro: cada fatia projeta sua
        # própria sombra deslocada, o que dá a sensação de relevo.
        # Fatia explodida leva a sombra junto no deslocamento.
        if shadow_off := _shadow_offset(chart):
            start = -90
            for i, v in enumerate(data):
                sweep = 360 * float(v or 0) / total
                if not v:
                    start += sweep
                    continue
                mid = start + sweep / 2
                ox = oy = 0
                if i < len(explode) and explode[i]:
                    ox = explode_r * math.cos(math.radians(mid))
                    oy = explode_r * math.sin(math.radians(mid))
                dx, dy = shadow_off[0], -shadow_off[1]
                draw.pieslice([cx - radius + ox + dx, cy - radius + oy + dy,
                               cx + radius + ox + dx, cy + radius + oy + dy],
                              start, start + sweep, fill=_SHADOW_COLOR)
                start += sweep

        start = -90
        for i, v in enumerate(data):
            sweep = 360 * float(v or 0) / total
            mid = start + sweep / 2
            ox = oy = 0
            if i < len(explode) and explode[i] and v:
                ox = explode_r * math.cos(math.radians(mid))
                oy = explode_r * math.sin(math.radians(mid))

            # Limpa a área interna da separação da fatia destacada antes
            # de desenhar a fatia real no novo lugar.
            if i < len(explode) and explode[i] and v:
                draw.pieslice([cx - radius, cy - radius,
                               cx + radius, cy + radius],
                              start, start + sweep, fill='white',
                              outline='white')

            draw.pieslice([cx - radius + ox, cy - radius + oy,
                           cx + radius + ox, cy + radius + oy],
                          start, start + sweep, fill=colors[i],
                          outline='white')
            start += sweep
        if has_text:
            # 'O' = fora da fatia (fundo branco → texto escuro + conector);
            # 'I' = dentro da fatia, centralizado (texto na cor de contraste
            # da própria fatia).
            start = -90
            for i, v in enumerate(data):
                sweep = 360 * float(v or 0) / total
                if not v:
                    start += sweep
                    continue
                mid = start + sweep / 2
                cos_m = math.cos(math.radians(mid))
                sin_m = math.sin(math.radians(mid))
                ox = oy = 0
                if i < len(explode) and explode[i]:
                    ox = explode_r * math.cos(math.radians(mid))
                    oy = explode_r * math.sin(math.radians(mid))
                scx, scy = cx + ox, cy + oy

                # Bloco empilhado: categoria (topo), valor (meio) e
                # porcentagem (base). Só entra o que está ativo.
                lines = []
                if show_cat:
                    name = labels[i] if i < len(labels) else f'Cat {i + 1}'
                    lines.append(str(name)[:16])
                if show_val:
                    lines.append(f"{v:,.0f}")
                if show_perc:
                    lines.append(f"{100*v/total:,.1f}%")

                if outside:
                    # Empurra o centro do bloco para fora da fatia somando
                    # a meia-largura/meia-altura do texto projetada no
                    # sentido radial. Sem isso, rótulos laterais invadem a
                    # pizza (texto é mais largo que alto).
                    half_w = max(_text_size(draw, t, f)[0]
                                 for t in lines) / 2
                    push = (label_gap + half_w * abs(cos_m)
                            + half_h * abs(sin_m))
                    lx = scx + (radius + push) * cos_m
                    ly = scy + (radius + push) * sin_m
                    # Conector: da borda da fatia até um pouco ANTES do
                    # rótulo (para a linha não cruzar o texto).
                    lx_edge = scx + radius * 0.98 * cos_m
                    ly_edge = scy + radius * 0.98 * sin_m
                    line_end = radius + max(label_gap - 8, 4)
                    lx_line = scx + line_end * cos_m
                    ly_line = scy + line_end * sin_m
                    draw.line((lx_edge, ly_edge, lx_line, ly_line),
                              fill='#9ca3af', width=1)
                    # Fora da fatia o fundo é branco: texto sempre escuro
                    fill = '#111827'
                else:
                    lx = scx + radius_label * cos_m
                    ly = scy + radius_label * sin_m
                    # Dentro da fatia: contraste com a cor da própria fatia
                    fill = _contrast(colors[i])

                top = ly - (len(lines) - 1) * line_h / 2
                for j, text in enumerate(lines):
                    draw.text((lx, top + j * line_h), text, fill=fill, font=f,
                              anchor='mm')
                start += sweep
        # Legenda: uma entrada por fatia, centralizada abaixo do gráfico
        items = []
        for i, _v in enumerate(data):
            name = labels[i] if i < len(labels) else f'Cat {i + 1}'
            items.append({'name': name, 'color': colors[i]})
        # Rótulos externos invadem a margem inferior; a legenda desce o
        # mesmo tanto para preservar o respiro entre texto e legenda.
        legend_gap = 28 + (half_h if (outside and has_text) else 0)
        self._draw_legend(draw, plot, items,
                          chart.legend,
                          bottom_gap=legend_gap)
        if limit_info.get('text'):
            # Abaixo da legenda quando ela existe; senão, sob os rótulos.
            if chart.legend != 'none':
                below = legend_gap + 28
            else:
                below = (half_h + 8) if (outside and has_text) else 8
            draw.text((x0, y0 + h + below), limit_info['text'],
                      fill='#6b7280', font=_font(11))

    # ------------------------------------------------- barras verticais ('col')
    def _bars_vertical(self, draw, plot, labels, series, chart, lbl,
                       limit_info):
        x0, y0, w, h = plot
        all_vals = [v for s in series for v in (s.get('data') or [])
                    if v is not None]
        if not all_vals:
            return
        vmin, vmax = min(0, min(all_vals)), max(0, max(all_vals))
        if vmax == vmin:
            vmax = vmin + 1

        def y_px(val):
            return y0 + h - (val - vmin) / (vmax - vmin) * h

        # Grid + valores do eixo Y
        f = _font(11)
        for i in range(5):
            val = vmin + (vmax - vmin) * i / 4
            py = y_px(val)
            draw.line([x0, py, x0 + w, py], fill='#e5e7eb')
            draw.text((x0 - 10, py), f"{val:,.0f}", fill='#6b7280', font=f,
                      anchor='rm')
        draw.line([x0, y0, x0, y0 + h], fill='#374151')

        # Rótulo do eixo Y (acima do topo da escala, à esquerda)
        if lbl.get('value'):
            draw.text((x0 - 5, y0 - 12), lbl['value'], fill='#111827',
                      font=_font(13), anchor='rs')

        n = len(labels)
        step = w / max(n, 1)
        stacked = any(s.get('stack') for s in series)
        bottoms = [0] * n if stacked else None

        if stacked:
            bar_w = max(8, min(42, step * 0.6))
        else:
            # Largura total do grupo cabe em 80% do slot da categoria,
            # dividindo igualmente entre as séries (sobra 20% de gap entre grupos).
            n_series = len(series)
            group_w = step * 0.8
            bar_w = max(4, min(42, group_w / max(n_series, 1)))

        # Coleta as barras para desenhar todas as sombras antes: a sombra
        # de um segmento não pode cair por cima do segmento vizinho.
        rects = []
        for si, s in enumerate(series):
            data = list(s.get('data') or [])
            base_color = _hex(s.get('color'), _PALETTE[si % len(_PALETTE)])
            point_colors = list(s.get('colors') or [])
            for i, val in enumerate(data):
                if val is None or val == 0:
                    continue
                color = _hex(point_colors[i] if i < len(point_colors) else None,
                             base_color)
                cx = x0 + (i + 0.5) * step
                top = y_px(val or 0)
                base = y_px(0)
                off = 0
                if stacked:
                    base = y_px(bottoms[i] or 0)
                    rect = [cx - bar_w / 2, min(top, base),
                            cx + bar_w / 2, max(top, base)]
                    bottoms[i] = (bottoms[i] or 0) + (val or 0)
                else:
                    off = (si - len(series) / 2) * bar_w + bar_w / 2
                    rect = [cx + off - bar_w / 2, min(top, base),
                            cx + off + bar_w / 2, max(top, base)]
                rects.append((rect, color, cx + off, min(top, base), val))

        if shadow_off := _shadow_offset(chart):
            dx, dy = shadow_off[0], -shadow_off[1]
            for rect, *_rest in rects:
                draw.rectangle([rect[0] + dx, rect[1] + dy,
                                rect[2] + dx, rect[3] + dy],
                               fill=_SHADOW_COLOR)

        for rect, color, lx, top_y, val in rects:
            draw.rectangle(rect, fill=color)
            # Rótulo de valor sobre barra (opcional) — centralizado na barra.
            if lbl.get('val', True):
                draw.text((lx, top_y - 4), f"{val:,.0f}",
                          fill='#111827', font=_font(10), anchor='mb')

        # Rótulos do eixo X
        fx = _font(10)
        for i, name in enumerate(labels):
            cx = x0 + (i + 0.5) * step
            draw.text((cx, y0 + h + 6), str(name)[:16], fill='#111827',
                      font=fx, anchor='ma')
        if isinstance(lbl.get('cat'), str):
            draw.text((x0 + w, y0 + h + 26), lbl['cat'], fill='#111827',
                      font=_font(13), anchor='ra')

        draw.line([x0, y0 + h, x0 + w, y0 + h], fill='#374151')

        self._draw_legend(draw, plot, series,
                          chart.legend,
                          bottom_gap=48)
        if limit_info.get('text'):
            draw.text((x0, y0 + h + 48 + 26), limit_info['text'],
                      fill='#6b7280', font=_font(11))

    # ------------------------------------------------- barras horizontais ('bar')
    def _bars_horizontal(self, draw, plot, labels, series, chart, lbl,
                         limit_info):
        x0, y0, w, h = plot
        all_vals = [v for s in series for v in (s.get('data') or [])
                    if v is not None]
        if not all_vals:
            return
        vmin, vmax = min(0, min(all_vals)), max(0, max(all_vals))
        if vmax == vmin:
            vmax = vmin + 1

        def x_px(val):
            return x0 + (val - vmin) / (vmax - vmin) * w

        # Grid + valores do eixo X
        f = _font(11)
        for i in range(5):
            val = vmin + (vmax - vmin) * i / 4
            px = x_px(val)
            draw.line([px, y0, px, y0 + h], fill='#e5e7eb')
            draw.text((px, y0 + h + 6), f"{val:,.0f}", fill='#6b7280', font=f,
                      anchor='ma')

        # Rótulo do eixo X (abaixo do eixo, alinhado à direita com respiro)
        if lbl.get('value'):
            draw.text((x0 + w, y0 + h + 26), lbl['value'], fill='#111827',
                      font=_font(13), anchor='ra')

        n = len(labels)
        step = h / max(n, 1)
        stacked = any(s.get('stack') for s in series)
        bottoms = [0] * n if stacked else None

        if stacked:
            bar_w = max(8, min(32, step * 0.6))
        else:
            # Largura total do grupo cabe em 80% do slot da categoria,
            # dividindo igualmente entre as séries (sobra 20% de gap entre grupos).
            n_series = len(series)
            group_w = step * 0.8
            bar_w = max(4, min(32, group_w / max(n_series, 1)))

        # Coleta as barras para desenhar todas as sombras antes (idem 'col').
        rects = []
        for si, s in enumerate(series):
            data = list(s.get('data') or [])
            base_color = _hex(s.get('color'), _PALETTE[si % len(_PALETTE)])
            point_colors = list(s.get('colors') or [])
            for i, val in enumerate(data):
                if val is None or val == 0:
                    continue
                color = _hex(point_colors[i] if i < len(point_colors) else None,
                             base_color)
                cy = y0 + (i + 0.5) * step
                right = x_px(val or 0)
                left = x0
                off = 0
                if stacked:
                    left = x_px(bottoms[i] or 0)
                    rect = [min(left, right), cy - bar_w / 2,
                            max(left, right), cy + bar_w / 2]
                    bottoms[i] = (bottoms[i] or 0) + (val or 0)
                else:
                    off = (si - len(series) / 2) * bar_w + bar_w / 2
                    rect = [min(left, right), cy + off - bar_w / 2,
                            max(left, right), cy + off + bar_w / 2]
                rects.append((rect, color, right, cy + off, val))

        if shadow_off := _shadow_offset(chart):
            dx, dy = shadow_off[0], -shadow_off[1]
            for rect, *_rest in rects:
                draw.rectangle([rect[0] + dx, rect[1] + dy,
                                rect[2] + dx, rect[3] + dy],
                               fill=_SHADOW_COLOR)

        for rect, color, right, cy, val in rects:
            draw.rectangle(rect, fill=color)
            # Rótulo de valor sobre barra horizontal (opcional) — na extremidade da barra.
            if lbl.get('val', True):
                draw.text((right + 4, cy), f"{val:,.0f}",
                          fill='#111827', font=_font(10), anchor='lm')

        # Rótulos do eixo Y
        fy = _font(10)
        for i, name in enumerate(labels):
            cy = y0 + (i + 0.5) * step
            draw.text((x0 - 6, cy), str(name)[:16], fill='#111827', font=fy,
                      anchor='rm')
        if isinstance(lbl.get('cat'), str):
            draw.text((x0 - 6, y0 - 12), lbl['cat'], fill='#111827',
                      font=_font(13), anchor='rs')

        draw.line([x0, y0, x0, y0 + h], fill='#374151')
        draw.line([x0, y0 + h, x0 + w, y0 + h], fill='#374151')

        self._draw_legend(draw, plot, series,
                          chart.legend,
                          bottom_gap=48)
        if limit_info.get('text'):
            draw.text((x0, y0 + h + 48 + 26), limit_info['text'],
                      fill='#6b7280', font=_font(11))

    # ----------------------------------------------------------- legenda
    def _draw_legend(self, draw, plot, series, position, bottom_gap=24):
        """Legenda centralizada no eixo do gráfico.

        top/bottom: itens em linha, centralizados na largura do plot.
        left/right: coluna centralizada verticalmente, fora da área de plot.
        """
        if position == 'none':
            return
        items = [s for s in series if s.get('name')]
        if not items:
            return

        x0, y0, w, h = plot
        f = _font(11)
        box = 12
        gap = 20
        row_h = 20
        color = '#111827'

        if position in ('top', 'bottom'):
            # Largura real de cada item: quadrado + 6px + texto.
            sizes = []
            for it in items:
                tw, _th = _text_size(draw, it['name'], f)
                sizes.append(box + 6 + tw)
            total = sum(sizes) + gap * (len(items) - 1)
            x = x0 + max(0, (w - total) // 2)
            y = (y0 - 12 - row_h) if position == 'top' \
                else (y0 + h + bottom_gap)
            for it, item_w in zip(items, sizes):
                draw.rectangle([x, y + 2, x + box, y + 2 + box],
                               fill=it.get('color') or '#6c757d')
                draw.text((x + box + 6, y), str(it['name']), fill=color,
                          font=f, anchor='la')
                x += item_w + gap
            return

        # left / right: coluna, centralizada em relação à altura do plot.
        sizes = []
        for it in items:
            tw, _th = _text_size(draw, it['name'], f)
            sizes.append(box + 6 + tw)
        total_h = row_h * len(items)
        y = y0 + max(0, (h - total_h) // 2)
        for it, item_w in zip(items, sizes):
            if position == 'left':
                x = x0 - 14 - item_w
            else:
                x = x0 + w + 14
            draw.rectangle([x, y + 4, x + box, y + 4 + box],
                           fill=it.get('color') or '#6c757d')
            draw.text((x + box + 6, y), str(it['name']), fill=color,
                      font=f, anchor='la')
            y += row_h