document.addEventListener("DOMContentLoaded", function () {
  var form = document.getElementById("research-form");
  var queryInput = document.getElementById("query");
  var tokenInput = document.getElementById("api-token");
  var submitBtn = document.getElementById("submit-btn");
  var errorDiv = document.getElementById("error");
  var progressSection = document.getElementById("progress-section");
  var progressDiv = document.getElementById("progress");
  var resultSection = document.getElementById("result-section");
  var resultDiv = document.getElementById("result");
  var loadingSpinner = document.getElementById("loading-spinner");
  var resultActions = document.getElementById("result-actions");
  var copyResultBtn = document.getElementById("copy-result-btn");
  var downloadResultBtn = document.getElementById("download-result-btn");
  var queryHistoryDiv = document.getElementById("query-history");
  var clearHistoryBtn = document.getElementById("clear-history-btn");

  var HISTORY_KEY = "queryHistory";
  var MAX_HISTORY = 10;

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
    // Remove duplicate if exists
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
    var text = resultDiv.textContent;
    navigator.clipboard.writeText(text).then(function () {
      copyResultBtn.textContent = "Copied!";
      setTimeout(function () {
        copyResultBtn.textContent = "Copy to Clipboard";
      }, 2000);
    });
  });

  downloadResultBtn.addEventListener("click", function () {
    var text = resultDiv.textContent;
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

  function showResultActions() {
    resultActions.hidden = false;
  }

  function hideResultActions() {
    resultActions.hidden = true;
  }

  // --- Loading Spinner ---

  function showSpinner() {
    loadingSpinner.hidden = false;
  }

  function hideSpinner() {
    loadingSpinner.hidden = true;
  }

  // --- Form Submit ---

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var query = queryInput.value.trim();
    if (!query) return;

    // Save to history
    saveQueryToHistory(query);

    // Reset UI
    errorDiv.hidden = true;
    errorDiv.textContent = "";
    progressSection.hidden = false;
    progressDiv.innerHTML = "";
    resultSection.hidden = true;
    resultDiv.textContent = "";
    hideResultActions();
    submitBtn.disabled = true;
    submitBtn.textContent = "Researching\u2026";
    showSpinner();

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
      var item = document.createElement("div");
      item.className = "progress-item";
      item.textContent = event.message || JSON.stringify(event);
      progressDiv.appendChild(item);
      progressDiv.scrollTop = progressDiv.scrollHeight;
    } else if (event.event === "result") {
      resultSection.hidden = false;
      resultDiv.textContent = event.data || JSON.stringify(event);
      showResultActions();
    } else if (event.event === "error") {
      errorDiv.textContent = event.message || "Research failed";
      errorDiv.hidden = false;
    }
  }

  function done() {
    submitBtn.disabled = false;
    submitBtn.textContent = "Research";
    hideSpinner();
  }
});
