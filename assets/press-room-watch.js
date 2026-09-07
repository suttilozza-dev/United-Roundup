document.addEventListener('DOMContentLoaded', function () {
  var data = PRESS_ROOM_QUESTIONS;

  var searchEl = document.getElementById('prw-search');
  var topicEl = document.getElementById('prw-topic');
  var contextEl = document.getElementById('prw-context');
  var resultEl = document.getElementById('prw-result');
  var wordingEl = document.getElementById('prw-wording');
  var resultsEl = document.getElementById('prw-results');
  var countEl = document.getElementById('prw-count');

  // Populate topic dropdown from data
  var topics = Array.from(new Set(data.map(function (d) { return d.topic; })))
    .filter(Boolean).sort();
  topics.forEach(function (t) {
    var opt = document.createElement('option');
    opt.value = t;
    opt.textContent = t;
    topicEl.appendChild(opt);
  });

  var resultLabels = { win: 'Win', draw: 'Draw', loss: 'Loss', not_applicable: '—' };
  var resultClasses = { win: 'res-win', draw: 'res-draw', loss: 'res-loss', not_applicable: '' };

  function render() {
    var q = searchEl.value.trim().toLowerCase();
    var topic = topicEl.value;
    var context = contextEl.value;
    var result = resultEl.value;
    var wording = wordingEl.value;

    var filtered = data.filter(function (row) {
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

    countEl.textContent = filtered.length + (filtered.length === 1 ? ' question matches' : ' questions match');

    resultsEl.innerHTML = filtered.map(function (row) {
      var contextLabel = row.context === 'pre_match' ? 'Pre-match' : 'Post-match';
      var resultBadge = row.result && row.result !== 'not_applicable'
        ? '<span class="conf-result ' + resultClasses[row.result] + '">' + resultLabels[row.result] + '</span>'
        : '';
      var wordingBadge = row.wording_status === 'article-verbatim'
        ? '<span class="prw-tag prw-tag-verbatim">Club verbatim</span>'
        : '<span class="prw-tag prw-tag-transcript">Transcript-derived</span>';
      var link = row.source_url
        ? '<a href="' + row.source_url + '" target="_blank" rel="noreferrer" class="prw-source-link">Source ↗</a>'
        : '';
      return (
        '<article class="prw-card">' +
          '<div class="prw-card-head">' +
            '<span class="prw-fixture">' + row.fixture + ' &middot; ' + contextLabel + ' &middot; ' + row.date_disp + '</span>' +
            resultBadge +
          '</div>' +
          '<p class="prw-question">' + escapeHtml(row.question) + '</p>' +
          '<div class="prw-card-foot">' +
            '<span class="prw-tag">' + escapeHtml(row.topic) + '</span>' +
            wordingBadge +
            link +
          '</div>' +
        '</article>'
      );
    }).join('');
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  [searchEl, topicEl, contextEl, resultEl, wordingEl].forEach(function (el) {
    el.addEventListener('input', render);
    el.addEventListener('change', render);
  });

  render();
});
