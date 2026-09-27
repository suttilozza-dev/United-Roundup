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

  // Bigger version of a publisher's image for the large slots (Top story
  // card, wire lead, video cards). Feeds give thumbnail-sized links; these
  // image servers offer the same picture at a larger size. If the larger one
  // is missing, the <img> falls back to the original (data-fallback).
  function largeImage(u) {
    u = u || '';
    return u
      .replace(/(\/ALTERNATES\/)s\d+\//, '$1s1200/')                        // Reach (MEN, Mirror)
      .replace(/(\.365dm\.com\/\d+\/\d+\/)\d+x\d+\//, '$11600x900/')     // Sky Sports
      .replace(/(ichef\.bbci\.co\.uk\/ace\/standard\/)\d+\//, '$1976/')     // BBC
      .replace(/(i\.ytimg\.com\/vi\/[^/]+\/)hqdefault\.jpg/, '$1maxresdefault.jpg'); // YouTube
  }
  // onerror handler: try the original image first, then give up and show
  // the branded art behind it.
  window.urImgFallback = function (img, onGiveUp) {
    var fb = img.getAttribute('data-fallback');
    if (fb) { img.removeAttribute('data-fallback'); img.src = fb; return; }
    if (onGiveUp) onGiveUp(img);
  };
  // YouTube answers a missing large thumbnail with a tiny 120x90 grey
  // placeholder instead of an error, so check the size once it loads.
  window.urImgCheck = function (img) {
    if (img.naturalWidth && img.naturalWidth <= 120 && img.getAttribute('data-fallback')) window.urImgFallback(img);
  };

  var heroUrl = null;
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
    var leadArt = document.getElementById('lead-art');
    var heroImg = /^https:\/\//i.test(top.image || '') ? top.image : '';
    if (leadArt && heroImg) {
      var ph = document.createElement('img');
      ph.className = 'lead-art-photo'; ph.alt = ''; ph.referrerPolicy = 'no-referrer';
      var heroBig = largeImage(heroImg);
      if (heroBig !== heroImg) ph.setAttribute('data-fallback', heroImg);
      ph.onerror = function () { window.urImgFallback(ph, function () { leadArt.classList.remove('has-image'); ph.remove(); }); };
      ph.onload = function () { window.urImgCheck(ph); };
      ph.src = heroBig;
      leadArt.appendChild(ph); leadArt.classList.add('has-image');
    }
    heroUrl = top.url;
  }

  // ---- Wire list ----
  // The newest story in the chosen filter gets the big "lead" slot above the
  // scrolling list. Every story shows the publisher's own image; when there
  // isn't one (or it fails to load) the red box names the outlet instead.
  var listEl = document.getElementById('home-story-list');
  var leadSlot = document.getElementById('wire-lead');
  var countEl = document.getElementById('wire-count');
  var checkedEl = document.getElementById('wire-checked');
  var tabs = document.querySelectorAll('.wire-toolbar .filters button');
  var activeCategory = 'all';
  var WIRE_ARROW = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-arrow-up-right" aria-hidden="true"><path d="M7 7h10v10"></path><path d="M7 17 17 7"></path></svg>';

  // Friendlier names for the "no image" box, where the feed's own spelling
  // runs words together.
  var DISPLAY_NAMES = { 'redcafe': 'Red Cafe', 'unitedpeoplestv': 'United Peoples TV' };
  function displayName(source) {
    return DISPLAY_NAMES[(source || '').replace(/\s+/g, '').toLowerCase()] || source || 'Unknown source';
  }
  function httpsUrl(u) {
    return /^https:\/\//i.test(u || '') ? esc(u).replace(/"/g, '&quot;') : '';
  }
  function wireThumb(item, extra, big) {
    var src = httpsUrl(item.image);
    var fallback = '<i><b>' + esc(displayName(item.source)) + '</b><small>No image available</small></i>';
    var bigSrc = big && src ? httpsUrl(largeImage(item.image)) : '';
    var useSrc = bigSrc || src;
    var img = src ? '<img alt="" loading="lazy" referrerpolicy="no-referrer" src="' + useSrc + '"' +
      (bigSrc && bigSrc !== src ? ' data-fallback="' + src + '"' : '') +
      ' onload="urImgCheck(this)" onerror="urImgFallback(this,function(i){i.parentNode.classList.remove(\'has-image\');i.remove()})">' : '';
    return '<span class="story-thumb' + (src ? ' has-image' : '') + (extra ? ' ' + extra : '') + '" aria-hidden="true">' + img + fallback + '</span>';
  }
  function labelFor(item) {
    return item.type === 'video' ? 'Videos' : (categoryLabels[item.category] || item.category || 'News');
  }

  function render() {
    var filtered = activeCategory === 'all' ? items : items.filter(function (i) { return i.category === activeCategory; });
    if (countEl) countEl.textContent = filtered.length + ' report' + (filtered.length === 1 ? '' : 's');
    // The big wire slot goes to the newest story that has a photo. In
    // "All stories" it also skips the story already shown as the Top story
    // card above, so the two don't repeat each other.
    function notHero(i) { return !(activeCategory === 'all' && heroUrl && i.url === heroUrl); }
    var top = filtered.find(function (i) { return notHero(i) && /^https:\/\//i.test(i.image || ''); }) ||
      filtered.find(notHero) || filtered[0];
    var flag = top === filtered[0] ? 'Latest' : 'Featured';
    var rest = leadSlot ? filtered.filter(function (i) { return i !== top; }) : filtered;
    if (leadSlot) {
      leadSlot.innerHTML = top ?
        '<a class="wire-lead" href="' + httpsUrl(top.url) + '" target="_blank" rel="noreferrer">' +
          wireThumb(top, 'wire-lead-thumb', true) +
          '<div class="wire-lead-body"><p><span class="wire-lead-flag">' + flag + '</span><b>' + esc(labelFor(top)) + '</b> &middot; ' + timeAgo(top.published) + '</p>' +
          '<h3>' + esc(top.title) + '</h3>' +
          '<span class="byline">' + esc(top.source) + ' ' + WIRE_ARROW + '</span></div></a>' : '';
    }
    if (!listEl) return;
    listEl.innerHTML = rest.map(function (item, idx) {
      var num = String(idx + (leadSlot ? 2 : 1)).padStart(2, '0');
      return '<a class="story" href="' + httpsUrl(item.url) + '" target="_blank" rel="noreferrer">' +
        '<span class="story-index">' + num + '</span>' +
        wireThumb(item) +
        '<div><p><b>' + esc(labelFor(item)) + '</b> &middot; ' + timeAgo(item.published) + '</p>' +
        '<h3>' + esc(item.title) + '</h3>' +
        '<span class="byline">' + esc(item.source) + ' ' + WIRE_ARROW + '</span>' +
        '</div></a>';
    }).join('');
  }

  // ---- "Who's reporting most" ----
  // Counts stories per outlet over the last 24 hours (or the whole wire if
  // the last day is quiet). A count, not a verdict.
  (function renderSourceCounts() {
    var box = document.getElementById('wire-sources');
    var list = document.getElementById('wire-sources-list');
    if (!box || !list || !items.length) return;
    var dayAgo = Date.now() - 24 * 3600 * 1000;
    var pool = items.filter(function (i) { return new Date(i.published).getTime() >= dayAgo; });
    var title = 'Last 24 hours';
    if (pool.length < 8) { pool = items; title = 'Across the current wire'; }
    var counts = {};
    pool.forEach(function (i) { var k = i.source || 'Unknown'; counts[k] = (counts[k] || 0) + 1; });
    var ranked = Object.keys(counts).map(function (k) { return { name: k, n: counts[k] }; })
      .sort(function (a, b) { return b.n - a.n || a.name.localeCompare(b.name); });
    var max = ranked[0] ? ranked[0].n : 1;
    list.innerHTML = ranked.slice(0, 6).map(function (r) {
      return '<li><span class="ws-name">' + esc(r.name) + '</span><b>' + r.n + '</b>' +
        '<span class="ws-bar"><i style="width:' + Math.max(6, Math.round(r.n / max * 100)) + '%"></i></span></li>';
    }).join('');
    var t = document.getElementById('wire-sources-title');
    var s = document.getElementById('wire-sources-sum');
    if (t) t.textContent = title;
    if (s) s.textContent = pool.length + ' report' + (pool.length === 1 ? '' : 's') + ' from ' + ranked.length + ' outlet' + (ranked.length === 1 ? '' : 's');
    box.hidden = false;
  })();

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
  function thumb(item, cls, big) {
    var src = safeUrl(item.image);
    if (!src) return '';
    var bigSrc = big ? safeUrl(largeImage(item.image)) : '';
    return '<img class="' + cls + '" alt="" loading="lazy" referrerpolicy="no-referrer" src="' + (bigSrc || src) + '"' +
      (bigSrc && bigSrc !== src ? ' data-fallback="' + src + '"' : '') +
      ' onload="urImgCheck(this)" onerror="urImgFallback(this,function(i){i.parentNode.classList.remove(\'has-image\');i.remove()})">';
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
      var img = thumb(v, 'video-thumb', true);
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
