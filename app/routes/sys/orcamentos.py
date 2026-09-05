from flask import request, redirect, url_for, flash, render_template, render_template_string
from datetime import datetime, timezone
from ajsystem.core.extensions import db
from ajsystem.core.do_report import print_report
from app.models.client import Conta
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.models.quote import Entity as QuoteEntity
from app.models.quote_item import Entity as QuoteItemEntity
from app.reports.orcamentos import ORCAMENTO

# Entity aninhada para o motor de relatórios (`_module_entity`): labels,
# formatos, FK e calc resolvidos a partir das Entities dos models.
Entity = {
    'Quote': QuoteEntity,
    'QuoteItem': QuoteItemEntity,
}


def _btn_enviar_action(instance):
    """Botão Enviar do form — pré-controle + impressão do orçamento.

    Exibição no padrão das listagens (operações/PLANO): o fragmento vai para
    o container exclusivo `#report-content` (via `render`), cujo script
    alterna com a página; o Voltar (`closeReport`) restaura sem recarregar.
    """
    if instance is None or not instance.items:
        return ''
    return print_report(ORCAMENTO, instance)


Schema = {
    'Quote': {
        'status': {'pos_form': 4},
        'total': {'editor': 'eTotal'},
        'pedido_id': {'pos_form': 4},
    },
    'QuoteItem': {
        'product_id': {
            'lookup': {
                'replaces': {
                    'quantidade': 'qtd_minima',
                    'preco_unitario': 'preco_unitario',
                },
            },
        },
    },
}

Page = {
    'label': 'Orçamento',
    'type': 'crud',
    'props': {
        'tabs': {
            'Dados': {'type': 'List'},
            'Filtros': {'type': 'Filter'},
        },
        'list': {
            'columns': 'Quote',
            'order': ['id'],
        },
        'form': {
            'fields': 'Quote',
            'readonly': lambda q: q is not None and q.pedido_id is not None,
            'delete': {
                'when': lambda q: q.pedido_id is None,
                'msg_ok': 'Orçamento excluído!',
                'msg_no': 'Exclua o pedido vinculado antes de excluir o orçamento.',
            },
            'buttons': [
                {'label': 'Enviar', 'icon': 'paper-airplane', 'color': 'success', 'outline': True,
                 'action': _btn_enviar_action, 'render': '#report-content',
                 'position': 'nav_right',
                 'when': lambda q: q is not None and q.pedido_id is None and q.status < 7},
                {'label': 'Aprovar', 'icon': 'check', 'color': 'success', 'outline': False,
                 'endpoint': 'orcamentos.aprovar', 'url_var': 'id',
                 'position': 'nav_right',
                 'when': lambda q: q is not None and q.pedido_id is None and q.status < 7},
                {'label': 'Renovar', 'icon': 'arrow-path', 'color': 'info', 'outline': False,
                 'endpoint': 'orcamentos.renovar', 'url_var': 'id', 'method': 'POST',
                 'position': 'nav_right',
                 'when': lambda q: q is not None and q.pedido_id is None and q.status == 7},
            ],
            'sessions': {
                'Itens do Orçamento': {
                    'buttons': [
                        {'label': 'Preços zerados',
                         'icon': 'currency-dollar', 'color': 'secondary',
                         'js': 'itUpdateZerados(this)'},
                    ],
                    'table': {
                        'columns': ['QuoteItem'],
                        'totals': ['quantidade', {'valor': 'eTotal'}],
                    },
                },
                'Evento': {
                    'fields': ['Event'],
                },
            },
        },
    },
}


def _converter_context(quote):
    """Clientes + sugestões para a página de aprovação (portado do antigo converter)."""
    clients = Conta.query.filter_by(ativo=True).filter(Conta.tipo.in_([0, 1])).order_by(Conta.nome).all()
    ctx = dict(clients=clients, perfect_match=None, suggested_client=None, phone_conflict=None)
    if not quote or not quote.cliente_nome:
        return ctx
    perfect = Conta.query.filter(
        Conta.nome.ilike(quote.cliente_nome),
        Conta.telefone == quote.cliente_telefone,
    ).first()
    ctx['perfect_match'] = perfect
    if perfect:
        return ctx
    suggested = Conta.query.filter(Conta.nome.ilike(quote.cliente_nome)).first()
    if not suggested and quote.cliente_telefone:
        suggested = Conta.query.filter(Conta.telefone == quote.cliente_telefone).first()
    if suggested:
        ctx['suggested_client'] = suggested
    if quote.cliente_telefone:
        phone_owner = Conta.query.filter(Conta.telefone == quote.cliente_telefone).first()
        if phone_owner and (not suggested or phone_owner.id != suggested.id):
            ctx['phone_conflict'] = phone_owner
    return ctx


