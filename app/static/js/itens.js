function capturarPreco(select) {
  const opt = select.options[select.selectedIndex];
  const precoTotal = opt && parseFloat(opt.dataset.preco);
  if (precoTotal) {
    const row = select.closest('tr');
    const precoInput = row.querySelector('.preco-input');
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
  document.querySelectorAll('#itens-body .item-row').forEach(function(row) {
    const select = row.querySelector('.product-select');
    const precoInput = row.querySelector('.preco-input');
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
  const row = el.closest('tr');
  const qtd = parseFloat(row.querySelector('[name="quantidade"]').value) || 0;
  const precoInput = row.querySelector('.preco-input');
  const preco = parseFloat((precoInput.value || '').replace(/\./g, '').replace(',', '.')) || 0;
  precoInput.classList.toggle('bg-warning', preco === 0);
  const valor = qtd * preco;
  row.querySelector('.valor-item').textContent = 'R$ ' + fmt_brl(valor);
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
  document.getElementById('total-geral').textContent = 'R$ ' + fmt_brl(total);
}
