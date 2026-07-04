// Minimal, dependency-free lightbox for the Examples gallery.
// Clicking a rendered-PDF preview (img.ym-page-shot) opens it enlarged in an
// overlay. Close by clicking the backdrop, the close button, or pressing Escape.
(function () {
  "use strict";

  function ready(fn) {
    if (document.readyState !== "loading") {
      fn();
    } else {
      document.addEventListener("DOMContentLoaded", fn);
    }
  }

  ready(function () {
    var shots = document.querySelectorAll("img.ym-page-shot");
    if (!shots.length) return;

    // Build the overlay once and reuse it.
    var overlay = document.createElement("div");
    overlay.className = "ym-lightbox";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-hidden", "true");
    overlay.innerHTML =
      '<button type="button" class="ym-lightbox__close" aria-label="Close enlarged preview">&times;</button>' +
      '<img class="ym-lightbox__img" alt="">';
    document.body.appendChild(overlay);

    var overlayImg = overlay.querySelector(".ym-lightbox__img");
    var closeBtn = overlay.querySelector(".ym-lightbox__close");
    var lastFocused = null;

    function open(src, alt) {
      lastFocused = document.activeElement;
      overlayImg.setAttribute("src", src);
      overlayImg.setAttribute("alt", alt || "Enlarged preview");
      overlay.classList.add("is-open");
      overlay.setAttribute("aria-hidden", "false");
      document.body.classList.add("ym-lightbox-open");
      closeBtn.focus();
    }

    function close() {
      overlay.classList.remove("is-open");
      overlay.setAttribute("aria-hidden", "true");
      document.body.classList.remove("ym-lightbox-open");
      // Release the (potentially large) image from memory.
      overlayImg.removeAttribute("src");
      if (lastFocused && typeof lastFocused.focus === "function") {
        lastFocused.focus();
      }
    }

    shots.forEach(function (img) {
      img.classList.add("ym-zoomable");
      img.setAttribute("tabindex", "0");
      img.setAttribute("role", "button");
      img.setAttribute("aria-label", "Enlarge preview: " + (img.alt || "PDF page"));

      img.addEventListener("click", function (e) {
        // If Sphinx wrapped the image in a link to the full asset, stop it
        // from navigating so the lightbox handles the click instead.
        e.preventDefault();
        open(img.currentSrc || img.src, img.alt);
      });
      img.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") {
          e.preventDefault();
          open(img.currentSrc || img.src, img.alt);
        }
      });
    });

    overlay.addEventListener("click", function (e) {
      // Click anywhere except on the enlarged image itself closes it.
      if (e.target !== overlayImg) close();
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && overlay.classList.contains("is-open")) {
        close();
      }
    });
  });
})();