_CONVERTER_HTML = """{% extends "pages/sys.html" %}
{% import "components/item_table.html" as itb with context %}

{% block head_extra %}
{{ super() }}
{{ itb.item_table_styles() }}
{% endblock %}

{% block page_content %}
<style>
  .form-container { margin-inline: auto; max-width: 120ch; width: 100%; }
  @media (max-width: 767px) { .form-container { max-width: none; margin-inline: 0; } }
</style>
<div class="grow flex flex-col min-h-0">
  <div class="app-bar shrink-0"
       style="border-bottom:1px solid var(--fallback-b3, oklch(var(--b3)));background:var(--bar-bg-form);color:var(--bar-txt-form);">
    <div class="app-bar-left">
      <a href="{{ url_for('orcamentos.form', id=quote.id) }}" class="btn btn-ghost btn-sm inline-flex items-center gap-1">
        <svg class="w-4 h-4" aria-hidden="true"><use href="#i-arrow-left"/></svg> Voltar
      </a>
    </div>
    <div class="app-bar-center"><span class="font-bold">Converter Orçamento #{{ quote.id|fmtid }}</span></div>
    <div class="app-bar-right"></div>
  </div>

  <div class="flex-1 min-h-0 overflow-auto px-4">
    <div class="form-container p-2 pb-3">
      <div class="alert alert-info flex items-center gap-2 py-2 mb-3 text-sm">
        <svg class="w-4 h-4 shrink-0" aria-hidden="true"><use href="#i-information-circle"/></svg>
        <span>Os itens do orçamento serão convertidos em um pedido.</span>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
        <div class="card bg-base-200 p-2"><div class="text-xs opacity-60">Cliente</div><div class="text-sm font-semibold">{{ quote.cliente_nome }}</div></div>
        <div class="card bg-base-200 p-2"><div class="text-xs opacity-60">Telefone</div><div class="text-sm font-semibold">{{ quote.cliente_telefone }}</div></div>
        <div class="card bg-base-200 p-2"><div class="text-xs opacity-60">Itens</div><div class="text-sm font-semibold">{{ quote.items|length }}</div></div>
        <div class="card bg-base-200 p-2"><div class="text-xs opacity-60">Total</div><div class="text-sm font-semibold">{{ total|brl if total is not none else '—' }}</div></div>
      </div>

      {% if clientes.phone_conflict %}
      <div class="alert alert-warning flex items-center gap-2 py-2 mb-3 text-sm">
        <svg class="w-4 h-4 shrink-0" aria-hidden="true"><use href="#i-exclamation-triangle"/></svg>
        <span>O telefone {{ quote.cliente_telefone }} já está cadastrado para <strong>{{ clientes.phone_conflict.nome }}</strong>. Verifique se não há erro de digitação.</span>
      </div>
      {% endif %}

      {% if clientes.perfect_match %}
      <div class="alert alert-success flex items-center gap-2 py-2 mb-3 text-sm">
        <svg class="w-4 h-4 shrink-0" aria-hidden="true"><use href="#i-check-circle"/></svg>
        <span>Cliente já cadastrado com o mesmo nome e telefone: <strong>{{ clientes.perfect_match.nome }}</strong>.</span>
      </div>
      {% endif %}

      <form method="POST" class="card bg-base-100 border border-base-300 p-4">
        <div class="flex flex-wrap gap-4 mb-3">
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="radio" name="converter_tipo" class="radio radio-sm" value="existente"
                   {{ 'checked' if clientes.perfect_match or not clientes.suggested_client }} onchange="toggleConvTipo()">
            <span class="text-sm font-medium">Usar conta existente</span>
          </label>
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="radio" name="converter_tipo" class="radio radio-sm" value="nova" onchange="toggleConvTipo()">
            <span class="text-sm font-medium">Criar nova conta</span>
          </label>
        </div>
        <div id="convExistenteFields">
          {% if clientes.perfect_match %}
          <div class="form-control mb-2">
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="radio" name="client_id" class="radio radio-sm" value="{{ clientes.perfect_match.id }}" checked>
              <span class="text-sm">{{ clientes.perfect_match.nome }} — {{ clientes.perfect_match.telefone }} <span class="badge badge-success badge-sm">Combinação exata</span></span>
            </label>
          </div>
          {% endif %}
          <select name="client_id" class="select select-bordered select-sm w-full">
            <option value="">— Selecione —</option>
            {% for c in clientes.clients %}
            <option value="{{ c.id }}"
                    {{ 'selected' if not clientes.perfect_match and clientes.suggested_client and c.id == clientes.suggested_client.id }}>{{ c.nome }} — {{ c.telefone }}</option>
            {% endfor %}
          </select>
          {% if clientes.suggested_client and not clientes.perfect_match %}
          <p class="text-xs opacity-60 mt-1">Sugerido: {{ clientes.suggested_client.nome }}</p>
          {% endif %}
        </div>
        <div id="convNovaFields" style="display:none;">
          <input type="text" name="novo_nome" class="input input-bordered input-sm w-full mb-2" placeholder="Nome" value="{{ quote.cliente_nome }}">
          <input type="text" name="novo_telefone" class="input input-bordered input-sm w-full" placeholder="Telefone" value="{{ quote.cliente_telefone }}" data-mask="(99) 99999-9999">
        </div>
        <p class="text-sm opacity-60 mt-3 mb-0">O status do orçamento será alterado para <strong>Aprovado</strong> e um novo pedido será gerado.</p>
        <div class="flex justify-end gap-2 mt-3">
          <a href="{{ url_for('orcamentos.form', id=quote.id) }}" class="btn btn-ghost btn-sm">Cancelar</a>
          <button type="submit" class="btn btn-success btn-sm inline-flex items-center gap-1">
            <svg class="w-4 h-4" aria-hidden="true"><use href="#i-arrow-right"/></svg> Confirmar Conversão
          </button>
        </div>
      </form>
    </div>
  </div>
</div>
{% endblock %}

{% block scripts %}
{{ super() }}
<script>
function toggleConvTipo() {
  var nova = document.querySelector('input[name="converter_tipo"][value="nova"]');
  var existente = document.querySelector('input[name="converter_tipo"][value="existente"]');
  var ef = document.getElementById('convExistenteFields');
  var nf = document.getElementById('convNovaFields');
  if (ef) ef.style.display = (nova && nova.checked) ? 'none' : '';
  if (nf) nf.style.display = (nova && nova.checked) ? '' : 'none';
}
document.addEventListener('DOMContentLoaded', function () {
  toggleConvTipo();
});
</script>
{% endblock %}
"""


