/* modals.js (ajsystem) — diálogos do framework. Self-contained.
 *
 * Núcleo `ajModal(opts)` (barra com tom + corpo claro, DaisyUI + tema) e
 * adapters: showConfirm, showAlert, showErrorModal, confirmSair,
 * showFieldHelp, searchDialog. Exportados em `window` para os `onclick` dos
 * templates e os fluxos internos (submit, busca).
 * Puro: sem DOM fora do escopo das funções, sem imports do app (portável).
 * Versionamento: bump no `?v=` do `<script src>` a cada mudança.
 */
(function () {
  'use strict';

  function ajModalTone(tone) {
    var tons = (window.AJ_MODAL && window.AJ_MODAL.tons) || {};
    var t = tons[tone];
    if (t && t.fundo) return {bg: t.fundo, fg: t.texto || '#fff'};
    var fb = {
      error:   ['#E53935', '#fff'],
      warning: ['#FB8C00', '#000'],
      info:    ['#0288D1', '#fff'],
      primary: ['#26A69A', '#fff'],
      success: ['#43A047', '#fff'],
    };
    var f = fb[tone] || fb.primary;
    return {bg: f[0], fg: f[1]};
  }

  function ajModalKind(kind) {
    var tipos = (window.AJ_MODAL && window.AJ_MODAL.tipos) || {};
    if (tipos[kind]) return tipos[kind];
    var fb = {erro: 'error', alerta: 'warning', ajuda: 'info',
              confirma: 'primary', busca: 'primary', sair: 'warning'};
    return fb[kind] || 'primary';
  }

  function ajModal(opts) {
    opts = opts || {};
    var tc = ajModalTone(opts.tone || ajModalKind(opts.kind));
    var d = document.createElement('dialog');
    d.className = 'modal';
    var box = document.createElement('div');
  box.className = 'modal-box p-0 overflow-hidden';
  box.style.maxWidth = opts.wide ? 'min(48rem,calc(100vw - 2rem))' : 'min(32rem,calc(100vw - 2rem))';
  box.style.border = '1px solid ' + tc.bg;
    var bar = document.createElement('div');
    bar.className = 'flex items-center gap-2';
    bar.setAttribute('style', 'background:' + tc.bg + ';color:' + tc.fg + ';padding:.75rem 1.5rem');
    if (opts.closable) {
      var xb = document.createElement('button');
      xb.className = 'btn btn-sm btn-circle btn-ghost absolute right-2 top-2';
      xb.setAttribute('style', 'color:inherit;margin-right:.25rem');
      xb.setAttribute('aria-label', 'Fechar');
      xb.innerHTML = '<svg class="w-4 h-4" aria-hidden="true"><use href="#i-xmark"/></svg>';
      xb.addEventListener('click', function() { d.close(); });
      bar.appendChild(xb);
    }
    if (opts.title) {
      var h = document.createElement('h3');
      h.className = 'font-bold text-lg flex items-center gap-2';
      if (opts.icon) {
        var ic = document.createElement('span');
        ic.innerHTML = '<svg style="width:2rem;height:2rem;display:block" aria-hidden="true"><use href="#i-' + opts.icon + '"/></svg> ';
        h.appendChild(ic);
      }
      h.appendChild(document.createTextNode(opts.title));
      bar.appendChild(h);
    }
    box.appendChild(bar);
    var bodyEl = document.createElement('div');
    bodyEl.className = '';
    bodyEl.setAttribute('style', 'padding:1rem 1.5rem');
    if (opts.node && opts.node.appendChild) {
      bodyEl.appendChild(opts.node);
    } else if (opts.html !== undefined && opts.html !== null) {
      var hb = document.createElement('div');
      hb.innerHTML = opts.html;
      bodyEl.appendChild(hb);
    }
    (opts.lines || []).forEach(function(t) {
      var p = document.createElement('p');
      p.className = 'py-1';
      p.setAttribute('style', 'margin-left:.25rem');
      p.textContent = t;
      bodyEl.appendChild(p);
    });
    var cbs = {};
    var btns = opts.buttons || [{label: 'OK', cls: 'btn-primary', value: 'ok'}];
  if (btns.length) {
    var foot = document.createElement('div');
    foot.setAttribute('style', 'background-color:oklch(var(--b2,91.887% 0 0)/1);padding:.5rem 0');
    var form = document.createElement('form');
    form.method = 'dialog';
    form.className = 'modal-action';
    form.setAttribute('style', 'margin:0;padding:0 1.5rem');
      btns.forEach(function(b) {
        b = b || {};
        var btn = document.createElement('button');
        btn.className = 'btn btn-sm ' + (b.cls || 'btn-ghost');
        var val = (b.value === undefined || b.value === null) ? b.label : String(b.value);
        btn.value = val;
        if (b.icon) {
          var bi = document.createElement('span');
          bi.innerHTML = '<svg class="w-4 h-4" aria-hidden="true"><use href="#i-' + b.icon + '"/></svg> ';
          btn.appendChild(bi);
        }
        btn.appendChild(document.createTextNode(b.label || 'OK'));
      if (typeof b.onClick === 'function') cbs[val] = b.onClick;
      form.appendChild(btn);
    });
    foot.appendChild(form);
  }
    box.appendChild(bodyEl);
    if (btns.length) box.appendChild(foot);
    d.appendChild(box);
    d.addEventListener('close', function() {
      var v = d.returnValue;
      try {
        if (cbs[v]) cbs[v]();
        else if (typeof opts.onClose === 'function') opts.onClose(v);
        else if (opts.focus && document.contains(opts.focus) && opts.focus.focus) opts.focus.focus();
      } finally {
        if (d.parentNode) d.parentNode.removeChild(d);
      }
    });
    document.body.appendChild(d);
    if (typeof opts.onOpen === 'function') opts.onOpen(d);
    d.showModal();
    return d;
  }

  function showAlert(msg) {
    ajModal({
      kind: 'alerta', title: 'Atenção', icon: 'exclamation-triangle',
      lines: [msg],
      buttons: [{label: 'OK', cls: 'btn-primary', value: 'ok'}],
    });
  }

  function showConfirm(msg, onConfirm, tone) {
    ajModal({
      kind: 'confirma', tone: tone, title: 'Confirmação', icon: 'question-mark-circle',
      lines: [msg],
      buttons: [
        {label: 'Cancelar', cls: 'btn-ghost', value: 'cancel'},
        {label: 'Confirmar', cls: 'btn-error', value: 'ok', onClick: onConfirm},
      ],
    });
  }

  function showErrorModal(msgs, firstEl) {
    ajModal({
      kind: 'erro', title: 'Verifique os campos', icon: 'exclamation-triangle',
      lines: (msgs || []).map(function(m) { return '• ' + m; }),
      buttons: [{label: 'Entendi', cls: 'btn-error', value: 'ok'}],
      focus: firstEl,
    });
  }

  function confirmSair() {
    if (window._formModified || window.modified) {
      ajModal({
        kind: 'sair', title: 'Há alterações não salvas.',
        lines: ['Sair e descartar alterações?'],
        buttons: [
          {label: 'Cancelar', cls: 'btn-ghost', value: 'cancel'},
          {label: 'Sair', cls: 'btn-error', icon: 'logout', value: 'sair',
           onClick: function() { window.history.back(); }},
        ],
      });
    } else {
      window.history.back();
    }
  }

  function showFieldHelp(btn) {
    var title = btn.getAttribute('data-help-title') || '';
    var items = btn.getAttribute('data-help-items');
    if (items) {
      var obj = null;
      try { obj = JSON.parse(items); } catch (e) { obj = null; }
      if (obj) {
        var table = document.createElement('table');
        table.className = 'table table-sm w-full';
        var thead = document.createElement('thead');
        var trh = document.createElement('tr');
        ['Entrada', 'Descrição'].forEach(function(h) {
          var th = document.createElement('th');
          th.textContent = h;
          trh.appendChild(th);
        });
        thead.appendChild(trh);
        table.appendChild(thead);
        var tbody = document.createElement('tbody');
        Object.keys(obj).forEach(function(k) {
          var tr = document.createElement('tr');
          var td1 = document.createElement('td');
          td1.className = 'font-mono text-xs whitespace-nowrap';
          td1.textContent = k;
          var td2 = document.createElement('td');
          td2.textContent = obj[k];
          tr.appendChild(td1);
          tr.appendChild(td2);
          tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        ajModal({kind: 'ajuda', title: title, closable: true, node: table, buttons: []});
        return;
      }
    }
    var p = document.createElement('p');
    p.className = 'text-sm whitespace-pre-line';
    p.textContent = btn.getAttribute('data-help-text') || '';
    ajModal({kind: 'ajuda', title: title, closable: true, node: p, buttons: []});
  }

  function searchDialog(box, cols, rows) {
    var html = '<div style="max-height:65vh;overflow:auto;margin-top:0.5rem;">'
      + '<table class="table table-sm w-full"><thead><tr>';
    cols.forEach(function(c) { html += '<th class="text-sm">' + c.label + '</th>'; });
    html += '</tr></thead><tbody>';
    if (!rows.length) html += '<tr><td colspan="' + Math.max(cols.length, 1) + '" class="text-center text-sm opacity-60">Nenhum registro.</td></tr>';
    rows.forEach(function(r) {
      var rawAttr = JSON.stringify(r.raw || {}).replace(/'/g, "&#39;");
      html += '<tr data-search-id="' + r.id + '" data-search-raw=\'' + rawAttr + '\' style="cursor:pointer;">';
      r.cells.forEach(function(c) { html += '<td class="text-sm">' + c + '</td>'; });
      html += '</tr>';
    });
    html += '</tbody></table></div>';
    ajModal({
      kind: 'busca', title: 'Buscar', icon: 'magnifying-glass', wide: true,
      html: html,
      buttons: [{label: 'Fechar', cls: 'btn-ghost', value: 'close'}],
      onOpen: function(d) {
        d.querySelectorAll('tr[data-search-id]').forEach(function(tr) {
          tr.addEventListener('click', function() {
            var hid = box.querySelector('input[type="hidden"]');
            var vis = box.querySelector('.search-val');
            if (hid) {
              hid.value = tr.getAttribute('data-search-id');
              hid.dispatchEvent(new Event('change', {bubbles: true}));
            }
            if (vis) vis.textContent = tr.getAttribute('data-search-id');
            searchApplyReplaces(box, hid, tr);
            if (window.marcarFormAlterado) marcarFormAlterado();
            d.close();
          });
        });
      },
    });
  }

  window.ajModal = ajModal;
  window.showConfirm = showConfirm;
  window.showAlert = showAlert;
  window.showErrorModal = showErrorModal;
  window.confirmSair = confirmSair;
  window.showFieldHelp = showFieldHelp;
  window.searchDialog = searchDialog;
})();
