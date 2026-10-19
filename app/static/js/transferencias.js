/* Soma ao vivo do total de um pai, a partir das linhas filhas.
 *
 * O sinal NÃO vem do nome da tabela: vem do hidden que o motor renderiza do
 * `defaults` da sessão. Assim o JS não conhece o relationship — só precisa
 * saber qual código debita.
 *
 * Um campo derivado que depende do estado da tela (e não do último save) é
 * responsabilidade do cliente: o servidor não tem como saber o número que o
 * usuário ainda não gravou.
 */
(function () {
  'use strict';

  var TOLERANCIA = 0.005; // mesmo do model: resto de ponto flutuante, não folga
  var ERRO = 'var(--fallback-er, oklch(var(--er)/1))';   // a cor do daisyUI

  function q(name, root) {
    return (root || document).querySelector('[name="' + name + '"]');
  }
  function num(v) {
    if (v == null) return 0;
    v = String(v).trim().replace(/[^0-9,.\-+]/g, '');
    if (!v) return 0;
    if (v.indexOf(',') >= 0) v = v.replace(/\./g, '').replace(',', '.');
    var n = parseFloat(v);
    return isNaN(n) ? 0 : n;
  }
  function round2(n) { return Math.round((n + Number.EPSILON) * 100) / 100; }
  function fmt(v) { return v.toFixed(2).replace('.', ','); }

  /* Só os tbody desktop: o mobile repete os mesmos inputs (mesmos `name`), e
   * contar os dois somaria cada linha duas vezes. */
  function tabelas() {
    return Array.prototype.slice.call(
      document.querySelectorAll('.it-desktop tbody[data-rel]'));
  }

  function linhas(tbody) {
    return Array.prototype.slice.call(tbody.querySelectorAll('tr[data-crow]'))
      .filter(function (tr) {
        var crow = tr.getAttribute('data-crow');
        return crow && crow !== '__IDX__' && !tr.id; // ignora o *RowTemplate
      });
  }

  function campo(tr, crow, nome) {
    return tr.querySelector('[name="child_movtos_' + crow + '_' + nome + '"]');
  }

  function sinal(tr, crow) {
    var el = campo(tr, crow, 'tipo');
    return el && el.value === 'S' ? -1 : 1;
  }

  function diferenca() {
    var soma = 0;
    tabelas().forEach(function (tbody) {
      linhas(tbody).forEach(function (tr) {
        var crow = tr.getAttribute('data-crow');
        var v = campo(tr, crow, 'valor');
        if (v) soma += sinal(tr, crow) * num(v.value);
      });
    });
    return round2(soma);
  }

  /* O `total` é `readonly` → input `disabled`, e `numDecimals` recusa disabled
   * (formats.js:387): `fmtFieldInput` nele é no-op. Por isso o número entra
   * já na convenção do campo, por `numToInputFor` — a mesma saída que o
   * `itSessionTotals` usa nos alvos `data-total-target` dele (ver sys.html:451).
   * O fallback `fmt` cobre campo sem `data-num-decimals`. */
  function escreve(campoTotal, d) {
    if (Math.abs(num(campoTotal.value) - d) >= TOLERANCIA) {
      campoTotal.value = (window.numToInputFor
        ? (numToInputFor(campoTotal, d) || fmt(d))
        : fmt(d));
      /* Dispara como o `itSessionTotals` nos alvos dele: os `it*` do motor
       * escutam `input`/`change` e reagem ao novo valor. */
      campoTotal.dispatchEvent(new Event('input', { bubbles: true }));
      campoTotal.dispatchEvent(new Event('change', { bubbles: true }));
    }
    /* A cor vai inline: `.input-error` não vence de `.input[disabled]` — mesma
     * propriedade (border-color), especificidade maior e depois no CSS. A
     * expressão é a mesma que o motor usa no aviso do `diff`. */
    var fecha = Math.abs(d) <= TOLERANCIA;
    campoTotal.style.borderColor = fecha ? '' : ERRO;
    campoTotal.classList.toggle('input-error', !fecha);
    campoTotal.title = fecha ? 'Fechada em zero.' : 'Não fecha em zero.';
  }

  /* Linha nova: o `Adicionar` clona o template `__IDX__` e o `on_new` da rota já
   * trouxe data/documento/histórico do mestre. O `valor` é deste arquivo: nasce
   * com o que falta fechar NESTA sessão — entrada credita (−diferença), saída
   * debita (+diferença). */
  function preencheNovas(tbody) {
    linhas(tbody).forEach(function (tr) {
      var crow = tr.getAttribute('data-crow');
      if (crow.indexOf('n') !== 0) return;
      var v = campo(tr, crow, 'valor');
      if (!v || String(v.value || '').trim()) return;
      var falta = -diferenca() * sinal(tr, crow);
      if (falta <= TOLERANCIA) return;
      v.value = fmt(falta);
      if (window.fmtFieldInput) fmtFieldInput(v);
      v.dispatchEvent(new Event('input', { bubbles: true }));
      v.dispatchEvent(new Event('change', { bubbles: true }));
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var campoTotal = q('total');
    var tbs = tabelas();
    if (!campoTotal || !tbs.length) return;

    var atualiza = function () { escreve(campoTotal, diferenca()); };
    tbs.forEach(function (tb) {
      if ('MutationObserver' in window) {
        new MutationObserver(function () {
          preencheNovas(tb);
          atualiza();
        }).observe(tb, { childList: true });
      }
    });

    var form = document.getElementById('main-form');
    if (form) {
      form.addEventListener('input', atualiza);
      form.addEventListener('change', atualiza);
    }
    atualiza();
  });
  /* ── Lançamento rápido (o botão "Lançar") ─────────────────────────────────
   *
   * Os três campos do bloco `MEMORY` (Valor, De e Para — ver o Schema da rota)
   * não persistem: existem só para digitar uma transferência de uma vez. O
   * botão cria a linha da Entrada (recurso destino) e a da Saída (recurso
   * origem), e o `on_new` de cada sessão já traz data, documento e histórico do
   * cabeçalho.
   *
   * Duas coisas que o motor entrega e que valem usar em vez de reimplementar:
   * `addChildRow` (clona o template da sessão e devolve a chave `n-N` da linha
   * nova) e `on_new` (herança do mestre, desktop e mobile). O que este arquivo
   * escreve por cima é só o par recurso+valor, com a mesma disciplina do `on_new`:
   * número na convenção do campo alvo (`numToInputFor` → `fmtFieldInput`) e
   * `input`/`change` para os `it*` do motor recalcularem a Diferença.
   *
   * As sessões são localizadas pelo hidden do `tipo` de cada `.child-table-wrap`
   * — o mesmo sinal que a Diferença usa — em vez do nome da tabela: "Saídas" tem
   * acento e viraria `saídasTableBody`, e renomear a sessão quebraria o JS.
   *
   * Fica dentro do IIFE (usa `num`/`fmt` daqui) e é exposta no `window`, porque
   * o destino do botão é `onclick="transferenciaLancar(this)"`.
   */
  function transferenciaLancar(btn) {
    var form = (btn && btn.closest) ? (btn.closest('form') || document) : document;

    function campo(nome) {
      return form.querySelector('[name="' + nome + '"]');
    }
    function avisa(msg, tipo) {
      if (window.itToasts) itToasts(msg, tipo);
      else alert(msg);
    }
    function rotuloDe(select) {
      return select && select.selectedIndex >= 0
        ? select.options[select.selectedIndex].text : '';
    }

    var iv = campo('valor'), ide = campo('de'), ipa = campo('para');
    var de = ide ? ide.value : '', para = ipa ? ipa.value : '';
    if (!de || !para) {
      avisa('Preencha a origem (De) e o destino (Para).', 'warning');
      return;
    }
    /* Vazio e zero são avisos diferentes: `num()` devolve 0 nos dois casos, e
     * o "preencha" engoliria o "maior que zero" de quem digitou 0. */
    if (!String(iv && iv.value || '').trim()) {
      avisa('Preencha o valor do lançamento.', 'warning');
      return;
    }
    var valor = num(iv.value);
    if (valor <= 0) {
      avisa('O valor do lançamento precisa ser maior que zero.', 'warning');
      return;
    }
    /* Aviso antes de a linha existir: o `pre_save` da rota é quem barra o save
     * depois, com o dado já gravado. */
    if (de === para) {
      avisa('A origem e o destino precisam ser recursos diferentes.', 'warning');
      return;
    }

    /* wrap da sessão de quem credita e de quem debita. */
    var wraps = {};
    Array.prototype.forEach.call(form.querySelectorAll('.child-table-wrap'), function (wrap) {
      var t = wrap.querySelector('input[name$="_tipo"]');
      if (t && (t.value === 'E' || t.value === 'S')) wraps[t.value] = wrap;
    });
    if (!wraps.E || !wraps.S) {
      avisa('Esta tela não tem as duas sessões da transferência.', 'warning');
      return;
    }

    function cria(wrap, recurso) {
      var add = wrap.querySelector('[onclick*="addChildRow"]');
      if (!add || !window.addChildRow) return false;
      var key = addChildRow(add);          // devolve a chave `n-N` da linha nova
      if (!key) return false;
      var pref = 'child_movtos_' + key + '_';
      /* Desktop e mobile: o `itmApplyPage` só pagina, não sincroniza — quem
       * escreve nas duas cópias é o `on_new`, e aqui é esta escrita. */
      wrap.querySelectorAll('[name="' + pref + 'recurso_id"]').forEach(function (s) {
        s.value = recurso;
        s.dispatchEvent(new Event('change', { bubbles: true }));
      });
      wrap.querySelectorAll('[name="' + pref + 'valor"]').forEach(function (i) {
        i.value = (window.numToInputFor ? (numToInputFor(i, valor) || fmt(valor))
                                        : fmt(valor));
        if (window.fmtFieldInput) fmtFieldInput(i);
        i.dispatchEvent(new Event('input', { bubbles: true }));
        i.dispatchEvent(new Event('change', { bubbles: true }));
      });
      return true;
    }

    if (!cria(wraps.E, para) || !cria(wraps.S, de)) {
      avisa('Não consegui criar as linhas: falta a tabela da sessão.', 'warning');
      return;
    }

    /* Limpa os três para o próximo lançamento e devolve o foco ao Valor. O
     * `change` é o que reavalia o `enabled` do botão (`itEnabledEval`) e o
     * `marcarFormAlterado` do form. */
    [iv, ide, ipa].forEach(function (el) {
      if (!el) return;
      el.value = '';
      el.dispatchEvent(new Event('change', { bubbles: true }));
    });
    if (iv) iv.focus();
    avisa('Lançado: entrada em ' + rotuloDe(ipa) + ', saída em ' + rotuloDe(ide) + '.',
          'success');
  }
  window.transferenciaLancar = transferenciaLancar;
})();
