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

  // ---- "United on Screen" (videos) and "The Next Generation" (academy) ----
  // Both are rebuilt from the daily data feed so they always show the newest
  // items with thumbnails. The hand-written cards in index.html stay in place
  // as a fallback if the feed has nothing for a section.
  var ARROW = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-arrow-up-right" aria-hidden="true"><path d="M7 7h10v10"></path><path d="M7 17 17 7"></path></svg>';
  var PLAY = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-play" aria-hidden="true"><path d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z"></path></svg>';

  function safeUrl(u) {
    return /^https:\/\//i.test(u || '') ? esc(u).replace(/"/g, '&quot;') : '';
  }
  // If a publisher's image fails to load, fall back to the branded card art.
  function thumb(item, cls) {
    var src = safeUrl(item.image);
    if (!src) return '';
    return '<img class="' + cls + '" alt="" loading="lazy" referrerpolicy="no-referrer" src="' + src + '" ' +
      'onerror="this.parentNode.classList.remove(\'has-image\');this.remove()">';
  }
  // Newest first, but no more than `perSource` from any one outlet/channel so
  // a single busy YouTube channel can't fill the whole row.
  function pickLatest(list, count, perSource) {
    var picked = [], perCount = {};
    list.forEach(function (item) {
      if (picked.length >= count) return;
      var key = (item.source || '').toLowerCase();
      if ((perCount[key] || 0) >= perSource) return;
      perCount[key] = (perCount[key] || 0) + 1;
      picked.push(item);
    });
    return picked;
  }

  var videoGrid = document.querySelector('#videos .video-grid');
  var videos = pickLatest(items.filter(function (i) { return i.type === 'video' && i.url; }), 6, 2);
  if (videoGrid && videos.length >= 3) {
    if (videos.length < 6) videos = videos.slice(0, 3);
    videoGrid.innerHTML = videos.map(function (v, idx) {
      var official = CLUB_SOURCES.indexOf((v.source || '').trim().toLowerCase()) !== -1;
      var img = thumb(v, 'video-thumb');
      return '<a class="video-card" href="' + safeUrl(v.url) + '" target="_blank" rel="noreferrer">' +
        '<div class="video-art v' + (idx % 3) + (img ? ' has-image' : '') + '">' + img +
        '<span class="play">' + PLAY + '</span>' +
        '<small>' + (official ? 'OFFICIAL &middot; ' : '') + esc(timeAgo(v.published).toUpperCase()) + '</small></div>' +
        '<p>' + esc(v.source) + '</p><h3>' + esc(v.title) + '</h3></a>';
    }).join('');
  }

  var academyGrid = document.querySelector('#academy .academy-grid');
  var academy = pickLatest(items.filter(function (i) { return i.category === 'academy' && i.url; }), 4, 2);
  if (academyGrid && academy.length) {
    academyGrid.innerHTML = academy.map(function (a) {
      var img = thumb(a, 'academy-thumb-img');
      return '<a href="' + safeUrl(a.url) + '" target="_blank" rel="noreferrer">' +
        '<div class="academy-thumb' + (img ? ' has-image' : '') + '">' + img + '<i>' + esc(initials(a.source)) + '</i></div>' +
        '<div class="academy-body"><span>Youth &amp; academy &middot; ' + esc(timeAgo(a.published)) + '</span>' +
        '<h3>' + esc(a.title) + '</h3><small>' + esc(a.source) + ' ' + ARROW + '</small></div></a>';
    }).join('');
  }

  if (checkedEl) {
    var updated = (typeof LATEST_UPDATED !== 'undefined') ? LATEST_UPDATED : (items[0] && items[0].published);
    checkedEl.textContent = updated ? ('checked ' + timeAgo(updated)) : 'checked recently';
  }
});
