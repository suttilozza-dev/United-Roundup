// Client-side HTML includes.
//
// Finds every placeholder element with a `data-include="<name>"` attribute,
// fetches the matching partial from /assets/partials/<name>.html and swaps
// the placeholder for the fetched markup. Used for chrome that's shared
// across every page (nav, footer) so it only has to be edited in one place.
//
// To add a new shared partial:
//   1. Put the markup in assets/partials/<name>.html (root-relative links
//      only, e.g. href="/about.html", so it works from any page depth).
//   2. Drop <div data-include="<name>"></div> where the markup should go.
//   3. Make sure the page also loads this script:
//        <script src="/assets/includes.js" defer></script>
//
// Once every placeholder on the page has been replaced, a `partials:ready`
// event is dispatched on `document` so other deferred scripts (e.g. the
// mobile menu toggle in main.js) can safely look for the injected markup.
(function () {
  "use strict";

  function loadPartial(el) {
    var name = el.getAttribute("data-include");
    if (!name) return Promise.resolve();
    return fetch("/assets/partials/" + name + ".html")
      .then(function (res) {
        if (!res.ok) {
          throw new Error("includes.js: failed to fetch partial \"" + name + "\" (" + res.status + ")");
        }
        return res.text();
      })
      .then(function (html) {
        el.outerHTML = html;
      })
      .catch(function (err) {
        // Leave the placeholder out of the page rather than crash the rest
        // of the page's scripts; log so it's obvious during development.
        console.error(err);
        if (el.parentNode) el.parentNode.removeChild(el);
      });
  }

  function run() {
    var placeholders = Array.prototype.slice.call(document.querySelectorAll("[data-include]"));
    if (!placeholders.length) return;
    Promise.all(placeholders.map(loadPartial)).then(function () {
      document.dispatchEvent(new CustomEvent("partials:ready"));
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
