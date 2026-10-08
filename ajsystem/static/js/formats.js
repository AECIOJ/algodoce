/* FORMATS — formatação e parse de valores no cliente (espelho de
   `core/formats.py`). Carregado ANTES do inline JS de sys.html.
   Contém: máscaras com tokens de data/hora (inclui derivados ddd/mmm) e
   alfanuméricos (A/N/#), comandos de máscara @U/L/C/T/@R, `format(value,
   mask)` para qualquer valor, números/moeda pt-BR, data. Validação
   (CPF/CNPJ) fica em validators.js. */
var _AJM = (window.AJ_MASK || {});
var _DEC = _AJM.DECIMAL || '.';
var _THOU = _AJM.THOUSAND || ',';
var _MONEY = _AJM.MONEY || { USD: '$' };
var _DEF_MONEY = _AJM.DEFAULT_MONEY || 'USD';
var _PT_DOW = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom'];
var _PT_MES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun',
               'jul', 'ago', 'set', 'out', 'nov', 'dez'];
var _MASK_TOKENS = ['aaaa', 'yyyy', 'mmm', 'ddd', 'aa', 'yy', 'dd', 'mm', 'hh', 'ii', 'ss', '9', 'A', 'N', '#'];
var _MASK_COMMANDS = ['B', 'C', 'L', 'M', 'R', 'T', 'U', 'X'];
var _TEXT_COMMANDS = ['U', 'L', 'C', 'T'];
var _MASK_CONNECTORS = ['de', 'da', 'do', 'das', 'dos', 'para', 'pra', 'com', 'sem',
                        'em', 'no', 'na', 'nos', 'nas', 'por', 'ao', 'aos', 'às', 'e',
                        'ou', 'a', 'o', 'as', 'os', 'um', 'uma', 'uns', 'umas', 'num',
                        'numa', 'dum', 'duma', 'pelo', 'pela', 'pelos', 'pelas', 'pro',
                        'pros', 'pras'];
