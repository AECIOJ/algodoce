/* FORMATS — formatação e parse de valores no cliente (espelho de
   `core/formats.py`). Carregado ANTES do inline JS de sys.html.
   Contém: máscaras com tokens de data/hora (inclui derivados ddd/mmm) e
   alfanuméricos (A/N/#), comandos de máscara @U/L/C/T/@R, `format(value,
   mask)` para qualquer valor, números/moeda pt-BR, data. Validação
   (CPF/CNPJ) fica em validators.js. */
var _PT_DOW = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom'];
var _PT_MES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun',
               'jul', 'ago', 'set', 'out', 'nov', 'dez'];
var _MASK_TOKENS = ['aaaa', 'yyyy', 'mmm', 'ddd', 'aa', 'yy', 'dd', 'mm', 'hh', 'ii', 'ss', '9', 'A', 'N', '#'];
var _MASK_COMMANDS = ['B', 'C', 'L', 'R', 'T', 'U', 'X'];
var _TEXT_COMMANDS = ['U', 'L', 'C', 'T'];
var _MASK_CONECTORES = ['de', 'da', 'do', 'das', 'dos', 'para', 'pra', 'com', 'sem',
                        'em', 'no', 'na', 'nos', 'nas', 'por', 'ao', 'aos', 'às', 'e',
                        'ou', 'a', 'o', 'as', 'os', 'um', 'uma', 'uns', 'umas', 'num',
                        'numa', 'dum', 'duma', 'pelo', 'pela', 'pelos', 'pelas', 'pro',
                        'pros', 'pras'];
function _maskDigits(v) {
  return (v || '').replace(/\D/g, '');
}
function _maskParseCommands(mask) {
  if (!mask) return { cmds: [], display: '' };
  var s = String(mask).replace(/^\s+|\s+$/g, '');
  var cmds = [], i = 0;
  while (i < s.length && s.charAt(i) === '@') {
    var j = i + 1, letters = '';
    while (j < s.length && _MASK_COMMANDS.indexOf(s.charAt(j)) >= 0) { letters += s.charAt(j); j++; }
    if (!letters) throw new Error("MASK: comando desconhecido '@" + (s.charAt(i + 1) || '') + "' em " + mask);
    for (var k = 0; k < letters.length; k++) cmds.push(letters[k]);
    i = j;
    if (s.charAt(i) === '@') continue;
    break;
  }
  var display = s.slice(i).replace(/^[ \t]+/, '');
  if (display.charAt(0) === '@') throw new Error('MASK: comandos devem ser contíguos em ' + mask);
  return { cmds: cmds, display: display };
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
    if (i > 0 && _MASK_CONECTORES.indexOf(lw) >= 0) out.push(lw);
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
  if (!display) return null;
  var idx = -1;
  for (var k = 0; k < display.length; k++) if (display[k] === '.' || display[k] === ',') idx = k;
  if (idx < 0) return null;
  var tail = display.slice(idx + 1);
  if (!tail || /[^9]/.test(tail)) return null;
  return tail.length;
}
/* format(value, mask): formata QUALQUER valor por uma máscara.
   Número → render numérico (casas da máscara + comandos B/X);
   Date   → fmtMask (tokens de data); string → fmtMask. */
function format(value, mask) {
  if (value === null || value === undefined) return '';
  if (typeof value === 'number') {
    var p = _maskParseCommands(mask);
    if (p.cmds.indexOf('B') >= 0 && value === 0) return '';
    var base = fmtNumBR(Number(value), _maskDecimals(p.display));
    if (p.cmds.indexOf('X') >= 0) {
      if (value < 0) base += ' D';
      else if (value > 0) base += ' C';
    }
    return base;
  }
  if (value instanceof Date && !isNaN(value.getTime())) {
    return fmtMask(value, mask);
  }
  return fmtMask(String(value), mask);
}
/* ── moeda pt-BR (totais, sessões, cálculos) ─────────────────────────────── */
function itFmtMoney(v, cur) {
  var m = itMoneyInfo(cur);
  var num = Number(v) || 0;
  return m.symbol + ' ' + num.toLocaleString(m.locale, {minimumFractionDigits: 2, maximumFractionDigits: 2});
}
function itMoneyInfo(cur) {
  var map = {1: {symbol: 'R$', locale: 'pt-BR'}, 2: {symbol: '$', locale: 'en-US'}, 3: {symbol: '€', locale: 'pt-BR'}};
  return map[itNormalizeCurrency(cur)] || map[1];
}
function itNormalizeCurrency(cur) {
  if (cur === undefined || cur === null) return 1;
  var s = String(cur).trim().toLowerCase();
  if (s === '' || s === 'brl' || s === 'true' || s === 'sim' || s === '1') return 1;
  var n = parseInt(s, 10);
  return (n === 2 || n === 3) ? n : 1;
}
/* ── numéricos pt-BR (inputs com data-num-decimals) ────────────────────────
   Leitura: parseNum aceita '1.234,56' e '1.5' (vírgula presente ⇒ pt-BR).
   Escrita: fmtFieldInput formata pela casa do field no blur e após
   preenchimentos (replaces/totais); vazio/inválido não é tocado. */
function parseNum(v) {
  if (v === null || v === undefined) return NaN;
  var s = String(v).replace(/\s/g, '');
  if (s === '') return NaN;
  if (s.indexOf(',') >= 0) s = s.replace(/\./g, '').replace(',', '.');
  var n = parseFloat(s);
  return isNaN(n) ? NaN : n;
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
  return n.toLocaleString('pt-BR', {minimumFractionDigits: dec, maximumFractionDigits: dec});
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