function container(el) {
  return el.closest('tr') || el.closest('.item-mobile-card');
}

function capturarPreco(select) {
  const opt = select.options[select.selectedIndex];
  const precoTotal = opt && parseFloat(opt.dataset.preco);
  if (opt && !isNaN(precoTotal)) {
    const c = container(select);
    const precoInput = c.querySelector('.preco-input');
    const qtdMinima = parseInt(opt.dataset.qtdMinima) || 1;
    precoInput.value = fmt_brl(preco_unit(precoTotal, qtdMinima));
    calcValor(precoInput);
  }
}

function fmt_brl(valor) {
  return valor.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

function preco_unit(valor, qtd) {
  if (!valor) return 0;
  if (!qtd) return parseFloat(valor);
  return parseFloat(valor) / parseFloat(qtd);
}

function atualizarPrecos() {
  markModified();
  document.querySelectorAll('.product-select').forEach(function(select) {
    const c = container(select);
    if (!c) return;
    const precoInput = c.querySelector('.preco-input');
    if (!precoInput.value || parseFloat(precoInput.value.replace(/\./g, '').replace(',', '.')) === 0) {
      const opt = select.options[select.selectedIndex];
      if (opt && opt.dataset.preco) {
        const precoTotal = parseFloat(opt.dataset.preco);
        const qtdMinima = parseInt(opt.dataset.qtdMinima) || 1;
        precoInput.value = fmt_brl(preco_unit(precoTotal, qtdMinima));
        calcValor(precoInput);
      }
    }
  });
}

function calcValor(el) {
  const c = container(el);
  if (!c) return;
  const qtd = parseFloat(c.querySelector('[name="quantidade"]').value) || 0;
  const precoInput = c.querySelector('.preco-input');
  const preco = parseFloat((precoInput.value || '').replace(/\./g, '').replace(',', '.')) || 0;
  precoInput.classList.toggle('bg-warning', preco === 0);
  const valor = qtd * preco;
  c.querySelector('.valor-item').textContent = 'R$ ' + fmt_brl(valor);
  calcTotal();
}

let modified = false;

function markModified() {
  if (modified) return;
  modified = true;
  const btn = document.querySelector('button[type="submit"].btn-primary');
  if (btn) btn.disabled = false;
}

document.addEventListener('DOMContentLoaded', function() {
  const form = document.querySelector('form[data-editing]');
  if (form) {
    const btn = form.querySelector('button[type="submit"].btn-primary');
    if (btn) btn.disabled = true;
    form.addEventListener('input', markModified);
    form.addEventListener('change', markModified);
    form.addEventListener('submit', function() {
      if (btn) btn.disabled = false;
    });
  }

  document.querySelectorAll('.preco-input').forEach(function(input) {
    const val = parseFloat((input.value || '').replace(/\./g, '').replace(',', '.')) || 0;
    input.classList.toggle('bg-warning', val === 0);
  });

  const telInput = document.querySelector('input[name="cliente_telefone"]');
  if (telInput && !telInput.readOnly) {
    telInput.addEventListener('input', function() {
      let v = this.value.replace(/\D/g, '');
      if (v.length > 11) v = v.slice(0, 11);
      if (v.length > 6) {
        v = '(' + v.slice(0, 2) + ') ' + v.slice(2, 7) + '-' + v.slice(7);
      } else if (v.length > 2) {
        v = '(' + v.slice(0, 2) + ') ' + v.slice(2);
      } else if (v.length > 0) {
        v = '(' + v;
      }
      this.value = v;
    });
  }
});

function calcTotal() {
  const spans = document.querySelectorAll('.valor-item');
  let total = 0;
  spans.forEach(function(s) {
    const txt = s.textContent.replace('R$ ', '').trim();
    const v = parseFloat(txt.replace(/\./g, '').replace(',', '.')) || 0;
    total += v;
  });
  const fmt = 'R$ ' + fmt_brl(total);
  document.getElementById('total-geral').textContent = fmt;
  const mobileTotal = document.getElementById('total-geral-mobile');
  if (mobileTotal) mobileTotal.textContent = fmt;
}