def aprovar(id):
    """Aprova o orçamento e gera o pedido a partir dele (antigo botão Converter).

    Rota registrada em `create_app` como `orcamentos.aprovar`
    (`/<int:id>/aprovar`, GET+POST), pois o motor gera apenas o CRUD.
    """
    quote = Quote.query.get_or_404(id)
    if quote.pedido_id:
        flash("Orçamento já foi convertido!", "warning")
        return redirect(url_for("orcamentos.list"))
    if quote.status >= 7:
        flash("Orçamento não pode ser convertido — expirado ou rejeitado.", "warning")
        return redirect(url_for("orcamentos.list"))

    if request.method == "GET":
        return render_template_string(
            _CONVERTER_HTML,
            quote=quote,
            total=quote.total,
            clientes=_converter_context(quote),
        )

    tipo = request.form.get("converter_tipo", "existente")

    if tipo == "nova":
        nome = request.form.get("novo_nome", "").strip()
        telefone = request.form.get("novo_telefone", "").strip()
        if not nome:
            flash("Informe o nome da nova conta.", "warning")
            return redirect(url_for("orcamentos.aprovar", id=id))
        existing = Conta.query.filter(Conta.nome.ilike(nome)).first()
        if existing:
            flash(f"Já existe uma conta com o nome '{existing.nome}'. Selecione-a na lista de contas existentes.", "warning")
            return redirect(url_for("orcamentos.aprovar", id=id))
        conta = Conta(
            nome=nome,
            telefone=telefone or None,
            email=None,
            tipo=0,
        )
        db.session.add(conta)
        db.session.flush()
    else:
        client_id = request.form.get("client_id", type=int)
        conta = Conta.query.get(client_id)
        if not conta:
            flash("Selecione um cliente para converter.", "warning")
            return redirect(url_for("orcamentos.aprovar", id=id))

    order = Order(
        client_id=conta.id,
        data_entrega=None,
        observacao=quote.observacao,
        carteira_id=quote.carteira_id,
        forminhas=quote.forminhas,
        status=0,
    )
    db.session.add(order)
    db.session.flush()

    for item in quote.items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantidade=item.quantidade,
            preco_unitario=item.preco_unitario,
            observacao=item.observacao,
        )
        db.session.add(order_item)

    db.session.flush()
    order.total = sum(
        (i.preco_unitario or 0) * i.quantidade for i in order.items
    )
    if quote.event:
        order.event = quote.event
    quote.status = 9
    quote.pedido_id = order.id
    order.quote_id = quote.id

    db.session.commit()
    flash("Orçamento convertido para pedido!", "success")
    return redirect(url_for("orcamentos.list"))


def renovar(id):
    """Renova um orçamento expirado (status 7→6 + nova data de renovação).

    Rota registrada em `create_app` como `orcamentos.renovar`
    (`/<int:id>/renovar`, POST), pois o motor gera apenas o CRUD.
    """
    quote = Quote.query.get_or_404(id)
    if quote.status != 7:
        flash("Apenas orçamentos expirados podem ser renovados.", "warning")
        return redirect(url_for("orcamentos.list"))
    quote.data_renovacao = datetime.now(timezone.utc)
    quote.status = 6
    db.session.commit()
    flash("Orçamento renovado com sucesso!", "success")
    return redirect(url_for("orcamentos.form", id=id))
