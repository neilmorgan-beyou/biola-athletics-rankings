(function () {
  var APP = document.querySelector('.rk-app');
  if (!APP) return;
  // Controls are hidden in CSS until this class is set, so a script failure
  // never leaves dead filters on the page; the static tables still read fine.
  APP.classList.add('js-on');

  // Tabs. Without this script they are plain jump links and every panel shows.
  var tabs = Array.prototype.slice.call(APP.querySelectorAll('.rk-tab'));
  var panels = tabs.map(function (t) { return document.getElementById(t.getAttribute('aria-controls')); });
  function show(i, focus) {
    tabs.forEach(function (t, j) {
      var on = i === j;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.setAttribute('tabindex', on ? '0' : '-1');
      if (panels[j]) panels[j].hidden = !on;
    });
    if (focus) tabs[i].focus();
  }
  tabs.forEach(function (t, i) {
    t.addEventListener('click', function (ev) {
      ev.preventDefault();
      show(i);
      try { history.replaceState(null, '', '#' + t.getAttribute('aria-controls')); } catch (e) {}
    });
    t.addEventListener('keydown', function (ev) {
      var k = ev.key, n = tabs.length;
      if (k === 'ArrowRight' || k === 'ArrowDown') { ev.preventDefault(); show((i + 1) % n, true); }
      if (k === 'ArrowLeft' || k === 'ArrowUp') { ev.preventDefault(); show((i - 1 + n) % n, true); }
    });
  });
  if (tabs.length) {
    var start = 0;
    try {
      var h = location.hash.slice(1);
      tabs.forEach(function (t, i) { if (t.getAttribute('aria-controls') === h) start = i; });
    } catch (e) {}
    show(start);
  }

  function cellVal(tr, i, kind) {
    var td = tr.children[i];
    if (!td) return '';
    var v = td.hasAttribute('data-v') ? td.getAttribute('data-v') : td.textContent.trim();
    if (kind === 'num') { var n = parseFloat(v); return isNaN(n) ? 1e9 : n; }
    return v.toLowerCase();
  }

  Array.prototype.forEach.call(APP.querySelectorAll('.rk-table'), function (table) {
    var tbody = table.tBodies[0];
    var ths = table.querySelectorAll('th[data-k]');
    Array.prototype.forEach.call(ths, function (th) {
      var btn = th.querySelector('button');
      if (!btn) return;
      btn.addEventListener('click', function () {
        var i = Array.prototype.indexOf.call(th.parentNode.children, th);
        var kind = th.getAttribute('data-t');
        var dir = th.getAttribute('aria-sort') === 'ascending' ? -1 : 1;
        Array.prototype.forEach.call(ths, function (o) { o.removeAttribute('aria-sort'); });
        th.setAttribute('aria-sort', dir === 1 ? 'ascending' : 'descending');
        var rows = Array.prototype.slice.call(tbody.rows);
        rows.sort(function (a, b) {
          var x = cellVal(a, i, kind), y = cellVal(b, i, kind);
          return (x < y ? -1 : x > y ? 1 : 0) * dir;
        });
        var frag = document.createDocumentFragment();
        rows.forEach(function (r) { frag.appendChild(r); });
        tbody.appendChild(frag);
      });
    });
  });

  Array.prototype.forEach.call(APP.querySelectorAll('.rk-filters'), function (bar) {
    var table = document.getElementById(bar.getAttribute('data-for'));
    if (!table) return;
    var rows = Array.prototype.slice.call(table.tBodies[0].rows);
    var count = bar.querySelector('.rk-count');
    var controls = bar.querySelectorAll('[data-f]');
    var t;
    // Record table: with no season chosen show each program's all-seasons row; games: show all.
    function seasonOk(r, want) {
      var ds = (r.getAttribute('data-season') || '').toLowerCase();
      if (table.id === 't-vsrec') return want ? ds === want : ds === 'all seasons';
      return !want || ds === want;
    }
    function apply() {
      var f = {};
      Array.prototype.forEach.call(controls, function (c) { f[c.getAttribute('data-f')] = c.value.trim().toLowerCase(); });
      var shown = 0;
      rows.forEach(function (r) {
        var ok = (!f.sport || (r.getAttribute('data-sport') || '').toLowerCase() === f.sport) &&
                 (!f.era || (r.getAttribute('data-era') || '').toLowerCase() === f.era) &&
                 (!f.scope || (r.getAttribute('data-scope') || '').toLowerCase() === f.scope) &&
                 (!f.res || (r.getAttribute('data-res') || '').toLowerCase() === f.res) &&
                 seasonOk(r, f.season) &&
                 (!f.q || r.textContent.toLowerCase().indexOf(f.q) !== -1);
        r.classList.toggle('is-hidden', !ok);
        if (ok) shown++;
      });
      if (count) count.textContent = shown + ' of ' + rows.length + ' rows';
    }
    Array.prototype.forEach.call(controls, function (c) {
      c.addEventListener(c.tagName === 'SELECT' ? 'change' : 'input', function () {
        clearTimeout(t); t = setTimeout(apply, 100);
      });
    });
    apply();
  });
})();
