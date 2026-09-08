document.addEventListener('DOMContentLoaded', function () {
  var items = LATEST_ITEMS.slice().sort((a, b) => new Date(b.published) - new Date(a.published));
  var listEl = document.getElementById('lt-list');
  var tabs = document.querySelectorAll('.lt-tab');
  var activeCategory = 'all';

  var categoryLabels = {
    transfers: 'Transfers', team: 'Team & injuries', academy: 'Youth & academy',
    interviews: 'Interviews', club: 'Club', videos: 'Videos'
  };

  function timeAgo(iso) {
    var diff = Math.floor((Date.now() - new Date(iso)) / 60000);
    if (diff < 60) return diff + 'm ago';
    if (diff < 1440) return Math.floor(diff / 60) + 'h ago';
    return Math.floor(diff / 1440) + 'd ago';
  }

  function render() {
    var filtered = activeCategory === 'all' ? items : items.filter(i => i.category === activeCategory);
    if (!filtered.length) {
      listEl.innerHTML = '<p class="lt-empty">No stories in this category yet.</p>';
      return;
    }
    listEl.innerHTML = filtered.map(function (i) {
      var label = categoryLabels[i.category] || i.category;
      return '<a class="lt-item" href="' + i.url + '" target="_blank" rel="noreferrer">' +
        '<span class="lt-item-badge">' + (i.type === 'video' ? 'Video' : label) + '</span>' +
        '<span><span class="lt-item-title">' + i.title + '</span>' +
        '<span class="lt-item-meta">' + i.source + ' &middot; ' + timeAgo(i.published) + '</span></span>' +
        '</a>';
    }).join('');
  }

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      activeCategory = tab.dataset.category;
      render();
    });
  });

  render();
});
