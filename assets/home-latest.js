document.addEventListener('DOMContentLoaded', function () {
  if (typeof LATEST_ITEMS === 'undefined') return;

  var items = LATEST_ITEMS.slice().sort(function (a, b) {
    return new Date(b.published) - new Date(a.published);
  });

  var categoryLabels = {
    transfers: 'Transfers', team: 'Team & injuries', academy: 'Youth & academy',
    interviews: 'Interviews', club: 'Club', videos: 'Videos'
  };

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function timeAgo(iso) {
    var diff = Math.floor((Date.now() - new Date(iso)) / 60000);
    if (diff < 1) return 'just now';
    if (diff < 60) return diff + 'm ago';
    if (diff < 1440) return Math.floor(diff / 60) + 'h ago';
    return Math.floor(diff / 1440) + 'd ago';
  }

  function initials(source) {
    var words = (source || '').replace(/[^A-Za-z0-9 ]/g, '').split(/\s+/).filter(Boolean);
    if (!words.length) return '--';
    if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
    return (words[0][0] + words[1][0]).toUpperCase();
  }

  // ---- Lead ("top story") card ----
  // Only genuine national/regional newsrooms and wire agencies qualify for
  // this slot -- independent blogs, fanzines, forums (RedCafe) and YouTube
  // channels are excluded even when their story is the most recent thing
  // in the wire. An official club item can still win the slot, but only
  // when it reads like an actual announcement (a signing, an appointment,
  // a sacking, a big club statement) -- routine club news is excluded like
  // any other ineligible source. Extend either list below as new outlets
  // or announcement phrasing show up.
  var NATIONAL_REGIONAL_OUTLETS = [
    'bbc sport', 'bbc sport football', 'sky sports', 'the athletic', 'the telegraph',
    'the guardian', 'manchester evening news', 'espn', 'reuters', 'daily mail',
    'the times', 'pa media', 'associated press', 'ap', 'yahoo sports',
    'evening standard', 'tnt sports', 'teamtalk', 'footballtransfers',
    'the independent', 'mirror', 'the sun', 'metro', 'talksport', 'wsls'
  ];
  var CLUB_SOURCES = ['manchester united', 'manchester united academy'];
  var CLUB_ANNOUNCEMENT_WORDS = [
    'sign', 'signs', 'signing', 'signed', 'appoint', 'appoints', 'appointed',
    'sack', 'sacked', 'sacking', 'depart', 'departs', 'departure', 'resign',
    'resigns', 'resignation', 'confirm', 'confirms', 'confirmed', 'announce',
    'announces', 'announced', 'statement', 'contract extension', 'new manager',
    'new head coach', 'charged', 'banned', 'charge'
  ];

  function isNationalOrRegional(source) {
    return NATIONAL_REGIONAL_OUTLETS.indexOf((source || '').trim().toLowerCase()) !== -1;
  }
  function isBigClubAnnouncement(item) {
    if (CLUB_SOURCES.indexOf((item.source || '').trim().toLowerCase()) === -1) return false;
    var title = (item.title || '').toLowerCase();
    return CLUB_ANNOUNCEMENT_WORDS.some(function (w) { return title.indexOf(w) !== -1; });
  }

  var lead = document.getElementById('lead-card');
  if (lead && items.length) {
    var eligible = items.filter(function (i) {
      return i.type !== 'video' && (isNationalOrRegional(i.source) || isBigClubAnnouncement(i));
    });
    // Falls back to the previous "most recent, non-video" behaviour only
    // if nothing in the wire currently qualifies, so the card never ends
    // up empty.
    var top = eligible[0] || items.find(function (i) { return i.type !== 'video'; }) || items[0];
    lead.href = top.url;
    var leadTime = document.getElementById('lead-time');
    var leadTitle = document.getElementById('lead-title');
    var leadInitials = document.getElementById('lead-initials');
    var leadSource = document.getElementById('lead-source');
    if (leadTime) leadTime.textContent = timeAgo(top.published);
    if (leadTitle) leadTitle.textContent = top.title;
    if (leadInitials) leadInitials.textContent = initials(top.source);
    if (leadSource) leadSource.textContent = top.source;
  }

  // ---- Wire list ----
  var listEl = document.getElementById('home-story-list');
  var countEl = document.getElementById('wire-count');
  var checkedEl = document.getElementById('wire-checked');
  var tabs = document.querySelectorAll('.wire-toolbar .filters button');
  var activeCategory = 'all';

  function render() {
    var filtered = activeCategory === 'all' ? items : items.filter(function (i) { return i.category === activeCategory; });
    if (countEl) countEl.textContent = filtered.length + ' report' + (filtered.length === 1 ? '' : 's');
    if (!listEl) return;
    listEl.innerHTML = filtered.map(function (item, idx) {
      var label = categoryLabels[item.category] || item.category;
      var num = String(idx + 1).padStart(2, '0');
      return '<a class="story" href="' + item.url + '" target="_blank" rel="noreferrer">' +
        '<span class="story-index">' + num + '</span>' +
        '<span class="story-thumb" aria-hidden="true"><i>' + esc(initials(item.source)) + '</i></span>' +
        '<div><p><b>' + esc(item.type === 'video' ? 'Videos' : label) + '</b> &middot; ' + timeAgo(item.published) + '</p>' +
        '<h3>' + esc(item.title) + '</h3>' +
        '<span class="byline">' + esc(item.source) + ' <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-arrow-up-right" aria-hidden="true"><path d="M7 7h10v10"></path><path d="M7 17 17 7"></path></svg></span>' +
        '</div></a>';
    }).join('');
  }

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      tabs.forEach(function (t) { t.classList.remove('active'); });
      tab.classList.add('active');
      activeCategory = tab.dataset.category;
      render();
    });
  });

  render();

  if (checkedEl) {
    var updated = (typeof LATEST_UPDATED !== 'undefined') ? LATEST_UPDATED : (items[0] && items[0].published);
    checkedEl.textContent = updated ? ('checked ' + timeAgo(updated)) : 'checked recently';
  }
});
