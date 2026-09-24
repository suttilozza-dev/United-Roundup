// Mobile menu toggle.
// The site header (including .menu-button and .site-header nav) is injected
// client-side by assets/includes.js, which isn't guaranteed to have finished
// by DOMContentLoaded. Wire up on 'partials:ready' when includes.js is on
// the page; fall back to DOMContentLoaded for any page that still has the
// header inline.
function wireMenuToggle() {
  var btn = document.querySelector('.menu-button');
  var nav = document.querySelector('.site-header nav');
  if (btn && nav && !btn.dataset.menuWired) {
    btn.dataset.menuWired = 'true';
    btn.addEventListener('click', function () {
      nav.classList.toggle('open');
    });
  }
}
document.addEventListener('partials:ready', wireMenuToggle);
document.addEventListener('DOMContentLoaded', wireMenuToggle);

// Ticker date: was a hardcoded "Monday 7 September" that never changed.
// Fill it in with today's real date on every page load instead.
document.addEventListener('DOMContentLoaded', function () {
  var el = document.getElementById('ticker-date');
  if (!el) return;
  var WEEKDAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  var now = new Date();
  el.textContent = WEEKDAYS[now.getDay()] + ' ' + now.getDate() + ' ' + MONTHS[now.getMonth()];
});

// Homepage only: show the UR nameplate (as a "back to top" button) in place
// of the social icons once the banner has scrolled out of view.
document.addEventListener('DOMContentLoaded', function () {
  var banner = document.querySelector('.brand-banner');
  if (!banner || !document.body.classList.contains('home') || !('IntersectionObserver' in window)) return;
  new IntersectionObserver(function (entries) {
    document.body.classList.toggle('past-banner', !entries[0].isIntersecting);
  }, { rootMargin: '-84px 0px 0px 0px' }).observe(banner);
});
