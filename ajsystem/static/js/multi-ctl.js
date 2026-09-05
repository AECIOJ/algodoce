/* Editor MULT10 (ajsystem) — self-contained.
 * Contrato: elemento .multi-ctl com:
 *   data-multi-options  JSON {code: label} — chaves de 1 caractere (0-9),
 *                        no máximo 10 opções (tipo MULT10)
 *   data-multi-title    título do modal
 *   input[type=hidden]  valor (códigos concatenados e ordenados)
 *   .it-multi-val       botão de abertura (chip com rótulo)
 * O <dialog> é criado lazy no primeiro clique (funciona em linhas __IDX__
 * adicionadas dinamicamente via delegação de eventos). */
(function () {
  'use strict';

  function multiLabel(options, val) {
    if (!val) return '—';
    var parts = [];
    var s = String(val);
    for (var i = 0; i < s.length; i++) {
      var l = options[s[i]];
      parts.push(l !== undefined ? l : s[i]);
    }
    return parts.length ? parts.join(', ') : val;
  }

  function getDialog() {
    var d = document.getElementById('multiModal');
    if (d) return d;
    d = document.createElement('dialog');
    d.id = 'multiModal';
    d.className = 'modal';
    d.innerHTML = [
      '<div class="modal-box">',
      '  <h3 class="font-bold text-lg text-center" id="multiModalTitle">Opções</h3>',
      '  <label class="flex items-center gap-2 cursor-pointer py-1 select-none" for="multiCheckAll">',
      '    <input type="checkbox" class="checkbox checkbox-sm" id="multiCheckAll">',
      '    <span class="text-sm font-medium">Tudo</span>',
      '  </label>',
      '  <hr style="border:0;border-top:1px solid var(--fallback-b3, oklch(var(--b3)));margin:0.5rem 0;">',
      '  <div id="multiModalOptions" class="py-3 flex flex-col gap-1.5" style="max-height:65vh;overflow:auto;"></div>',
      '  <hr style="border:0;border-top:1px solid var(--fallback-b3, oklch(var(--b3)));margin:0.5rem 0;">',
      '  <div class="modal-action justify-between">',
      '    <button type="button" class="btn btn-ghost" id="multiModalCancel">Cancelar</button>',
      '    <button type="button" class="btn btn-success" id="multiModalOk">',
      '      <svg class="w-4 h-4" aria-hidden="true"><use href="#i-check"/></svg> OK',
      '    </button>',
      '  </div>',
      '</div>'
    ].join('\n');
    document.body.appendChild(d);
    d.querySelector('#multiModalOk').addEventListener('click', multiModalOk);
    d.querySelector('#multiModalCancel').addEventListener('click', multiModalCancel);
    return d;
  }

  function openMultiCtl(btn) {
    var ctl = btn.closest('.multi-ctl');
    if (!ctl || ctl.getAttribute('data-multi-disabled')) return;
    var hidden = ctl.querySelector('input[type=hidden]');
    var options;
    try { options = JSON.parse(ctl.getAttribute('data-multi-options') || '{}') || {}; }
    catch (e) { options = {}; }
    var title = ctl.getAttribute('data-multi-title') || 'Opções';
    var current = hidden ? hidden.value : '';
    getDialog();
    var box = document.getElementById('multiModalOptions');
    box.innerHTML = '';
    var selected = {};
    var s = String(current || '');
    for (var i = 0; i < s.length; i++) selected[s[i]] = true;
    var keys = Object.keys(options);
    keys.sort();
    for (var j = 0; j < keys.length; j++) {
      var k = keys[j];
      var label = document.createElement('label');
      label.className = 'flex items-center gap-2 cursor-pointer';
      var cb = document.createElement('input');
      cb.type = 'checkbox'; cb.value = k; cb.className = 'checkbox checkbox-sm';
      cb.checked = !!selected[k];
      label.appendChild(cb);
      var span = document.createElement('span');
      span.className = 'text-sm'; span.textContent = options[k];
      label.appendChild(span);
      box.appendChild(label);
    }
    document.getElementById('multiModalTitle').textContent = title;
    var checkAll = document.getElementById('multiCheckAll');
    if (checkAll) {
      checkAll.checked = false;
      checkAll.indeterminate = false;
      checkAll.onchange = function() {
        var all = box.querySelectorAll('input[type=checkbox]');
        for (var i = 0; i < all.length; i++) all[i].checked = checkAll.checked;
      };
      box.onclick = function() {
        var all = box.querySelectorAll('input[type=checkbox]');
        var n = all.length, c = 0;
        for (var i = 0; i < n; i++) if (all[i].checked) c++;
        checkAll.checked = (n > 0 && c === n);
        checkAll.indeterminate = (c > 0 && c < n);
      };
      box.onclick();
    }
    window._multiState = { ns: hidden ? hidden.name : '', options: options, hidden: hidden };
    document.getElementById('multiModal').showModal();
  }

  function multiModalOk() {
    var st = window._multiState;
    if (!st) return;
    var codes = [];
    var checks = document.querySelectorAll('#multiModalOptions input[type=checkbox]');
    for (var i = 0; i < checks.length; i++) if (checks[i].checked) codes.push(checks[i].value);
    codes.sort();
    var v = codes.join('');
    var all = document.querySelectorAll('input[name="' + st.ns + '"]');
    for (var n = 0; n < all.length; n++) {
      var h = all[n];
      h.value = v;
      var c = h.closest('.multi-ctl');
      if (c) {
        var lbl = c.querySelector('.it-multi-label');
        if (lbl) lbl.textContent = multiLabel(st.options, v);
      }
    }
    window._multiState = null;
    if (window.marcarFormAlterado) marcarFormAlterado();
    document.getElementById('multiModal').close();
  }

  function multiModalCancel() {
    window._multiState = null;
    document.getElementById('multiModal').close();
  }

  document.addEventListener('click', function(e) {
    var btn = e.target && e.target.closest ? e.target.closest('.multi-ctl .it-multi-val') : null;
    if (btn) openMultiCtl(btn);
  });
})();
