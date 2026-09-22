/* Botão "Gerar" das previsões em Contas a Receber/Pagar.
 *
 * Client-side: monta as linhas na tabela de previsões a partir do `prazo`
 * (campo do mestre) e do `valor`; o Salvar do form persiste tudo junto.
 * Espelha app/utils.parse_prazo_recebimento (sem data de entrega).
 *
 * Carregado em receber/pagar pelo hook `_editor_js` (ver transacoes.py).
 */
(function () {
  'use strict';

  function q(name, root) {
    return (root || document).querySelector('[name="' + name + '"]');
  }
  function val(name, root) {
    var el = q(name, root);
    return el ? String(el.value == null ? '' : el.value).trim() : '';
  }
  function num(v) {
    if (v == null) return 0;
    v = String(v).trim();
    if (!v) return 0;
    if (v.indexOf(',') >= 0) v = v.replace(/\./g, '').replace(',', '.');
    var n = parseFloat(v);
    return isNaN(n) ? 0 : n;
  }
  function round2(n) { return Math.round((n + Number.EPSILON) * 100) / 100; }
  function fmt(v) { return v.toFixed(2).replace('.', ','); }

  function iso(d) {
    return d.getFullYear() + '-' +
           ('0' + (d.getMonth() + 1)).slice(-2) + '-' +
           ('0' + d.getDate()).slice(-2);
  }
  function todayIso() { return iso(new Date()); }
  function addDays(baseIso, days) {
    var p = baseIso.split('-');
    var d = new Date(parseInt(p[0], 10), parseInt(p[1], 10) - 1, parseInt(p[2], 10));
    d.setDate(d.getDate() + days);
    return iso(d);
  }

  function parsePrazo(texto, dataBase, total) {
    var t = (texto || '').trim().toUpperCase();
    if (!t) return [{ vencimento: dataBase, previsto: round2(total) }];

    if (t === 'P/E') {
      return [{ vencimento: dataBase, previsto: round2(total) }];
    }

    var mx = t.match(/^(\d+)X$/);
    if (mx) {
      var n = parseInt(mx[1], 10) || 1;
      if (n < 1) n = 1;
      var out = [];
      for (var i = 1; i <= n; i++) {
        var pv = (i < n) ? round2(total / n)
                         : round2(total - round2(total / n) * (n - 1));
        out.push({ vencimento: addDays(dataBase, 30 * i), previsto: pv });
      }
      return out;
    }

    if (/^\d+$/.test(t)) {
      return [{ vencimento: addDays(dataBase, parseInt(t, 10)), previsto: round2(total) }];
    }

    if (t.indexOf('/') >= 0) {
      var dias = t.split('/').map(function (s) { return parseInt(s.trim(), 10); })
                         .filter(function (d) { return !isNaN(d); });
      if (!dias.length) return [{ vencimento: dataBase, previsto: round2(total) }];
      var res = [];
      var acc = 0;
      for (var j = 0; j < dias.length; j++) {
        var p = (j === dias.length - 1) ? round2(total - acc)
                                        : round2(total / dias.length);
        acc = round2(acc + p);
        res.push({ vencimento: addDays(dataBase, dias[j]), previsto: p });
      }
      return res;
    }

    return [{ vencimento: dataBase, previsto: round2(total) }];
  }

  function wrap() {
    var body = document.querySelector('[data-rel="previsoes"]');
    return body ? body.closest('.child-table-wrap') : null;
  }
  function gerarBtn() { return document.querySelector('.btn-gerar-previsoes'); }

  function somaPrevisto(w) {
    var total = 0;
    w.querySelectorAll('input[name^="child_previsoes_"][name$="_previsto"]').forEach(function (el) {
      total += num(el.value);
    });
    return round2(total);
  }

  function limparLinhas(w) {
    var tbody = w.querySelector('.it-desktop tbody[data-rel="previsoes"]');
    if (tbody) {
      tbody.querySelectorAll('tr[data-crow]').forEach(function (tr) {
        if (tr.id) return;              // preserva *RowTemplate
        tr.remove();
      });
    }
    w.querySelectorAll('.it-mobile .itm-item[data-crow], .it-mobile .itm-cell[data-crow]')
     .forEach(function (el) { el.remove(); });
  }

  function vinculada() {
    if (val('pedido_id') || val('compra_id')) return true;
    var qs = new URLSearchParams(window.location.search);
    return qs.has('origem_pedido') || qs.has('origem_compra');
  }

  function atualizarBtn() {
    var w = wrap();
    var btn = gerarBtn();
    if (!w || !btn) return;
    var ok = val('conta_id') !== '' && val('operacao_id') !== '' &&
             val('prazo') !== '' && num(val('valor')) > 0;
    var divergente = Math.abs(num(val('valor')) - somaPrevisto(w)) > 0.005;
    btn.disabled = !(ok && divergente);
  }

  function atualizarValor() {
    var el = q('valor');
    if (!el || !vinculada()) return;
    el.readOnly = true;
    el.classList.add('input-disabled');
    el.title = 'Valor definido pelo pedido/compra de origem.';
  }

  function setField(el, value) {
    if (!el) return;
    el.value = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }

  window.gerarPrevisoes = function (btn) {
    var w = btn.closest('.child-table-wrap');
    if (!w) return;

    var base = val('data') || todayIso();
    var prazo = val('prazo');
    var total = num(val('valor'));
    if (!prazo) {
      if (window.itToasts) itToasts('Informe o prazo para gerar as previsões.', 'error');
      return;
    }
    if (!(total > 0)) {
      if (window.itToasts) itToasts('Informe o valor para gerar as previsões.', 'error');
      return;
    }

    var parcelas = parsePrazo(prazo, base, total);
    limparLinhas(w);

    var tbody = w.querySelector('.it-desktop tbody[data-rel="previsoes"]');
    parcelas.forEach(function (p) {
      addChildRow(btn);
      var tr = tbody ? tbody.lastElementChild : null;
      if (!tr || !tr.querySelector) return;
      setField(tr.querySelector('input[name$="_vencimento"]'), p.vencimento);
      setField(tr.querySelector('input[name$="_previsto"]'), fmt(p.previsto));
    });

    if (window.itToasts) itToasts(parcelas.length + ' previsão(ões) gerada(s).', 'success');
    atualizarBtn();
  };

  document.addEventListener('DOMContentLoaded', function () {
    if (!wrap()) return;
    atualizarValor();
    atualizarBtn();
    var form = document.getElementById('main-form');
    if (form) {
      form.addEventListener('input', atualizarBtn);
      form.addEventListener('change', atualizarBtn);
    }
  });
})();
