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
  var subQuestionsPanel = document.getElementById("sub-questions-panel");
  var subQuestionsList = document.getElementById("sub-questions-list");
  var confidencePanel = document.getElementById("confidence-panel");
  var confidenceDisplay = document.getElementById("confidence-display");
  var evidenceQualityPanel = document.getElementById("evidence-quality-panel");
  var evidenceQualityDisplay = document.getElementById("evidence-quality-display");
  var anglesPanel = document.getElementById("angles-panel");
  var anglesDisplay = document.getElementById("angles-display");
  var structuredResult = document.getElementById("structured-result");

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
    structuredResult.hidden = true;
    structuredResult.innerHTML = "";
    subQuestionsPanel.hidden = true;
    subQuestionsList.innerHTML = "";
    confidencePanel.hidden = true;
    confidenceDisplay.innerHTML = "";
    evidenceQualityPanel.hidden = true;
    evidenceQualityDisplay.innerHTML = "";
    anglesPanel.hidden = true;
    anglesDisplay.innerHTML = "";
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
    } else if (event.event === "state_update") {
      handleStateUpdate(event);
    } else if (event.event === "result") {
      resultSection.hidden = false;
      var text = event.data || JSON.stringify(event);
      resultDiv.textContent = text;
      renderStructuredResult(text);
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

    // Also show as progress item
    var item = document.createElement("div");
    item.className = "progress-item";
    item.textContent = msg;
    progressDiv.appendChild(item);
    progressDiv.scrollTop = progressDiv.scrollHeight;

    if (msg === "Sub-questions identified" && data && data.sub_questions) {
      subQuestionsPanel.hidden = false;
      subQuestionsList.innerHTML = "";
      for (var i = 0; i < data.sub_questions.length; i++) {
        var div = document.createElement("div");
        div.className = "sq-item";
        div.setAttribute("data-index", i);
        div.innerHTML = '<span class="sq-check"></span><span class="sq-text">' + escapeHtml(data.sub_questions[i].text) + "</span>";
        subQuestionsList.appendChild(div);
      }
    }

    if (data && data.exploration_angles && data.exploration_angles.length > 0) {
      anglesPanel.hidden = false;
      anglesDisplay.innerHTML = "";
      for (var ea = 0; ea < data.exploration_angles.length; ea++) {
        var angleDiv = document.createElement("div");
        angleDiv.className = "angle-item";
        angleDiv.textContent = data.exploration_angles[ea];
        anglesDisplay.appendChild(angleDiv);
      }
    }

    if (msg === "Iteration progress" && data) {
      confidencePanel.hidden = false;
      var pct = Math.round((data.avg_confidence || 0) * 100);
      var html = '<div class="confidence-bar-wrapper">' +
        '<div class="confidence-bar" style="width:' + pct + '%"></div>' +
        '</div>' +
        '<div class="confidence-label">' + pct + '% confidence — Iteration ' + (data.iteration || "?") + '/' + (data.max_iterations || "?") + '</div>';
      if (data.confidence_per_sub_question) {
        html += '<div class="sq-confidence-list">';
        for (var key in data.confidence_per_sub_question) {
          var val = Math.round(data.confidence_per_sub_question[key] * 100);
          html += '<div class="sq-confidence-item"><span class="sq-conf-label">' + escapeHtml(key) + '</span><span class="sq-conf-val">' + val + '%</span></div>';
        }
        html += '</div>';
      }
      if (data.remaining_gaps && data.remaining_gaps.length > 0) {
        html += '<div class="remaining-gaps"><strong>Remaining gaps:</strong> ' + escapeHtml(data.remaining_gaps.join(", ")) + '</div>';
      }
      confidenceDisplay.innerHTML = html;

      if (data.exploration_angles && data.exploration_angles.length > 0) {
        anglesPanel.hidden = false;
        anglesDisplay.innerHTML = "";
        for (var ea2 = 0; ea2 < data.exploration_angles.length; ea2++) {
          var angleDiv2 = document.createElement("div");
          angleDiv2.className = "angle-item";
          angleDiv2.textContent = data.exploration_angles[ea2];
          anglesDisplay.appendChild(angleDiv2);
        }
      }

      if (data.contradictions && data.contradictions.length > 0) {
        for (var ci = 0; ci < data.contradictions.length; ci++) {
          var cItem = document.createElement("div");
          cItem.className = "progress-item contradiction-item";
          cItem.textContent = "Contradiction: " + data.contradictions[ci].description;
          progressDiv.appendChild(cItem);
        }
      }

      // Mark completed sub-questions
      if (data.confidence_per_sub_question) {
        var sqItems = subQuestionsList.querySelectorAll(".sq-item");
        for (var j = 0; j < sqItems.length; j++) {
          var idx = sqItems[j].getAttribute("data-index");
          if (data.confidence_per_sub_question[idx] !== undefined && data.confidence_per_sub_question[idx] >= 0.8) {
            sqItems[j].classList.add("sq-done");
          }
        }
      }
    }

    if (msg === "Source credibility evaluated" && data) {
      evidenceQualityPanel.hidden = false;
      var evHtml = '<div class="evidence-count">Evidence pieces: <strong>' + (data.evidence_count || 0) + '</strong></div>';
      if (data.confidence_scores) {
        evHtml += '<div class="evidence-scores">';
        for (var s in data.confidence_scores) {
          var score = data.confidence_scores[s];
          var cls = score >= 0.7 ? "quality-high" : score >= 0.4 ? "quality-mid" : "quality-low";
          evHtml += '<div class="evidence-score-item ' + cls + '"><span>' + escapeHtml(s) + '</span><span>' + Math.round(score * 100) + '%</span></div>';
        }
        evHtml += '</div>';
      }
      evidenceQualityDisplay.innerHTML = evHtml;
    }

    if (msg === "Agents dispatched" && data) {
      if (data.agents && data.agents.length > 0) {
        anglesPanel.hidden = false;
        anglesDisplay.innerHTML = "";
        for (var a = 0; a < data.agents.length; a++) {
          var agentDiv = document.createElement("div");
          agentDiv.className = "angle-item";
          agentDiv.textContent = data.agents[a];
          anglesDisplay.appendChild(agentDiv);
        }
      }
    }

    if (msg === "Research complete" && data && data.confidence_scores) {
      confidencePanel.hidden = false;
      var finalHtml = '<div class="confidence-final"><strong>Final Confidence Scores</strong></div>';
      for (var fc in data.confidence_scores) {
        var fv = Math.round(data.confidence_scores[fc] * 100);
        finalHtml += '<div class="sq-confidence-item"><span class="sq-conf-label">' + escapeHtml(fc) + '</span><span class="sq-conf-val">' + fv + '%</span></div>';
      }
      confidenceDisplay.innerHTML += finalHtml;
    }
  }

  function renderStructuredResult(text) {
    var sections = ["Main Findings", "Evidence", "Contradictions", "Uncertainty", "Confidence"];
    var parts = [];
    var remaining = text;
    var foundAny = false;

    for (var i = 0; i < sections.length; i++) {
      var patterns = [
        "## " + sections[i],
        "**" + sections[i] + "**",
        sections[i] + ":"
      ];
      for (var p = 0; p < patterns.length; p++) {
        if (remaining.indexOf(patterns[p]) !== -1) {
          foundAny = true;
          break;
        }
      }
    }

    if (!foundAny) return;

    // Split by section headers
    var regex = new RegExp("(## (?:" + sections.join("|") + ")|\\*\\*(?:" + sections.join("|") + ")\\*\\*|(?:" + sections.join("|") + "):)", "g");
    var splitParts = remaining.split(regex);

    structuredResult.hidden = false;
    resultDiv.hidden = true;
    var html = "";

    if (splitParts[0] && splitParts[0].trim()) {
      html += '<div class="result-section-block"><div class="result-section-body">' + escapeHtml(splitParts[0].trim()) + '</div></div>';
    }

    for (var j = 1; j < splitParts.length; j += 2) {
      var header = splitParts[j] || "";
      var body = (splitParts[j + 1] || "").trim();
      var cleanHeader = header.replace(/^## /, "").replace(/^\*\*/, "").replace(/\*\*$/, "").replace(/:$/, "");
      var sectionClass = "section-" + cleanHeader.toLowerCase().replace(/\s+/g, "-");
      html += '<div class="result-section-block ' + sectionClass + '">' +
        '<h3 class="result-section-header">' + escapeHtml(cleanHeader) + '</h3>' +
        '<div class="result-section-body">' + escapeHtml(body) + '</div></div>';
    }

    structuredResult.innerHTML = html;
  }

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function done() {
    submitBtn.disabled = false;
    submitBtn.textContent = "Research";
    hideSpinner();
  }
});
