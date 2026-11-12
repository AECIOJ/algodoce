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

function setDate(inputDate) {
  let v = String(inputDate).trim();
  if (!v) return "";

  const ano = new Date().getFullYear();
  const mesAtual = String(new Date().getMonth() + 1).padStart(2, '0');
  let partes = v.split(/[\/\-\.]/);

  if (partes.length === 1) {
    if (v.length <= 2) {
      return `${v.padStart(2, '0')}/${mesAtual}/${ano}`;
    } else if (v.length === 4) {
      return `${v.slice(0, 2)}/${v.slice(2, 4)}/${ano}`;
    }
  } else if (partes.length === 2) {
    return `${partes[0].padStart(2, '0')}/${partes[1].padStart(2, '0')}/${ano}`;
  }

  return v;
}

function dtAutoComplete(root) {
  (root || document).querySelectorAll('.it-dtwrap input[type="text"]').forEach(function(el) {
    el.addEventListener('blur', function() {
      var novoValor = setDate(el.value.trim());
      if (novoValor !== el.value.trim()) {
        el.value = novoValor;
        dtSyncFilled();
      }
    });
  });
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
