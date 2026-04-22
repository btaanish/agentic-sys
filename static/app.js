document.addEventListener("DOMContentLoaded", function () {
  var form = document.getElementById("research-form");
  var queryInput = document.getElementById("query");
  var tokenInput = document.getElementById("api-token");
  var submitBtn = document.getElementById("submit-btn");
  var errorDiv = document.getElementById("error");
  var progressSection = document.getElementById("progress-section");
  var progressList = document.getElementById("progress");
  var resultSection = document.getElementById("result-section");
  var resultDiv = document.getElementById("result");
  var loadingSpinner = document.getElementById("loading-spinner");
  var resultActions = document.getElementById("result-actions");
  var copyResultBtn = document.getElementById("copy-result-btn");
  var downloadResultBtn = document.getElementById("download-result-btn");
  var queryHistoryDiv = document.getElementById("query-history");
  var clearHistoryBtn = document.getElementById("clear-history-btn");
  var subQuestionsPanel = document.getElementById("sub-questions-panel");
  var subQuestionsList = document.getElementById("sub-questions-list");

  var HISTORY_KEY = "queryHistory";
  var MAX_HISTORY = 10;

  var rawResultText = "";

  // --- Query History ---

  function getQueryHistory() {
    try {
      var stored = localStorage.getItem(HISTORY_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch (e) {
      return [];
    }
  }

  function saveQueryToHistory(query) {
    var history = getQueryHistory();
    history = history.filter(function (item) { return item !== query; });
    history.unshift(query);
    if (history.length > MAX_HISTORY) {
      history = history.slice(0, MAX_HISTORY);
    }
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    renderQueryHistory();
  }

  function renderQueryHistory() {
    var history = getQueryHistory();
    queryHistoryDiv.innerHTML = "";
    if (history.length === 0) {
      queryHistoryDiv.innerHTML = "<p class='history-empty'>No queries yet.</p>";
      return;
    }
    for (var i = 0; i < history.length; i++) {
      var item = document.createElement("div");
      item.className = "history-item";
      item.textContent = history[i];
      item.setAttribute("data-query", history[i]);
      item.addEventListener("click", function () {
        queryInput.value = this.getAttribute("data-query");
      });
      queryHistoryDiv.appendChild(item);
    }
  }

  clearHistoryBtn.addEventListener("click", function () {
    localStorage.removeItem(HISTORY_KEY);
    renderQueryHistory();
  });

  renderQueryHistory();

  // --- Export/Copy Results ---

  copyResultBtn.addEventListener("click", function () {
    navigator.clipboard.writeText(rawResultText || resultDiv.innerText).then(function () {
      copyResultBtn.textContent = "Copied!";
      setTimeout(function () {
        copyResultBtn.textContent = "Copy to Clipboard";
      }, 2000);
    });
  });

  downloadResultBtn.addEventListener("click", function () {
    var text = rawResultText || resultDiv.innerText;
    var blob = new Blob([text], { type: "text/plain" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "research-result.txt";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  function showResultActions() { resultActions.hidden = false; }
  function hideResultActions() { resultActions.hidden = true; }
  function showSpinner() { loadingSpinner.hidden = false; }
  function hideSpinner() { loadingSpinner.hidden = true; }

  // --- Progress stream ---
  // We only render an ordered, deduplicated list of meaningful steps.
  // The previous step is marked "done" when a new one arrives.

  var lastStepEl = null;
  var seenKeys = {};

  function addStep(key, label) {
    if (seenKeys[key]) return seenKeys[key];
    if (lastStepEl) {
      lastStepEl.classList.remove("step-active");
      lastStepEl.classList.add("step-done");
    }
    var li = document.createElement("li");
    li.className = "progress-step step-active";
    li.innerHTML = '<span class="step-indicator"></span><span class="step-label"></span>';
    li.querySelector(".step-label").textContent = label;
    progressList.appendChild(li);
    lastStepEl = li;
    seenKeys[key] = li;
    return li;
  }

  function finishAllSteps() {
    if (lastStepEl) {
      lastStepEl.classList.remove("step-active");
      lastStepEl.classList.add("step-done");
      lastStepEl = null;
    }
  }

  function addWarning(text) {
    var li = document.createElement("li");
    li.className = "progress-step step-warning";
    li.innerHTML = '<span class="step-indicator"></span><span class="step-label"></span>';
    li.querySelector(".step-label").textContent = text;
    progressList.appendChild(li);
  }

  // Map raw status messages to a stable (key, label) pair that makes sense
  // to the user. Returns null for noisy/internal messages we don't surface.
  function classifyStatus(msg) {
    if (!msg) return null;
    if (msg.indexOf("Decomposing") === 0) {
      return { key: "decompose", label: "Decomposing query into sub-questions" };
    }
    if (msg.indexOf("Researching sub-topic:") === 0) {
      var topic = msg.slice("Researching sub-topic:".length).trim();
      return { key: "research:" + topic, label: "Researching — " + topic };
    }
    if (msg.indexOf("Synthesizing") === 0) {
      return { key: "synthesize", label: "Synthesizing results" };
    }
    if (msg === "Done") {
      return { key: "done", label: "Done" };
    }
    return null;
  }

  // --- Form Submit ---

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var query = queryInput.value.trim();
    if (!query) return;

    saveQueryToHistory(query);

    // Reset UI
    errorDiv.hidden = true;
    errorDiv.textContent = "";
    progressSection.hidden = false;
    progressList.innerHTML = "";
    resultSection.hidden = true;
    resultDiv.innerHTML = "";
    rawResultText = "";
    subQuestionsPanel.hidden = true;
    subQuestionsList.innerHTML = "";
    hideResultActions();
    submitBtn.disabled = true;
    submitBtn.textContent = "Researching…";
    showSpinner();
    lastStepEl = null;
    seenKeys = {};

    var body = { query: query };
    var token = tokenInput.value.trim();
    if (token) body.api_token = token;

    fetch("/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Server error: " + response.status);
        }
        var reader = response.body.getReader();
        var decoder = new TextDecoder();
        var buffer = "";

        function read() {
          return reader.read().then(function (result) {
            if (result.done) {
              done();
              return;
            }
            buffer += decoder.decode(result.value, { stream: true });
            var lines = buffer.split("\n");
            buffer = lines.pop();
            for (var i = 0; i < lines.length; i++) {
              var line = lines[i];
              if (line.startsWith("data: ")) {
                try {
                  var event = JSON.parse(line.slice(6));
                  handleEvent(event);
                } catch (err) {
                  // skip malformed lines
                }
              }
            }
            return read();
          });
        }

        return read();
      })
      .catch(function (err) {
        errorDiv.textContent = err.message || "An error occurred";
        errorDiv.hidden = false;
        done();
      });
  });

  function handleEvent(event) {
    if (event.event === "status") {
      var mapped = classifyStatus(event.message || "");
      if (mapped) addStep(mapped.key, mapped.label);
    } else if (event.event === "state_update") {
      handleStateUpdate(event);
    } else if (event.event === "result") {
      finishAllSteps();
      resultSection.hidden = false;
      rawResultText = event.data || "";
      resultDiv.innerHTML = renderMarkdown(rawResultText);
      showResultActions();
    } else if (event.event === "error") {
      errorDiv.textContent = event.message || "Research failed";
      errorDiv.hidden = false;
    }
  }

  function handleStateUpdate(event) {
    var msg = event.message || "";
    var data = null;
    try {
      data = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
    } catch (e) {
      data = {};
    }

    // Populate sub-questions panel once.
    if (msg === "Sub-questions identified" && data && data.sub_questions) {
      subQuestionsPanel.hidden = false;
      subQuestionsList.innerHTML = "";
      for (var i = 0; i < data.sub_questions.length; i++) {
        var div = document.createElement("div");
        div.className = "sq-item";
        div.setAttribute("data-index", i);
        div.innerHTML = '<span class="sq-check"></span><span class="sq-text"></span>';
        div.querySelector(".sq-text").textContent = data.sub_questions[i].text;
        subQuestionsList.appendChild(div);
      }
      return;
    }

    // Mark completed sub-questions when their confidence crosses the threshold.
    if (msg === "Iteration progress" && data && data.confidence_per_sub_question) {
      var sqItems = subQuestionsList.querySelectorAll(".sq-item");
      for (var j = 0; j < sqItems.length; j++) {
        var idx = sqItems[j].getAttribute("data-index");
        if (data.confidence_per_sub_question[idx] !== undefined && data.confidence_per_sub_question[idx] >= 0.8) {
          sqItems[j].classList.add("sq-done");
        }
      }
      return;
    }

    // Surface genuine warnings.
    if (msg.indexOf("Warning:") === 0) {
      addWarning(msg);
      return;
    }
    // Everything else is internal bookkeeping — ignore for the progress UI.
  }

  // --- Minimal, safe markdown renderer ---
  // Escapes HTML first, then applies markdown transformations so that any
  // HTML in the source is rendered as literal text. Supports: headings (#..######),
  // bold/italic, inline code, fenced code blocks, unordered/ordered lists,
  // blockquotes, horizontal rules, paragraphs.

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function renderInline(s) {
    return s
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
  }

  function renderMarkdown(md) {
    if (!md) return "";

    // 1. Pull fenced code blocks out first so other rules don't mangle them.
    var codeBlocks = [];
    md = md.replace(/```(?:[\w-]+)?\n?([\s\S]*?)```/g, function (_, code) {
      codeBlocks.push(code);
      return " CODEBLOCK" + (codeBlocks.length - 1) + " ";
    });

    // 2. Escape everything so raw HTML in the response is inert.
    md = escapeHtml(md);

    var lines = md.split("\n");
    var out = [];
    var listType = null;
    var paraBuf = [];

    function flushPara() {
      if (paraBuf.length) {
        out.push("<p>" + renderInline(paraBuf.join(" ")) + "</p>");
        paraBuf = [];
      }
    }
    function closeList() {
      if (listType) {
        out.push("</" + listType + ">");
        listType = null;
      }
    }

    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];

      if (/^\s*$/.test(line)) {
        flushPara();
        closeList();
        continue;
      }

      var h = line.match(/^(#{1,6})\s+(.*)$/);
      if (h) {
        flushPara(); closeList();
        var level = h[1].length;
        out.push("<h" + level + ">" + renderInline(h[2].trim()) + "</h" + level + ">");
        continue;
      }

      if (/^\s*(---|\*\*\*|___)\s*$/.test(line)) {
        flushPara(); closeList();
        out.push("<hr>");
        continue;
      }

      var ul = line.match(/^\s*[-*+]\s+(.*)$/);
      if (ul) {
        flushPara();
        if (listType !== "ul") { closeList(); out.push("<ul>"); listType = "ul"; }
        out.push("<li>" + renderInline(ul[1]) + "</li>");
        continue;
      }

      var ol = line.match(/^\s*\d+\.\s+(.*)$/);
      if (ol) {
        flushPara();
        if (listType !== "ol") { closeList(); out.push("<ol>"); listType = "ol"; }
        out.push("<li>" + renderInline(ol[1]) + "</li>");
        continue;
      }

      var bq = line.match(/^\s*>\s?(.*)$/);
      if (bq) {
        flushPara(); closeList();
        out.push("<blockquote>" + renderInline(bq[1]) + "</blockquote>");
        continue;
      }

      closeList();
      paraBuf.push(line.trim());
    }
    flushPara();
    closeList();

    var html = out.join("\n");

    // 3. Restore code blocks.
    html = html.replace(/ CODEBLOCK(\d+) /g, function (_, idx) {
      return "<pre><code>" + escapeHtml(codeBlocks[parseInt(idx, 10)]) + "</code></pre>";
    });

    return html;
  }

  function done() {
    submitBtn.disabled = false;
    submitBtn.textContent = "Research";
    hideSpinner();
    finishAllSteps();
  }
});
