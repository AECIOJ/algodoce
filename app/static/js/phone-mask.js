(function() {
  function phoneMask(input) {
    input.addEventListener('input', function() {
      let value = this.value.replace(/\D/g, '');
      if (value.length > 11) value = value.slice(0, 11);
      if (value.length > 6) {
        value = '(' + value.slice(0, 2) + ') ' + value.slice(2, 7) + '-' + value.slice(7);
      } else if (value.length > 2) {
        value = '(' + value.slice(0, 2) + ') ' + value.slice(2);
      } else if (value.length > 0) {
        value = '(' + value;
      }
      this.value = value;
    });
  }

  function cpfMask(input) {
    input.addEventListener('input', function() {
      let v = this.value.replace(/\D/g, '').slice(0, 11);
      if (v.length > 9) {
        v = v.slice(0, 3) + '.' + v.slice(3, 6) + '.' + v.slice(6, 9) + '-' + v.slice(9);
      } else if (v.length > 6) {
        v = v.slice(0, 3) + '.' + v.slice(3, 6) + '.' + v.slice(6);
      } else if (v.length > 3) {
        v = v.slice(0, 3) + '.' + v.slice(3);
      }
      this.value = v;
    });
  }

  function cnpjMask(input) {
    input.addEventListener('input', function() {
      let v = this.value.replace(/\D/g, '').slice(0, 14);
      if (v.length > 12) {
        v = v.slice(0, 2) + '.' + v.slice(2, 5) + '.' + v.slice(5, 8) + '/' + v.slice(8, 12) + '-' + v.slice(12);
      } else if (v.length > 8) {
        v = v.slice(0, 2) + '.' + v.slice(2, 5) + '.' + v.slice(5, 8) + '/' + v.slice(8);
      } else if (v.length > 5) {
        v = v.slice(0, 2) + '.' + v.slice(2, 5) + '.' + v.slice(5);
      } else if (v.length > 2) {
        v = v.slice(0, 2) + '.' + v.slice(2);
      }
      this.value = v;
    });
  }

  function maskVal(input, fn) {
    var v = input.value.replace(/\D/g, '');
    if (fn) {
      input.value = '';
      var evt = new Event('input');
      input.addEventListener('input', function() {}, {once: true});
      Object.defineProperty(input, 'value', {
        get: function() { return v; },
        set: function() {}
      });
    }
    input.value = v;
  }

  function applyMasks() {
    document.querySelectorAll('input[name="telefone"], input[name="novo_telefone"]').forEach(function(input) {
      if (!input.dataset.masked) {
        input.dataset.masked = '1';
        phoneMask(input);
        var evt = new Event('input');
        input.dispatchEvent(evt);
      }
    });
    document.querySelectorAll('input[name="cpf"]').forEach(function(input) {
      if (!input.dataset.masked) {
        input.dataset.masked = '1';
        cpfMask(input);
        var evt = new Event('input');
        input.dispatchEvent(evt);
      }
    });
    document.querySelectorAll('input[name="cnpj"]').forEach(function(input) {
      if (!input.dataset.masked) {
        input.dataset.masked = '1';
        cnpjMask(input);
        var evt = new Event('input');
        input.dispatchEvent(evt);
      }
    });
  }

  document.addEventListener('DOMContentLoaded', applyMasks);
})();
