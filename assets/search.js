// Homepage search: matches the query against the news wire (title + source)
// and shows a dropdown of results. Supports Cmd/Ctrl+K to focus, arrow keys
// to move through results, Enter to open, Escape to close.
document.addEventListener('DOMContentLoaded', function () {
  var input = document.getElementById('site-search-input');
  if (!input) return;

  var results = document.createElement('div');
  results.className = 'search-results';
  results.setAttribute('role', 'listbox');
  results.hidden = true;
  document.body.appendChild(results);

  var activeIndex = -1;

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function position() {
    var r = input.getBoundingClientRect();
    results.style.left = r.left + 'px';
    results.style.top = (r.bottom + 8) + 'px';
    results.style.width = r.width + 'px';
  }

  function close() {
    results.hidden = true;
    results.innerHTML = '';
    activeIndex = -1;
  }

  function updateActive(items) {
    items.forEach(function (el, i) {
      el.classList.toggle('active', i === activeIndex);
    });
    if (activeIndex >= 0 && items[activeIndex]) {
      items[activeIndex].scrollIntoView({ block: 'nearest' });
    }
  }

  function render(matches) {
    activeIndex = -1;
    if (!matches.length) {
      results.innerHTML = '<div class="search-empty">No stories match that search.</div>';
      results.hidden = false;
      position();
      return;
    }
    results.innerHTML = matches.map(function (item) {
      return '<a class="search-result" href="' + item.url + '" target="_blank" rel="noreferrer">' +
        '<span class="search-result-title">' + esc(item.title) + '</span>' +
        '<span class="search-result-meta">' + esc(item.source) + '</span>' +
        '</a>';
    }).join('');
    results.hidden = false;
    position();
  }

  function runSearch() {
    var q = input.value.trim().toLowerCase();
    if (!q) { close(); return; }
    if (typeof LATEST_ITEMS === 'undefined') { close(); return; }
    var terms = q.split(/\s+/).filter(Boolean);
    var matches = LATEST_ITEMS.filter(function (item) {
      var hay = (item.title + ' ' + item.source).toLowerCase();
      return terms.every(function (t) { return hay.indexOf(t) !== -1; });
    }).slice(0, 8);
    render(matches);
  }

  input.addEventListener('input', runSearch);
  input.addEventListener('focus', function () {
    if (input.value.trim()) runSearch();
  });

  input.addEventListener('keydown', function (e) {
    if (results.hidden) return;
    var items = Array.prototype.slice.call(results.querySelectorAll('.search-result'));
    if (!items.length) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIndex = Math.min(activeIndex + 1, items.length - 1);
      updateActive(items);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIndex = Math.max(activeIndex - 1, 0);
      updateActive(items);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      (items[activeIndex] || items[0]).click();
    } else if (e.key === 'Escape') {
      close();
      input.blur();
    }
  });

  document.addEventListener('click', function (e) {
    if (e.target !== input && !results.contains(e.target)) close();
  });

  window.addEventListener('resize', function () { if (!results.hidden) position(); });
  window.addEventListener('scroll', function () { if (!results.hidden) position(); }, true);

  // Cmd+K / Ctrl+K focuses the search box, matching the on-screen hint.
  document.addEventListener('keydown', function (e) {
    if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
      e.preventDefault();
      input.focus();
      input.select();
    }
  });
});
