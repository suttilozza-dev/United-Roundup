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
