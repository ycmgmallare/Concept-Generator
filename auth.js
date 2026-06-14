// ===========================================================================
// auth.js — shared client-side login popup + authFetch (loaded by all 3 pages)
//
// The pages are public; only tool ACTIONS hit /api/* (guarded by middleware.js).
// Call authFetch(url, opts) instead of fetch() for those calls. On the first
// guarded call (or after wrong credentials) it shows a small login popup, then
// stores the credentials in sessionStorage and retries — so the user is asked
// once per browser session, only when they actually use a tool.
// ===========================================================================
(function () {
  "use strict";

  var STORE_KEY = "cg_auth"; // base64("user:pass") for this tab session
  var loginPromise = null; // shared so concurrent calls show ONE popup
  var modal = null, userEl = null, passEl = null, errEl = null, formEl = null;

  function getCred() {
    try { return sessionStorage.getItem(STORE_KEY) || ""; } catch (e) { return ""; }
  }
  function setCred(b64) {
    try { sessionStorage.setItem(STORE_KEY, b64); } catch (e) {}
  }
  function clearCred() {
    try { sessionStorage.removeItem(STORE_KEY); } catch (e) {}
  }

  function buildModal() {
    if (modal) return;
    var style = document.createElement("style");
    style.textContent =
      ".cg-auth-overlay{position:fixed;inset:0;background:rgba(15,15,18,.72);" +
      "backdrop-filter:blur(3px);display:none;align-items:center;justify-content:center;" +
      "z-index:99999;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}" +
      ".cg-auth-overlay.show{display:flex}" +
      ".cg-auth-card{background:#fff;color:#1a1a1a;width:min(360px,90vw);border-radius:14px;" +
      "padding:26px 24px;box-shadow:0 20px 60px rgba(0,0,0,.4)}" +
      ".cg-auth-card h2{margin:0 0 4px;font-size:19px}" +
      ".cg-auth-card p{margin:0 0 18px;font-size:13px;color:#666}" +
      ".cg-auth-card label{display:block;font-size:12px;font-weight:600;margin:12px 0 5px;color:#333}" +
      ".cg-auth-card input{width:100%;box-sizing:border-box;padding:10px 12px;font-size:14px;" +
      "border:1px solid #d4d4d8;border-radius:8px;outline:none}" +
      ".cg-auth-card input:focus{border-color:#6366f1;box-shadow:0 0 0 3px rgba(99,102,241,.15)}" +
      ".cg-auth-err{color:#dc2626;font-size:12px;min-height:16px;margin-top:10px}" +
      ".cg-auth-btn{width:100%;margin-top:16px;padding:11px;font-size:14px;font-weight:600;" +
      "color:#fff;background:#4f46e5;border:none;border-radius:8px;cursor:pointer}" +
      ".cg-auth-btn:hover{background:#4338ca}";
    document.head.appendChild(style);

    modal = document.createElement("div");
    modal.className = "cg-auth-overlay";
    modal.innerHTML =
      '<form class="cg-auth-card">' +
      "<h2>Sign in to continue</h2>" +
      "<p>Enter the username and password for this tool.</p>" +
      '<label for="cg-auth-user">Username</label>' +
      '<input id="cg-auth-user" type="text" autocomplete="username" autofocus>' +
      '<label for="cg-auth-pass">Password</label>' +
      '<input id="cg-auth-pass" type="password" autocomplete="current-password">' +
      '<div class="cg-auth-err"></div>' +
      '<button class="cg-auth-btn" type="submit">Continue</button>' +
      "</form>";
    document.body.appendChild(modal);

    formEl = modal.querySelector("form");
    userEl = modal.querySelector("#cg-auth-user");
    passEl = modal.querySelector("#cg-auth-pass");
    errEl = modal.querySelector(".cg-auth-err");
  }

  function showModal(message) {
    buildModal();
    errEl.textContent = message || "";
    modal.classList.add("show");
    passEl.value = "";
    setTimeout(function () { (userEl.value ? passEl : userEl).focus(); }, 30);
  }
  function hideModal() {
    if (modal) modal.classList.remove("show");
  }

  // Show the popup and resolve with base64 credentials when submitted.
  // Concurrent callers share the same popup/promise.
  function promptLogin(message) {
    if (loginPromise) return loginPromise;
    loginPromise = new Promise(function (resolve) {
      showModal(message);
      formEl.onsubmit = function (e) {
        e.preventDefault();
        var u = userEl.value.trim();
        var p = passEl.value;
        if (!u || !p) { errEl.textContent = "Enter both fields."; return; }
        var b64 = btoa(u + ":" + p);
        setCred(b64);
        hideModal();
        resolve(b64);
      };
    }).then(function (v) { loginPromise = null; return v; });
    return loginPromise;
  }

  // Drop-in fetch replacement for guarded /api/* calls.
  async function authFetch(url, opts) {
    opts = opts || {};
    var cred = getCred();
    if (!cred) cred = await promptLogin("");
    for (var attempt = 0; attempt < 5; attempt++) {
      var headers = Object.assign({}, opts.headers || {}, { Authorization: "Basic " + cred });
      var res = await fetch(url, Object.assign({}, opts, { headers: headers }));
      if (res.status !== 401) return res;
      clearCred();
      cred = await promptLogin("Incorrect username or password. Try again.");
    }
    throw new Error("Authentication failed.");
  }

  window.authFetch = authFetch;
})();
