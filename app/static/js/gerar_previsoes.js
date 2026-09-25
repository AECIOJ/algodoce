/* Botão "Gerar" das previsões em Contas a Receber/Pagar.
 *
 * Client-side: monta as linhas na tabela de previsões distribuindo o `ratear`
 * (valor a ratear, campo só-exibição do mestre) conforme o `prazo`; preenche
 * vencimento, previsto, recurso e documento (fatura/P#/C# + parcela); o Salvar
 * do form persiste tudo junto. Mantém ao vivo os agregados só-exibição
 * (previsto/realizado/variacao/saldo) e o `ratear` (= valor − previsto).
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

  function vinculada() {
    if (val('pedido_id') || val('compra_id')) return true;
    var qs = new URLSearchParams(window.location.search);
    return qs.has('origem_pedido') || qs.has('origem_compra');
  }

  /* Soma de um campo só nas linhas da tabela desktop (evita contar também as
   * duplicadas mobile e o total). `[[data-rel]]` aponta para o tbody desktop. */
  function somaDesktop(w, field) {
    var body = w.querySelector('.it-desktop tbody[data-rel="previsoes"]');
    if (!body) return 0;
    var total = 0;
    body.querySelectorAll('input[name$="_' + field + '"]').forEach(function (el) {
      total += num(el.value);
    });
    return round2(total);
  }

  function setNumField(el, n) {
    if (!el) return;
    n = round2(n);
    if (Math.abs(num(el.value) - n) < 0.005) return;
    el.value = fmt(n);
    if (window.fmtFieldInput) fmtFieldInput(el);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }

  /* Só é "manual" quando o próprio usuário edita `ratear` (evento trusted);
   * síntese/script não marca — assim `Gerar`/`Zerar` retomam a observância. */
  var ratearManual = false;

  function atualizarAgregados() {
    var w = wrap();
    if (!w) return;
    var sP = somaDesktop(w, 'previsto');
    var sR = somaDesktop(w, 'realizado');
    var sV = somaDesktop(w, 'variacao');
    setNumField(q('previsto'), sP);
    setNumField(q('realizado'), sR);
    setNumField(q('variacao'), sV);
    setNumField(q('saldo'), sP + sV - sR);
    if (!ratearManual) setNumField(q('ratear'), num(val('valor')) - sP);
  }

  function atualizarBtn() {
    var w = wrap();
    var btn = gerarBtn();
    if (!w || !btn) return;
    var ok = val('conta_id') !== '' && val('operacao_id') !== '' &&
             val('prazo') !== '' && val('recurso_id') !== '' && num(val('valor')) > 0;
    btn.disabled = !(ok && num(val('ratear')) > 0.005);
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

  /* Base do `documento` das parcelas: fatura informada → fatura/parcela; de
   * pedido/compra → P#<id>/parcela ou C#<id>/parcela; avulsa sem fatura → '' */
  function baseDocumento() {
    var fatura = String(val('fatura') || '').trim();
    if (fatura) return fatura;
    var qs = new URLSearchParams(window.location.search);
    var pid = val('pedido_id') || qs.get('origem_pedido') || '';
    if (pid) return 'P#' + pid;
    var cid = val('compra_id') || qs.get('origem_compra') || '';
    if (cid) return 'C#' + cid;
    return '';
  }

  window.gerarPrevisoes = function (btn) {
    var w = wrap() || (btn && btn.closest('.child-table-wrap'));
    if (!w) return;

    var base = val('data') || todayIso();
    var prazo = val('prazo');
    var total = num(val('ratear'));
    var recurso = val('recurso_id');
    if (!prazo) {
      if (window.itToasts) itToasts('Informe o prazo para gerar as previsões.', 'error');
      return;
    }
    if (!(total > 0)) {
      if (window.itToasts) itToasts('Informe o valor a ratear para gerar as previsões.', 'error');
      return;
    }
    if (!recurso) {
      if (window.itToasts) itToasts('Selecione o recurso para gerar as previsões.', 'error');
      return;
    }

    var parcelas = parsePrazo(prazo, base, total);
    var docBase = baseDocumento();

    var tbody = w.querySelector('.it-desktop tbody[data-rel="previsoes"]');
    var zeros = [];
    if (tbody) {
      tbody.querySelectorAll('tr[data-crow]').forEach(function (tr) {
        if (tr.id) return;                    // preserva *RowTemplate
        var crow = tr.getAttribute('data-crow');
        if (!crow || crow === '__IDX__') return;
        var prev = tr.querySelector('input[name$="_previsto"]');
        if (!prev || num(prev.value) > 0.005) return;
        zeros.push(tr);
      });
    }

    var zi = 0;
    parcelas.forEach(function (p, i) {
      var n = i + 1;
      var doc = docBase ? docBase + '/' + n : '';
      var tr = null;
      if (zi < zeros.length) {
        tr = zeros[zi++];
      } else {
        addChildRow(btn);
        tr = tbody ? tbody.lastElementChild : null;
      }
      if (!tr || !tr.querySelector) return;
      setField(tr.querySelector('input[name$="_vencimento"]'), p.vencimento);
      setField(tr.querySelector('input[name$="_previsto"]'), fmt(p.previsto));
      setField(tr.querySelector('[name$="_recurso_id"]'), recurso);
      if (docBase) setField(tr.querySelector('input[name$="_documento"]'), doc);
    });

    ratearManual = false;
    atualizarAgregados();
    if (window.itToasts) itToasts(parcelas.length + ' previsão(ões) gerada(s).', 'success');
    atualizarBtn();
  };

  window.zerarPrevisoes = function (btn) {
    var w = wrap() || (btn && btn.closest('.child-table-wrap'));
    if (!w) return;

    var tbody = w.querySelector('.it-desktop tbody[data-rel="previsoes"]');
    if (!tbody) {
      if (window.itToasts) itToasts('Não há previsões para zerar.', 'info');
      return;
    }

    var count = 0;
    tbody.querySelectorAll('tr[data-crow]').forEach(function (tr) {
      var crow = tr.getAttribute('data-crow');
      if (!crow || crow === '__IDX__') return;
      var prefix = 'child_previsoes_' + crow + '_';
      var realizado = tr.querySelector('[name="' + prefix + 'realizado"]');
      var variacao = tr.querySelector('[name="' + prefix + 'variacao"]');
      if (num(realizado && realizado.value) || num(variacao && variacao.value)) return;
      var prev = tr.querySelector('[name="' + prefix + 'previsto"]');
      if (!prev) return;
      setField(prev, '0,00');
      count++;
    });

    ratearManual = false;
    atualizarAgregados();
    if (count === 0) {
      if (window.itToasts) itToasts('Nenhuma previsão zerada.', 'info');
    } else {
      if (window.itToasts) itToasts(count + ' previsão(ões) zerada(s).', 'success');
    }
    atualizarBtn();
  };

  document.addEventListener('DOMContentLoaded', function () {
    var w = wrap();
    if (!w) return;
    atualizarValor();
    atualizarAgregados();
    atualizarBtn();

    var tbody = w.querySelector('.it-desktop tbody[data-rel="previsoes"]');
    if (tbody && 'MutationObserver' in window) {
      new MutationObserver(function () {
        atualizarAgregados();
        atualizarBtn();
      }).observe(tbody, { childList: true });
    }

    var form = document.getElementById('main-form');
    if (form) {
      var sinc = function (e) {
        if (e.isTrusted && e.target && e.target.name === 'ratear') ratearManual = true;
        atualizarAgregados();
        atualizarBtn();
      };
      form.addEventListener('input', sinc);
      form.addEventListener('change', sinc);
    }
  });
})();