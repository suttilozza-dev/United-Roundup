(function () {
  "use strict";

  var CONSENT_KEY = "ur_cookie_consent"; // 'accepted' | 'declined'

  // TODO: replace with the real GA4 Measurement ID once created, e.g. "G-ABC1234XYZ".
  // Left as a placeholder on purpose -- loadAnalytics() below refuses to fire while
  // this still looks like a placeholder, so nothing calls out to Google until a real
  // ID is dropped in here.
  var GA_MEASUREMENT_ID = "G-81QGG9136Z";

  // Google Ads tag. Loaded only after consent, together with GA4 (see loadAnalytics).
  var ADS_TAG_ID = "AW-18489674283";

  // Links to the Kit newsletter landing page.
  var NEWSLETTER_LINK = 'a[href^="https://unitedroundup.kit.com/df3c9b9f5a"]';

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

  // Google tags (GA4 + Google Ads). One gtag.js request, made only after Accept.
  // Nothing from googletagmanager.com is requested before that or after Decline.
  function loadAnalytics() {
    if (window.__urGaLoaded) return;
    window.__urGaLoaded = true;

    window.dataLayer = window.dataLayer || [];
    if (typeof window.gtag !== "function") {
      window.gtag = function () {
        window.dataLayer.push(arguments);
      };
    }
    var gtag = window.gtag;

    // Consent Mode v2 signals for UK/EU visitors. The tag only exists once the visitor
    // has accepted, so the default is set to denied and then updated to granted
    // straight away, before js/config are queued.
    var granted = {
      ad_storage: "granted",
      ad_user_data: "granted",
      ad_personalization: "granted",
      analytics_storage: "granted",
    };
    gtag("consent", "default", {
      ad_storage: "denied",
      ad_user_data: "denied",
      ad_personalization: "denied",
      analytics_storage: "denied",
      wait_for_update: 500,
    });
    gtag("consent", "update", granted);

    gtag("js", new Date());
    if (isConfigured()) gtag("config", GA_MEASUREMENT_ID);
    gtag("config", ADS_TAG_ID);

    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + ADS_TAG_ID;
    document.head.appendChild(s);

    trackNewsletterClicks();
  }

  // Kit landing page links (the sign-up buttons and the footer link). Delegated, so
  // links added later by the shared nav/footer partials are covered too. Registered
  // only after consent, so nothing is sent without it.
  function trackNewsletterClicks() {
    if (window.__urNewsletterTracked) return;
    window.__urNewsletterTracked = true;
    document.addEventListener("click", function (e) {
      var link = e.target && e.target.closest ? e.target.closest(NEWSLETTER_LINK) : null;
      if (link && typeof window.gtag === "function") window.gtag("event", "newsletter_click");
    });
  }

  // Embedded X posts: widgets.js is third-party and sets its own cookies, so it
  // loads only after consent. Without consent the <blockquote> shows as plain text.
  function loadEmbeds() {
    if (window.__urEmbedsLoaded) return;
    if (!document.querySelector(".twitter-tweet")) return;
    window.__urEmbedsLoaded = true;
    // Swaps the "loads once you accept cookies" placeholders for the posts (see .ur-embeds-on in extra.css).
    document.documentElement.classList.add("ur-embeds-on");
    var s = document.createElement("script");
    s.async = true;
    s.charset = "utf-8";
    s.src = "https://platform.x.com/widgets.js";
    document.body.appendChild(s);
  }

  // Google AdSense: the library and the slot markup (assets/ads.js) load only after
  // consent. Without it the .ur-ad placeholders stay hidden.
  function loadAds() {
    if (window.__urAdsLoaded) return;
    if (!document.querySelector(".ur-ad")) return;
    window.__urAdsLoaded = true;
    var s = document.createElement("script");
    s.async = true;
    s.src = "/assets/ads.js";
    document.body.appendChild(s);
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
      "stories they read, lets embedded posts from X load, and lets Google show and measure advertising, which uses its own cookies. " +
      "Nothing from Google loads unless you accept. " +
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
      loadEmbeds();
      loadAds();
    });
    document.getElementById("cookie-consent-decline").addEventListener("click", function () {
      setConsent("declined");
      removeBanner();
      // Only matters if the visitor accepted earlier this page view and has now changed their mind.
      if (typeof window.gtag === "function") {
        window.gtag("consent", "update", {
          ad_storage: "denied",
          ad_user_data: "denied",
          ad_personalization: "denied",
          analytics_storage: "denied",
        });
      }
    });
  }

  function init() {
    var consent = getConsent();
    if (consent === "accepted") {
      loadAnalytics();
      loadEmbeds();
      loadAds();
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
