(function () {
  "use strict";

  var CONSENT_KEY = "ur_cookie_consent"; // 'accepted' | 'declined'
  var KIT_SRC = "https://unitedroundup.kit.com/df3c9b9f5a/index.js";
  var KIT_UID = "df3c9b9f5a";

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

  function loadKitForm() {
    var mount = document.getElementById("kit-form-mount");
    if (!mount) return;
    var fallback = document.getElementById("newsletter-fallback");
    if (fallback) fallback.hidden = true;
    if (mount.querySelector("script[data-kit-form]")) return; // already loaded
    var s = document.createElement("script");
    s.async = true;
    s.setAttribute("data-uid", KIT_UID);
    s.setAttribute("data-kit-form", "1");
    s.src = KIT_SRC;
    mount.appendChild(s);
  }

  function showFallback() {
    var fallback = document.getElementById("newsletter-fallback");
    if (fallback) fallback.hidden = false;
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
      '<p>This site uses one cookie, only for the Weekly Roundup sign-up form, ' +
      "so it can remember if you&rsquo;ve already subscribed. No other cookies are set. " +
      'See our <a href="' + (window.__ur_privacy_href || "privacy.html") + '">privacy &amp; cookies page</a>.</p>' +
      '<div class="cookie-consent-actions">' +
      '<button type="button" id="cookie-consent-decline">Decline</button>' +
      '<button type="button" id="cookie-consent-accept">Accept</button>' +
      "</div>";
    document.body.appendChild(banner);
    document.getElementById("cookie-consent-accept").addEventListener("click", function () {
      setConsent("accepted");
      removeBanner();
      loadKitForm();
    });
    document.getElementById("cookie-consent-decline").addEventListener("click", function () {
      setConsent("declined");
      removeBanner();
      showFallback();
    });
  }

  function init() {
    var consent = getConsent();
    if (consent === "accepted") {
      loadKitForm();
      return;
    }
    if (consent === "declined") {
      showFallback();
      return;
    }
    // No decision yet: just show the banner. The form area stays empty
    // (not the "declined" message, which would be inaccurate) until a
    // choice is actually made.
    buildBanner();
  }

  // Exposed so the "change your choice" controls (in the fallback message
  // and on the privacy page) can re-open the prompt.
  window.UR_openCookieChoice = function () {
    clearConsent();
    removeBanner();
    buildBanner();
    var fallback = document.getElementById("newsletter-fallback");
    if (fallback) fallback.hidden = false;
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
