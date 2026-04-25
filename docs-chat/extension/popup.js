const BACKEND = "http://localhost:8000";

const statusText = document.getElementById("status-text");
const spinner = document.getElementById("spinner");
const messagesEl = document.getElementById("messages");
const questionEl = document.getElementById("question");
const sendBtn = document.getElementById("send-btn");
const indexBtn = document.getElementById("index-btn");

// ── helpers ──────────────────────────────────────────────

function setStatus(text, loading = false) {
  statusText.textContent = text;
  spinner.classList.toggle("active", loading);
}

function addMessage(text, type, sources = []) {
  const div = document.createElement("div");
  div.className = `msg ${type}`;
  div.innerHTML = text.replace(/\n/g, "<br>");

  if (sources.length > 0) {
    const sourcesDiv = document.createElement("div");
    sourcesDiv.className = "sources";
    sourcesDiv.innerHTML =
      "<strong>Sources:</strong>" +
      sources
        .map(
          (s) =>
            `<a href="${s.url}" target="_blank" title="${s.url}">${
              s.title || s.url
            }</a>`
        )
        .join("");
    div.appendChild(sourcesDiv);
  }

  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function addThinking() {
  const div = document.createElement("div");
  div.className = "thinking";
  div.innerHTML = "<span></span><span></span><span></span>";
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

async function getCurrentTabUrl() {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      resolve(tabs[0]?.url || "");
    });
  });
}

// ── check if current site is already indexed ─────────────

async function checkIndexed(hostname) {
  try {
    const res = await fetch(`${BACKEND}/is-indexed?hostname=${encodeURIComponent(hostname)}`);
    if (!res.ok) return false;
    const data = await res.json();
    return data.indexed === true;
  } catch {
    return false;
  }
}

// ── on popup open: check index status ────────────────────

async function onPopupOpen() {
  const url = await getCurrentTabUrl();
  if (!url || url.startsWith("chrome://")) {
    setStatus("Navigate to a docs site to begin.");
    return;
  }

  const hostname = new URL(url).hostname;
  const alreadyIndexed = await checkIndexed(hostname);

  if (alreadyIndexed) {
    setStatus(`✅ ${hostname} is indexed — ask away!`);
    addMessage(`I already have **${hostname}** indexed. Ask me anything!`, "bot");
    indexBtn.textContent = "Re-index site";
  } else {
    setStatus(`Not indexed yet. Click "Index this site" to begin.`);
  }
}

onPopupOpen();

// ── index ─────────────────────────────────────────────────

indexBtn.addEventListener("click", async () => {
  const url = await getCurrentTabUrl();

  if (!url || url.startsWith("chrome://") || url.startsWith("chrome-extension://")) {
    setStatus("Navigate to a docs site first.");
    return;
  }

  const hostname = new URL(url).hostname;
  indexBtn.disabled = true;
  setStatus(`Indexing ${hostname}… this takes 1–2 min`, true);

  try {
    const res = await fetch(`${BACKEND}/crawl`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });

    if (!res.ok) throw new Error(`Server error: ${res.status}`);
    const data = await res.json();

    // Save indexed hostname to chrome storage
    chrome.storage.local.set({ indexedHostname: hostname });

    setStatus(`Indexed ${data.pages_indexed} pages from ${hostname}`);
    addMessage(
      `✅ Indexed ${data.pages_indexed} pages from ${hostname}. Ask me anything!`,
      "bot"
    );
    indexBtn.textContent = "Re-index site";
  } catch (err) {
    setStatus("Error — is the backend running?");
    addMessage(
      "❌ Could not connect to backend.\n\nMake sure you ran:\nuvicorn main:app --reload --port 8000",
      "bot error"
    );
  }

  indexBtn.disabled = false;
});

// ── query ─────────────────────────────────────────────────

async function sendQuestion() {
  const question = questionEl.value.trim();
  if (!question) return;

  addMessage(question, "user");
  questionEl.value = "";
  sendBtn.disabled = true;

  const thinkingEl = addThinking();
  setStatus("Thinking…", true);

  try {
    const res = await fetch(`${BACKEND}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });

    thinkingEl.remove();

    if (!res.ok) throw new Error(`Server error: ${res.status}`);
    const data = await res.json();

    addMessage(data.answer, "bot", data.sources);
    setStatus("Ready");
  } catch (err) {
    thinkingEl.remove();
    addMessage("❌ Error getting answer. Is the backend running?", "bot error");
    setStatus("Error");
  }

  sendBtn.disabled = false;
  questionEl.focus();
}

sendBtn.addEventListener("click", sendQuestion);

questionEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendQuestion();
  }
});

// ── clear Chroma when popup closes ───────────────────────

window.addEventListener("unload", () => {
  // Use sendBeacon so the request fires even as the popup closes
  navigator.sendBeacon(`${BACKEND}/clear`);
  chrome.storage.local.remove("indexedHostname");
});