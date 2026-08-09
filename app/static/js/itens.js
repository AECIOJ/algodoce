/* Itens do Orçamento sobre o renderizador padrão (item_table):
   - preço unitário auto-preenchido a partir do catálogo via consulta();
   - total por linha (desktop) / por coluna (mobile) + total geral.
   A sincronização desktop/mobile e o add/remove de linhas ficam no engine. */
(function() {
  'use strict';
  var REL = 'items';
  var PREFIX = 'child_items_';
  var _precosPendentes = 0;
  var _subPendente = false;

  function wrap() {
    return document.querySelector('.child-table-wrap');
  }
  function crowOf(el) {
    var host = el.closest('[data-crow]');
    return host ? host.getAttribute('data-crow') : null;
  }
  function rowInput(root, crow, field) {
    if (!root || !crow) return null;
    return root.querySelector('[name="' + PREFIX + crow + '_' + field + '"]');
  }
  function parseNum(v) {
    var n = parseFloat(String(v == null ? '' : v));
    return isNaN(n) ? 0 : n;
  }
  function fmtBrl(v) {
    return v.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  }
  function lineTotal(crow) {
    var w = wrap();
    var q = parseNum(rowInput(w, crow, 'quantidade') && rowInput(w, crow, 'quantidade').value);
    var p = parseNum(rowInput(w, crow, 'preco_unitario') && rowInput(w, crow, 'preco_unitario').value);
    return q * p;
  }
  function crows() {
    var w = wrap();
    if (!w) return [];
    var body = w.querySelector('.it-desktop tbody[data-rel="' + REL + '"]');
    if (!body) return [];
    var out = [];
    body.querySelectorAll('tr[data-crow]').forEach(function(tr) {
      var c = tr.getAttribute('data-crow');
      if (c && out.indexOf(c) === -1) out.push(c);
    });
    return out;
  }
  function setupTotals() {
    var w = wrap();
    if (!w) return;
    var body = w.querySelector('.it-desktop tbody[data-rel="' + REL + '"]');
    if (!body) return;

    w.querySelectorAll('.it-total-cell, .it-total-row, .it-grand-total').forEach(function(el) { el.remove(); });

    var list = crows();
    body.querySelectorAll('tr[data-crow]').forEach(function(tr) {
      var c = tr.getAttribute('data-crow');
      var td = document.createElement('td');
      td.className = 'it-total-cell text-right';
      td.setAttribute('data-crow', c);
      td.textContent = 'R$ ' + fmtBrl(lineTotal(c));
      tr.appendChild(td);
    });

    var mtable = w.querySelector('.it-mobile table.itm-table');
    if (mtable) {
      var trTotal = document.createElement('tr');
      trTotal.className = 'it-total-row';
      var th = document.createElement('th');
      th.className = 'itm-label';
      th.textContent = 'Total';
      trTotal.appendChild(th);
      list.forEach(function(c) {
        var td = document.createElement('td');
        td.className = 'itm-cell it-total-cell text-right';
        td.setAttribute('data-crow', c);
        td.textContent = 'R$ ' + fmtBrl(lineTotal(c));
        trTotal.appendChild(td);
      });
      mtable.querySelector('tbody').appendChild(trTotal);
    }

    var total = list.reduce(function(acc, c) { return acc + lineTotal(c); }, 0);
    var gt = document.createElement('div');
    gt.className = 'it-grand-total text-right text-sm font-bold mt-1';
    gt.textContent = 'Total geral: R$ ' + fmtBrl(total);
    w.appendChild(gt);

    if (window.itmPagerInit) itmPagerInit();
  }
  function capturarPreco(select) {
    var crow = crowOf(select);
    if (!crow || !select.value) return;
    _precosPendentes++;
    consulta('product', select.value, 'preco,qtd_minima', function(d) {
      _precosPendentes = Math.max(0, _precosPendentes - 1);
      var w = wrap();
      var precoInput = rowInput(w, crow, 'preco_unitario');
      if (d && precoInput) {
        var precoTotal = parseNum(d.preco);
        var qtdMin = parseInt(d.qtd_minima, 10) || 0;
        var unit = qtdMin > 0 ? precoTotal / qtdMin : precoTotal;
        precoInput.value = unit.toFixed(2);
        precoInput.dispatchEvent(new Event('input', {bubbles: true}));
      }
      _trySubmit();
    });
  }
  function atualizarPrecos() {
    var w = wrap();
    if (!w) return;
    w.querySelectorAll('.it-desktop tbody[data-rel="' + REL + '"] select[name^="' + PREFIX + '"]').forEach(function(select) {
      var crow = crowOf(select);
      if (!crow || !select.value) return;
      var precoInput = rowInput(w, crow, 'preco_unitario');
      if (precoInput && parseNum(precoInput.value) === 0) capturarPreco(select);
    });
  }
  function _trySubmit() {
    if (_subPendente && _precosPendentes === 0) {
      _subPendente = false;
      var form = document.getElementById('main-form');
      if (form) form.submit();
    }
  }
  function atualizarESalvar() {
    _subPendente = true;
    atualizarPrecos();
    var f = document.getElementById('atualizar-precos-field');
    if (f) f.value = '1';
    if (window.marcarFormAlterado) marcarFormAlterado();
    _trySubmit();
  }

  window.atualizarPrecos = atualizarPrecos;
  window.atualizarESalvar = atualizarESalvar;

  document.addEventListener('DOMContentLoaded', function() {
    var form = document.getElementById('main-form');
    if (!form) return;
    var w = wrap();
    if (!w) return;

    form.addEventListener('change', function(e) {
      var t = e.target;
      if (!t || t.name.indexOf(PREFIX) !== 0 || !/_product_id$/.test(t.name)) return;
      capturarPreco(t);
      setupTotals();
    });
    form.addEventListener('input', function(e) {
      var t = e.target;
      if (!t || t.name.indexOf(PREFIX) !== 0) return;
      if (/_quantidade$/.test(t.name) || /_preco_unitario$/.test(t.name)) setupTotals();
    });

    setupTotals();

    var body = w.querySelector('.it-desktop tbody[data-rel="' + REL + '"]');
    if (body && 'MutationObserver' in window) {
      new MutationObserver(setupTotals).observe(body, {childList: true});
    }
  });
})();
