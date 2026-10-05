/* CropCare AI - shows the real rejection reason from the backend.
   Load it AFTER analyze.js on analyze.html. */
(function () {
  var originalFetch = window.fetch.bind(window);
  var lastReason = "";

  window.fetch = function (input, init) {
    var url = typeof input === "string" ? input : (input && input.url) || "";
    var isPredict = url.indexOf("/predict") !== -1;
    if (isPredict) lastReason = "";
    return originalFetch(input, init).then(function (res) {
      if (isPredict && (res.status === 422 || res.status === 400)) {
        res.clone().json().then(function (data) {
          lastReason = (data && (data.reason || data.message)) || "";
          showReason();
        }).catch(function () {});
      }
      return res;
    });
  };

  function showReason() {
    if (!lastReason) return;
    var section = document.getElementById("rejectionSection");
    var title = document.getElementById("rejTitle");
    var text = document.getElementById("rejText");
    if (!section || section.hidden || !title || !text) return;
    if (title.textContent !== "Image not suitable") title.textContent = "Image not suitable";
    if (text.textContent !== lastReason) text.textContent = lastReason;
  }

  function init() {
    var section = document.getElementById("rejectionSection");
    if (!section) return;
    new MutationObserver(showReason).observe(section, {
      attributes: true, childList: true, subtree: true, characterData: true
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
