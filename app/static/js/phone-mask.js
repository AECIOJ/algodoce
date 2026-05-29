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

  document.addEventListener('DOMContentLoaded', function() {
    var input = document.querySelector('input[name="telefone"]');
    if (input) phoneMask(input);
  });
})();