function _maskDigits(v) {
  return (v || '').replace(/\D/g, '');
}
function _maskParseCommands(mask) {
  if (!mask) return { cmds: [], display: '', money: null };
  var s = String(mask).replace(/^\s+|\s+$/g, '');
  var cmds = [], money = null, i = 0;
  while (i < s.length && s.charAt(i) === '@') {
    var j = i + 1, letters = '';
    while (j < s.length && _MASK_COMMANDS.indexOf(s.charAt(j)) >= 0) { letters += s.charAt(j); j++; }
    if (!letters) throw new Error("MASK: comando desconhecido '@" + (s.charAt(i + 1) || '') + "' em " + mask);
    for (var k = 0; k < letters.length; k++) cmds.push(letters[k]);
    i = j;
    if (letters.indexOf('M') >= 0 && s.charAt(i) === '(') {
      var close = s.indexOf(')', i + 1);
      if (close < 0) throw new Error("MASK: ')' ausente no money de " + mask);
      money = s.slice(i + 1, close).replace(/^\s+|\s+$/g, '') || null;
      i = close + 1;
    }
    if (s.charAt(i) === '@') continue;
    break;
  }
  var display = s.slice(i).replace(/^[ \t]+/, '');
  if (display.charAt(0) === '@') throw new Error('MASK: comandos devem ser contíguos em ' + mask);
  return { cmds: cmds, display: display, money: money };
}
function _hasDateTokens(mask) {
  if (!mask) return false;
  return /ddd|mmm|aaaa|yyyy|aa|yy|dd|mm|hh|ii|ss/.test(_maskParseCommands(mask).display);
}
function _maskTokenize(mask) {
  var toks = [], i = 0, k;
  while (i < mask.length) {
    var t = null;
    for (k = 0; k < _MASK_TOKENS.length; k++) {
      if (mask.substr(i, _MASK_TOKENS[k].length) === _MASK_TOKENS[k]) { t = _MASK_TOKENS[k]; break; }
    }
    if (t) { toks.push(t); i += t.length; }
    else { toks.push(mask[i]); i++; }
  }
  return toks;
}
function _maskTokenSpec(tok) {
  var n = parseInt(tok, 10), w;
  if (tok === '9' || (!isNaN(n) && tok.length >= 1 && /^9+$/.test(tok))) return { key: 'd', w: tok.length };
  if (tok === 'A') return { key: 'A', w: 1 };
  if (tok === 'N') return { key: 'N', w: 1 };
  if (tok === '#') return { key: 'x', w: 1 };
  if (tok === 'dd' || tok === 'mm' || tok === 'hh' || tok === 'ii' || tok === 'ss' || tok === 'aa' || tok === 'yy') return { key: tok === 'mm' ? 'M' : tok === 'ii' ? 'm' : tok === 'dd' ? 'd' : tok === 'hh' ? 'h' : tok === 'ss' ? 's' : 'y', w: 2 };
  if (tok === 'aaaa' || tok === 'yyyy') return { key: 'Y', w: 4 };
  if (tok === 'ddd' || tok === 'mmm') return { key: tok, w: 0 };
  return null;
}
function _maskTokOk(c, spec) {
  if (spec.key === 'd' || spec.key === 'M' || spec.key === 'm' || spec.key === 'h' || spec.key === 's' || spec.key === 'y' || spec.key === 'Y') return /[0-9]/.test(c);
  if (spec.key === 'A') return /[A-Za-z]/.test(c);
  if (spec.key === 'N') return /[A-Za-z0-9]/.test(c);
  if (spec.key === 'x') return !/[A-Za-z]/.test(c);
  return false;
}
function _maskDerived(tok, f) {
  if (f.d && f.d.length === 2 && f.M && f.M.length === 2 && f.Y && f.Y.length === 4) {
    var d = parseInt(f.d, 10), m = parseInt(f.M, 10), y = parseInt(f.Y, 10);
    var dt = new Date(y, m - 1, d);
    if (dt.getFullYear() === y && dt.getMonth() === m - 1 && dt.getDate() === d) {
      if (tok === 'ddd') return _PT_DOW[(dt.getDay() + 6) % 7];
      if (tok === 'mmm') return _PT_MES[m - 1];
    }
  }
  return '';
}
function _applyMask(text, mask) {
  var toks = _maskTokenize(mask), f = {}, consumed = [], out = '', si = 0, i, spec;
  for (i = 0; i < toks.length; i++) {
    spec = _maskTokenSpec(toks[i]);
    if (spec && spec.w) {
      var got = '';
      while (got.length < spec.w && si < text.length) {
        var c = text[si];
        if (_maskTokOk(c, spec)) { got += c; si++; }
        else if (!/[A-Za-z0-9]/.test(c)) { si++; }
        else { break; }
      }
      if (got.length) f[spec.key] = (f[spec.key] || '') + got;
      consumed.push(got);
    } else {
      consumed.push('');
    }
  }
  for (i = 0; i < toks.length; i++) {
    spec = _maskTokenSpec(toks[i]);
    if (spec && spec.w) out += consumed[i];
    else if (toks[i] === 'ddd' || toks[i] === 'mmm') out += _maskDerived(toks[i], f);
    else out += toks[i];
  }
  return out;
}
function _maskEl(el) {
  var mask = el.getAttribute('data-mask');
  if (!mask) return;
  if (!el.value) { el.value = ''; return; }
  el.value = _applyMask(_maskStrip(el.value, mask), mask);
}
function _maskStrip(text, mask) {
  var toks = _maskTokenize(mask || ''), s = String(text || ''), out = '', si = 0, i, spec, n;
  for (i = 0; i < toks.length && si < s.length; i++) {
    spec = _maskTokenSpec(toks[i]);
    if (!spec || !spec.w) continue;
    while (si < s.length && !_maskTokOk(s[si], spec)) si++;
    n = 0;
    while (n < spec.w && si < s.length && _maskTokOk(s[si], spec)) { out += s[si]; si++; n++; }
  }
  return out;
}
function _maskTitleCase(text) {
  var words = String(text || '').trim().split(/\s+/), out = [], i, w, lw;
  for (i = 0; i < words.length; i++) {
    w = words[i];
    if (!w) continue;
    lw = w.toLowerCase();
    if (i > 0 && _MASK_CONNECTORS.indexOf(lw) >= 0) out.push(lw);
    else out.push(w.charAt(0).toUpperCase() + lw.slice(1));
  }
  return out.join(' ');
}
function _applyMaskCmds(text, cmds) {
  for (var k = 0; k < _TEXT_COMMANDS.length; k++) {
    if (cmds.indexOf(_TEXT_COMMANDS[k]) >= 0) {
      var cmd = _TEXT_COMMANDS[k], s = String(text);
      if (cmd === 'U') return s.toUpperCase();
      if (cmd === 'L') return s.toLowerCase();
      if (cmd === 'C') return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
      if (cmd === 'T') return _maskTitleCase(s);
    }
  }
  return text;
}
function _maskCmdTransform(text, cmds) {
  if (text === null || text === undefined) return text;
  var s = String(text);
  if (cmds.indexOf('U') >= 0) return s.toUpperCase();
  if (cmds.indexOf('L') >= 0) return s.toLowerCase();
  if (cmds.indexOf('C') >= 0) return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
  if (cmds.indexOf('T') >= 0) return _maskTitleCase(s);
  return s;
}
function _fmtMaskDigits(text, display) {
  var digits = String(text || '').replace(/\D/g, '');
  var out = '', di = 0;
  for (var i = 0; i < display.length; i++) {
    if (display[i] === '9') {
      if (di < digits.length) { out += digits[di]; di++; } else break;
    } else out += display[i];
  }
  return out;
}
function _fmtMaskAlpha(text, display) {
  var s = String(text || ''), out = '', si = 0, spec, ch;
  for (var i = 0; i < display.length; i++) {
    if (si >= s.length) break;
    ch = display[i];
    if (ch === '9' || ch === 'A' || ch === 'N' || ch === '#') {
      spec = { key: ch === '9' ? 'd' : ch === 'A' ? 'A' : ch === 'N' ? 'N' : 'x', w: 1 };
      while (si < s.length && !_maskTokOk(s[si], spec)) si++;
      if (si >= s.length) break;
      out += s[si]; si++;
    } else {
      out += ch;
    }
  }
  return out;
}
function _fmtMaskData(d, display) {
  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  function pad4(n) { return (n < 10 ? '000' : n < 100 ? '00' : n < 1000 ? '0' : '') + n; }
  var rep = {};
  var y = d.getFullYear(), m = d.getMonth() + 1, dd = d.getDate();
  rep['aaaa'] = pad4(y); rep['yyyy'] = pad4(y);
  rep['aa'] = pad2(y % 100); rep['yy'] = pad2(y % 100);
  rep['mmm'] = _PT_MES[m - 1]; rep['mm'] = pad2(m); rep['dd'] = pad2(dd);
  rep['ddd'] = _PT_DOW[(d.getDay() + 6) % 7];
  rep['hh'] = pad2(d.getHours()); rep['ii'] = pad2(d.getMinutes()); rep['ss'] = pad2(d.getSeconds());
  var digits = pad2(dd) + pad2(m) + pad4(y);
  var toks = _maskTokenize(display), out = '', di = 0, i, tok, spec;
  for (i = 0; i < toks.length; i++) {
    tok = toks[i];
    spec = _maskTokenSpec(tok);
    if (tok === '9') {
      if (di < digits.length) { out += digits[di]; di++; } else break;
    } else if (spec && rep[tok]) {
      out += rep[tok];
    } else {
      out += tok;
    }
  }
  return out;
}
function fmtMask(value, mask) {
  if (value === null || value === undefined) return '';
  var p = _maskParseCommands(mask || '');
  var cmds = p.cmds, display = p.display;
  if (display && _hasDateTokens(display) && value instanceof Date && !isNaN(value.getTime())) {
    return _applyMaskCmds(_fmtMaskData(value, display), cmds);
  }
  if (display && /[AN#]/.test(display)) {
    return _applyMaskCmds(_fmtMaskAlpha(String(value), display), cmds);
  }
  if (display) {
    return _applyMaskCmds(_fmtMaskDigits(String(value), display), cmds);
  }
  return _applyMaskCmds(String(value), cmds);
}
function _maskDecimals(display) {
  if (!display || display.indexOf('.') < 0) return null;
  var tail = display.slice(display.lastIndexOf('.') + 1);
  if (!tail || /[^09]/.test(tail)) return null;
  return tail.length;
}
function _groupDigits(digits, sep) {
  var out = [];
  while (digits.length > 3) { out.unshift(digits.slice(-3)); digits = digits.slice(0, -3); }
  out.unshift(digits);
  return out.join(sep);
}
function _renderNumMask(value, display) {
  var intPart = (display || '').split('.')[0].replace(/,/g, '');
  var decPart = (display || '').indexOf('.') >= 0 ? display.split('.')[1] : '';
  var dec = (decPart.match(/[09]/g) || []).length;
  var group = (display || '').indexOf(',') >= 0;
  var padInt = intPart.indexOf('0') >= 0;
  var widthInt = (intPart.match(/[09]/g) || []).length;
  var n = Number(value);
  var neg = n < 0;
  var parts = Math.abs(n).toFixed(dec).split('.');
  var ip = parts[0];
  if (padInt && widthInt) { while (ip.length < widthInt) ip = '0' + ip; }
  if (group) ip = _groupDigits(ip, _THOU);
  return (neg ? '-' : '') + ip + (dec ? _DEC + parts[1] : '');
}
function _fmtDec(value, dec, group) {
  var n = Number(value) || 0;
  var neg = n < 0;
  var parts = Math.abs(n).toFixed(dec === undefined ? 2 : dec).split('.');
  var ip = (group === false) ? parts[0] : _groupDigits(parts[0], _THOU);
  return (neg ? '-' : '') + ip + (parts[1] ? _DEC + parts[1] : '');
}
/* format(value, mask): número → máscara canônica (+ `@M(id)`); data/string → fmtMask. */
function _isNumMask(display) {
  /* canônica numérica: só `0`/`9`/`,`/`.` — máscara de texto/documento (CPF
     `999.999.999-99`, tel `(99) 99999-9999`) tem literais → caminho de texto. */
  if (!display) return false;
  return /^[09,.]*$/.test(display);
}
function format(value, mask) {
  if (value === null || value === undefined) return '';
  if (typeof value !== 'number' || isNaN(value)) {
    if (value instanceof Date && !isNaN(value.getTime())) return fmtMask(value, mask);
    return fmtMask(String(value), mask);
  }
  var p = _maskParseCommands(mask);
  if (p.display && !_isNumMask(p.display)) return fmtMask(String(value), mask);
  if (p.cmds.indexOf('B') >= 0 && value === 0) return '';
  var dec = _maskDecimals(p.display);
  var mid = p.money;
  if (!mid && p.cmds.indexOf('M') >= 0) mid = _DEF_MONEY;
  var base;
  if (mid) {
    var sym = _MONEY[mid] || '';
    var body = p.display ? _renderNumMask(value, p.display)
                         : _fmtDec(value, dec === null ? 2 : dec, true);
    base = (sym ? sym + ' ' : '') + body;
  } else if (p.display) {
    base = _renderNumMask(value, p.display);
  } else {
    base = _fmtDec(value, dec === null ? 2 : dec, true);
  }
  if (p.cmds.indexOf('X') >= 0) base += value < 0 ? ' D' : (value > 0 ? ' C' : '');
  return base;
}
/* ── moeda (totais, sessões, cálculos) — separadores/símbolos do app ─────── */
function itNormalizeCurrency(cur) {
  if (cur === undefined || cur === null || cur === 0 || cur === false) return _DEF_MONEY;
  if (cur === true) return _DEF_MONEY;
  var s = String(cur).trim();
  if (s === '') return _DEF_MONEY;
  var low = s.toLowerCase();
  if (low === 'brl' || low === 'real' || low === 'true' || low === 'sim' || low === '1') return _DEF_MONEY;
  if (_MONEY[s]) return s;
  if (s === '2') return _MONEY.USD ? 'USD' : _DEF_MONEY;
  if (s === '3') return _MONEY.EUR ? 'EUR' : _DEF_MONEY;
  return _DEF_MONEY;
}
function itFmtMoney(v, cur) {
  var mid = itNormalizeCurrency(cur);
  var sym = _MONEY[mid] || '';
  return (sym ? sym + ' ' : '') + _fmtDec(Number(v) || 0, 2, true);
}
/* ── numéricos (inputs com data-num-decimals) — separadores do app ─────────
   Leitura: parseNum aceita os separadores do app. Escrita: fmtFieldInput
   formata pela casa do field no blur e após preenchimentos; vazio/inválido
   não é tocado. */
function parseNum(v) {
  if (v === null || v === undefined) return NaN;
  var s = String(v).replace(/\s/g, '');
  if (s === '') return NaN;
  s = s.replace(/[^0-9\-,\.]/g, '');
  if (s === '' || s === '-' || s === '.' || s === ',') return NaN;
  if (_THOU && _THOU !== _DEC && s.indexOf(_THOU) >= 0) s = s.split(_THOU).join('');
  if (_DEC !== '.') s = s.split(_DEC).join('.');
  var n = parseFloat(s);
  return isNaN(n) ? NaN : n;
}
/* ── input numérico: o valor *desformatado* do campo ────────────────────────
   `parseNum` acima lê o texto já na convenção do app (milhar agrupado). Mas o
   input numérico guarda o valor na convenção do CAMPO, e nem sempre é a mesma:
   com `data-num-decimals` ele sai de `fmtNumBR`/`fmt_num` (vírgula decimal);
   sem `decimals` o campo não agrupa — é o que `fmt_num` documenta para a
   leitura de volta ser inequívoca — e o que vem por `on_set` chega cru, como
   `str(Decimal)` ('6.00'). Nesse caso `parseNum` lê '6.00' como milhar e
   devolve 600. É a regra de `_coerce` (core/form.py): vírgula presente = o
   decimal é o do app e o ponto é milhar; sem vírgula, o ponto é decimal. Como
   o servidor vai ler o MESMO texto no POST, ler igual aqui é o que mantém o
   cálculo e o salvamento falando do mesmo número. */
function parseNumText(v) {
  if (v === null || v === undefined) return NaN;
  var s = String(v).replace(/\s/g, '');
  if (s === '') return NaN;
  s = s.replace(/[^0-9\-,\.]/g, '');
  if (s === '' || s === '-' || s === '.' || s === ',') return NaN;
  if (_DEC && s.indexOf(_DEC) >= 0) {
    if (_THOU && _THOU !== _DEC) s = s.split(_THOU).join('');
    s = s.split(_DEC).join('.');
  }
  var n = parseFloat(s);
  return isNaN(n) ? NaN : n;
}
function parseNumField(el) { return el ? parseNumText(el.value) : NaN; }
/* Escrita: valor que entra programaticamente (on_set, botões) sai na convenção
   do campo alvo, para o input continuar legível e o POST mandar o texto que
   `_coerce`/`parse_brl` vão ler. Espelha `fmt_num`. */
function numToInput(v, dec) {
  var n = Number(v);
  if (isNaN(n)) return null;
  if (dec === null || dec === undefined) {
    if (n % 1 === 0) return String(n);
    return String(n).replace('.', _DEC);
  }
  return _fmtDec(n, dec, true);
}
function numToInputFor(el, v) {
  var d = (el && el.getAttribute) ? el.getAttribute('data-num-decimals') : null;
  var dec = (d === null || d === '') ? null : parseInt(d, 10);
  if (isNaN(dec)) dec = null;
  return numToInput(v, dec);
}
function numDecimals(el) {
  if (!el || el.disabled) return null;
  var d = el.getAttribute('data-num-decimals');
  if (d === null || d === '') return null;
  var n = parseInt(d, 10);
  return isNaN(n) ? null : n;
}
function fmtNumBR(v, dec) {
  var n = Number(v);
  if (isNaN(n)) return null;
  if (!dec) return String(Math.round(n));
  return _fmtDec(n, dec, true);
}
function fmtFieldInput(el) {
  var dec = numDecimals(el);
  if (dec === null) return false;
  var raw = el.value;
  if (raw === null || raw === undefined || String(raw).trim() === '') return false;
  var s = String(raw);
  var f = (!dec) ? s.trim() : fmtNumBR(parseNum(s), dec);
  if (f === null || f === undefined || f === s) return false;
  el.value = f;
  el.dispatchEvent(new Event('input', {bubbles: true}));
  el.dispatchEvent(new Event('change', {bubbles: true}));
  return true;
}
/* ── data (parse de cel. DD/MM/YYYY p/ ordenação) ────────────────────────── */
function parseDate(str) {
  var m = str.match(/(\d{2})\/(\d{2})\/(\d{4})/);
  if (m) return new Date(+m[3], +m[2] - 1, +m[1]);
  return null;
}