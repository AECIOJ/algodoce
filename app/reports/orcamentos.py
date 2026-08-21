from app.constantes import FORMINHAS


def _event_after(instance):
    e = instance.event
    if not e:
        return []
    lines = []
    has_any = False
    if e.tipo:
        lines.append({'text': f'Evento: {e.tipo}', 'font_size': 10, 'font_style': 'B'})
        has_any = True
    if e.tema:
        lines.append({'text': f'Tema: {e.tema}', 'font_size': 10})
        has_any = True
    if e.data:
        data_str = e.data.strftime('%d/%m/%Y')
        hora_str = e.hora.strftime('%H:%M') if e.hora else ''
        lines.append({'text': f'Data: {data_str} {hora_str}'.strip(), 'font_size': 10})
        has_any = True
    if e.local:
        lines.append({'text': f'Local: {e.local}', 'font_size': 10})
        has_any = True
    if e.convidados:
        lines.append({'text': f'Convidados: {e.convidados}', 'font_size': 10})
        has_any = True
    if e.cerimonial:
        lines.append({'text': f'Cerimonial: {e.cerimonial}', 'font_size': 10})
        has_any = True
    if e.obs:
        lines.append({'text': f'Obs: {e.obs}', 'font_size': 10})
        has_any = True
    if has_any:
        lines.append({'text': ''})
    return lines


def _forminhas_carteira(q):
    f = FORMINHAS.get(q.forminhas, '-')
    c = q.carteira.nome if q.carteira else '50% no pedido + 50% na entrega'
    return f"Forminhas: {f} | Forma de Pagamento: {c}"


ORCAMENTO_REPORT = {
    'label': 'Orçamento',
    'header': {
        'layout': 'logo_left',
        'title': 'Orçamento #{id}',
        'fields': [
            'cliente_nome',       # tudo da Entity
            'data_pedido',
            'cliente_telefone',
            'validade_data',      # calc da Entity (label 'Válido até')
        ],
    },
    'after_table': _event_after,
    'table': {
        'columns': {
            'product_id':     {'width': 44},   # FK → label 'Produto'; valor via product.nome
            'quantidade':     {'width': 8},    # INT → center
            'preco_unitario': {'width': 14},   # NUM brl → right/brl
            'valor':          {'width': 14, 'agg': 'sum'},   # calc da Entity
        },
        'footer': True,
        'footer_label': 'Total',
        'after': _forminhas_carteira,
    },
}
