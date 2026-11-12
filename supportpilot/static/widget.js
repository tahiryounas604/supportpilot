/* SupportPilot embeddable widget — vanilla JS, no dependencies.
   Usage:
     <script src="http://localhost:8765/widget.js" data-api="http://localhost:8765"></script>
   If data-api is omitted, the script's own origin is used. */
(function () {
  "use strict";
  var script = document.currentScript;
  var api = "";
  if (script) {
    api = script.getAttribute("data-api") || "";
    if (!api && script.src) {
      try { api = new URL(script.src).origin; } catch (e) { api = ""; }
    }
  }

  var style = document.createElement("style");
  style.textContent =
    "#sp-bubble{position:fixed;right:20px;bottom:20px;width:56px;height:56px;border-radius:50%;" +
    "background:#0f766e;color:#fff;border:none;font-size:24px;cursor:pointer;z-index:99999;" +
    "box-shadow:0 4px 16px rgba(0,0,0,.25)}" +
    "#sp-panel{position:fixed;right:20px;bottom:88px;width:340px;max-width:92vw;height:440px;" +
    "max-height:70vh;background:#fff;border:1px solid #ddd;border-radius:12px;display:none;" +
    "flex-direction:column;z-index:99999;box-shadow:0 8px 32px rgba(0,0,0,.2);font-family:system-ui,sans-serif}" +
    "#sp-panel.open{display:flex}" +
    "#sp-head{background:#0f766e;color:#fff;padding:12px 16px;border-radius:12px 12px 0 0;font-weight:600}" +
    "#sp-msgs{flex:1;overflow-y:auto;padding:12px;font-size:14px}" +
    ".sp-msg{margin:0 0 10px;padding:8px 10px;border-radius:8px;white-space:pre-wrap}" +
    ".sp-user{background:#e0f2f1;text-align:right}.sp-bot{background:#f3f4f6}" +
    ".sp-src{font-size:11px;color:#666;margin-top:4px}" +
    "#sp-form{display:flex;border-top:1px solid #eee}" +
    "#sp-input{flex:1;border:none;padding:12px;font-size:14px;outline:none}" +
    "#sp-send{border:none;background:#0f766e;color:#fff;padding:0 16px;cursor:pointer}";
  document.head.appendChild(style);

  var bubble = document.createElement("button");
  bubble.id = "sp-bubble";
  bubble.textContent = "💬";
  bubble.setAttribute("aria-label", "Open support chat");

  var panel = document.createElement("div");
  panel.id = "sp-panel";
  panel.innerHTML =
    '<div id="sp-head">Support</div><div id="sp-msgs"></div>' +
    '<form id="sp-form"><input id="sp-input" placeholder="Ask a question…" autocomplete="off">' +
    '<button id="sp-send" type="submit">Send</button></form>';

  function ready() {
    document.body.appendChild(bubble);
    document.body.appendChild(panel);
    var msgs = panel.querySelector("#sp-msgs");
    var input = panel.querySelector("#sp-input");
    bubble.addEventListener("click", function () { panel.classList.toggle("open"); });
    function add(text, cls, sources) {
      var d = document.createElement("div");
      d.className = "sp-msg " + cls;
      d.textContent = text;
      if (sources && sources.length) {
        var s = document.createElement("div");
        s.className = "sp-src";
        s.textContent = "Sources: " + sources.map(function (x) { return x.source; }).join(", ");
        d.appendChild(s);
      }
      msgs.appendChild(d);
      msgs.scrollTop = msgs.scrollHeight;
    }
    panel.querySelector("#sp-form").addEventListener("submit", function (ev) {
      ev.preventDefault();
      var q = input.value.trim();
      if (!q) return;
      add(q, "sp-user");
      input.value = "";
      fetch(api + "/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q })
      }).then(function (r) { return r.json(); })
        .then(function (data) { add(data.answer || "No answer.", "sp-bot", data.sources); })
        .catch(function () { add("Sorry — the chat service is unreachable.", "sp-bot"); });
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ready);
  } else { ready(); }
})();
