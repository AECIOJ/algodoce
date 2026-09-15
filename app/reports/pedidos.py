from app.constantes import FORMINHAS


def _valor_item(item):
    return (item.preco or 0) * item.qtd


def _cliente_nome(order):
    return order.conta.nome if order.conta else '-'


def _cliente_telefone(order):
    return order.conta.telefone if order.conta else ''


def _event_after(instance):
    e = instance.evento
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


def _forminhas_carteira(order):
    f = FORMINHAS.get(order.forminhas, '-')
    c = order.carteira.nome if order.carteira else '-'
    return f"Forminhas: {f} | Forma de Pagamento: {c}"


def _brl(v):
    if v is None:
        return "R$ 0,00"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _report_after(order):
    lines = []
    acrescimo = float(order.acrescimo or 0)
    desconto = float(order.desconto or 0)
    total = float(order.total or 0)
    if acrescimo:
        lines.append({'text': f'Acréscimo: {_brl(acrescimo)}', 'align': 'R'})
    if desconto:
        lines.append({'text': f'Desconto: {_brl(desconto)}', 'align': 'R'})
    if acrescimo or desconto:
        lines.append({'text': ''})
    lines.append({'text': f'Total: {_brl(total)}', 'align': 'R',
                  'font_size': 11, 'font_style': 'B'})
    lines.append({'text': ''})
    lines += _event_after(order)
    return lines


PEDIDO = {
    'label': 'Pedido',
    'print_fragment_template': 'components/print_overlay.html',
    'header': {
        'layout': 'logo_left',
        'title': 'Pedido #{id}',
        'fields': [
            {'function': _cliente_nome, 'label': 'Cliente'},
            {'field': 'pedido_em', 'label': 'Data', 'align': 'right', 'format': 'date'},
            {'function': _cliente_telefone, 'label': 'Telefone'},
            {'field': 'data_previsao_entrega', 'label': 'Previsão', 'align': 'right', 'format': 'datetime'},
        ],
    },
    'body': {
        'table': {
            'columns': {
                'produto.nome':   {'label': 'Produto', 'width': 50},
                'qtd':            {'label': 'Qtd.', 'width': 10, 'align': 'center'},
                'preco':          {'label': 'Preço', 'width': 20, 'align': 'right'},
                'valor':          {'label': 'Valor', 'width': 20, 'align': 'right',
                                   'function': _valor_item, 'agg': 'sum'},
            },
            'footer': True,
            'footer_label': 'Subtotal',
            'after': _forminhas_carteira,
        },
        'after': _report_after,
    },
}
