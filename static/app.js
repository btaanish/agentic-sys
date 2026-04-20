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

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var query = queryInput.value.trim();
    if (!query) return;

    // Reset UI
    errorDiv.hidden = true;
    errorDiv.textContent = "";
    progressSection.hidden = false;
    progressDiv.innerHTML = "";
    resultSection.hidden = true;
    resultDiv.textContent = "";
    submitBtn.disabled = true;
    submitBtn.textContent = "Researching\u2026";

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
    if (event.type === "status") {
      var item = document.createElement("div");
      item.className = "progress-item";
      item.textContent = event.message || JSON.stringify(event);
      progressDiv.appendChild(item);
      progressDiv.scrollTop = progressDiv.scrollHeight;
    } else if (event.type === "result") {
      resultSection.hidden = false;
      resultDiv.textContent = event.content || JSON.stringify(event);
    } else if (event.type === "error") {
      errorDiv.textContent = event.message || "Research failed";
      errorDiv.hidden = false;
    }
  }

  function done() {
    submitBtn.disabled = false;
    submitBtn.textContent = "Research";
  }
});
