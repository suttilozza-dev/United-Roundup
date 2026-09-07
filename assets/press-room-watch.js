document.addEventListener('DOMContentLoaded', function () {
  var data = PRESS_ROOM_QUESTIONS;
  var PAGE_SIZE = 20;
  var visibleCount = PAGE_SIZE;

  var searchEl = document.getElementById('prw-topic-search');
  var topicEl = document.getElementById('prw-topic-select');
  var contextEl = document.getElementById('prw-context-select');
  var resultEl = document.getElementById('prw-result-select');
  var wordingEl = document.getElementById('prw-evidence-select');
  var listEl = document.getElementById('prw-question-list');
  var countEl = document.getElementById('prw-match-count');
  var moreEl = document.getElementById('prw-load-more');

  var topics = Array.from(new Set(data.map(function (d) { return d.topic; })))
    .filter(Boolean).sort();
  topics.forEach(function (t) {
    var opt = document.createElement('option');
    opt.value = t;
    opt.textContent = t;
    topicEl.appendChild(opt);
  });

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str || '';
    return div.innerHTML;
  }

  function getFiltered() {
    var q = searchEl.value.trim().toLowerCase();
    var topic = topicEl.value;
    var context = contextEl.value;
    var result = resultEl.value;
    var wording = wordingEl.value;

    return data.filter(function (row) {
      if (topic && row.topic !== topic) return false;
      if (context && row.context !== context) return false;
      if (result && row.result !== result) return false;
      if (wording && row.wording_status !== wording) return false;
      if (q) {
        var hay = (row.question + ' ' + row.fixture + ' ' + row.topic).toLowerCase();
        if (hay.indexOf(q) === -1) return false;
      }
      return true;
    });
  }

  function render() {
    var filtered = getFiltered();

    countEl.textContent = filtered.length + (filtered.length === 1 ? ' question matches' : ' questions match');

    var toShow = filtered.slice(0, visibleCount);

    listEl.innerHTML = toShow.map(function (row, i) {
      var resultAttr = row.result && row.result !== 'not_applicable' ? row.result : 'not_applicable';
      var response = row.response
        ? '<div class="prw-response">' + escapeHtml(row.response) + '</div>'
        : '<div class="prw-response prw-response-missing">No linked response recovered for this question.</div>';
      return (
        '<article>' +
          '<button class="prw-question-toggle" aria-expanded="false" data-idx="' + i + '">' +
            '<div class="prw-question-meta">' +
              '<span>' + row.date_disp + '</span>' +
              '<b>' + escapeHtml(row.fixture) + '</b>' +
              '<i class="' + resultAttr + '">' + row.context_label + '</i>' +
              '<i>' + escapeHtml(row.section) + '</i>' +
            '</div>' +
            '<h3>' + escapeHtml(row.question) + '</h3>' +
            '<div class="prw-question-tags">' +
              '<span>' + escapeHtml(row.topic) + '</span>' +
              (row.framing ? '<span>' + escapeHtml(row.framing) + '</span>' : '') +
              (row.narrative_tag ? '<span>' + escapeHtml(row.narrative_tag) + '</span>' : '') +
            '</div>' +
            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-chevron-down" aria-hidden="true"><path d="m6 9 6 6 6-6"></path></svg>' +
          '</button>' +
          response +
        '</article>'
      );
    }).join('');

    listEl.querySelectorAll('.prw-question-toggle').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var article = btn.closest('article');
        var open = article.classList.toggle('prw-open');
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    });

    if (moreEl) {
      var remaining = filtered.length - visibleCount;
      if (remaining > 0) {
        moreEl.hidden = false;
        moreEl.textContent = 'Show ' + Math.min(PAGE_SIZE, remaining) + ' more question' + (Math.min(PAGE_SIZE, remaining) === 1 ? '' : 's');
      } else {
        moreEl.hidden = true;
      }
    }
  }

  if (moreEl) {
    moreEl.addEventListener('click', function () {
      visibleCount += PAGE_SIZE;
      render();
    });
  }

  [searchEl, topicEl, contextEl, resultEl, wordingEl].forEach(function (el) {
    el.addEventListener('input', function () { visibleCount = PAGE_SIZE; render(); });
    el.addEventListener('change', function () { visibleCount = PAGE_SIZE; render(); });
  });

  render();

  // Method section tabs (Counting / Evidence / Fairness) — Radix markup was exported
  // statically with no click behaviour wired up; this restores it using the same
  // data-state/aria-selected/hidden attributes the existing CSS already targets.
  var tabRoot = document.querySelector('.prw-method-tabs');
  if (tabRoot) {
    var tabButtons = tabRoot.querySelectorAll('[role="tab"]');
    var tabPanels = tabRoot.querySelectorAll('[role="tabpanel"]');
    tabButtons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var controls = btn.getAttribute('aria-controls');
        tabButtons.forEach(function (b) {
          var active = b === btn;
          b.setAttribute('aria-selected', active ? 'true' : 'false');
          b.setAttribute('data-state', active ? 'active' : 'inactive');
        });
        tabPanels.forEach(function (panel) {
          var show = panel.id === controls;
          panel.hidden = !show;
          panel.setAttribute('data-state', show ? 'active' : 'inactive');
        });
      });
    });
  }
});
