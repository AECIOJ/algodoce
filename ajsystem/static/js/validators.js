/* validators.js (ajsystem) — validadores genéricos client-side. Self-contained.
 *
 * Contrato:
 *   - Registro global `window.FieldValidators`:
 *       .register(name, fn)  — registra validador custom (fn(valor) → bool).
 *       .get(name)           — devolve a função ou undefined.
 *       .validate(rule, value) — executa a regra; regra desconhecida ou erro
 *         na função = true (fail-soft: sem JS correspondente, sem bloqueio).
 *   - Validadores built-in recebem DÍGITOS (extração é de quem chama).
 *   - Puro: sem DOM, sem dependências, sem imports do app (portável com o
 *     framework). O espelho Python vive em `ajsystem/defs/validators.py`.
 *   - Versionamento: bump no `?v=` do `<script src>` a cada mudança.
 */
(function () {
  'use strict';

  function cpfOk(d) {
    d = String(d === null || d === undefined ? '' : d);
    if (d.length !== 11 || /^(\d)\1+$/.test(d)) return false;
    var s = 0;
    for (var i = 0; i < 9; i++) s += +d[i] * (10 - i);
    var d1 = (s * 10) % 11 % 11 === 10 ? 0 : (s * 10) % 11;
    if (d1 !== +d[9]) return false;
    s = 0;
    for (var i = 0; i < 10; i++) s += +d[i] * (11 - i);
    var d2 = (s * 10) % 11 % 11 === 10 ? 0 : (s * 10) % 11;
    return d2 === +d[10];
  }

  function cnpjOk(d) {
    d = String(d === null || d === undefined ? '' : d);
    if (d.length !== 14 || /^(\d)\1+$/.test(d)) return false;
    var w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], s = 0;
    for (var i = 0; i < 12; i++) s += +d[i] * w1[i];
    var d1 = s % 11 < 2 ? 0 : 11 - s % 11;
    if (d1 !== +d[12]) return false;
    var w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]; s = 0;
    for (var i = 0; i < 13; i++) s += +d[i] * w2[i];
    var d2 = s % 11 < 2 ? 0 : 11 - s % 11;
    return d2 === +d[13];
  }

  var registry = {
    cpf: cpfOk,
    cnpj: cnpjOk,
  };

  window.FieldValidators = {
    register: function (name, fn) {
      if (typeof fn === 'function' && name) registry[name] = fn;
    },
    get: function (name) {
      return registry[name];
    },
    validate: function (rule, value) {
      var fn = registry[rule];
      if (typeof fn !== 'function') return true;
      try {
        return !!fn(value);
      } catch (e) {
        return false;
      }
    },
  };
})();
