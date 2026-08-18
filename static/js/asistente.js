(function () {
  "use strict";

  var fab = document.getElementById("piaFab");
  var fabBadge = document.getElementById("piaFabBadge");
  var teaser = document.getElementById("piaTeaser");
  var panel = document.getElementById("piaPanel");
  var closeBtn = document.getElementById("piaClose");
  var resetBtn = document.getElementById("piaReset");
  var messages = document.getElementById("piaMessages");
  var chips = document.getElementById("piaChips");
  var input = document.getElementById("piaInput");
  var sendBtn = document.getElementById("piaSend");
  var csrfInput = document.querySelector("#pia-assistant-root [name=csrfmiddlewaretoken]");

  if (!fab || !panel || !messages || !input || !sendBtn) return;

  var STORAGE_KEY = "piaConversation";
  var GREETING_HTML = messages.innerHTML;

  var isOpen = false;
  var isSending = false;
  var conversationHistory = [];

  // ---------- Abrir / cerrar panel ----------

  function openPanel() {
    isOpen = true;
    panel.classList.add("is-open");
    panel.setAttribute("aria-hidden", "false");
    teaser.classList.remove("is-visible");
    fabBadge.classList.remove("is-visible");
    input.focus();
  }

  function closePanel() {
    isOpen = false;
    panel.classList.remove("is-open");
    panel.setAttribute("aria-hidden", "true");
  }

  fab.addEventListener("click", function () {
    isOpen ? closePanel() : openPanel();
  });

  closeBtn.addEventListener("click", closePanel);

  // ---------- Burbuja proactiva ----------

  setTimeout(function () {
    if (!isOpen) {
      teaser.classList.add("is-visible");
      fabBadge.classList.add("is-visible");
    }
  }, 8000);

  teaser.addEventListener("click", function () {
    openPanel();
  });

  // ---------- Chips de acceso rápido ----------

  if (chips) {
    chips.addEventListener("click", function (e) {
      var chip = e.target.closest(".pia-chip");
      if (!chip) return;
      var prompt = chip.getAttribute("data-prompt");
      if (prompt) sendMessage(prompt);
    });
  }

  // ---------- Reiniciar conversación ----------

  function resetConversation() {
    conversationHistory = [];
    messages.innerHTML = GREETING_HTML;
    saveHistory();
    input.focus();
  }

  if (resetBtn) {
    resetBtn.addEventListener("click", resetConversation);
  }

  // ---------- Persistencia (sobrevive a un refresh de la página) ----------
  // sessionStorage: se olvida al cerrar la pestaña.

  function saveHistory() {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(conversationHistory));
    } catch (err) {
      /* sin persistencia si sessionStorage no está disponible */
    }
  }

  function restoreHistory() {
    var raw;
    try {
      raw = sessionStorage.getItem(STORAGE_KEY);
    } catch (err) {
      return;
    }
    if (!raw) return;

    var saved;
    try {
      saved = JSON.parse(raw);
    } catch (err) {
      return;
    }
    if (!Array.isArray(saved) || saved.length === 0) return;

    conversationHistory = saved;
    saved.forEach(function (turn) {
      addMessage(turn.content, turn.role === "assistant" ? "bot" : "user", turn.time, true);
    });
  }

  // ---------- Formato de texto: Markdown ligero y seguro ----------

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderMarkdown(rawText) {
    var escaped = escapeHtml(rawText);

    escaped = escaped.replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
    );
    escaped = escaped.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    escaped = escaped.replace(/(?<!\*)\*(?!\*)(.+?)\*(?!\*)/g, "<em>$1</em>");
    escaped = escaped.replace(/`([^`]+)`/g, "<code>$1</code>");

    var lines = escaped.split("\n");
    var html = "";
    var inList = false;

    lines.forEach(function (line) {
      var trimmed = line.trim();
      var isListItem = /^[-*]\s+/.test(trimmed);

      if (isListItem) {
        if (!inList) {
          html += "<ul>";
          inList = true;
        }
        html += "<li>" + trimmed.replace(/^[-*]\s+/, "") + "</li>";
      } else {
        if (inList) {
          html += "</ul>";
          inList = false;
        }
        if (trimmed !== "") {
          html += "<p>" + trimmed + "</p>";
        }
      }
    });
    if (inList) html += "</ul>";

    return html || escaped;
  }

  function formatTime(date) {
    var d = date ? new Date(date) : new Date();
    var h = d.getHours().toString().padStart(2, "0");
    var m = d.getMinutes().toString().padStart(2, "0");
    return h + ":" + m;
  }

  // ---------- Envío de mensajes ----------

  function addMessage(text, from, time, skipSave) {
    var div = document.createElement("div");
    div.className = "pia-msg from-" + from;

    if (from === "bot") {
      div.innerHTML = renderMarkdown(text);
    } else {
      div.textContent = text;
    }

    var timeEl = document.createElement("span");
    timeEl.className = "pia-msg-time";
    timeEl.textContent = formatTime(time);
    div.appendChild(timeEl);

    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function showTyping() {
    var div = document.createElement("div");
    div.className = "pia-msg from-bot is-typing";
    div.id = "piaTyping";
    div.innerHTML = "<span></span><span></span><span></span>";
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  function hideTyping() {
    var typing = document.getElementById("piaTyping");
    if (typing) typing.remove();
  }

  function setSending(state) {
    isSending = state;
    input.disabled = state;
    sendBtn.disabled = state;
  }

  function sendMessage(text) {
    if (!text || !text.trim() || isSending) return;

    var now = Date.now();
    addMessage(text, "user", now);
    conversationHistory.push({ role: "user", content: text, time: now });
    saveHistory();
    input.value = "";
    showTyping();
    setSending(true);

    fetchAssistantReply(text)
      .then(function (reply) {
        hideTyping();
        var replyTime = Date.now();
        addMessage(reply, "bot", replyTime);
        conversationHistory.push({ role: "assistant", content: reply, time: replyTime });
        saveHistory();
      })
      .catch(function () {
        hideTyping();
        addMessage("No pude conectar con el asistente. Intenta de nuevo en un momento.", "bot", Date.now(), true);
      })
      .finally(function () {
        setSending(false);
        input.focus();
      });
  }

  // Endpoint Django: /asistente/chat/ (ver asistente/urls.py)
  var ASSISTANT_ENDPOINT = "/asistente/chat/";

  function fetchAssistantReply(text) {
    var historyToSend = conversationHistory.slice(0, -1).map(function (turn) {
      return { role: turn.role, content: turn.content };
    });

    var headers = { "Content-Type": "application/json" };
    if (csrfInput && csrfInput.value) {
      headers["X-CSRFToken"] = csrfInput.value;
    }

    return fetch(ASSISTANT_ENDPOINT, {
      method: "POST",
      headers: headers,
      credentials: "same-origin",
      body: JSON.stringify({
        message: text,
        history: historyToSend
      })
    })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        if (data.error) throw new Error(data.error);
        return data.reply;
      });
  }

  sendBtn.addEventListener("click", function () {
    sendMessage(input.value);
  });

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      sendMessage(input.value);
    }
  });

  restoreHistory();
})();