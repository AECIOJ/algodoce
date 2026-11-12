/* ── ajsystem/static/js/dates.js ──
   Funções compartilhadas de data/calendário (flatpickr + auto-complete dd/mm/aaaa).
   Incluído em page_layout.html → disponível em todas as páginas (sys e site). ── */

function dtSyncFilled(root) {
  (root || document).querySelectorAll('input[type="date"], input[type="datetime-local"], input[type="time"]').forEach(function(el) {
    if (el.value) el.setAttribute('data-filled', '1');
    else el.removeAttribute('data-filled');
  });
}
window.dtSyncFilled = dtSyncFilled;

// Inputs de data: preenchimento automático quando o usuário digita apenas dia
// (usa mês/ano corrente) ou dia+mês (usa ano corrente). Formato dd/mm/aaaa.
function _dtCompleteOne(el) {
  var v = el.value.trim();
  if (!v) return false;
  var now = new Date();
  var yy = String(now.getFullYear());
  var mm = String(now.getMonth() + 1).padStart(2, '0');
  var dd = String(now.getDate()).padStart(2, '0');
  var m;
  // YYYY-MM-DD (ISO) — converte para brasileiro dd/mm/aaaa
  if (/^\d{4}-\d{2}-\d{2}$/.test(v)) {
    var parts = v.split('-');
    el.value = parts[2] + '/' + parts[1] + '/' + parts[0];
    return true;
  }
  // Apenas dígitos: DD (dia) ou DDMM (dia+mês)
  if (m = /^(\d{1,2})$/.exec(v)) {
    var d = String(parseInt(m[1], 10)).padStart(2, '0');
    el.value = d + '/' + mm + '/' + yy;
    return true;
  }
  if (m = /^(\d{1,2})(\d{2})$/.exec(v)) {
    var d = String(parseInt(m[1], 10)).padStart(2, '0');
    var mo = String(parseInt(m[2], 10)).padStart(2, '0');
    el.value = d + '/' + mo + '/' + yy;
    return true;
  }
  // DD/MM (com barra)
  if (m = /^(\d{1,2})\/(\d{1,2})$/.exec(v)) {
    var d = String(parseInt(m[1], 10)).padStart(2, '0');
    var mo = String(parseInt(m[2], 10)).padStart(2, '0');
    el.value = d + '/' + mo + '/' + yy;
    return true;
  }
  // DD/MM/AAAA (completo) — não altera
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(v)) return false;
  return false;
}

function dtAutoComplete(root) {
  var changed = false;
  (root || document).querySelectorAll('.it-dtwrap input[type="text"]').forEach(function(el) {
    el.addEventListener('blur', function() {
      if (_dtCompleteOne(el)) dtSyncFilled();
    });
    if (_dtCompleteOne(el)) changed = true;
  });
  if (changed) dtSyncFilled();
}
window.dtAutoComplete = dtAutoComplete;

function initFlatpickr() {
  document.querySelectorAll('.it-dtwrap input[data-datepicker="1"]').forEach(function(input) {
    var fmt = input.getAttribute('data-fp-format') || 'd/m/Y';
    var fp = flatpickr(input, {
      dateFormat: fmt,
      altInput: false,
      allowInput: true,
      clickOpens: false,
      onChange: function(selectedDates, dateStr, instance) {
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        if (typeof dtSyncFilled === 'function') dtSyncFilled();
      }
    });
    input._fp = fp;
  });
}
window.initFlatpickr = initFlatpickr;

// Abre o calendário Flatpickr do input texto vizinho ao botão clicado.
function openDatePicker(btn) {
  var wrap = btn.closest('.it-dtwrap');
  if (!wrap) return;
  var input = wrap.querySelector('input[data-datepicker="1"]');
  if (!input || !input._fp) return;
  input._fp.open();
  input.focus();
}
window.openDatePicker = openDatePicker;

// Inicializa quando o DOM estiver pronto
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function() {
    initFlatpickr();
    dtAutoComplete();
    dtSyncFilled();
  });
} else {
  initFlatpickr();
  dtAutoComplete();
  dtSyncFilled();
}
