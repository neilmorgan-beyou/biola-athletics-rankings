(function () {
  var APP = document.querySelector('.rk-app');
  if (!APP) return;
  // Hosted data: fetch the current parts (updated weekly) and swap them in before wiring up
  // tabs, sorting and filters. If the fetch fails the static page is used as is.
  var src = APP.getAttribute('data-src');
  if (src && window.fetch && window.JSON) {
    fetch(src, { cache: 'no-cache' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        var p = d && d.parts;
        if (!p || (d.generated || '') < (APP.getAttribute('data-generated') || '')) return;
        ['rk-seasons', 'rk-polls', 'rk-dept', 'rk-vs'].forEach(function (id) {
          var el = document.getElementById(id);
          if (el && p[id]) el.innerHTML = p[id];
        });
        var st = APP.querySelector('.rk-stats'); if (st && p['rk-stats']) st.innerHTML = p['rk-stats'];
        var on = APP.querySelector('.rk-ones'); if (on && p['rk-ones']) on.outerHTML = p['rk-ones'];
        var as = APP.querySelector('.rk-asof'); if (as && p['rk-asof']) as.textContent = p['rk-asof'];
      })
      ['catch'](function () {
        Array.prototype.forEach.call(APP.querySelectorAll('.rk-loading'), function (x) {
          x.textContent = 'The full tables could not be loaded right now. Please try again later.';
        });
      })
      .then(init, init);
  } else {
    init();
  }

  function init() {
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

  // Sort labels for the phone "Sort by" menu (headers are hidden when rows become cards).
  // [first option, second option, direction of the first]: 1 = ascending, -1 = descending.
  var RANKISH = /^(rank|preseason|peak|final|finish)$/i;
  function sortWords(name, kind) {
    if (/^(season|date)$/i.test(name)) return ['newest first', 'oldest first', -1];
    if (/^opp\. rank$/i.test(name)) return ['highest-ranked first', 'lowest-ranked first', 1];
    if (RANKISH.test(name)) return ['best first', 'worst first', 1];
    if (/^vs\./i.test(name)) return ['best record first', 'worst record first', -1];
    if (kind === 'num') return ['most first', 'fewest first', -1];
    return ['A to Z', 'Z to A', 1];
  }

  function blank(td) {
    return !td || !td.textContent.trim() || td.getAttribute('data-v') === '999';
  }

  function sortTable(table, i, dir) {
    var tbody = table.tBodies[0];
    var ths = table.querySelectorAll('th[data-k]');
    Array.prototype.forEach.call(ths, function (o) { o.removeAttribute('aria-sort'); });
    var rows = Array.prototype.slice.call(tbody.rows);
    if (i < 0) {
      rows.sort(function (a, b) { return a._rkOrder - b._rkOrder; });
    } else {
      var th = table.tHead.rows[0].children[i];
      var kind = th.getAttribute('data-t');
      th.setAttribute('aria-sort', dir === 1 ? 'ascending' : 'descending');
      rows.sort(function (a, b) {
        // Blank cells always go last, whichever way the column is sorted.
        // (An unnumbered "Ranked" entry carries 999 and counts as blank.)
        var ea = blank(a.children[i]), eb = blank(b.children[i]);
        if (ea !== eb) return ea ? 1 : -1;
        var x = cellVal(a, i, kind), y = cellVal(b, i, kind);
        return (x < y ? -1 : x > y ? 1 : a._rkOrder - b._rkOrder) * (x === y ? 1 : dir);
      });
    }
    rows.forEach(function (r) {
      Array.prototype.forEach.call(r.children, function (td, j) { td.classList.toggle('is-sorted', j === i); });
    });
    var frag = document.createDocumentFragment();
    rows.forEach(function (r) { frag.appendChild(r); });
    tbody.appendChild(frag);
    if (table._rkMenu) table._rkMenu.value = i < 0 ? '' : i + ':' + dir;
  }

  Array.prototype.forEach.call(APP.querySelectorAll('.rk-table'), function (table) {
    Array.prototype.forEach.call(table.tBodies[0].rows, function (r, n) { r._rkOrder = n; });
    var ths = table.querySelectorAll('th[data-k]');
    Array.prototype.forEach.call(ths, function (th) {
      var btn = th.querySelector('button');
      if (!btn) return;
      btn.addEventListener('click', function () {
        var i = Array.prototype.indexOf.call(th.parentNode.children, th);
        sortTable(table, i, th.getAttribute('aria-sort') === 'ascending' ? -1 : 1);
      });
    });

    // Phone sort menu, placed in the table's filter bar (shown only at phone width in CSS).
    var bar = APP.querySelector('.rk-filters[data-for="' + table.id + '"]');
    if (!bar || !ths.length) return;
    var label = document.createElement('label');
    label.className = 'rk-sort';
    label.appendChild(document.createTextNode('Sort by'));
    var sel = document.createElement('select');
    sel.appendChild(new Option('Default order', ''));
    Array.prototype.forEach.call(ths, function (th) {
      var i = Array.prototype.indexOf.call(th.parentNode.children, th);
      var name = th.textContent.trim(), w = sortWords(name, th.getAttribute('data-t'));
      sel.appendChild(new Option(name + ': ' + w[0], i + ':' + w[2]));
      sel.appendChild(new Option(name + ': ' + w[1], i + ':' + -w[2]));
    });
    sel.addEventListener('change', function () {
      if (!sel.value) return sortTable(table, -1, 1);
      var v = sel.value.split(':');
      sortTable(table, +v[0], +v[1]);
    });
    label.appendChild(sel);
    table._rkMenu = sel;
    var count = bar.querySelector('.rk-count');
    bar.insertBefore(label, count);
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
  }
})();
