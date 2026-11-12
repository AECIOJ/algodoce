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

function dtAutoComplete(root) {
  // Mantido para compatibilidade (chamado em sys.html linha 363).
  // O auto-complete de dia agora é feito pelo parseDate customizado do flatpickr.
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
      // Auto-complete de data: se o usuário digitar apenas o dia (ex: "20"),
      // completa com mês/ano atuais. Se digitar dia+mês (ex: "2011" ou "20/11"),
      // completa com o ano atual. Valida dias inválidos (ex: 31 de fevereiro).
      parseDate: function(datestr, format) {
        var valorLimpo = String(datestr || '').trim();
        if (!valorLimpo) return null;

        // Apenas dígitos: DD (dia) ou DDMM (dia+mês)
        var m = valorLimpo.match(/^(\d{1,2})$/);
        if (m) {
          var dia = parseInt(m[1], 10);
          if (dia >= 1 && dia <= 31) {
            var hoje = new Date();
            var mes = hoje.getMonth();
            var ano = hoje.getFullYear();
            var dataCriada = new Date(ano, mes, dia);
            // Garante que o JS não pulou para o mês seguinte (ex: 31 de fevereiro)
            if (dataCriada.getMonth() === mes) {
              return dataCriada;
            }
          }
          return null;
        }

        // DDMM (dia+mês, 4 dígitos)
        m = valorLimpo.match(/^(\d{1,2})(\d{2})$/);
        if (m) {
          var dia = parseInt(m[1], 10);
          var mes = parseInt(m[2], 10) - 1;
          if (dia >= 1 && dia <= 31 && mes >= 0 && mes <= 11) {
            var hoje = new Date();
            var ano = hoje.getFullYear();
            var dataCriada = new Date(ano, mes, dia);
            if (dataCriada.getMonth() === mes) {
              return dataCriada;
            }
          }
          return null;
        }

        // DD/MM (com barra)
        m = valorLimpo.match(/^(\d{1,2})\/(\d{1,2})$/);
        if (m) {
          var dia = parseInt(m[1], 10);
          var mes = parseInt(m[2], 10) - 1;
          if (dia >= 1 && dia <= 31 && mes >= 0 && mes <= 11) {
            var hoje = new Date();
            var ano = hoje.getFullYear();
            var dataCriada = new Date(ano, mes, dia);
            if (dataCriada.getMonth() === mes) {
              return dataCriada;
            }
          }
          return null;
        }

        // DD/MM/AAAA completo ou ISO — usa o parser padrão do Flatpickr
        return flatpickr.parseDate(datestr, format);
      },
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
