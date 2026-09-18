// Mobile menu toggle
document.addEventListener('DOMContentLoaded', function () {
  var btn = document.querySelector('.menu-button');
  var nav = document.querySelector('.site-header nav');
  if (btn && nav) {
    btn.addEventListener('click', function () {
      nav.classList.toggle('open');
    });
  }
});

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
