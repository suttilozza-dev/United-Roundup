(function () {
  "use strict";

  var CONSENT_KEY = "ur_cookie_consent"; // 'accepted' | 'declined'

  // TODO: replace with the real GA4 Measurement ID once created, e.g. "G-ABC1234XYZ".
  // Left as a placeholder on purpose -- loadAnalytics() below refuses to fire while
  // this still looks like a placeholder, so nothing calls out to Google until a real
  // ID is dropped in here.
  var GA_MEASUREMENT_ID = "G-81QGG9136Z";

  function isConfigured() {
    return typeof GA_MEASUREMENT_ID === "string" && GA_MEASUREMENT_ID.indexOf("XXXX") === -1;
  }

  function getConsent() {
    try {
      return localStorage.getItem(CONSENT_KEY);
    } catch (e) {
      return null;
    }
  }

  function setConsent(value) {
    try {
      localStorage.setItem(CONSENT_KEY, value);
    } catch (e) {
      /* ignore - storage unavailable, treat as session-only */
    }
  }

  function clearConsent() {
    try {
      localStorage.removeItem(CONSENT_KEY);
    } catch (e) {
      /* ignore */
    }
  }

  // Works out how many directory levels deep the current page is, so the banner's
  // privacy-policy link and any other relative link stay correct on article pages
  // (e.g. /briefings/derby-apology/) as well as root pages (e.g. /about.html).
  function relativePrefix() {
    var path = window.location.pathname;
    var segments = path.split("/").filter(Boolean);
    var depth;
    if (path.charAt(path.length - 1) === "/") {
      depth = segments.length; // directory-style URL, e.g. /briefings/derby-apology/
    } else {
      depth = Math.max(segments.length - 1, 0); // file URL, e.g. /about.html or /
    }
    var prefix = "";
    for (var i = 0; i < depth; i++) prefix += "../";
    return prefix;
  }

  function loadAnalytics() {
    if (!isConfigured()) return; // no real Measurement ID yet -- do nothing
    if (window.__urGaLoaded) return;
    window.__urGaLoaded = true;

    window.dataLayer = window.dataLayer || [];
    function gtag() {
      window.dataLayer.push(arguments);
    }
    window.gtag = gtag;
    gtag("js", new Date());
    gtag("config", GA_MEASUREMENT_ID);

    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + GA_MEASUREMENT_ID;
    document.head.appendChild(s);
  }

  function removeBanner() {
    var banner = document.getElementById("cookie-consent-banner");
    if (banner && banner.parentNode) banner.parentNode.removeChild(banner);
  }

  function buildBanner() {
    if (document.getElementById("cookie-consent-banner")) return;
    var banner = document.createElement("div");
    banner.id = "cookie-consent-banner";
    banner.className = "cookie-consent";
    banner.setAttribute("role", "region");
    banner.setAttribute("aria-label", "Cookie notice");
    banner.innerHTML =
      "<p>This site uses analytics cookies to understand how many people visit and which " +
      "stories they read. No tracking or advertising cookies are set. " +
      'See our <a href="' + relativePrefix() + 'privacy.html">privacy &amp; cookies page</a>.</p>' +
      '<div class="cookie-consent-actions">' +
      '<button type="button" id="cookie-consent-decline">Decline</button>' +
      '<button type="button" id="cookie-consent-accept">Accept</button>' +
      "</div>";
    document.body.appendChild(banner);
    document.getElementById("cookie-consent-accept").addEventListener("click", function () {
      setConsent("accepted");
      removeBanner();
      loadAnalytics();
    });
    document.getElementById("cookie-consent-decline").addEventListener("click", function () {
      setConsent("declined");
      removeBanner();
    });
  }

  function init() {
    var consent = getConsent();
    if (consent === "accepted") {
      loadAnalytics();
      return;
    }
    if (consent === "declined") {
      return;
    }
    // No decision yet: show the banner and wait.
    buildBanner();
  }

  // Exposed so a "Cookie settings" link (in the footer, or the privacy page's own
  // button) can reopen the prompt and let a visitor change their mind.
  window.UR_openCookieChoice = function () {
    clearConsent();
    removeBanner();
    buildBanner();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
